"""Development-only model helpers with explicit H,D,A probability order."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score,confusion_matrix,precision_recall_fscore_support
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

LABELS=['H','D','A']


def label_indices(y):
    lookup={v:i for i,v in enumerate(LABELS)}
    if not set(y).issubset(lookup):raise ValueError('Unknown or missing outcome label')
    return np.array([lookup[x] for x in y],dtype=int)


def validate_probabilities(p):
    p=np.asarray(p,dtype=float)
    if p.ndim!=2 or p.shape[1]!=3 or not np.isfinite(p).all():raise ValueError('Expected finite Nx3 probabilities')
    if (p<0).any() or (p>1).any() or not np.allclose(p.sum(axis=1),1,atol=1e-10,rtol=0):raise ValueError('Invalid probability simplex')
    return p


def ordered_probabilities(estimator,X):
    if set(estimator.classes_)!=set(LABELS):raise ValueError('Estimator lacks one of H,D,A')
    p=estimator.predict_proba(X)
    order=[list(estimator.classes_).index(k) for k in LABELS]
    return validate_probabilities(p[:,order])


def per_match_log_loss(y,p):
    p=validate_probabilities(p); idx=label_indices(y)
    if len(idx)!=len(p):raise ValueError('Label/probability length mismatch')
    return -np.log(np.clip(p[np.arange(len(idx)),idx],1e-15,1))


def classification_metrics(y,pred):
    if len(y)!=len(pred) or not len(y):raise ValueError('Empty or unmatched label arrays')
    label_indices(y);label_indices(pred)
    precision,recall,f1,support=precision_recall_fscore_support(y,pred,labels=LABELS,zero_division=0)
    return {'n':len(y),'accuracy':float(accuracy_score(y,pred)),'macro_f1':float(f1.mean()),
            'per_class':{c:{'precision':float(precision[i]),'recall':float(recall[i]),'f1':float(f1[i]),'support':int(support[i])} for i,c in enumerate(LABELS)},
            'confusion_matrix_rows_true_cols_pred_HDA':confusion_matrix(y,pred,labels=LABELS).tolist(),
            'predicted_label_counts':{c:int(np.sum(np.asarray(pred)==c)) for c in LABELS}}


def evaluate(y,p):
    p=validate_probabilities(p); losses=per_match_log_loss(y,p)
    truth=np.eye(3)[label_indices(y)]
    pred=np.asarray(LABELS)[p.argmax(axis=1)]
    result=classification_metrics(y,pred)
    result.update(log_loss=float(losses.mean()),brier_sum=float(np.mean(np.sum((p-truth)**2,axis=1))))
    return result


def historical_frequencies(y,n,alpha=1.):
    if alpha<=0:raise ValueError('Smoothing alpha must be positive')
    label_indices(y)
    counts=np.array([np.sum(np.asarray(y)==c) for c in LABELS],dtype=float)
    return np.tile((counts+alpha)/(counts.sum()+3*alpha),(n,1))


def logistic_pipeline(C,config):
    return Pipeline([
        ('imputer',SimpleImputer(strategy='median',add_indicator=True,keep_empty_features=True)),
        ('scaler',StandardScaler()),
        ('classifier',LogisticRegression(C=C,solver=config['logistic_solver'],l1_ratio=0.,
            max_iter=config['logistic_max_iter'],tol=config['logistic_tol'],class_weight=None,random_state=config['random_seed']))])


def fit_checked(model,X,y):
    with warnings.catch_warnings():
        warnings.simplefilter('error',ConvergenceWarning)
        model.fit(X,y)
    return model


def assert_development_only(frame):
    if frame.empty:raise ValueError('Empty development frame')
    if not frame['split'].isin(['train','validation']).all():raise ValueError('Test/warmup rows forbidden in model development')
    if frame.season.str[:4].astype(int).max()>2023:raise ValueError('Future/test season forbidden')


def load_development(root: Path,columns):
    curated=root/'data/curated'
    meta=pd.read_csv(curated/'matches.csv',usecols=['match_id','season','match_date','split'])
    meta=meta[meta['split'].isin(['train','validation'])].copy()
    ids=set(meta.match_id)
    # Shared outcomes store is streamed; only development IDs are retained/scored.
    with (curated/'match_outcomes.csv').open(encoding='utf-8',newline='') as f:
        labels=pd.DataFrame([{'match_id':r['match_id'],'result':r['result']} for r in csv.DictReader(f) if r['match_id'] in ids])
    matrices=[]
    for split in ['train','validation']:
        part=pd.read_csv(curated/f'features_A_{split}.csv')
        if set(part.columns)!={'match_id',*columns}:raise ValueError('Feature file does not match allowlist')
        expected=set(meta.loc[meta['split'].eq(split),'match_id'])
        if set(part.match_id)!=expected:raise ValueError('Feature/split ID mismatch')
        matrices.append(part)
    frame=meta.merge(pd.concat(matrices,ignore_index=True),on='match_id',validate='one_to_one').merge(labels,on='match_id',validate='one_to_one')
    if len(frame)!=len(meta):raise ValueError('Missing labels or features')
    assert_development_only(frame)
    frame['match_date']=pd.to_datetime(frame.match_date)
    return frame.sort_values(['match_date','match_id']).reset_index(drop=True)


def temporal_folds(frame,seasons):
    assert_development_only(frame)
    train=frame[frame['split'].eq('train')]
    for season in seasons:
        earlier=train[train.season.str[:4].astype(int)<int(season[:4])]
        later=train[train.season.eq(season)]
        if earlier.empty or later.empty or earlier.match_date.max()>=later.match_date.min():raise ValueError('Invalid temporal fold boundary')
        yield season,earlier,later


def choose_C(cv_rows):
    scores=pd.DataFrame(cv_rows)
    scores=scores[scores.model.eq('logistic_A')]
    grouped=scores.groupby('C',as_index=False).agg(mean_log_loss=('log_loss','mean'),std_log_loss=('log_loss','std'))
    ranked=grouped.sort_values(['mean_log_loss','C'])
    return float(ranked.iloc[0]['C']),ranked.to_dict('records')


def reliability_rows(y,p,bins=5):
    p=validate_probabilities(p); truth=np.eye(3)[label_indices(y)]; records=[]
    for j,label in enumerate(LABELS):
        # qcut keeps equal probabilities together; constant baseline yields one bin.
        if np.ptp(p[:,j])<1e-12:groups=np.zeros(len(p),dtype=int)
        else:groups=np.asarray(pd.qcut(p[:,j],q=bins,labels=False,duplicates='drop'))
        for group in sorted(set(groups)):
            selected=groups==group;n=int(selected.sum());observed=float(truth[selected,j].mean())
            z=1.96;den=1+z*z/n;center=(observed+z*z/(2*n))/den
            half=z*np.sqrt(observed*(1-observed)/n+z*z/(4*n*n))/den
            records.append({'class':label,'bin':int(group),'n':n,'mean_predicted':float(p[selected,j].mean()),
                            'observed_fraction':observed,'observed_wilson_low':float(center-half),'observed_wilson_high':float(center+half)})
    return records


def paired_week_bootstrap(dates,differences,block_weeks=2,repeats=2000,seed=42):
    """Non-circular moving blocks of consecutive calendar weeks, paired models."""
    dates=pd.Series(pd.to_datetime(dates)).reset_index(drop=True)
    weeks=dates.dt.to_period('W-SUN').dt.start_time
    calendar=pd.date_range(weeks.min(),weeks.max(),freq='7D')
    if block_weeks<1 or block_weeks>len(calendar):raise ValueError('Invalid block length')
    differences=np.asarray(differences,dtype=float)
    if len(differences)!=len(dates):raise ValueError('Dates/losses do not align')
    arrays=[np.flatnonzero(weeks.eq(day)) for day in calendar]
    rng=np.random.default_rng(seed);samples=[]
    while len(samples)<repeats:
        starts=rng.integers(0,len(calendar)-block_weeks+1,size=int(np.ceil(len(calendar)/block_weeks)))
        picked=[i for start in starts for i in range(start,start+block_weeks)][:len(calendar)]
        indices=np.concatenate([arrays[i] for i in picked])
        if len(indices):samples.append(float(differences[indices].mean()))
    lo,hi=np.quantile(samples,[.025,.975])
    return {'delta_log_loss_LR_minus_baseline':float(differences.mean()),'ci95_low':float(lo),'ci95_high':float(hi),
            'block_weeks':block_weeks,'replicates':repeats,'negative_favors_LR':True}
