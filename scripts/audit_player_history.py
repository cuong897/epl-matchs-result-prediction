"""Audit training/validation FPL history, without fitting or reading test stats."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from audit_pilot import TEAM_ALIASES, fixture_table, link_matches

ROOT = Path(__file__).resolve().parents[1]
CORE = ['element','fixture','kickoff_time','was_home','opponent_team','minutes','goals_scored','assists']
OPTIONAL = ['starts','expected_goals','expected_assists','position','team','birth_date','value']


def read_players(path):
    try:return pd.read_csv(path,encoding='utf-8-sig'),'utf-8-sig'
    except UnicodeDecodeError:return pd.read_csv(path,encoding='latin1'),'latin1_fallback_not_verified_original_encoding'


def remove_documented_placeholders(players, fixtures, season, corrections):
    """Never keep last/drop duplicate blindly; require a documented unplayed event."""
    p = players.copy()
    excluded = []
    for rule in corrections:
        if rule['season'] != season:continue
        old = p.fixture.eq(rule['fixture']) & p.kickoff_time.eq(rule['obsolete_kickoff'])
        if not old.any():continue
        fx = fixtures[fixtures.id.eq(rule['fixture'])]
        if len(fx)!=1 or fx.iloc[0].kickoff_time!=rule['completed_kickoff']:
            raise ValueError('Correction disagrees with completed fixture')
        if not p.loc[old,'minutes'].eq(0).all() or not p.loc[old,['team_h_score','team_a_score']].isna().all().all():
            raise ValueError('Refuse to discard a row with played minutes or scores')
        replacement = p[p.fixture.eq(rule['fixture']) & p.kickoff_time.eq(rule['completed_kickoff'])]
        if not set(p.loc[old,'element']).issubset(set(replacement.element)):
            raise ValueError('Missing completed replacement for placeholder player')
        excluded.append({'season':season,'fixture':rule['fixture'],'rows':int(old.sum()),
                         'reason':'documented_unplayed_placeholder','source_rows':p.loc[old,'source_data_row'].tolist() if 'source_data_row' in p else [],
                         'evidence':rule['evidence']})
        p = p.loc[~old].copy()
    if p.duplicated(['element','fixture']).any():raise ValueError('Unresolved duplicate player-fixture')
    return p,excluded


def normalize_players(p, fixtures, teams, matches, season):
    """Team-at-match from fixture side, never end-of-season player team."""
    if p[CORE].isna().any().any():raise ValueError('Missing mandatory player fields')
    if not p.was_home.isin([True,False]).all():raise ValueError('Invalid home flag')
    for name in ['element','fixture','opponent_team','minutes','goals_scored','assists']:
        x = pd.to_numeric(p[name],errors='coerce')
        if (x.isna()|x.lt(0)|x.mod(1).ne(0)).any():raise ValueError(f'Invalid {name}')
    if p.minutes.gt(90).any():raise ValueError('Minutes above 90')
    if p.duplicated(['element','fixture']).any():raise ValueError('Duplicate player-fixture')
    fx = fixture_table(fixtures,teams)
    p = p.merge(fx[['id','team_h','team_a','kickoff_utc','date','home','away']],left_on='fixture',right_on='id',how='left',validate='many_to_one')
    if p.id.isna().any():raise ValueError('Unknown fixture')
    if p.opponent_team.ne(p.team_a.where(p.was_home,p.team_h)).any():raise ValueError('Opponent does not match fixture side')
    p['historic_team_id'] = p.team_h.where(p.was_home,p.team_a)
    p['historic_team_name'] = p.home.where(p.was_home,p.away)
    p['match_date'] = p['date']
    kickoff = pd.to_datetime(p.kickoff_time,utc=True,errors='coerce')
    if kickoff.isna().any():raise ValueError('Invalid player kickoff time')
    # Within-day delays stay visible; cross-date disagreement cannot silently move a match.
    if kickoff.dt.tz_convert('Europe/London').dt.strftime('%Y-%m-%d').ne(p.match_date).any():
        raise ValueError('Unresolved player/fixture calendar date disagreement')
    p['kickoff_conflict_within_day'] = kickoff.ne(p.kickoff_utc)
    lookup = matches[matches.season.eq(season)][['match_id','match_date','home_team','away_team']]
    p = p.merge(lookup,left_on=['match_date','home','away'],right_on=['match_date','home_team','away_team'],how='left',validate='many_to_one')
    if p.match_id.isna().any():raise ValueError('Unmapped canonical match')
    for stat in ['starts','expected_goals','expected_assists']:
        if stat in p:
            numeric = pd.to_numeric(p[stat],errors='coerce')
            if (numeric.isna()|numeric.lt(0)).any():raise ValueError(f'Invalid optional statistic {stat}')
            if stat=='starts' and not numeric.isin([0,1]).all():raise ValueError('Invalid starts flag')
    p['season'] = season
    p['player_season_id'] = season+':'+p.element.astype(str)
    midnight = pd.to_datetime(p.match_date)+pd.Timedelta(days=1)
    p['available_at_assumed_utc'] = midnight.dt.tz_localize('Europe/London').dt.tz_convert('UTC')
    p['availability_status'] = 'reconstructed_assumption'
    return p


def mask_unusable_advanced(p):
    """Keep genuine individual zeros; mask fixture-wide all-zero starts/xG/xA."""
    p=p.copy()
    advanced=['starts','expected_goals','expected_assists']
    if not set(advanced).issubset(p.columns):
        p['advanced_stats_quality']='columns_unavailable'
        return p,{'fixture_wide_zero_advanced_stats':None}
    grouped=p.groupby('match_id')[advanced].sum()
    invalid=grouped.eq(0).all(axis=1)
    ids=set(grouped.index[invalid])
    selected=p.match_id.isin(ids)
    diagnostic={'fixture_wide_zero_advanced_stats':len(ids),
                'rows_masked_advanced_stats':int(selected.sum()),
                'fixtures_with_22_recorded_starts':int(grouped.starts.eq(22).sum()),
                'first_date_with_22_recorded_starts':p.loc[p.match_id.isin(grouped.index[grouped.starts.eq(22)]),'match_date'].min() if grouped.starts.eq(22).any() else None}
    p['advanced_stats_quality']='recorded_publication_time_unverified'
    p.loc[selected,'advanced_stats_quality']='fixture_wide_zero_starts_xg_xa_unusable'
    for c in advanced:
        p[c]=p[c].astype(float)
        p.loc[selected,c]=np.nan
    return p,diagnostic


def main():
    records = json.loads((ROOT/'research/download_manifest.json').read_text(encoding='utf-8'))
    corrections = json.loads((ROOT/'research/player_history_corrections.json').read_text())
    matches = pd.read_csv(ROOT/'data/curated/matches.csv')
    matches = matches[matches.season.str[:4].astype(int).between(2016,2023)]
    hashes = {}
    def verified(path):
        relative = str(path.relative_to(ROOT)).replace('\\','/')
        found = [r for r in records.values() if r.get('path')==relative and r.get('status')=='downloaded']
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if len(found)!=1 or digest!=found[0]['sha256']:raise ValueError(f'Unverified cache {relative}')
        hashes[relative] = digest
        return digest
    summaries=[];curated=[];coverage=[];exclusions=[];links=[]
    for year in range(2016,2024):
        season=f'{year}-{str(year+1)[-2:]}'
        path=ROOT/f'data/raw/fpl/{season}.csv'
        digest=verified(path)
        p,encoding=read_players(path)
        p['source_data_row']=np.arange(1,len(p)+1)
        absent=sorted(set(CORE)-set(p.columns))
        summary={'season':season,'raw_rows':len(p),'encoding':encoding,'mandatory_columns_absent':absent,
                 'fixture_count_raw':int(p.fixture.nunique()),'duplicate_player_fixture_rows_raw':int(p.duplicated(['element','fixture']).sum()),
                 'optional_missing_rows':{c:int(p[c].isna().sum()) if c in p else None for c in OPTIONAL},
                 'announced_XI_at_T_minus_60_verified':False,'market_value_available':False}
        if absent:raise ValueError(f'Missing core columns: {season}')
        summary['core_missing_rows']={c:int(p[c].isna().sum()) for c in CORE}
        fx_path=ROOT/f'data/raw/fpl/{season}-fixtures.csv'
        team_path=ROOT/f'data/raw/fpl/{season}-teams.csv'
        summary['fixture_file_available']=fx_path.exists()
        summary['team_mapping_file_available']=team_path.exists()
        if not fx_path.exists() or not team_path.exists():
            summary['status']='not_normalized_missing_fixture_or_team_mapping_file'
            summaries.append(summary)
            continue
        verified(fx_path);verified(team_path)
        f=pd.read_csv(fx_path);t=pd.read_csv(team_path)
        clean,excluded=remove_documented_placeholders(p,f,season,corrections)
        exclusions.extend(excluded)
        normalized=normalize_players(clean,f,t,matches,season)
        normalized['source_sha256']=digest
        fd_path=ROOT/f'data/raw/football_data/{season}.csv'
        verified(fd_path)
        fd=pd.read_csv(fd_path)
        cross,linked=link_matches(fd,fixture_table(f,t),season)
        if cross['matched']!=380 or cross['fd_only'] or cross['fpl_only']:raise ValueError('Incomplete fixture linkage')
        score=normalized.merge(f[['id','team_h_score','team_a_score']],on='id',suffixes=('','_fixture'),validate='many_to_one')
        score_mismatch=int((score.team_h_score.ne(score.team_h_score_fixture)|score.team_a_score.ne(score.team_a_score_fixture)).sum())
        if score_mismatch:raise ValueError('Player rows disagree with fixture score')
        # Per-team coverage checks count matches/participants, not target distributions.
        by_side=normalized.groupby(['match_id','historic_team_name']).agg(rows=('element','size'),participants=('minutes',lambda x:int(x.gt(0).sum())),minutes=('minutes','sum')).reset_index()
        if len(by_side)!=760 or by_side.participants.lt(11).any():raise ValueError('Missing team-side player coverage')
        for team,group in by_side.groupby('historic_team_name'):
            coverage.append({'season':season,'team':team,'matches':len(group),'participants_min':int(group.participants.min()),
                             'participants_max':int(group.participants.max()),'minutes_min':int(group.minutes.min()),'minutes_max':int(group.minutes.max())})
        if 'team' in normalized:
            wrong=normalized.team.replace(TEAM_ALIASES).ne(normalized.historic_team_name)
            summary['archived_team_name_disagreements']=int(wrong.sum())
            summary['active_player_team_name_disagreements']=int((wrong&normalized.minutes.gt(0)).sum())
        else:summary['archived_team_name_disagreements']=None
        summary.update(status='normalized_and_linked',curated_rows=len(normalized),excluded_placeholder_rows=len(p)-len(normalized),
                       linked_fixtures=cross['matched'],team_sides=len(by_side),min_participants_per_side=int(by_side.participants.min()),
                       player_fixture_time_conflict_rows=int(normalized.kickoff_conflict_within_day.sum()),score_mismatch_rows=score_mismatch,
                       clock_conflicts_vs_football_data=cross.get('clock_mismatches_assuming_FD_London'))
        if 'starts' in normalized:
            counts=normalized.groupby(['match_id','historic_team_name']).starts.sum()
            summary['sides_with_11_recorded_starts']=int(counts.eq(11).sum())
        else:summary['sides_with_11_recorded_starts']=None
        normalized,advanced_quality=mask_unusable_advanced(normalized)
        summary['advanced_quality']=advanced_quality
        cols=['season','match_id','player_season_id','element','historic_team_id','historic_team_name','match_date',
              'kickoff_time','kickoff_utc','kickoff_conflict_within_day','minutes','goals_scored','assists',
              'available_at_assumed_utc','availability_status','source_data_row','source_sha256','advanced_stats_quality']
        cols += [c for c in ['starts','expected_goals','expected_assists'] if c in normalized]
        curated.append(normalized[cols]);summaries.append(summary);links.append(linked)
    output=ROOT/'reports/player_history'
    output.mkdir(exist_ok=True)
    curated_path=ROOT/'data/curated/player_match_stats_P_development.csv'
    pd.concat(curated,ignore_index=True).to_csv(curated_path,index=False)
    pd.DataFrame(coverage).to_csv(output/'coverage_by_team_season.csv',index=False)
    pd.concat(links,ignore_index=True).to_csv(output/'fixture_links.csv',index=False)
    result={'audited_at_utc':datetime.now(timezone.utc).isoformat(),'scope':'training_and_validation_only_no_model_fit_or_test_scoring',
            'seasons':summaries,'documented_exclusions':exclusions,'input_sha256':hashes,
            'curated_rows':sum(len(d) for d in curated),'normalized_seasons':[s['season'] for s in summaries if s['status']=='normalized_and_linked'],
            'cross_season_player_identity':'not resolved; player IDs explicitly scoped to season',
            'fixture_clock_policy':'retain both clocks; same-local-day discrepancies flagged; other unresolved dates rejected',
            'availability_policy':'assumed following Europe/London midnight; actual historical publication/version unverified',
            'github_commit_resolution':'GitHub API rate limited; raw URLs use master and each downloaded file is SHA-256 frozen',
            'source_rights':'repository software license does not establish unrestricted upstream data redistribution rights',
            'curated_sha256':hashlib.sha256(curated_path.read_bytes()).hexdigest(),
            'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'corrections_sha256':hashlib.sha256((ROOT/'research/player_history_corrections.json').read_bytes()).hexdigest(),
            'canonical_matches_sha256':hashlib.sha256((ROOT/'data/curated/matches.csv').read_bytes()).hexdigest(),
            'test_player_stats_read':False,'models_trained':False}
    (output/'audit.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'curated_rows':result['curated_rows'],'seasons':summaries,'exclusions':exclusions},indent=2))


if __name__=='__main__':main()
