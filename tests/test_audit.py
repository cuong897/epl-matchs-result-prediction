"""Synthetic fixtures only: these are not football observations or model results."""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_pilot import audit_matches, audit_players, fixture_table, link_matches, parse_fd_dates


def synthetic_league():
    teams = [f'Club{i:02d}' for i in range(20)]
    return pd.DataFrame([{'Div':'E0','Date':'01/08/2023','HomeTeam':a,'AwayTeam':b,
                          'FTHG':0,'FTAG':0,'FTR':'D'} for a in teams for b in teams if a!=b])


def synthetic_players():
    teams = pd.DataFrame({'id':[1,2],'name':['Arsenal','Spurs']})
    fx = fixture_table(pd.DataFrame({'id':[101],'kickoff_time':['2023-08-01T14:00:00Z'],'team_h':[1],'team_a':[2]}),teams)
    rows=[]
    for i in range(22):
        home=i<11
        rows.append({'position':'MID','element':i+1,'fixture':101,'was_home':home,
                     'team':'Arsenal' if home else 'Spurs','opponent_team':2 if home else 1,
                     'kickoff_time':'2023-08-01T14:00:00Z','minutes':90,'starts':1,
                     'goals_scored':0,'assists':0,'expected_goals':0.,'expected_assists':0.,'value':50})
    rows.append(dict(rows[0],position='AM',element=999,minutes=0))
    return pd.DataFrame(rows),fx,teams


class AuditTests(unittest.TestCase):
    def test_dates_are_day_first_in_both_archive_formats(self):
        actual=parse_fd_dates(pd.Series(['02/03/16','02/03/2024','impossible']))
        self.assertEqual(actual.iloc[0],pd.Timestamp('2016-03-02'))
        self.assertEqual(actual.iloc[1],pd.Timestamp('2024-03-02'))
        self.assertTrue(pd.isna(actual.iloc[2]))

    def test_complete_round_robin_is_valid_but_clock_stays_unknown(self):
        out=audit_matches(synthetic_league(),'2023-24')
        self.assertTrue(out['core_pass'])
        self.assertEqual(out['valid_clock_times'],0)

    def test_inconsistent_result_is_detected(self):
        df=synthetic_league(); df.loc[0,'FTR']='H'
        out=audit_matches(df,'2023-24')
        self.assertEqual(out['result_goal_inconsistencies'],1)
        self.assertFalse(out['core_pass'])

    def test_duplicate_match_is_detected(self):
        df=synthetic_league(); df=pd.concat([df,df.iloc[:1]],ignore_index=True)
        self.assertEqual(audit_matches(df,'2023-24')['duplicate_match_keys'],1)

    def test_manager_excluded_and_actual_XI_not_claimed_announced(self):
        p,fx,t=synthetic_players(); out=audit_players(p,fx,t,'2023-24')
        self.assertEqual(out['excluded_manager_rows'],1)
        self.assertEqual(out['fixtures_with_22_recorded_starters'],1)
        self.assertFalse(out['announced_XI_at_cutoff_verified'])

    def test_duplicate_player_fixture_rejected(self):
        p,fx,t=synthetic_players(); p=pd.concat([p,p.iloc[:1]],ignore_index=True)
        with self.assertRaisesRegex(ValueError,'Duplicate player-fixture'):
            audit_players(p,fx,t,'2023-24')

    def test_unknown_position_rejected(self):
        p,fx,t=synthetic_players(); p.loc[0,'position']='UNKNOWN'
        with self.assertRaisesRegex(ValueError,'Unknown player positions'):
            audit_players(p,fx,t,'2023-24')

    def test_alias_mapping_and_late_kickoff_do_not_silently_shift_clock(self):
        p,fx,t=synthetic_players()
        fd=pd.DataFrame({'Date':['01/08/2023'],'Time':['14:30'],'HomeTeam':['Arsenal'],'AwayTeam':['Tottenham']})
        out,links=link_matches(fd,fx,'2023-24')
        self.assertEqual(out['matched'],1)
        self.assertEqual(out['clock_mismatches_assuming_FD_London'],1)
        self.assertNotEqual(links.iloc[0]['fd_kickoff_utc_assuming_London'],links.iloc[0]['fpl_recorded_kickoff_utc'])

    def test_ambiguous_duplicate_fixture_link_rejected(self):
        p,fx,t=synthetic_players()
        fd=pd.DataFrame({'Date':['01/08/2023']*2,'Time':['15:00']*2,'HomeTeam':['Arsenal']*2,'AwayTeam':['Tottenham']*2})
        with self.assertRaises(pd.errors.MergeError):
            link_matches(fd,fx,'2023-24')


if __name__=='__main__':
    unittest.main()
