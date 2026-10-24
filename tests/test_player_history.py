"""Synthetic records exercise postponed matches, team identity and false zeros."""
import json
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from audit_player_history import remove_documented_placeholders,normalize_players,mask_unusable_advanced


class PlayerHistoryTests(unittest.TestCase):
    def setUp(self):
        self.rules=json.loads((ROOT/'research/player_history_corrections.json').read_text())
        self.rows=pd.DataFrame({'element':[1,1],'fixture':[275,275],
            'kickoff_time':['2020-03-11T19:30:00Z','2020-06-17T19:15:00Z'],
            'minutes':[0,90],'team_h_score':[np.nan,3],'team_a_score':[np.nan,0]})
        self.fixtures=pd.DataFrame({'id':[275],'kickoff_time':['2020-06-17T19:15:00Z']})

    def test_only_documented_unplayed_placeholder_removed(self):
        p,log=remove_documented_placeholders(self.rows,self.fixtures,'2019-20',self.rules)
        self.assertEqual(p.minutes.tolist(),[90])
        self.assertEqual(log[0]['rows'],1)
        self.assertEqual(len(self.rows),2)

    def test_cannot_discard_played_row_or_without_replacement(self):
        p=self.rows.copy();p.loc[0,'minutes']=1
        with self.assertRaises(ValueError):remove_documented_placeholders(p,self.fixtures,'2019-20',self.rules)
        with self.assertRaises(ValueError):remove_documented_placeholders(self.rows.iloc[:1],self.fixtures,'2019-20',self.rules)

    def test_unexplained_duplicates_rejected(self):
        with self.assertRaises(ValueError):remove_documented_placeholders(self.rows,self.fixtures,'2020-21',self.rules)

    def example(self):
        p=pd.DataFrame({'element':[1],'fixture':[1],'kickoff_time':['2021-03-28T15:00:00Z'],
            'was_home':[True],'opponent_team':[2],'minutes':[90],'goals_scored':[0],'assists':[0],'team':['Wrong final club']})
        f=pd.DataFrame({'id':[1],'kickoff_time':['2021-03-28T15:30:00Z'],'team_h':[1],'team_a':[2]})
        t=pd.DataFrame({'id':[1,2],'name':['Arsenal','Chelsea']})
        m=pd.DataFrame({'season':['2020-21'],'match_id':['m1'],'match_date':['2021-03-28'],'home_team':['Arsenal'],'away_team':['Chelsea']})
        return p,f,t,m

    def test_fixture_side_not_archived_club_and_DST_availability(self):
        p,f,t,m=self.example()
        r=normalize_players(p,f,t,m,'2020-21')
        self.assertEqual(r.historic_team_name.iloc[0],'Arsenal')
        self.assertEqual(r.player_season_id.iloc[0],'2020-21:1')
        self.assertTrue(r.kickoff_conflict_within_day.iloc[0])
        self.assertEqual(str(r.available_at_assumed_utc.iloc[0]),'2021-03-28 23:00:00+00:00')

    def test_wrong_opponent_rejected(self):
        p,f,t,m=self.example();p['opponent_team']=1
        with self.assertRaises(ValueError):normalize_players(p,f,t,m,'2020-21')

    def test_unresolved_cross_date_clock_rejected(self):
        p,f,t,m=self.example();p['kickoff_time']='2021-03-27T15:00:00Z'
        with self.assertRaises(ValueError):normalize_players(p,f,t,m,'2020-21')

    def test_all_zero_fixture_masked_but_individual_zeros_retained(self):
        p=pd.DataFrame({'match_id':['m1','m1','m2','m2'],'match_date':['2022-08-01']*4,
            'starts':[0,0,1,1],'expected_goals':[0,0,.5,0],'expected_assists':[0,0,0,0]})
        r,d=mask_unusable_advanced(p)
        self.assertTrue(r.loc[:1,['starts','expected_goals','expected_assists']].isna().all().all())
        self.assertEqual(r.loc[3,'expected_goals'],0)
        self.assertEqual(d['fixture_wide_zero_advanced_stats'],1)

    def test_missing_advanced_columns_never_imputed_to_zero(self):
        r,d=mask_unusable_advanced(pd.DataFrame({'minutes':[90]}))
        self.assertNotIn('expected_goals',r)
        self.assertEqual(r.advanced_stats_quality.iloc[0],'columns_unavailable')


if __name__=='__main__':unittest.main()
