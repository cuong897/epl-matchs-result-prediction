"""Registered RF/XGBoost comparison; never loads the test feature matrix."""
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time

import joblib
import numpy as np
import pandas as pd

from modeling import (LABELS, evaluate, load_development, ordered_probabilities,
                      paired_week_bootstrap, per_match_log_loss, reliability_rows, temporal_folds)
from train_model_A import flat_metrics, permutation_groups
from tree_modeling import rank_candidates, tree_pipeline

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    config_path = ROOT/'research/model_A_tree_config.json'
    config = json.loads(config_path.read_text(encoding='utf-8'))
    if config['test_evaluation_enabled'] or config['posthoc_calibration_fit'] or config['early_stopping']:
        raise ValueError('This runner forbids test scoring, calibration and early stopping')
    out = ROOT/'reports'/config['run_id']
    model_dir = ROOT/'models'/config['run_id']
    if out.exists() or model_dir.exists():
        raise FileExistsError('Run directory already exists; preserve it and register a new run ID')
    previous_path = ROOT/config['previous_run']
    previous = json.loads(previous_path.read_text(encoding='utf-8'))
    for relative, expected in previous['input_sha256'].items():
        if sha(ROOT/relative) != expected:raise ValueError(f'Previous input changed: {relative}')
    for name, expected in previous['code_sha256'].items():
        if sha(ROOT/'scripts'/name) != expected:raise ValueError(f'Previous code changed: {name}')
    columns = json.loads((ROOT/'research/feature_columns_A.json').read_text())
    frame = load_development(ROOT, columns)
    out.mkdir(parents=True)
    model_dir.mkdir(parents=True)
    # Persist exact configuration + hashes BEFORE any estimator is fitted.
    manifest = {'run_id':config['run_id'], 'started_at_utc':datetime.now(timezone.utc).isoformat(),
                'config':config, 'config_sha256':sha(config_path),
                'input_sha256':previous['input_sha256'],
                'previous_results_sha256':sha(previous_path),
                'previous_predictions_sha256':sha(previous_path.parent/'validation_predictions.csv'),
                'code_sha256':{name:sha(ROOT/'scripts'/name) for name in
                               ['train_model_A_trees.py','tree_modeling.py','modeling.py','train_model_A.py']},
                'runtime':{p:importlib.metadata.version(p) for p in ['scikit-learn','xgboost','numpy','pandas','scipy','joblib']}}
    (out/'run_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    cv = []
    fold_manifest = []
    started = time.perf_counter()
    for season, train, valid in temporal_folds(frame,config['walk_forward_validation_seasons']):
        fold_manifest.append({'season':season,'train_rows':len(train),'valid_rows':len(valid),
                              'last_train_date':str(train.match_date.max().date()),
                              'first_valid_date':str(valid.match_date.min().date())})
        for family in ['random_forest','xgboost']:
            for candidate, params in enumerate(config[f'{family}_candidates']):
                tick = time.perf_counter()
                model = tree_pipeline(family,params,config).fit(train[columns],train.result)
                metric = evaluate(valid.result.to_numpy(),ordered_probabilities(model,valid[columns]))
                cv.append(flat_metrics(family,metric,season=season,candidate=candidate,
                                       elapsed_seconds=time.perf_counter()-tick))
            print(f'Walk-forward {season}: {family} 4 candidates complete',flush=True)
    pd.DataFrame(cv).to_csv(out/'walk_forward_metrics.csv',index=False)
    rankings = {family:rank_candidates([r for r in cv if r['model']==family],
                config['walk_forward_validation_seasons'],len(config[f'{family}_candidates']))
                for family in ['random_forest','xgboost']}
    selected = {family:int(rows[0]['candidate']) for family,rows in rankings.items()}
    # No validation score is used for the choices above.
    train = frame[frame['split'].eq('train')].copy()
    valid = frame[frame['split'].eq('validation')].copy()
    if len(train)!=3040 or len(valid)!=380 or set(valid.season)!={config['final_validation_season']}:
        raise ValueError('Unexpected development splits')
    if train.match_date.max()>=valid.match_date.min():raise ValueError('Invalid chronology')
    probabilities = {}
    old_predictions = pd.read_csv(previous_path.parent/'validation_predictions.csv')
    for family in ['frequency','elo_threeway','logistic_A']:
        part = old_predictions[old_predictions.model.eq(family)]
        if len(part)!=len(valid) or part.match_id.duplicated().any() or set(part.match_id)!=set(valid.match_id):
            raise ValueError('Baseline comparison cohort mismatch')
        part = part.set_index('match_id').loc[valid.match_id]
        if part.result.tolist()!=valid.result.tolist():raise ValueError('Comparison label mismatch')
        probabilities[family] = part[['p_H','p_D','p_A']].to_numpy()
        score = evaluate(valid.result.to_numpy(),probabilities[family])
        for key in ['log_loss','brier_sum','accuracy','macro_f1']:
            np.testing.assert_allclose(score[key],previous['validation_metrics'][family][key],atol=1e-12,rtol=0)
    fitted = {}
    for family in ['random_forest','xgboost']:
        params = config[f'{family}_candidates'][selected[family]]
        fitted[family] = tree_pipeline(family,params,config).fit(train[columns],train.result)
        probabilities[family] = ordered_probabilities(fitted[family],valid[columns])
        joblib.dump(fitted[family],model_dir/f'{family}.joblib')
        print(f'Final {family}: candidate {selected[family]}, validation scored',flush=True)
    fitted['xgboost'].named_steps['classifier'].estimator_.save_model(model_dir/'xgboost_native.ubj')
    joblib.dump({'models':fitted,'feature_columns':columns,'label_order':LABELS,
                 'feature_version':config['feature_version'],'selected_candidates':selected},model_dir/'bundle.joblib')
    metrics = {name:evaluate(valid.result.to_numpy(),p) for name,p in probabilities.items()}
    metrics['always_home'] = previous['validation_metrics']['always_home']
    prediction_records = []
    reliability = []
    for name,p in probabilities.items():
        part = valid[['match_id','season','match_date','result']].copy()
        part['model'] = name
        for j,label in enumerate(LABELS):part[f'p_{label}'] = p[:,j]
        part['predicted_label'] = np.asarray(LABELS)[p.argmax(axis=1)]
        prediction_records.append(part)
        reliability += [dict(model=name,**r) for r in reliability_rows(valid.result.to_numpy(),p,config['reliability_bins_per_class'])]
    pd.concat(prediction_records,ignore_index=True).to_csv(out/'validation_predictions.csv',index=False)
    pd.DataFrame([flat_metrics(n,m) for n,m in metrics.items()]).to_csv(out/'validation_metrics.csv',index=False)
    pd.DataFrame(reliability).to_csv(out/'reliability_bins.csv',index=False)
    uncertainty = []
    for family in ['random_forest','xgboost']:
        for reference in ['elo_threeway','logistic_A']:
            delta = per_match_log_loss(valid.result.to_numpy(),probabilities[family])-per_match_log_loss(valid.result.to_numpy(),probabilities[reference])
            for block in config['paired_bootstrap_block_weeks']:
                item = paired_week_bootstrap(valid.match_date,delta,block,config['paired_bootstrap_replicates'],config['random_seed'])
                item['delta_log_loss_model_minus_reference'] = item.pop('delta_log_loss_LR_minus_baseline')
                item.pop('negative_favors_LR')
                uncertainty.append(dict(model=family,reference=reference,negative_favors_model=True,**item))
    importance = []
    X = valid[columns].reset_index(drop=True)
    months = valid.match_date.dt.to_period('M').to_numpy()
    for family in ['random_forest','xgboost']:
        rng = np.random.default_rng(config['random_seed'])
        for group,features in permutation_groups(columns).items():
            increases = []
            for repeat in range(config['group_permutation_repeats']):
                order = np.arange(len(X))
                for month in np.unique(months):
                    ix = np.flatnonzero(months==month)
                    order[ix] = rng.permutation(ix)
                changed = X.copy()
                changed[features] = X.iloc[order][features].to_numpy()
                loss = per_match_log_loss(valid.result.to_numpy(),ordered_probabilities(fitted[family],changed)).mean()
                increases.append(float(loss-metrics[family]['log_loss']))
            importance.append({'model':family,'group':group,'mean_increase_log_loss':float(np.mean(increases)),
                               'repeat_std':float(np.std(increases,ddof=1)),'repeats':len(increases)})
        print(f'Diagnostics {family}: permutation complete',flush=True)
    pd.DataFrame(importance).to_csv(out/'group_permutation_importance.csv',index=False)
    result = {'run_id':config['run_id'],'completed_at_utc':datetime.now(timezone.utc).isoformat(),
              'elapsed_seconds':time.perf_counter()-started,'folds':fold_manifest,'candidate_rankings':rankings,
              'selected_candidates':{name:{'index':i,'parameters':config[f'{name}_candidates'][i]} for name,i in selected.items()},
              'validation_metrics':metrics,'paired_uncertainty_validation':uncertainty,
              'permutation_groups_validation':importance,'validation_used_for_parameter_selection':False,
              'posthoc_calibration_fitted':False,'test_feature_matrix_loaded':False,
              'test_predictions_generated':False,'test_metrics_computed':False,'label_order':LABELS}
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'selected':result['selected_candidates'],
                      'metrics':{n:{k:m[k] for k in ['accuracy','macro_f1','log_loss','brier_sum']} for n,m in metrics.items() if n!='always_home'}},indent=2))


if __name__=='__main__':main()
