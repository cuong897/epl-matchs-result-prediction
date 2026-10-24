"""One locked scoring round: generate probabilities before reading test labels."""
from datetime import datetime,timezone
import json
import importlib.metadata
from pathlib import Path
import numpy as np
import pandas as pd
from final_models import sha,feature_frame,predict_registered
from temperature_calibration import transform_temperature
from modeling import LABELS,evaluate,classification_metrics,per_match_log_loss,reliability_rows
from final_bootstrap import paired_intervals

ROOT=Path(__file__).resolve().parents[1]


def main():
    lock_path=ROOT/'research/final_lock.json';lock=json.loads(lock_path.read_text())
    for relative,digest in lock['files_sha256'].items():
        if sha(ROOT/relative)!=digest:raise ValueError(f'Locked artifact changed: {relative}')
    for name,digest in lock['code_sha256'].items():
        if sha(ROOT/'scripts'/name)!=digest:raise ValueError(f'Locked code changed: {name}')
    for name,version in lock['runtime'].items():
        if importlib.metadata.version(name)!=version:raise ValueError(f'Locked runtime changed: {name}')
    config=json.loads((ROOT/'research/final_evaluation_config.json').read_text())
    registry=json.loads((ROOT/'research/final_model_registry.json').read_text())
    temps=json.loads((ROOT/'reports/final_calibration/temperatures.json').read_text())
    frame=feature_frame(ROOT,'test')
    if len(frame)!=380 or set(frame.season)!={'2024-25'}:raise ValueError('Wrong test cohort')
    out=ROOT/'reports'/config['run_id']
    if out.exists():raise FileExistsError('Final scoring already started/completed; do not overwrite or tune')
    out.mkdir()
    def log(message):
        print(message,flush=True)
        with (out/'progress.log').open('a',encoding='utf-8') as stream:stream.write(message+'\n')
    started=datetime.now(timezone.utc).isoformat();records=[];probs={}
    for entry in registry:
        raw=predict_registered(ROOT,entry,frame)
        variants={'raw':raw}
        if entry['calibrate']:
            variants['temperature']=transform_temperature(raw,temps[entry['id']]['temperature'])
            if not np.array_equal(raw.argmax(axis=1),variants['temperature'].argmax(axis=1)):raise ValueError('Argmax changed')
        for variant,p in variants.items():
            key=entry['id']+'::'+variant;probs[key]=p
            part=frame[['match_id','season','match_date']].copy();part['model']=entry['id'];part['variant']=variant
            for j,label in enumerate(LABELS):part[f'p_{label}']=p[:,j]
            part['predicted_label']=np.asarray(LABELS)[p.argmax(axis=1)];records.append(part)
        log(f"Predicted frozen {entry['id']}; test labels not used for prediction")
    if len(probs)!=30:raise ValueError('Missing probability outputs')
    predictions=pd.concat(records,ignore_index=True)
    predictions.to_csv(out/'test_probabilities_before_labels.csv',index=False)
    # First target read in this scoring runner, AFTER all fixed probabilities saved.
    outcomes=pd.read_csv(ROOT/'data/curated/match_outcomes.csv',usecols=['match_id','result'])
    truth=frame[['match_id']].merge(outcomes,on='match_id',validate='one_to_one')
    if len(truth)!=380 or truth.result.isna().any():raise ValueError('Missing test labels')
    y=truth.result.to_numpy();metrics={key:evaluate(y,p) for key,p in probs.items()}
    always=classification_metrics(y,np.repeat('H',380))
    predictions.merge(truth,on='match_id',validate='many_to_one').to_csv(out/'test_predictions_scored.csv',index=False)
    pd.DataFrame([{'key':key,**{k:m[k] for k in ['accuracy','macro_f1','log_loss','brier_sum']}} for key,m in metrics.items()]).to_csv(out/'test_metrics.csv',index=False)
    reliability=[]
    for key,p in probs.items():reliability += [dict(key=key,**r) for r in reliability_rows(y,p,5)]
    pd.DataFrame(reliability).to_csv(out/'reliability_bins.csv',index=False)
    comparisons=[];bs=config['paired_bootstrap']
    for variant in ['raw','temperature']:
        for comparison in config['primary_feature_comparisons']:
            family=comparison['family'];model=f"common__{family}__{comparison['model_arm']}::{variant}"
            reference=f"common__{family}__{comparison['reference_arm']}::{variant}"
            delta=per_match_log_loss(y,probs[model])-per_match_log_loss(y,probs[reference])
            for block in bs['block_weeks']:
                intervals=paired_intervals(frame.match_date,delta,block,bs['replicates'],bs['seed'],6 if variant=='temperature' else 1)
                comparisons.append(dict(family=family,variant=variant,model_arm=comparison['model_arm'],reference_arm=comparison['reference_arm'],**intervals))
    reference=config['primary_practical_reference_chosen_before_test']
    result={'run_id':config['run_id'],'started_at_utc':started,'completed_at_utc':datetime.now(timezone.utc).isoformat(),
            'lock_sha256':sha(lock_path),'test_matches':380,'label_order':LABELS,'metrics':metrics,
            'always_home_classification_only':always,'paired_feature_comparisons':comparisons,
            'primary_practical_reference':reference,'test_class_counts':{label:int((y==label).sum()) for label in LABELS},
            'base_estimator_fit_in_test':False,'calibrator_fit_in_test':False,'test_probabilities_saved_before_label_join':True,
            'post_test_model_selection_or_tuning':False,'prediction_export_sha256':sha(out/'test_probabilities_before_labels.csv')}
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    log('Locked final scoring complete. No estimator/calibrator fit or post-test tuning.')
    log(json.dumps({'primary_reference_raw':metrics[reference+'::raw'],
                    'primary_reference_temperature':metrics[reference+'::temperature']},indent=2))


if __name__=='__main__':main()
