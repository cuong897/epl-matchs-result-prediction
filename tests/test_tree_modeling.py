"""Synthetic data only: class mapping, softmax rounding and fold selection."""
import json
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd
from sklearn.base import clone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from modeling import ordered_probabilities
from tree_modeling import normalized_float_probabilities, rank_candidates, tree_pipeline


class TreeModelingTests(unittest.TestCase):
    def test_float32_rounding_is_normalized_but_bad_probabilities_rejected(self):
        p = normalized_float_probabilities(np.array([[.2,.3,.5]],dtype=np.float32))
        self.assertAlmostEqual(p.sum(),1.,places=14)
        for bad in [[[.3,.3,.3]], [[-.1,.6,.5]], [[np.nan,.5,.5]]]:
            with self.assertRaises(ValueError): normalized_float_probabilities(bad)

    def test_candidate_ranking_requires_all_same_folds(self):
        rows = [{'candidate':c,'season':s,'log_loss':1+c*.1} for c in [0,1] for s in ['a','b','c']]
        self.assertEqual(rank_candidates(rows,['a','b','c'],2)[0]['candidate'],0)
        with self.assertRaises(ValueError):rank_candidates(rows[:-1],['a','b','c'],2)
        with self.assertRaises(ValueError):rank_candidates(rows+[rows[0]],['a','b','c'],2)

    def test_candidate_tie_uses_declared_order(self):
        rows = [{'candidate':c,'season':s,'log_loss':1.} for c in [1,0] for s in ['a','b','c']]
        self.assertEqual(rank_candidates(rows,['a','b','c'],2)[0]['candidate'],0)

    def test_both_estimators_fit_mapping_and_holdout_do_not_change_imputation(self):
        config = json.loads((ROOT/'research/model_A_tree_config.json').read_text())
        config['n_jobs'] = 1
        X = pd.DataFrame({'x':np.repeat([-3.,0.,3.],10),'z':[np.nan,2.,4.]*10})
        y = np.repeat(['H','D','A'],10)
        for family in ['random_forest','xgboost']:
            config[f'{family}_fixed']['n_estimators'] = 8
            if family == 'xgboost':config['xgboost_fixed']['min_child_weight'] = 0
            model = clone(tree_pipeline(family,{'max_depth':2},config)).fit(X,y)
            stat = model.named_steps['imputer'].statistics_.copy()
            p = ordered_probabilities(model,X)
            self.assertEqual(p.shape,(30,3))
            self.assertEqual(list(np.asarray(['H','D','A'])[p.argmax(axis=1)][[0,10,20]]),['H','D','A'])
            ordered_probabilities(model,pd.DataFrame({'x':[1e8],'z':[np.nan]}))
            np.testing.assert_array_equal(stat,model.named_steps['imputer'].statistics_)


if __name__ == '__main__':unittest.main()
