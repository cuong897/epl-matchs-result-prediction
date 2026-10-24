"""Frozen comparators must use the same matches, labels and probability values."""
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from apf_modeling import frozen_probabilities
from modeling import evaluate


class ComparatorTests(unittest.TestCase):
    def setUp(self):
        self.valid=pd.DataFrame({'match_id':['a','b','c'],'season':['2023-24']*3,'result':['H','D','A']})
        self.p=np.array([[.7,.2,.1],[.2,.5,.3],[.2,.2,.6]])
        self.saved=self.valid.copy();self.saved['model']='frozen'
        for i,label in enumerate(['H','D','A']):self.saved[f'p_{label}']=self.p[:,i]
        self.result={'validation_metrics':{'frozen':evaluate(self.valid.result.to_numpy(),self.p)}}

    def test_frozen_rows_are_aligned_by_id(self):
        actual=frozen_probabilities(self.valid,self.saved.sample(frac=1,random_state=2),self.result)
        np.testing.assert_allclose(actual['frozen'],self.p)

    def test_wrong_cohort_duplicate_or_labels_rejected(self):
        wrong=self.saved.copy();wrong.loc[0,'match_id']='other'
        with self.assertRaises(ValueError):frozen_probabilities(self.valid,wrong,self.result)
        with self.assertRaises(ValueError):frozen_probabilities(self.valid,pd.concat([self.saved,self.saved.iloc[:1]]),self.result)
        wrong=self.saved.copy();wrong.loc[0,'result']='D'
        with self.assertRaises(ValueError):frozen_probabilities(self.valid,wrong,self.result)

    def test_revised_probabilities_cannot_silently_replace_frozen_values(self):
        wrong=self.saved.copy();wrong.loc[0,['p_H','p_D','p_A']]=[.4,.3,.3]
        with self.assertRaises(AssertionError):frozen_probabilities(self.valid,wrong,self.result)


if __name__=='__main__':unittest.main()
