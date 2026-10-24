"""Tree estimators with explicit class encoding and train-only preprocessing."""
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.utils.validation import check_is_fitted

from modeling import LABELS, label_indices, validate_probabilities

LOCAL_DEPS = Path(__file__).resolve().parents[1] / '.deps'
if LOCAL_DEPS.is_dir():
    sys.path.insert(0, str(LOCAL_DEPS))
from xgboost import XGBClassifier


def normalized_float_probabilities(raw):
    """Normalize float32 softmax rounding only; reject larger errors."""
    p = np.asarray(raw, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 3 or not np.isfinite(p).all():
        raise ValueError('Expected finite Nx3 probabilities')
    if (p < 0).any() or (p > 1).any() or not np.allclose(p.sum(axis=1), 1, atol=1e-6, rtol=0):
        raise ValueError('Not a softmax probability matrix')
    return validate_probabilities(p / p.sum(axis=1, keepdims=True))


class XGBHDAClassifier(ClassifierMixin, BaseEstimator):
    """Encode H=0, D=1, A=2 and persist the mapping with the estimator."""
    def __init__(self, params=None, random_state=42, n_jobs=2):
        self.params = params
        self.random_state = random_state
        self.n_jobs = n_jobs

    def fit(self, X, y):
        if set(y) != set(LABELS):
            raise ValueError('Training must contain all three labels H,D,A')
        self.estimator_ = XGBClassifier(**(self.params or {}), random_state=self.random_state, n_jobs=self.n_jobs)
        self.estimator_.fit(X, label_indices(y), verbose=False)
        self.classes_ = np.asarray(LABELS)
        self.n_features_in_ = self.estimator_.n_features_in_
        return self

    def predict_proba(self, X):
        check_is_fitted(self, 'estimator_')
        if not np.array_equal(self.estimator_.classes_, [0, 1, 2]):
            raise ValueError('Unexpected encoded class order')
        return normalized_float_probabilities(self.estimator_.predict_proba(X))

    def predict(self, X):
        return self.classes_[self.predict_proba(X).argmax(axis=1)]


def tree_pipeline(family, candidate, config):
    if family not in ['random_forest', 'xgboost']:
        raise ValueError('Unknown model family')
    params = dict(config[f'{family}_fixed'], **candidate)
    if family == 'random_forest':
        estimator = RandomForestClassifier(**params, random_state=config['random_seed'],
                                           n_jobs=config['n_jobs'], class_weight=None)
    else:
        estimator = XGBHDAClassifier(params=params, random_state=config['random_seed'], n_jobs=config['n_jobs'])
    return Pipeline([('imputer', SimpleImputer(strategy='median', add_indicator=True, keep_empty_features=True)),
                     ('classifier', estimator)])


def rank_candidates(rows, expected_seasons, n_candidates):
    """Refuse incomplete/duplicate folds; tie-break by predeclared order."""
    frame = pd.DataFrame(rows)
    if set(frame.candidate) != set(range(n_candidates)):
        raise ValueError('Missing candidate')
    for _, group in frame.groupby('candidate'):
        if len(group) != len(expected_seasons) or set(group.season) != set(expected_seasons):
            raise ValueError('Incomplete or duplicate temporal folds')
    if not np.isfinite(frame.log_loss).all():
        raise ValueError('Invalid candidate score')
    ranked = frame.groupby('candidate', as_index=False).agg(mean_log_loss=('log_loss','mean'), std_log_loss=('log_loss','std'))
    return ranked.sort_values(['mean_log_loss','candidate']).to_dict('records')
