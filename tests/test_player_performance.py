"""Hand calculations plus temporal and proxy-selection counterfactuals for F."""
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from player_performance_features import BASE,performance_snapshot,build_performance
from test_player_proxy import example


def performance_example():
    m,p=example()
    p['goals_scored']=0;p['assists']=0
    p.loc[p.player_season_id.str.endswith('A0'),'goals_scored']=1
    p.loc[p.player_season_id.str.endswith('B0'),'assists']=1
    return m,p


class PerformanceTests(unittest.TestCase):
    def test_hand_calculation(self):
        h=[{'a':(90,1,0),'b':(90,0,1)},{'a':(90,0,0),'c':(90,1,1)}]
        r=performance_snapshot(h)
        self.assertAlmostEqual(r[BASE[0]],.5*90/360+.5*90/270)
        self.assertAlmostEqual(r[BASE[1]],.5*90/270)
        self.assertAlmostEqual(r[BASE[2]],.375)
        self.assertAlmostEqual(r[BASE[3]],.75)

    def test_empty_history_and_zero_contributions(self):
        self.assertTrue(all(np.isnan(x) for x in performance_snapshot([]).values()))
        r=performance_snapshot([{'a':(90,0,0)}])
        self.assertEqual(r[BASE[0]],0)
        self.assertTrue(np.isnan(r[BASE[2]]))

    def test_low_minutes_are_shrunk_without_average_of_raw_per90(self):
        r=performance_snapshot([{'a':(1,1,0)}])
        self.assertAlmostEqual(r[BASE[0]],90/181)
        self.assertLess(r[BASE[0]],1)

    def test_current_and_future_performance_cannot_change_past(self):
        m,p=performance_example();a,_=build_performance(m,p)
        p.loc[p.match_id.isin(['m3','m4','m5','m6']),'goals_scored']=5
        b,_=build_performance(m,p)
        pd.testing.assert_frame_equal(a.iloc[:4],b.iloc[:4])

    def test_prefix_and_input_order_invariance(self):
        m,p=performance_example();a,_=build_performance(m,p)
        b,_=build_performance(m.iloc[:3],p[p.match_id.isin(m.iloc[:3].match_id)])
        pd.testing.assert_frame_equal(a.iloc[:3],b)
        c,_=build_performance(m.sample(frac=1,random_state=1),p.sample(frac=1,random_state=2))
        pd.testing.assert_frame_equal(a,c)

    def test_last_group_uses_only_previous_match_not_current_participants(self):
        m,p=performance_example();a,_=build_performance(m,p)
        sel=p.match_id.eq('m3');p.loc[sel,'player_season_id']+='new'
        b,_=build_performance(m,p)
        pd.testing.assert_frame_equal(a[a.match_id.eq('m3')],b[b.match_id.eq('m3')])

    def test_current_XI_price_or_xg_not_used(self):
        m,p=performance_example();a,_=build_performance(m,p)
        p['starts']=1;p['value']=999;p['expected_goals']=999
        b,_=build_performance(m,p)
        pd.testing.assert_frame_equal(a,b)

    def test_invalid_or_zero_minute_contribution_rejected(self):
        m,p=performance_example();q=p.copy();q.loc[0,'goals_scored']=-1
        with self.assertRaises(ValueError):build_performance(m,q)
        q=p.copy();q.loc[0,'minutes']=0;q.loc[0,'goals_scored']=1
        with self.assertRaises(ValueError):build_performance(m,q)

    def test_unregistered_shrinkage_rejected(self):
        m,p=performance_example()
        with self.assertRaises(ValueError):build_performance(m,p,90)


if __name__=='__main__':unittest.main()
