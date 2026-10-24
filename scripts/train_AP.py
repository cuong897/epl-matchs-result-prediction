"""Fair paired feature comparison: refit both arms on identical temporal cohort."""
from datetime import datetime,timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time

import joblib
import numpy as np
import pandas as pd

from modeling import (LABELS,evaluate,fit_checked,historical_frequencies,load_development,logistic_pipeline,
                      ordered_probabilities,paired_week_bootstrap,per_match_log_loss,reliability_rows,temporal_folds)
from tree_modeling import tree_pipeline,rank_candidates

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    config_path=ROOT/'research/AP_development_config.json'
    config=json.loads(config_path.read_text())
    if config['test_evaluation_enabled'] or config['posthoc_calibration_fit']:raise ValueError('No test/calibration allowed')
    lr=json.loads((ROOT/config['logistic_settings']).read_text())
    trees=json.loads((ROOT/config['tree_settings']).read_text())
    feature_report=json.loads((ROOT/'reports/player_proxy/feature_build.json').read_text())
    for path,digest in {**feature_report['input_sha256'],**feature_report['output_sha256']}.items():
        if sha(ROOT/path)!=digest:raise ValueError(f'Feature artifact changed: {path}')
    for name,digest in feature_report['code_sha256'].items():
        if sha(ROOT/'scripts'/name)!=digest:raise ValueError('Feature code changed')
    if not all(feature_report['tests'].values()):raise ValueError('Feature checks incomplete')
    a=json.loads((ROOT/'research/feature_columns_A.json').read_text())
    p=json.loads((ROOT/'research/feature_columns_P.json').read_text())
    frame=load_development(ROOT,a)
    frame=frame[frame.season.str[:4].astype(int).ge(int(config['first_training_season'][:4]))].copy()
    extra=pd.concat([pd.read_csv(ROOT/f'data/curated/features_P_{split}.csv') for split in ['train','validation']],ignore_index=True)
    if set(extra.columns)!={'match_id',*p} or set(extra.match_id)!=set(frame.match_id):raise ValueError('P allowlist/cohort mismatch')
    frame=frame.merge(extra,on='match_id',validate='one_to_one').sort_values(['match_date','match_id']).reset_index(drop=True)
    columns={'A_common':a,'A_plus_P':a+p}
    candidates={'logistic':[{'C':c} for c in lr['logistic_C_grid']],
                **{f:trees[f'{f}_candidates'] for f in ['random_forest','xgboost']}}
    if any(len(v)!=config['candidate_budget_per_family_per_arm'] for v in candidates.values()):raise ValueError('Unequal tuning budgets')
    def estimator(family,params):
        return logistic_pipeline(params['C'],lr) if family=='logistic' else tree_pipeline(family,params,trees)
    out=ROOT/'reports'/config['run_id'];models=ROOT/'models'/config['run_id']
    if out.exists() or models.exists():raise FileExistsError('Register a new run ID; existing runs are immutable')
    out.mkdir();models.mkdir()
    def log(message):
        print(message,flush=True)
        with (out/'progress.log').open('a',encoding='utf-8') as stream:stream.write(message+'\n')
    inputs=[config_path,ROOT/config['logistic_settings'],ROOT/config['tree_settings'],
            ROOT/'research/feature_columns_A.json',ROOT/'research/feature_columns_P.json',ROOT/'reports/player_proxy/feature_build.json',
            ROOT/'data/curated/matches.csv',ROOT/'data/curated/match_outcomes.csv']
    inputs += [ROOT/f'data/curated/features_{group}_{split}.csv' for group in ['A','P'] for split in ['train','validation']]
    manifest={'run_id':config['run_id'],'started_at_utc':datetime.now(timezone.utc).isoformat(),'config':config,
              'candidates':candidates,'feature_columns':columns,'input_sha256':{str(path.relative_to(ROOT)):sha(path) for path in inputs},
              'code_sha256':{name:sha(ROOT/'scripts'/name) for name in ['train_AP.py','modeling.py','tree_modeling.py','player_proxy_features.py']},
              'runtime':{name:importlib.metadata.version(name) for name in ['scikit-learn','xgboost','numpy','pandas','joblib']}}
    (out/'run_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    frame[['match_id','season','match_date','split']].to_csv(out/'common_cohort.csv',index=False)
    started=time.perf_counter();cv=[];folds=[]
    log('Device: local CPU; trees n_jobs=2. Both arms use identical training and validation matches.')
    for fold,(season,train,valid) in enumerate(temporal_folds(frame,config['walk_forward_validation_seasons'])):
        if len(train)!=config['expected_fold_training_rows'][fold] or len(valid)!=380:raise ValueError('Unexpected temporal fold')
        folds.append({'season':season,'train_rows':len(train),'validation_rows':len(valid),
                      'last_train_date':str(train.match_date.max().date()),'first_validation_date':str(valid.match_date.min().date())})
        for family in config['families']:
            for arm in config['arms']:
                for index,params in enumerate(candidates[family]):
                    model=fit_checked(estimator(family,params),train[columns[arm]],train.result)
                    metrics=evaluate(valid.result.to_numpy(),ordered_probabilities(model,valid[columns[arm]]))
                    cv.append({'family':family,'arm':arm,'candidate':index,'season':season,
                               **{k:metrics[k] for k in ['log_loss','brier_sum','accuracy','macro_f1']}})
                log(f'Walk-forward {season}: {family}/{arm}, 4 candidates complete ({len(train)} -> {len(valid)})')
    pd.DataFrame(cv).to_csv(out/'walk_forward_metrics.csv',index=False)
    rankings={};selected={}
    for family in config['families']:
        for arm in config['arms']:
            name=f'{family}__{arm}'
            ranks=rank_candidates([r for r in cv if r['family']==family and r['arm']==arm],config['walk_forward_validation_seasons'],4)
            rankings[name]=ranks;selected[name]=int(ranks[0]['candidate'])
    train=frame[frame['split'].eq('train')];valid=frame[frame['split'].eq('validation')]
    if len(train)!=config['expected_training_rows'] or len(valid)!=config['expected_validation_rows']:raise ValueError('Bad final splits')
    if set(valid.season)!={config['final_validation_season']}:raise ValueError('Bad validation season')
    fitted={};probs={};model_columns={}
    for family in config['families']:
        for arm in config['arms']:
            name=f'{family}__{arm}';model_columns[name]=columns[arm]
            fitted[name]=fit_checked(estimator(family,candidates[family][selected[name]]),train[columns[arm]],train.result)
            probs[name]=ordered_probabilities(fitted[name],valid[columns[arm]])
            log(f'Final fit {name}: candidate {selected[name]}; validation scored')
    probs['frequency_common']=historical_frequencies(train.result.to_numpy(),len(valid),1.)
    fitted['elo_common']=fit_checked(logistic_pipeline(1.,lr),train[['elo_diff']],train.result)
    model_columns['elo_common']=['elo_diff']
    probs['elo_common']=ordered_probabilities(fitted['elo_common'],valid[['elo_diff']])
    metrics={name:evaluate(valid.result.to_numpy(),prob) for name,prob in probs.items()}
    for name,model in fitted.items():joblib.dump(model,models/f'{name}.joblib')
    for arm in config['arms']:
        name=f'xgboost__{arm}'
        fitted[name].named_steps['classifier'].estimator_.save_model(models/f'{name}.ubj')
    joblib.dump({'models':fitted,'model_columns':model_columns,'label_order':LABELS,
                 'frequency_probabilities':probs['frequency_common'][0],'selected_candidates':selected},models/'bundle.joblib')
    predictions=[];reliability=[]
    for name,prob in probs.items():
        part=valid[['match_id','season','match_date','result']].copy();part['model']=name
        for j,label in enumerate(LABELS):part[f'p_{label}']=prob[:,j]
        part['predicted_label']=np.asarray(LABELS)[prob.argmax(axis=1)];predictions.append(part)
        reliability += [dict(model=name,**r) for r in reliability_rows(valid.result.to_numpy(),prob,5)]
    pd.concat(predictions,ignore_index=True).to_csv(out/'validation_predictions.csv',index=False)
    pd.DataFrame(reliability).to_csv(out/'reliability_bins.csv',index=False)
    pd.DataFrame([{'model':name,**{k:m[k] for k in ['accuracy','macro_f1','log_loss','brier_sum']}} for name,m in metrics.items()]).to_csv(out/'validation_metrics.csv',index=False)
    uncertainty=[];importance=[]
    for family in config['families']:
        name=f'{family}__A_plus_P';reference=f'{family}__A_common'
        delta=per_match_log_loss(valid.result.to_numpy(),probs[name])-per_match_log_loss(valid.result.to_numpy(),probs[reference])
        for block in config['paired_bootstrap_block_weeks']:
            item=paired_week_bootstrap(valid.match_date,delta,block,config['paired_bootstrap_replicates'],config['random_seed'])
            item['delta_log_loss_AP_minus_A']=item.pop('delta_log_loss_LR_minus_baseline');item.pop('negative_favors_LR')
            uncertainty.append(dict(family=family,**item))
        rng=np.random.default_rng(config['random_seed']);X=valid[columns['A_plus_P']].reset_index(drop=True)
        months=valid.match_date.dt.to_period('M').to_numpy();increases=[]
        for repeat in range(config['group_permutation_repeats']):
            order=np.arange(len(X))
            for month in np.unique(months):
                ids=np.flatnonzero(months==month);order[ids]=rng.permutation(ids)
            changed=X.copy();changed[p]=X.iloc[order][p].to_numpy()
            increases.append(float(per_match_log_loss(valid.result.to_numpy(),ordered_probabilities(fitted[name],changed)).mean()-metrics[name]['log_loss']))
        importance.append({'family':family,'group':'all_12_P_features','mean_increase_log_loss':float(np.mean(increases)),
                           'repeat_std':float(np.std(increases,ddof=1)),'repeats':len(increases)})
    result={'run_id':config['run_id'],'completed_at_utc':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':time.perf_counter()-started,
            'folds':folds,'candidate_rankings':rankings,'selected_candidates':selected,'validation_metrics':metrics,
            'paired_uncertainty':uncertainty,'P_group_permutation':importance,'label_order':LABELS,
            'parameter_selection_used_final_validation':False,'posthoc_calibration_fitted':False,
            'test_feature_matrix_loaded':False,'test_predictions_generated':False,'test_metrics_computed':False}
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    log(json.dumps({n:{k:m[k] for k in ['accuracy','macro_f1','log_loss','brier_sum']} for n,m in metrics.items()},indent=2))


if __name__=='__main__':main()
