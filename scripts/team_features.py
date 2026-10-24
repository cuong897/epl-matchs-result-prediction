"""Date-batched, past-only team features. This module fits no ML models.

Input dates are local calendar dates. The conservative v1 policy excludes ALL
same-date outcomes, even when kickoff times exist. Availability is reconstructed,
not verified historical publication. Targets are consumed only AFTER a batch's
features have been emitted.
"""
from __future__ import annotations

from collections import defaultdict, deque
import hashlib
import json
import math

import pandas as pd

SIDE_FEATURES = [
    'form5_ppg','form5_gf','form5_ga','form10_ppg','form10_gf','form10_ga',
    'history_n10','venue5_ppg','venue_n5','season_matches','season_points',
    'season_ppg','season_gd_per_game','days_since_last_pl','newly_promoted',
    'prior_season_membership_known','elo','missing_history',
]
FEATURE_COLUMNS = [f'{side}_{field}' for side in ['home','away'] for field in SIDE_FEATURES] + [
    'elo_diff','rest_days_diff','h2h_home_ppg5','h2h_n5',
]


def match_id(season: str, home: str, away: str) -> str:
    """Identity independent of outcome, file order, and rescheduled date."""
    payload=json.dumps([season,home,away],ensure_ascii=False,separators=(',',':'))
    return 'epl_' + hashlib.sha256(payload.encode()).hexdigest()[:20]


def local_midnight_utc(day, timezone: str) -> pd.Timestamp:
    return pd.Timestamp(day).tz_localize(timezone).tz_convert('UTC')


def mean(records, index: int):
    return sum(r[index] for r in records)/len(records) if records else math.nan


