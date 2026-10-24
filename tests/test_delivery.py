"""Read-only checks on tracked presentation artifacts; no model evaluation changes."""
from pathlib import Path
import json
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from delivery_data import load_delivery,demo_payload


class DeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=load_delivery(ROOT)

    def test_archive_covers_380_matches_and_30_probability_outputs(self):
        self.assertEqual(len(self.data['matches']),380)
        groups={}
        for row in self.data['predictions']:groups.setdefault((row['model'],row['variant']),set()).add(row['match_id'])
        self.assertEqual(len(groups),30)
        self.assertTrue(all(len(v)==380 for v in groups.values()))

    def test_payload_default_was_selected_before_test(self):
        payload=demo_payload(self.data)
        self.assertEqual(payload['defaultModel'],self.data['result']['primary_practical_reference'])
        self.assertEqual(len(payload['models']),16)
        for model in payload['models']:
            self.assertEqual('temperature' in payload['probabilities'][model['id']],model['calibrate'])

    def test_catalog_scores_agree_with_outcomes(self):
        for row in self.data['matches']:
            h,a=int(row['home_goals']),int(row['away_goals'])
            self.assertEqual(row['result'],'H' if h>a else 'A' if h<a else 'D')

    def test_notebook_has_executed_cells_without_errors(self):
        n=json.loads((ROOT/'notebooks/results_reproduction.ipynb').read_text(encoding='utf-8'))
        code=[c for c in n['cells'] if c['cell_type']=='code']
        self.assertEqual(len(code),10)
        self.assertTrue(all(c['execution_count'] is not None for c in code))
        self.assertFalse(any(o['output_type']=='error' for c in code for o in c['outputs']))


if __name__=='__main__':unittest.main()
