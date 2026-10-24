"""Read a fixed registry of existing models; never fit base estimators."""
import hashlib
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from modeling import evaluate,ordered_probabilities
import tree_modeling  # register project-local XGBoost wrapper for trusted joblib artifacts


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def predict_registered(root,entry,features):
    if entry['type']=='frequency':return np.tile(entry['probabilities'],(len(features),1))
    path=root/entry['model_path']
    if sha(path)!=entry['model_sha256']:raise ValueError('Registered estimator changed')
    estimator=joblib.load(path)
    return ordered_probabilities(estimator,features[entry['columns']])


def feature_frame(root,split):
    meta=pd.read_csv(root/'data/curated/matches.csv',usecols=['match_id','season','match_date','split'])
    meta=meta[meta['split'].eq(split)].copy()
    for group in ['A','P','F']:
        part=pd.read_csv(root/f'data/curated/features_{group}_{split}.csv')
        if set(part.match_id)!=set(meta.match_id) or part.match_id.duplicated().any():raise ValueError('Final feature cohort mismatch')
        meta=meta.merge(part,on='match_id',validate='one_to_one')
    return meta.sort_values(['match_date','match_id']).reset_index(drop=True)


def registered_validation(root,entry,frame):
    path=root/entry['validation_predictions_path']
    if sha(path)!=entry['validation_predictions_sha256']:raise ValueError('Validation archive changed')
    p=pd.read_csv(path);p=p[p.model.eq(entry['source_model'])]
    if len(p)!=380 or p.match_id.duplicated().any() or set(p.match_id)!=set(frame.match_id):raise ValueError('Bad calibration cohort')
    p=p.set_index('match_id').loc[frame.match_id]
    if not p.season.eq('2023-24').all():raise ValueError('Calibration contains non-validation season')
    prob=p[['p_H','p_D','p_A']].to_numpy();truth=p.result.to_numpy()
    actual=predict_registered(root,entry,frame)
    np.testing.assert_allclose(actual,prob,atol=1e-12,rtol=0)
    metrics=evaluate(truth,prob)
    for key in ['log_loss','brier_sum','accuracy','macro_f1']:
        np.testing.assert_allclose(metrics[key],entry['expected_validation_metrics'][key],atol=1e-12,rtol=0)
    return truth,prob
