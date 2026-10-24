"""Lagged personnel usage only: snapshots precede whole-day state updates."""
from collections import defaultdict, deque
import numpy as np
import pandas as pd

BASE = ['p_history_n5','p_participants_n5','p_minutes_hhi5','p_top11_minutes_share5',
        'p_last_returning_minutes_share5','p_mean_minutes_overlap5']
COLUMNS = [f'{side}_{name}' for side in ['home','away'] for name in BASE]


def usage_snapshot(history):
    result = dict.fromkeys(BASE,np.nan)
    result['p_history_n5'] = len(history)
    if not history:return result
    totals=defaultdict(float)
    for event in history:
        for player,minutes in event['minutes'].items():totals[player]+=minutes
    total=sum(totals.values())
    shares=np.asarray(list(totals.values()),dtype=float)/total
    result.update(p_participants_n5=len(totals),p_minutes_hhi5=float(np.sum(shares**2)),
                  p_top11_minutes_share5=float(np.sort(shares)[-11:].sum()))
    if len(history)>=2:
        earlier=set().union(*(set(event['minutes']) for event in list(history)[:-1]))
        latest=history[-1]['minutes']
        result['p_last_returning_minutes_share5']=sum(m for p,m in latest.items() if p in earlier)/sum(latest.values())
        overlap=[]
        for a,b in zip(list(history)[:-1],list(history)[1:]):
            am,bm=a['minutes'],b['minutes'];at,bt=sum(am.values()),sum(bm.values())
            overlap.append(sum(min(am[p]/at,bm[p]/bt) for p in set(am)&set(bm)))
        result['p_mean_minutes_overlap5']=float(np.mean(overlap))
    return result


def build_proxy(matches,players):
    """No labels accepted/used; require exact canonical player match membership."""
    m=matches[['match_id','season','match_date','home_team','away_team']].copy()
    if m.match_id.duplicated().any():raise ValueError('Duplicate canonical match')
    if m.home_team.eq(m.away_team).any():raise ValueError('Self match')
    p=players[['season','match_id','player_season_id','historic_team_name','match_date','minutes','available_at_assumed_utc']].copy()
    if p.isna().any().any():raise ValueError('Missing required player fields')
    if set(p.match_id)!=set(m.match_id):raise ValueError('Player/canonical match cohort mismatch')
    if p.duplicated(['match_id','player_season_id']).any():raise ValueError('Duplicate player in match')
    if not np.isfinite(p.minutes).all() or p.minutes.lt(0).any() or p.minutes.gt(90).any():raise ValueError('Invalid minutes')
    m['match_date']=pd.to_datetime(m.match_date).dt.normalize()
    p['match_date']=pd.to_datetime(p.match_date).dt.normalize()
    p['available_at_assumed_utc']=pd.to_datetime(p.available_at_assumed_utc,utc=True)
    check=p.merge(m,on='match_id',suffixes=('','_match'),validate='many_to_one')
    if check.season.ne(check.season_match).any() or check.match_date.ne(check.match_date_match).any():raise ValueError('Player date/season disagrees with match')
    if (~(check.historic_team_name.eq(check.home_team)|check.historic_team_name.eq(check.away_team))).any():raise ValueError('Player belongs to neither fixture side')
    if not p.player_season_id.str.split(':').str[0].eq(p.season).all():raise ValueError('Player ID is not season-scoped')
    # Availability is reconstructed next local midnight, never silently earlier.
    expected=(p.match_date+pd.Timedelta(days=1)).dt.tz_localize('Europe/London').dt.tz_convert('UTC')
    if p.available_at_assumed_utc.ne(expected).any():raise ValueError('Unexpected availability policy')
    events={}
    for (match_id,team),group in p.groupby(['match_id','historic_team_name'],sort=False):
        minutes=dict(zip(group.loc[group.minutes.gt(0),'player_season_id'],group.loc[group.minutes.gt(0),'minutes']))
        if not minutes:raise ValueError('No observed minutes for fixture side')
        events[(match_id,team)]={'match_id':match_id,'date':group.match_date.iloc[0],
                                'available_at':group.available_at_assumed_utc.max(),'minutes':minutes}
    if len(events)!=2*len(m):raise ValueError('Incomplete player sides')
    state=defaultdict(lambda:deque(maxlen=5))
    records=[];lineage=[]
    for date,batch in m.sort_values(['match_date','match_id']).groupby('match_date',sort=True):
        seen=set();cutoff=date.tz_localize('Europe/London').tz_convert('UTC')
        for row in batch.itertuples():
            record={'match_id':row.match_id}
            for side,team in [('home',row.home_team),('away',row.away_team)]:
                key=(row.season,team)
                if key in seen:raise ValueError('Team plays twice on same date')
                seen.add(key)
                history=state[key]
                if history and (max(e['date'] for e in history)>=date or max(e['available_at'] for e in history)>cutoff):
                    raise ValueError('Future/same-day information in history')
                record.update({f'{side}_{name}':value for name,value in usage_snapshot(history).items()})
                lineage.append({'match_id':row.match_id,'side':side,'season':row.season,'team':team,
                                'asof_utc':cutoff,'history_match_ids':'|'.join(e['match_id'] for e in history),
                                'source_max_match_date':max((e['date'] for e in history),default=pd.NaT),
                                'source_max_available_at':max((e['available_at'] for e in history),default=pd.NaT),
                                'availability_status':'reconstructed_assumption'})
            records.append(record)
        for row in batch.itertuples():
            for team in [row.home_team,row.away_team]:state[(row.season,team)].append(events[(row.match_id,team)])
    return pd.DataFrame(records,columns=['match_id',*COLUMNS]),pd.DataFrame(lineage)