def build_features(matches: pd.DataFrame, config: dict) -> pd.DataFrame:
    required={'match_id','season','match_date','home_team','away_team','home_goals','away_goals'}
    if not required.issubset(matches):
        raise ValueError(f'Missing input columns: {sorted(required-set(matches))}')
    if config['h2h_window'] != 5 or config['history_policy'] != 'strictly_previous_local_calendar_days_only':
        raise ValueError('This feature version supports day-batched history and H2H window 5 only')
    if matches.match_id.duplicated().any():
        raise ValueError('Duplicate match ID')
    data=matches.copy()
    data['match_date']=pd.to_datetime(data.match_date,format='%Y-%m-%d',errors='raise').dt.normalize()
    if data.match_date.isna().any() or data[['season','home_team','away_team']].isna().any().any():
        raise ValueError('Missing fixture identity/date')
    if data.home_team.eq(data.away_team).any():
        raise ValueError('Team cannot play itself')
    data=data.sort_values(['match_date','match_id']).reset_index(drop=True)
    elo={}
    histories=defaultdict(lambda:deque(maxlen=10))
    last_played={}
    venues=defaultdict(lambda:deque(maxlen=5))
    season_stats=defaultdict(lambda:[0,0,0])  # matches, points, goal difference
    participants=defaultdict(set)
    initialized=set()
    h2h=defaultdict(lambda:deque(maxlen=5))
    current_season=None
    last_available=pd.NaT
    last_match_date=pd.NaT
    output=[]

    for day,batch in data.groupby('match_date',sort=True):
        if batch.season.nunique()!=1:
            raise ValueError('Overlapping seasons in one date batch')
        season=batch.season.iloc[0]
        if current_season!=season:
            if current_season is not None and int(season[:4])<=int(current_season[:4]):
                raise ValueError('Season order goes backwards')
            for team in elo:
                elo[team]=config['elo_initial'] + config['elo_season_retention']*(elo[team]-config['elo_initial'])
            current_season=season
        previous_start=int(season[:4])-1
        previous=f'{previous_start}-{str(previous_start+1)[-2:]}'
        previous_known=bool(participants.get(previous))
        # Validate no team appears twice on one day. This also makes batching unambiguous.
        playing=pd.concat([batch.home_team,batch.away_team])
        if playing.duplicated().any():
            raise ValueError('A team appears in multiple matches on the same day')
        for team in playing:
            if (season,team) not in initialized:
                if previous_known and team not in participants[previous]:
                    elo[team]=config['elo_promoted_prior']
                    histories[team].clear()
                    venues[(team,'home')].clear()
                    venues[(team,'away')].clear()
                else:
                    elo.setdefault(team,config['elo_initial'])
                initialized.add((season,team))

        asof=local_midnight_utc(day,config['timezone'])
        if pd.notna(last_available) and last_available>asof:
            raise AssertionError('A source observation exceeds feature as-of time')
        for row in batch.itertuples():
            if hasattr(row,'prediction_cutoff_assumed_utc') and pd.notna(row.prediction_cutoff_assumed_utc):
                if asof>pd.Timestamp(row.prediction_cutoff_assumed_utc):
                    raise ValueError('Day-start feature snapshot exceeds requested cutoff')
            record={'match_id':row.match_id,'feature_version':config['version'],
                    'feature_asof_utc':asof,'source_max_available_at_assumed_utc':last_available,
                    'history_max_match_date':last_match_date,
                    'availability_status':'reconstructed_assumption'}
            for side,team in [('home',row.home_team),('away',row.away_team)]:
                history=list(histories[team]); venue=list(venues[(team,side)])
                played,points,gd=season_stats[(season,team)]
                stats={}
                for window in [5,10]:
                    recent=history[-window:]
                    stats.update({f'form{window}_ppg':mean(recent,0),f'form{window}_gf':mean(recent,1),f'form{window}_ga':mean(recent,2)})
                stats.update(history_n10=len(history),venue5_ppg=mean(venue,0),venue_n5=len(venue),
                    season_matches=played,season_points=points,
                    season_ppg=points/played if played else math.nan,
                    season_gd_per_game=gd/played if played else math.nan,
                    days_since_last_pl=(day-last_played[team]).days if team in last_played else math.nan,
                    newly_promoted=int(team not in participants[previous]) if previous_known else math.nan,
                    prior_season_membership_known=int(previous_known),elo=elo[team],missing_history=int(not history))
                record.update({f'{side}_{k}':v for k,v in stats.items()})
            prior=h2h[tuple(sorted([row.home_team,row.away_team]))]
            points=[3 if (a==row.home_team and hg>ag) or (b==row.home_team and ag>hg) else 1 if hg==ag else 0 for a,b,hg,ag in prior]
            record.update(elo_diff=record['home_elo']-record['away_elo'],
                          rest_days_diff=record['home_days_since_last_pl']-record['away_days_since_last_pl'],
                          h2h_home_ppg5=sum(points)/len(points) if points else math.nan,h2h_n5=len(points))
            output.append(record)

        # Outcomes from this day become state only AFTER every feature snapshot is emitted.
        for row in batch.itertuples():
            hg,ag=row.home_goals,row.away_goals
            if pd.isna(hg) or pd.isna(ag) or hg<0 or ag<0 or hg%1 or ag%1:
                raise ValueError('Historical builder requires valid completed-match goals')
            home_points=3 if hg>ag else 1 if hg==ag else 0
            away_points=3 if ag>hg else 1 if hg==ag else 0
            expected=1/(1+10**((elo[row.away_team]-elo[row.home_team]-config['elo_home_advantage'])/400))
            actual=1 if hg>ag else .5 if hg==ag else 0
            delta=config['elo_k']*(actual-expected)
            elo[row.home_team]+=delta; elo[row.away_team]-=delta
            for side,team,points,gf,ga in [('home',row.home_team,home_points,hg,ag),('away',row.away_team,away_points,ag,hg)]:
                event=(points,gf,ga,day)
                histories[team].append(event); venues[(team,side)].append(event)
                last_played[team]=day
                totals=season_stats[(season,team)]; totals[0]+=1; totals[1]+=points; totals[2]+=gf-ga
                participants[season].add(team)
            h2h[tuple(sorted([row.home_team,row.away_team]))].append((row.home_team,row.away_team,hg,ag))
        # DateOffset preserves local midnight across DST; a fixed UTC +24h does not.
        last_available=local_midnight_utc(day+pd.DateOffset(days=1),config['timezone'])
        last_match_date=day

    if not output:
        return pd.DataFrame(columns=['match_id']+FEATURE_COLUMNS)
    result=pd.DataFrame(output)
    if result[FEATURE_COLUMNS].isin([math.inf,-math.inf]).any().any():
        raise AssertionError('Infinite feature value')
    return result
