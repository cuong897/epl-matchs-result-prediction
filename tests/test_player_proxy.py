"""Synthetic temporal counterfactuals and hand-computed personnel statistics."""
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from player_proxy_features import build_proxy,usage_snapshot


def example(n=7):
    matches=[];players=[]
    for i in range(n):
        date=pd.Timestamp('2020-08-01')+pd.Timedelta(days=i)
        matches.append({'match_id':f'm{i}','season':'2020-21','match_date':str(date.date()),'home_team':'A','away_team':'B'})
        for team in ['A','B']:
            for number in [0,i+1]:
                players.append({'season':'2020-21','match_id':f'm{i}','player_season_id':f'2020-21:{team}{number}',
                    'historic_team_name':team,'match_date':str(date.date()),'minutes':90,
                    'available_at_assumed_utc':(date+pd.Timedelta(days=1)).tz_localize('Europe/London').tz_convert('UTC')})
    return pd.DataFrame(matches),pd.DataFrame(players)


class ProxyTests(unittest.TestCase):
    def test_hand_computed_concentration_and_overlap(self):
        h=[{'minutes':{'a':90,'b':90}},{'minutes':{'a':90,'c':90}}]
        r=usage_snapshot(h)
        self.assertEqual(r['p_participants_n5'],3)
        self.assertAlmostEqual(r['p_minutes_hhi5'],.375)
        self.assertAlmostEqual(r['p_last_returning_minutes_share5'],.5)
        self.assertAlmostEqual(r['p_mean_minutes_overlap5'],.5)

    def test_top11_share_counts_minutes_not_number_of_players(self):
        r=usage_snapshot([{'minutes':{str(i):1 for i in range(12)}}])
        self.assertAlmostEqual(r['p_top11_minutes_share5'],11/12)

    def test_empty_and_one_match_missingness(self):
        r=usage_snapshot([])
        self.assertEqual(r['p_history_n5'],0)
        self.assertTrue(np.isnan(r['p_participants_n5']))
        self.assertTrue(np.isnan(usage_snapshot([{'minutes':{'a':90}}])['p_mean_minutes_overlap5']))

    def test_window_is_five_prior_team_matches(self):
        m,p=example();f,line=build_proxy(m,p)
        self.assertEqual(f.home_p_history_n5.tolist(),[0,1,2,3,4,5,5])
        self.assertEqual(line[(line.match_id=='m6')&(line.side=='home')].history_match_ids.iloc[0],'m1|m2|m3|m4|m5')

    def test_current_minutes_cannot_change_own_features(self):
        m,p=example();a,_=build_proxy(m,p)
        p.loc[p.match_id.eq('m3'),'minutes']=45
        b,_=build_proxy(m,p)
        pd.testing.assert_frame_equal(a[a.match_id.eq('m3')],b[b.match_id.eq('m3')])

    def test_future_changes_cannot_change_past(self):
        m,p=example();a,_=build_proxy(m,p)
        p.loc[p.match_id.isin(['m5','m6']),'minutes']=30
        b,_=build_proxy(m,p)
        pd.testing.assert_frame_equal(a.iloc[:5],b.iloc[:5])

    def test_prefix_and_shuffle_invariance(self):
        m,p=example();a,_=build_proxy(m,p)
        b,_=build_proxy(m.iloc[:3],p[p.match_id.isin(m.iloc[:3].match_id)])
        pd.testing.assert_frame_equal(a.iloc[:3],b)
        c,_=build_proxy(m.sample(frac=1,random_state=1),p.sample(frac=1,random_state=2))
        pd.testing.assert_frame_equal(a,c)

    def test_season_state_reset(self):
        m,p=example(3)
        m.loc[2,'season']='2021-22';m.loc[2,'match_date']='2021-08-01'
        sel=p.match_id.eq('m2');p.loc[sel,'season']='2021-22';p.loc[sel,'match_date']='2021-08-01'
        p.loc[sel,'player_season_id']=p.loc[sel,'player_season_id'].str.replace('2020-21','2021-22')
        p.loc[sel,'available_at_assumed_utc']=pd.Timestamp('2021-08-01T23:00:00Z')
        f,_=build_proxy(m,p)
        self.assertEqual(f.iloc[2].home_p_history_n5,0)

    def test_no_current_roster_or_goal_columns_used(self):
        m,p=example();a,_=build_proxy(m,p)
        p['starts']=1;p['goals_scored']=999;p['team']='Wrong Club';p['expected_goals']=999
        b,_=build_proxy(m,p)
        pd.testing.assert_frame_equal(a,b)

    def test_duplicates_wrong_team_and_availability_rejected(self):
        m,p=example()
        with self.assertRaises(ValueError):build_proxy(m,pd.concat([p,p.iloc[:1]]))
        q=p.copy();q.loc[0,'historic_team_name']='X'
        with self.assertRaises(ValueError):build_proxy(m,q)
        q=p.copy();q.loc[0,'available_at_assumed_utc']=pd.Timestamp('2030-01-01T00:00:00Z')
        with self.assertRaises(ValueError):build_proxy(m,q)

    def test_zero_minute_rows_are_not_participants(self):
        m,p=example(2);p.loc[p.player_season_id.str.endswith('A1'),'minutes']=0
        f,_=build_proxy(m,p)
        self.assertEqual(f.iloc[1].home_p_participants_n5,1)

    def test_same_day_team_duplicate_rejected(self):
        m,p=example(2);m.loc[1,'match_date']=m.loc[0,'match_date']
        p.loc[p.match_id.eq('m1'),'match_date']=m.loc[0,'match_date']
        p.loc[p.match_id.eq('m1'),'available_at_assumed_utc']=p.iloc[0].available_at_assumed_utc
        with self.assertRaises(ValueError):build_proxy(m,p)


if __name__=='__main__':unittest.main()
