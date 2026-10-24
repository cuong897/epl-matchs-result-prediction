"""Load one common cohort and verify frozen A/P comparators before F scoring."""
import hashlib
import json
import numpy as np
import pandas as pd
from modeling import evaluate,load_development


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def load_apf(root,config):
    previous=root/'reports'/config['frozen_comparator_run']
    old_manifest=json.loads((previous/'run_manifest.json').read_text())
    old_result=json.loads((previous/'results.json').read_text())
    f_report=json.loads((root/'reports/player_performance/feature_build.json').read_text())
    for relative,digest in old_manifest['input_sha256'].items():
        if sha(root/relative)!=digest:raise ValueError(f'Frozen A/P input changed: {relative}')
    for name,digest in old_manifest['code_sha256'].items():
        if sha(root/'scripts'/name)!=digest:raise ValueError('Frozen A/P training code changed')
    for relative,digest in {**f_report['input_sha256'],**f_report['output_sha256']}.items():
        if sha(root/relative)!=digest:raise ValueError(f'F input/output changed: {relative}')
    for name,digest in f_report['code_sha256'].items():
        if sha(root/'scripts'/name)!=digest:raise ValueError('F feature code changed')
    if not all(f_report['tests'].values()):raise ValueError('F temporal checks incomplete')
    a=old_manifest['feature_columns']['A_common']
    ap=old_manifest['feature_columns']['A_plus_P']
    f=json.loads((root/'research/feature_columns_F.json').read_text())
    p=ap[len(a):]
    if len(a)!=40 or len(p)!=12 or len(f)!=8 or ap[:len(a)]!=a:raise ValueError('Unexpected feature design')
    frame=load_development(root,a)
    frame=frame[frame.season.str[:4].astype(int).ge(int(config['first_training_season'][:4]))].copy()
    for group,columns in [('P',p),('F',f)]:
        extra=pd.concat([pd.read_csv(root/f'data/curated/features_{group}_{split}.csv') for split in ['train','validation']],ignore_index=True)
        if set(extra.columns)!={'match_id',*columns} or set(extra.match_id)!=set(frame.match_id):raise ValueError('Feature cohort/allowlist mismatch')
        frame=frame.merge(extra,on='match_id',validate='one_to_one')
    frame=frame.sort_values(['match_date','match_id']).reset_index(drop=True)
    cohort=pd.read_csv(previous/'common_cohort.csv',parse_dates=['match_date'])
    pd.testing.assert_frame_equal(frame[['match_id','season','match_date','split']],cohort)
    if frame['split'].value_counts().to_dict()!={'train':1520,'validation':380}:raise ValueError('Bad common splits')
    return frame,{'A_common':a,'A_plus_P':ap,config['new_arm']:ap+f},old_manifest,old_result,f_report


def frozen_probabilities(valid,saved,result):
    if saved.duplicated(['model','match_id']).any():raise ValueError('Duplicate frozen prediction')
    if set(saved.model)!=set(result['validation_metrics']):raise ValueError('Missing frozen model')
    probabilities={}
    for name,expected in result['validation_metrics'].items():
        part=saved[saved.model.eq(name)]
        if len(part)!=len(valid) or set(part.match_id)!=set(valid.match_id):raise ValueError('Frozen comparison cohort differs')
        part=part.set_index('match_id').loc[valid.match_id]
        if part.result.tolist()!=valid.result.tolist():raise ValueError('Frozen label mismatch')
        if set(part.season)!={'2023-24'}:raise ValueError('Frozen predictions include a different season')
        prob=part[['p_H','p_D','p_A']].to_numpy()
        actual=evaluate(valid.result.to_numpy(),prob)
        for key in ['accuracy','macro_f1','log_loss','brier_sum']:
            np.testing.assert_allclose(actual[key],expected[key],atol=1e-12,rtol=0)
        if actual['per_class']!=expected['per_class']:raise ValueError('Frozen per-class metrics changed')
        probabilities[name]=prob
    return probabilities
