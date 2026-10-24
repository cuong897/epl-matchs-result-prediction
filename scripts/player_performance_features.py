"""Performance proxies reuse audited prior-team-match lineage from P."""
from collections import defaultdict
import numpy as np
import pandas as pd
from player_proxy_features import build_proxy

BASE=['f_recent_group_goal90_s180_5','f_recent_group_assist90_s180_5',
      'f_contribution_hhi5','f_recent_group_contribution_share5']
COLUMNS=[f'{side}_{name}' for side in ['home','away'] for name in BASE]


def performance_snapshot(history,shrinkage=180):
    result=dict.fromkeys(BASE,np.nan)
    if not history:return result
    totals=defaultdict(lambda:np.zeros(3))
    for event in history:
        for player,stats in event.items():totals[player]+=np.asarray(stats,dtype=float)
    latest=history[-1]
    last_minutes=sum(stats[0] for stats in latest.values())
    if last_minutes<=0:raise ValueError('Latest historical side has no minutes')
    for j,name in [(1,BASE[0]),(2,BASE[1])]:
        result[name]=sum((stats[0]/last_minutes)*90*totals[player][j]/(totals[player][0]+shrinkage)
                         for player,stats in sorted(latest.items()))
    contributions={player:float(stats[1]+stats[2]) for player,stats in totals.items()}
    total=sum(contributions.values())
    if total>0:
        result[BASE[2]]=sum((c/total)**2 for c in contributions.values())
        result[BASE[3]]=sum(contributions[p] for p in latest)/total
    return result


def build_performance(matches,players,shrinkage=180):
    if shrinkage!=180:raise ValueError('Register a separate feature version for a different prior')
    # This validates IDs, date/availability policy, minutes, both sides and duplicates.
    _,lineage=build_proxy(matches,players)
    for c in ['goals_scored','assists']:
        x=players[c]
        if not np.isfinite(x).all() or x.lt(0).any() or x.mod(1).ne(0).any():raise ValueError(f'Invalid {c}')
    if (players.minutes.eq(0)&(players.goals_scored.gt(0)|players.assists.gt(0))).any():
        raise ValueError('Unresolved contribution with zero minutes')
    events={}
    for key,group in players.groupby(['match_id','historic_team_name'],sort=False):
        positive=group[group.minutes.gt(0)].sort_values('player_season_id')
        events[key]={r.player_season_id:(r.minutes,r.goals_scored,r.assists) for r in positive.itertuples()}
    records={match_id:{'match_id':match_id} for match_id in matches.match_id}
    for row in lineage.itertuples():
        ids=row.history_match_ids.split('|') if row.history_match_ids else []
        history=[events[(match_id,row.team)] for match_id in ids]
        values=performance_snapshot(history,shrinkage)
        records[row.match_id].update({f'{row.side}_{name}':value for name,value in values.items()})
    output=pd.DataFrame(records.values(),columns=['match_id',*COLUMNS])
    order=lineage.match_id.drop_duplicates().tolist()
    return output.set_index('match_id').loc[order].reset_index(),lineage
