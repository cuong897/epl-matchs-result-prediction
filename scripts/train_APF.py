"""One registered performance proxy extension; reuses frozen A/P comparators."""
from datetime import datetime,timezone
import importlib.metadata
import json
from pathlib import Path
import time

import joblib
import numpy as np
import pandas as pd

from apf_modeling import sha,load_apf,frozen_probabilities
from modeling import (LABELS,evaluate,fit_checked,logistic_pipeline,ordered_probabilities,paired_week_bootstrap,
                      per_match_log_loss,reliability_rows,temporal_folds)
from tree_modeling import tree_pipeline,rank_candidates

ROOT=Path(__file__).resolve().parents[1]


def main():
    config_path=ROOT/'research/APF_development_config.json'
    config=json.loads(config_path.read_text())
    if config['test_evaluation_enabled'] or config['posthoc_calibration_fit']:raise ValueError('No test/calibration in this runner')
    frame,columns,old_manifest,old_result,f_report=load_apf(ROOT,config)
    previous=ROOT/'reports'/config['frozen_comparator_run']
    lr=json.loads((ROOT/old_manifest['config']['logistic_settings']).read_text())
    trees=json.loads((ROOT/old_manifest['config']['tree_settings']).read_text())
    candidates=old_manifest['candidates']
    if any(len(candidates[f])!=4 for f in config['families']):raise ValueError('Tuning budget changed')
    arm=config['new_arm'];used=columns[arm];f_columns=used[52:]
    def estimator(family,index):
        params=candidates[family][index]
        return logistic_pipeline(params['C'],lr) if family=='logistic' else tree_pipeline(family,params,trees)
    out=ROOT/'reports'/config['run_id'];model_dir=ROOT/'models'/config['run_id']
    if out.exists() or model_dir.exists():raise FileExistsError('Do not overwrite a registered run')
    out.mkdir();model_dir.mkdir()
    def log(message):
        print(message,flush=True)
        with (out/'progress.log').open('a',encoding='utf-8') as stream:stream.write(message+'\n')
    inputs=[config_path,ROOT/'research/player_performance_config.json',ROOT/'research/feature_columns_F.json',
            ROOT/'reports/player_performance/feature_build.json',previous/'run_manifest.json',previous/'results.json',
            previous/'common_cohort.csv',previous/'validation_predictions.csv',
            ROOT/old_manifest['config']['logistic_settings'],ROOT/old_manifest['config']['tree_settings']]
    manifest={'run_id':config['run_id'],'started_at_utc':datetime.now(timezone.utc).isoformat(),
              'config':config,'candidates':candidates,'feature_columns':columns,
              'input_sha256':{str(x.relative_to(ROOT)):sha(x) for x in inputs},
              'frozen_AP_input_sha256':old_manifest['input_sha256'],
              'F_input_output_sha256':{**f_report['input_sha256'],**f_report['output_sha256']},
              'code_sha256':{name:sha(ROOT/'scripts'/name) for name in ['train_APF.py','apf_modeling.py','modeling.py','tree_modeling.py','player_proxy_features.py','player_performance_features.py']},
              'runtime':{name:importlib.metadata.version(name) for name in ['scikit-learn','xgboost','numpy','pandas','joblib']}}
    (out/'run_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    frame[['match_id','season','match_date','split']].to_csv(out/'common_cohort.csv',index=False)
    started=time.perf_counter();cv=[];folds=[]
    log('Device: local CPU; trees n_jobs=2; A and AP comparators frozen from AP_dev_v1.')
    for fold,(season,train,valid) in enumerate(temporal_folds(frame,config['walk_forward_validation_seasons'])):
        if len(train)!=config['expected_fold_training_rows'][fold] or len(valid)!=380:raise ValueError('Unexpected fold cohort')
        folds.append({'season':season,'training_rows':len(train),'validation_rows':len(valid),
                      'last_train_date':str(train.match_date.max().date()),'first_validation_date':str(valid.match_date.min().date())})
        for family in config['families']:
            for index in range(4):
                model=fit_checked(estimator(family,index),train[used],train.result)
                m=evaluate(valid.result.to_numpy(),ordered_probabilities(model,valid[used]))
                cv.append({'family':family,'arm':arm,'candidate':index,'season':season,
                           **{k:m[k] for k in ['log_loss','brier_sum','accuracy','macro_f1']}})
            log(f'Walk-forward {season}: {family}/{arm}, 4 candidates ({len(train)} -> {len(valid)}) complete')
    pd.DataFrame(cv).to_csv(out/'walk_forward_metrics.csv',index=False)
    ranks={f:rank_candidates([r for r in cv if r['family']==f],config['walk_forward_validation_seasons'],4) for f in config['families']}
    selected={f:int(rows[0]['candidate']) for f,rows in ranks.items()}
    train=frame[frame['split'].eq('train')];valid=frame[frame['split'].eq('validation')]
    if len(train)!=1520 or len(valid)!=380 or set(valid.season)!={'2023-24'}:raise ValueError('Bad final cohort')
    probs=frozen_probabilities(valid,pd.read_csv(previous/'validation_predictions.csv'),old_result)
    fitted={}
    for family in config['families']:
        name=f'{family}__{arm}'
        fitted[name]=fit_checked(estimator(family,selected[family]),train[used],train.result)
        probs[name]=ordered_probabilities(fitted[name],valid[used])
        joblib.dump(fitted[name],model_dir/f'{name}.joblib')
        log(f'Final {name}: candidate {selected[family]}, validation scored')
    fitted[f'xgboost__{arm}'].named_steps['classifier'].estimator_.save_model(model_dir/'xgboost_native.ubj')
    joblib.dump({'models':fitted,'feature_columns':used,'label_order':LABELS,'selected_candidates':selected},model_dir/'bundle.joblib')
    metrics={name:evaluate(valid.result.to_numpy(),p) for name,p in probs.items()}
    exports=[];reliability=[]
    for name,p in probs.items():
        part=valid[['match_id','season','match_date','result']].copy();part['model']=name
        for j,label in enumerate(LABELS):part[f'p_{label}']=p[:,j]
        part['predicted_label']=np.asarray(LABELS)[p.argmax(axis=1)];exports.append(part)
        reliability += [dict(model=name,**r) for r in reliability_rows(valid.result.to_numpy(),p,5)]
    pd.concat(exports,ignore_index=True).to_csv(out/'validation_predictions.csv',index=False)
    pd.DataFrame([{'model':n,**{k:m[k] for k in ['log_loss','brier_sum','accuracy','macro_f1']}} for n,m in metrics.items()]).to_csv(out/'validation_metrics.csv',index=False)
    pd.DataFrame(reliability).to_csv(out/'reliability_bins.csv',index=False)
    uncertainty=[];importance=[]
    for family in config['families']:
        name=f'{family}__{arm}'
        for reference_arm in config['comparator_arms']:
            reference=f'{family}__{reference_arm}'
            delta=per_match_log_loss(valid.result.to_numpy(),probs[name])-per_match_log_loss(valid.result.to_numpy(),probs[reference])
            for block in config['paired_bootstrap_block_weeks']:
                item=paired_week_bootstrap(valid.match_date,delta,block,config['paired_bootstrap_replicates'],config['random_seed'])
                item['delta_log_loss_APF_minus_reference']=item.pop('delta_log_loss_LR_minus_baseline');item.pop('negative_favors_LR')
                uncertainty.append(dict(family=family,reference_arm=reference_arm,**item))
        rng=np.random.default_rng(config['random_seed']);X=valid[used].reset_index(drop=True)
        months=valid.match_date.dt.to_period('M').to_numpy();increases=[]
        for repeat in range(config['group_permutation_repeats']):
            order=np.arange(len(X))
            for month in np.unique(months):
                ids=np.flatnonzero(months==month);order[ids]=rng.permutation(ids)
            changed=X.copy();changed[f_columns]=X.iloc[order][f_columns].to_numpy()
            increases.append(float(per_match_log_loss(valid.result.to_numpy(),ordered_probabilities(fitted[name],changed)).mean()-metrics[name]['log_loss']))
        importance.append({'family':family,'group':'all_8_F_features','mean_increase_log_loss':float(np.mean(increases)),
                           'repeat_std':float(np.std(increases,ddof=1)),'repeats':10})
    result={'run_id':config['run_id'],'completed_at_utc':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':time.perf_counter()-started,
            'folds':folds,'candidate_rankings':ranks,'selected_candidates':selected,'validation_metrics':metrics,
            'paired_uncertainty':uncertainty,'F_group_permutation':importance,'new_CV_fits':36,'new_final_estimators':3,
            'frozen_comparator_models':list(old_result['validation_metrics']),'label_order':LABELS,
            'parameter_selection_used_final_validation':False,'posthoc_calibration_fitted':False,
            'test_feature_matrix_loaded':False,'test_predictions_generated':False,'test_metrics_computed':False}
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    log(json.dumps({n:{k:metrics[n][k] for k in ['log_loss','brier_sum','accuracy','macro_f1']} for n in fitted},indent=2))


if __name__=='__main__':main()
