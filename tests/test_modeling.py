"""Synthetic examples check scoring, preprocessing and temporal guards."""
import json
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from modeling import (assert_development_only,choose_C,evaluate,fit_checked,historical_frequencies,
    logistic_pipeline,ordered_probabilities,paired_week_bootstrap,reliability_rows,temporal_folds,validate_probabilities)
from train_model_A import permutation_groups


class ModelingTests(unittest.TestCase):
    def test_probability_order_remapped_from_alphabetical(self):
        class Fake:
            classes_=np.array(['A','D','H'])
            def predict_proba(self,X):return np.array([[.1,.2,.7]])
        np.testing.assert_allclose(ordered_probabilities(Fake(),None),[[.7,.2,.1]])

    def test_logloss_matches_hand_calculation_and_reference(self):
        y=np.array(['H','D','A']);p=np.array([[.8,.1,.1],[.1,.7,.2],[.2,.2,.6]])
        result=evaluate(y,p)
        self.assertAlmostEqual(result['log_loss'],-np.log([.8,.7,.6]).mean())
        self.assertAlmostEqual(result['log_loss'],log_loss(y,p[:,[2,1,0]],labels=['A','D','H']))
        self.assertEqual(result['accuracy'],1.)

    def test_brier_scale_zero_to_two(self):
        self.assertEqual(evaluate(['H'],[[1.,0.,0.]])['brier_sum'],0.)
        self.assertEqual(evaluate(['H'],[[0.,0.,1.]])['brier_sum'],2.)

    def test_invalid_probability_or_labels_rejected(self):
        for p in [[[.4,.4,.4]],[[.5,np.nan,.5]],[[1.1,-.1,0.]]]:
            with self.assertRaises(ValueError):validate_probabilities(p)
        with self.assertRaises(ValueError):evaluate(['X'],[[1.,0.,0.]])

    def test_frequency_baseline_smoothing(self):
        np.testing.assert_allclose(historical_frequencies(['H','H','D'],2),[[.5,1/3,1/6]]*2)

    def test_holdout_cannot_change_fitted_imputer_and_scaler(self):
        config=json.loads((ROOT/'research/model_A_development_config.json').read_text())
        X=pd.DataFrame({'a':[0.,2.,np.nan,4.,6.,8.],'b':[1.,2.,3.,4.,5.,6.]})
        y=['H','D','A','H','D','A']
        model=fit_checked(logistic_pipeline(.1,config),X,y)
        imputer=model.named_steps['imputer'];scaler=model.named_steps['scaler']
        np.testing.assert_allclose(imputer.statistics_,[4.,3.5])
        stats=imputer.statistics_.copy();means=scaler.mean_.copy()
        ordered_probabilities(model,pd.DataFrame({'a':[1e8,np.nan],'b':[-1e8,1e8]}))
        np.testing.assert_array_equal(imputer.statistics_,stats)
        np.testing.assert_array_equal(scaler.mean_,means)

    def test_development_rejects_test_and_warmup(self):
        for split,season in [('test','2024-25'),('warmup','2013-14')]:
            with self.assertRaises(ValueError):assert_development_only(pd.DataFrame({'split':[split],'season':[season]}))

    def test_temporal_folds_exclude_validation_and_future_train(self):
        frame=pd.DataFrame({'split':['train','train','train','validation'],
            'season':['2019-20','2020-21','2021-22','2023-24'],
            'match_date':pd.to_datetime(['2020-07-26','2020-09-12','2021-08-13','2023-08-11'])})
        season,train,valid=next(temporal_folds(frame,['2020-21']))
        self.assertEqual(train.season.tolist(),['2019-20'])
        self.assertEqual(valid.season.tolist(),['2020-21'])

    def test_hyperparameter_selection_uses_loss_not_accuracy(self):
        C,ranking=choose_C([{'model':'logistic_A','C':.1,'log_loss':.9,'accuracy':.4},
            {'model':'logistic_A','C':1.,'log_loss':1.,'accuracy':.9}])
        self.assertEqual(C,.1)

    def test_reliability_constant_forecast_keeps_samples(self):
        rows=reliability_rows(['H','D','A'],np.full((3,3),1/3))
        self.assertEqual(len(rows),3)
        self.assertTrue(all(r['n']==3 for r in rows))

    def test_paired_bootstrap_identity_has_zero_interval(self):
        result=paired_week_bootstrap(pd.date_range('2023-08-01',periods=60),np.zeros(60),2,50,42)
        self.assertEqual(result['ci95_low'],0.)
        self.assertEqual(result['ci95_high'],0.)

    def test_permutation_groups_partition_allowlist(self):
        cols=json.loads((ROOT/'research/feature_columns_A.json').read_text())
        groups=permutation_groups(cols)
        self.assertEqual(sum(len(g) for g in groups.values()),40)


if __name__=='__main__':unittest.main()
