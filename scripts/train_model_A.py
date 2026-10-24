"""Registered baseline/LR development. Does not load test feature matrix."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path
from datetime import datetime,timezone

import joblib
import numpy as np
import pandas as pd

from modeling import (LABELS,choose_C,classification_metrics,evaluate,fit_checked,historical_frequencies,
    load_development,logistic_pipeline,ordered_probabilities,paired_week_bootstrap,per_match_log_loss,
    reliability_rows,temporal_folds)

ROOT=Path(__file__).resolve().parents[1]


def flat_metrics(name,metrics,**extra):
    return dict(model=name,**extra,**{k:metrics.get(k) for k in ['n','log_loss','brier_sum','accuracy','macro_f1']})


def permutation_groups(columns):
    groups={
        'elo':[c for c in columns if 'elo' in c],
        'recent_form':[c for c in columns if 'form' in c or 'history' in c],
        'venue_form':[c for c in columns if 'venue' in c],
        'season_progress':[c for c in columns if '_season_' in c and 'membership' not in c],
        'rest':[c for c in columns if 'days_since' in c or c=='rest_days_diff'],
        'promotion':[c for c in columns if 'promoted' in c or 'membership' in c],
        'h2h':[c for c in columns if c.startswith('h2h_')]}
    assigned=[c for group in groups.values() for c in group]
    if len(assigned)!=len(set(assigned)) or set(assigned)!=set(columns):raise ValueError('Permutation groups must partition features')
    return groups


def main():
    config_path=ROOT/'research/model_A_development_config.json'
    config=json.loads(config_path.read_text(encoding='utf-8'))
    if config['test_evaluation_enabled']:raise ValueError('This runner never evaluates test')
    columns=json.loads((ROOT/'research/feature_columns_A.json').read_text(encoding='utf-8'))
    frame=load_development(ROOT,columns)
    output=ROOT/'reports/model_A_development';output.mkdir(parents=True,exist_ok=True)
    models=ROOT/'models/A_dev_v1';models.mkdir(parents=True,exist_ok=True)
    cv=[];fold_manifest=[]
    for season,train,valid in temporal_folds(frame,config['walk_forward_validation_seasons']):
        y=train.result.to_numpy();truth=valid.result.to_numpy()
        fold_manifest.append({'validation_season':season,'training_rows':len(train),'validation_rows':len(valid),
            'training_last_date':str(train.match_date.max().date()),'validation_first_date':str(valid.match_date.min().date())})
        p=historical_frequencies(y,len(valid),config['frequency_smoothing_alpha'])
        cv.append(flat_metrics('frequency',evaluate(truth,p),season=season,C=None))
        cv.append(flat_metrics('always_home',classification_metrics(truth,np.repeat('H',len(valid))),season=season,C=None))
        elo=fit_checked(logistic_pipeline(1.,config),train[['elo_diff']],y)
        cv.append(flat_metrics('elo_threeway',evaluate(truth,ordered_probabilities(elo,valid[['elo_diff']])),season=season,C=1.))
        for C in config['logistic_C_grid']:
            model=fit_checked(logistic_pipeline(C,config),train[columns],y)
            cv.append(flat_metrics('logistic_A',evaluate(truth,ordered_probabilities(model,valid[columns])),season=season,C=C))
        print(f'Walk-forward {season}: completed {len(train)} -> {len(valid)}',flush=True)
    selected_C,ranking=choose_C(cv)
    # Selection complete using training seasons only; now reveal development validation.
    train=frame[frame['split'].eq('train')].copy();valid=frame[frame['split'].eq('validation')].copy()
    if len(train)!=3040 or len(valid)!=380:raise ValueError('Unexpected final development split sizes')
    if train.match_date.max()>=valid.match_date.min():raise ValueError('Final split is not chronological')
    fitted={
        'elo_threeway':fit_checked(logistic_pipeline(1.,config),train[['elo_diff']],train.result),
        'logistic_A':fit_checked(logistic_pipeline(selected_C,config),train[columns],train.result)}
    predictions={
        'frequency':historical_frequencies(train.result.to_numpy(),len(valid),config['frequency_smoothing_alpha']),
        'elo_threeway':ordered_probabilities(fitted['elo_threeway'],valid[['elo_diff']]),
        'logistic_A':ordered_probabilities(fitted['logistic_A'],valid[columns])}
    metrics={name:evaluate(valid.result.to_numpy(),p) for name,p in predictions.items()}
    metrics['always_home']=classification_metrics(valid.result.to_numpy(),np.repeat('H',len(valid)))
    for name,model in fitted.items():joblib.dump(model,models/f'{name}.joblib')
    probability_records=[]
    for name,p in predictions.items():
        part=valid[['match_id','season','match_date','result']].copy();part['model']=name
        for j,label in enumerate(LABELS):part[f'p_{label}']=p[:,j]
        part['predicted_label']=np.asarray(LABELS)[p.argmax(axis=1)]
        probability_records.append(part)
    pd.concat(probability_records,ignore_index=True).to_csv(output/'validation_predictions.csv',index=False)
    pd.DataFrame(cv).to_csv(output/'walk_forward_metrics.csv',index=False)
    pd.DataFrame([flat_metrics(name,m) for name,m in metrics.items()]).to_csv(output/'validation_metrics.csv',index=False)
    reliability=[]
    for name,p in predictions.items():
        reliability.extend([dict(model=name,**row) for row in reliability_rows(valid.result.to_numpy(),p,config['reliability_bins_per_class'])])
    pd.DataFrame(reliability).to_csv(output/'reliability_bins.csv',index=False)
    # Uncertainty: paired same matches; no extra training and no test data.
    uncertainty=[]
    lr_loss=per_match_log_loss(valid.result.to_numpy(),predictions['logistic_A'])
    for name in ['frequency','elo_threeway']:
        delta=lr_loss-per_match_log_loss(valid.result.to_numpy(),predictions[name])
        for block in config['paired_bootstrap_block_weeks']:
            uncertainty.append(dict(comparator=name,**paired_week_bootstrap(valid.match_date,delta,block,
                config['paired_bootstrap_replicates'],config['random_seed'])))
    # Descriptive validation importance; never used to refit or select this run.
    rng=np.random.default_rng(config['random_seed']);base=metrics['logistic_A']['log_loss'];permutation=[]
    months=valid.match_date.dt.to_period('M').to_numpy()
    X=valid[columns].reset_index(drop=True)
    for name,group in permutation_groups(columns).items():
        deltas=[]
        for repeat in range(config['group_permutation_repeats']):
            order=np.arange(len(X))
            for month in np.unique(months):
                ix=np.flatnonzero(months==month);order[ix]=rng.permutation(ix)
            perturbed=X.copy();perturbed[group]=X.iloc[order][group].to_numpy()
            loss=per_match_log_loss(valid.result.to_numpy(),ordered_probabilities(fitted['logistic_A'],perturbed)).mean()
            deltas.append(float(loss-base))
        permutation.append({'group':name,'features':group,'mean_increase_log_loss':float(np.mean(deltas)),
                            'repeat_std':float(np.std(deltas,ddof=1)),'repeats':len(deltas)})
    pd.DataFrame(permutation).to_csv(output/'group_permutation_importance.csv',index=False)
    clf=fitted['logistic_A'].named_steps['classifier']
    names=fitted['logistic_A'].named_steps['imputer'].get_feature_names_out(columns)
    coefs=pd.DataFrame(clf.coef_.T,index=names,columns=clf.classes_).rename_axis('transformed_feature')
    coefs[LABELS].to_csv(output/'standardized_coefficients.csv')
    inputs=[ROOT/'data/curated/features_A_train.csv',ROOT/'data/curated/features_A_validation.csv',
            ROOT/'data/curated/matches.csv',ROOT/'data/curated/match_outcomes.csv',config_path,
            ROOT/'research/feature_columns_A.json',ROOT/'research/team_feature_config.json']
    summary={'run_id':config['run_id'],'completed_at_utc':datetime.now(timezone.utc).isoformat(),
             'validation_season':'2023-24','label_order':LABELS,'selected_logistic_C':selected_C,
             'C_ranking_training_folds':ranking,'folds':fold_manifest,'validation_metrics':metrics,
             'paired_uncertainty_validation':uncertainty,'permutation_groups_validation':permutation,
             'probability_models_calibrated_posthoc':False,'validation_used_for_C_selection':False,
             'test_feature_matrix_loaded':False,'test_predictions_generated':False,'test_metrics_computed':False,
             'fitted_estimators_final':2,'warmup_used_for_estimator_fit':False,
             'convergence_warnings':0,'runtime':{n:importlib.metadata.version(n) for n in ['scikit-learn','numpy','pandas','scipy','joblib']},
             'input_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
             'code_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'scripts/modeling.py']}}
    (output/'results.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    joblib.dump({'models':fitted,'feature_columns':columns,'label_order':LABELS,'selected_C':selected_C,
                 'frequency_probabilities':predictions['frequency'][0],'feature_version':config['feature_version']},models/'bundle.joblib')
    print(json.dumps({'selected_C':selected_C,'validation_metrics':metrics},indent=2),flush=True)


if __name__=='__main__':main()
