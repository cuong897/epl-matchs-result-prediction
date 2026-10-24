from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from final_bootstrap import paired_intervals


class FinalBootstrapTests(unittest.TestCase):
    def test_identical_models_and_bonferroni_nesting(self):
        dates=pd.date_range('2024-08-01',periods=90)
        r=paired_intervals(dates,np.zeros(90),2,100,42,6)
        self.assertEqual(r['ci95_low'],0);self.assertEqual(r['family_ci_high'],0)
        r=paired_intervals(dates,np.linspace(-1,2,90),2,100,42,6)
        self.assertLessEqual(r['family_ci_low'],r['ci95_low'])
        self.assertGreaterEqual(r['family_ci_high'],r['ci95_high'])

    def test_pair_alignment_and_block_guard(self):
        dates=pd.date_range('2024-08-01',periods=90)
        with self.assertRaises(ValueError):paired_intervals(dates,[1],2)
        with self.assertRaises(ValueError):paired_intervals(dates,np.zeros(90),100)


if __name__=='__main__':unittest.main()
