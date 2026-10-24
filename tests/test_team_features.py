"""Synthetic outcomes exclusively for mathematical/temporal invariance checks."""
import json
from pathlib import Path
import sys
import unittest

import pandas as pd
from pandas.testing import assert_frame_equal

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from team_features import FEATURE_COLUMNS,build_features,match_id,local_midnight_utc
from build_team_dataset import clean_fd
from audit_pilot import audit_matches


def config():
    return json.loads((ROOT/'research/team_feature_config.json').read_text(encoding='utf-8'))


def sample():
    # First two fixtures share a date: no outcome can affect the other's feature.
    rows=[('2023-08-01','A','B',2,0),('2023-08-01','C','D',0,1),
          ('2023-08-05','B','C',1,1),('2023-08-05','D','A',0,0),
          ('2023-08-12','A','C',3,1),('2023-08-12','B','D',0,1),
          ('2023-08-20','C','B',2,2),('2023-08-20','A','D',1,0)]
    return make_rows([('2023-24',)+r for r in rows])


def make_rows(rows):
    frame=pd.DataFrame(rows,columns=['season','match_date','home_team','away_team','home_goals','away_goals'])
    frame['match_id']=[match_id(s,h,a) for s,h,a in zip(frame.season,frame.home_team,frame.away_team)]
    return frame


def values(frame):
    return build_features(frame,config()).set_index('match_id')[FEATURE_COLUMNS].sort_index()


class FeatureTests(unittest.TestCase):
    def test_manual_first_and_second_match_form_and_elo(self):
        df=sample(); out=values(df)
        first=out.loc[match_id('2023-24','A','B')]
        self.assertEqual(first.home_history_n10,0)
        self.assertTrue(pd.isna(first.home_form5_ppg))
        self.assertEqual(first.home_elo,1500)
        second=out.loc[match_id('2023-24','D','A')]
        self.assertEqual(second.away_form5_ppg,3)
        self.assertEqual(second.away_form5_gf,2)
        self.assertEqual(second.away_form5_ga,0)
        self.assertEqual(second.away_days_since_last_pl,4)
        expected=1500+20*(1-1/(1+10**(-65/400)))
        self.assertAlmostEqual(second.away_elo,expected)

    def test_current_outcome_cannot_change_own_features(self):
        original=sample(); changed=original.copy()
        changed.loc[4,['home_goals','away_goals']]=[0,9]
        before=values(original); after=values(changed)
        ids=original.loc[original.match_date.le('2023-08-12'),'match_id']
        assert_frame_equal(before.loc[ids],after.loc[ids])

    def test_future_outcomes_cannot_change_past(self):
        original=sample(); changed=original.copy()
        changed.loc[changed.match_date.gt('2023-08-05'),'home_goals']=10
        ids=original.loc[original.match_date.le('2023-08-05'),'match_id']
        assert_frame_equal(values(original).loc[ids],values(changed).loc[ids])

    def test_prefix_invariance_even_inside_a_date_batch(self):
        full=sample(); prefix=full.iloc[:5]
        assert_frame_equal(values(full).loc[values(prefix).index],values(prefix))

    def test_input_row_order_has_no_effect(self):
        full=sample()
        assert_frame_equal(values(full),values(full.sample(frac=1,random_state=42)))

    def test_same_day_match_outcome_does_not_enter_other_match(self):
        full=sample(); changed=full.copy(); changed.loc[0,'home_goals']=8
        target=match_id('2023-24','C','D')
        assert_frame_equal(values(full).loc[[target]],values(changed).loc[[target]])

    def test_h2h_orientation_and_only_past_matches(self):
        out=values(sample()).loc[match_id('2023-24','C','B')]
        self.assertEqual(out.h2h_n5,1)
        self.assertEqual(out.h2h_home_ppg5,1)

    def test_season_reset_promotion_and_gap(self):
        df=make_rows([('2013-14','2013-08-01','A','B',1,0),
                      ('2014-15','2014-08-01','B','C',0,0),
                      ('2015-16','2015-08-01','A','B',0,2)])
        row=values(df).loc[match_id('2015-16','A','B')]
        self.assertEqual(row.home_newly_promoted,1)
        self.assertEqual(row.home_elo,1400)
        self.assertEqual(row.home_history_n10,0)
        self.assertEqual(row.home_season_matches,0)
        self.assertEqual(row.home_season_points,0)
        self.assertEqual(row.home_days_since_last_pl,730)
        self.assertEqual(row.away_newly_promoted,0)
        self.assertEqual(row.away_history_n10,2)

    def test_actual_rolling_windows_exclude_current(self):
        rows=[('2023-24',str((pd.Timestamp('2023-08-01')+pd.Timedelta(days=i*7)).date()),'A',f'O{i}',i,0) for i in range(12)]
        out=values(make_rows(rows)).loc[match_id('2023-24','A','O11')]
        self.assertEqual(out.home_form5_gf,8)  # prior goals 6..10
        self.assertEqual(out.home_form10_gf,5.5)  # prior goals 1..10
        self.assertEqual(out.home_history_n10,10)
        self.assertEqual(out.home_venue_n5,5)

    def test_calendar_midnight_uses_DST_not_fixed_24_hours(self):
        a=local_midnight_utc('2024-03-31','Europe/London')
        b=local_midnight_utc('2024-04-01','Europe/London')
        self.assertEqual((b-a).total_seconds()/3600,23)

    def test_no_lineage_time_exceeds_asof(self):
        out=build_features(sample(),config())
        self.assertFalse((out.source_max_available_at_assumed_utc>out.feature_asof_utc).any())
        self.assertFalse({'result','home_goals','away_goals','match_date','season'} & set(FEATURE_COLUMNS))
        self.assertEqual(len(FEATURE_COLUMNS),40)

    def test_same_team_twice_on_same_date_rejected(self):
        data=sample(); data.loc[1,'home_team']='A'
        with self.assertRaisesRegex(ValueError,'multiple matches'):
            values(data)

    def test_empty_row_cleanup_preserves_partial_invalid_record(self):
        raw=pd.DataFrame({'Date':['01/08/2023',None,None],'HomeTeam':['A',None,'B']})
        clean,report=clean_fd(raw)
        self.assertEqual(report['removed_all_empty_rows'],1)
        self.assertEqual(len(clean),2)
        self.assertEqual(clean.source_data_row.tolist(),[1,3])

    def test_covid_season_july_is_valid_calendar_but_other_year_is_not(self):
        fields={'Div':['E0'],'Date':['26/07/2020'],'HomeTeam':['A'],'AwayTeam':['B'],'FTHG':[0],'FTAG':[0],'FTR':['D']}
        self.assertEqual(audit_matches(pd.DataFrame(fields),'2019-20')['outside_season_dates'],0)
        fields['Date']=['26/07/2022']
        self.assertEqual(audit_matches(pd.DataFrame(fields),'2021-22')['outside_season_dates'],1)


if __name__=='__main__':unittest.main()
