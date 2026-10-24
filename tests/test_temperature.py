"""Calibration invariants, strict split guard and a known overconfidence case."""
import json
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from temperature_calibration import fit_temperature,transform_temperature


class TemperatureTests(unittest.TestCase):
    def setUp(self):
        self.settings=json.loads((Path(__file__).resolve().parents[1]/'research/final_evaluation_config.json').read_text())['calibration']
        self.p=np.array([[.98,.01,.01]]*6)
        self.y=np.array(['H','D','A','H','D','A'])
        self.meta=pd.DataFrame({'match_id':[str(i) for i in range(6)],'season':['2023-24']*6,'split':['validation']*6})

    def test_identity_and_argmax_preserved(self):
        p=np.array([[.1,.2,.7],[.4,.4,.2]])
        np.testing.assert_allclose(transform_temperature(p,1),p)
        for t in [.5,1.,5.]:np.testing.assert_array_equal(transform_temperature(p,t).argmax(axis=1),p.argmax(axis=1))

    def test_overconfident_model_softened_and_fit_loss_not_worse(self):
        r=fit_temperature(self.y,self.p,self.meta,self.settings)
        self.assertGreater(r['temperature'],1)
        self.assertLessEqual(r['calibrated_fit_log_loss'],r['raw_log_loss'])

    def test_test_train_or_wrong_season_rejected(self):
        for split,season in [('test','2024-25'),('train','2022-23'),('validation','2024-25')]:
            m=self.meta.copy();m['split']=split;m['season']=season
            with self.assertRaises(ValueError):fit_temperature(self.y,self.p,m,self.settings)

    def test_duplicate_match_rejected(self):
        m=self.meta.copy();m.loc[1,'match_id']=m.loc[0,'match_id']
        with self.assertRaises(ValueError):fit_temperature(self.y,self.p,m,self.settings)

    def test_uniform_and_exact_zeros_finite(self):
        for p in [np.full((2,3),1/3),np.array([[1.,0.,0.],[0.,1.,0.]])]:
            q=transform_temperature(p,5)
            self.assertTrue(np.isfinite(q).all());np.testing.assert_allclose(q.sum(axis=1),1)

    def test_invalid_temperature_and_probabilities_rejected(self):
        for t in [0,-1,np.nan]:
            with self.assertRaises(ValueError):transform_temperature(self.p,t)
        with self.assertRaises(ValueError):transform_temperature([[.2,.2,.2]],1)


if __name__=='__main__':unittest.main()
