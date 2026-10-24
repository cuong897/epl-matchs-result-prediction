"""Structural pilot audit. No training, label frequencies, or model metrics.

Run: python scripts/audit_pilot.py
All reported coverage refers only to the downloaded files, not all history.
"""
from __future__ import annotations

import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TEAM_ALIASES = {'Man Utd': 'Man United', 'Spurs': 'Tottenham', 'Sheffield Utd': 'Sheffield United'}
PLAYER_POSITIONS = {'GK', 'DEF', 'MID', 'FWD'}
CORE = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR']
# Calendar QA only, never a predictive feature or inferred season boundary.
# Official revised calendar: https://www.premierleague.com/en/news/1702418
SEASON_END_OVERRIDES = {'2019-20': '2020-07-26'}


def parse_fd_dates(values: pd.Series) -> pd.Series:
    result = pd.to_datetime(values, format='%d/%m/%Y', errors='coerce')
    return result.fillna(pd.to_datetime(values, format='%d/%m/%y', errors='coerce'))


def missing_counts(df: pd.DataFrame, columns: list[str]) -> dict:
    return {c: int(df[c].isna().sum()) if c in df else None for c in columns}


def audit_matches(df: pd.DataFrame, season: str) -> dict:
    absent = sorted(set(CORE) - set(df.columns))
    if absent:
        return {'season': season, 'rows': len(df), 'missing_columns': absent, 'core_pass': False}
    dates = parse_fd_dates(df.Date)
    home = pd.to_numeric(df.FTHG, errors='coerce')
    away = pd.to_numeric(df.FTAG, errors='coerce')
    invalid_goals = home.isna() | away.isna() | home.lt(0) | away.lt(0) | home.mod(1).ne(0) | away.mod(1).ne(0)
    expected = pd.Series('D', index=df.index).mask(home.gt(away), 'H').mask(home.lt(away), 'A')
    mismatches = int((expected.ne(df.FTR) | invalid_goals).sum())
    starts = int(season[:4])
    season_end = SEASON_END_OVERRIDES.get(season, f'{starts+1}-06-30')
    outside = int((dates.lt(f'{starts}-07-01') | dates.gt(season_end)).sum())
    teams = pd.concat([df.HomeTeam, df.AwayTeam]).value_counts()
    times = df['Time'].astype('string') if 'Time' in df else pd.Series(pd.NA, index=df.index, dtype='string')
    valid_time = pd.to_datetime(times, format='%H:%M', errors='coerce').notna()
    core_missing = missing_counts(df, CORE)
    keys = pd.DataFrame({'date': dates, 'home': df.HomeTeam, 'away': df.AwayTeam})
    duplicate = int(keys.duplicated().sum())
    duplicate_pair = int(df.duplicated(['HomeTeam', 'AwayTeam']).sum())
    bad_division = int(df.Div.ne('E0').sum()) if 'Div' in df else len(df)
    self_matches = int(df.HomeTeam.eq(df.AwayTeam).sum())
    side_counts_ok = bool(df.HomeTeam.value_counts().eq(19).all() and df.AwayTeam.value_counts().eq(19).all())
    core_pass = (len(df) == 380 and len(teams) == 20 and teams.eq(38).all() and side_counts_ok
                 and not any(core_missing.values()) and not dates.isna().any() and not outside
                 and not duplicate and not duplicate_pair and not mismatches and not bad_division and not self_matches)
    return {
        'season': season, 'rows': len(df), 'columns': len(df.columns), 'teams': len(teams),
        'matches_per_team_min': int(teams.min()), 'matches_per_team_max': int(teams.max()),
        'home_away_19_each': side_counts_ok, 'missing_core': core_missing,
        'invalid_dates': int(dates.isna().sum()), 'outside_season_dates': outside,
        'duplicate_match_keys': duplicate, 'duplicate_ordered_team_pairs': duplicate_pair,
        'self_matches': self_matches, 'non_E0_rows': bad_division,
        'invalid_goals': int(invalid_goals.sum()), 'result_goal_inconsistencies': mismatches,
        'valid_clock_times': int(valid_time.sum()), 'date_min': str(dates.min().date()),
        'date_max': str(dates.max().date()), 'core_pass': bool(core_pass),
        'optional_stats_missing': missing_counts(df, ['HS','AS','HST','AST','HC','AC','HY','AY','HR','AR']),
        'available_at_evidence': 'unknown; retrospective reconstruction required',
    }


def fixture_table(fixtures: pd.DataFrame, teams: pd.DataFrame) -> pd.DataFrame:
    if fixtures.id.duplicated().any() or teams.id.duplicated().any():
        raise ValueError('Duplicate fixture/team ID')
    names = teams.set_index('id')['name'].replace(TEAM_ALIASES)
    out = fixtures[['id', 'kickoff_time', 'team_h', 'team_a']].copy()
    out['home'] = out.team_h.map(names)
    out['away'] = out.team_a.map(names)
    out['kickoff_utc'] = pd.to_datetime(out.kickoff_time, utc=True, errors='coerce')
    if out[['home','away','kickoff_utc']].isna().any().any():
        raise ValueError('Unknown team mapping or invalid fixture time')
    out['date'] = out.kickoff_utc.dt.tz_convert('Europe/London').dt.strftime('%Y-%m-%d')
    return out


def link_matches(fd: pd.DataFrame, fx: pd.DataFrame, season: str) -> tuple[dict, pd.DataFrame]:
    left = pd.DataFrame({'date': parse_fd_dates(fd.Date).dt.strftime('%Y-%m-%d'), 'home': fd.HomeTeam, 'away': fd.AwayTeam})
    left['fd_row_1based'] = range(1, len(fd)+1)
    merged = left.merge(fx[['id','date','home','away','kickoff_utc']], on=['date','home','away'], how='outer', validate='one_to_one', indicator=True)
    counts = merged['_merge'].value_counts()
    summary = {'season':season, 'matched':int(counts.get('both',0)), 'fd_only':int(counts.get('left_only',0)), 'fpl_only':int(counts.get('right_only',0))}
    matched = merged[merged['_merge'].eq('both')].copy()
    if 'Time' in fd:
        naive = pd.to_datetime(parse_fd_dates(fd.Date).dt.strftime('%Y-%m-%d') + ' ' + fd.Time, format='%Y-%m-%d %H:%M', errors='coerce')
        clock = naive.dt.tz_localize('Europe/London', ambiguous='NaT', nonexistent='NaT').dt.tz_convert('UTC')
        lookup = pd.Series(clock.tolist(), index=range(1,len(fd)+1))
        candidate = matched.fd_row_1based.map(lookup)
        summary['clock_mismatches_assuming_FD_London'] = int((candidate.isna() | candidate.ne(matched.kickoff_utc)).sum())
        matched['fd_kickoff_utc_assuming_London'] = candidate
        matched['time_conflict'] = candidate.isna() | candidate.ne(matched.kickoff_utc)
        summary['time_conflict_details'] = [
            {'date':row.date, 'home':row.home, 'away':row.away,
             'fd_kickoff_utc_assuming_London':str(row.fd_kickoff_utc_assuming_London),
             'fpl_recorded_kickoff_utc':str(row.kickoff_utc)}
            for row in matched[matched.time_conflict].itertuples()
        ]
    else:
        matched['fd_kickoff_utc_assuming_London'] = pd.NaT
        matched['time_conflict'] = pd.NA
    summary['FD_timezone_assumption'] = 'Europe/London; consistency check, not independent historical publication proof'
    matched['season'] = season
    matched = matched.rename(columns={'kickoff_utc':'fpl_recorded_kickoff_utc'})
    return summary, matched[['season','fd_row_1based','id','date','home','away','fd_kickoff_utc_assuming_London','fpl_recorded_kickoff_utc','time_conflict']]


def audit_players(df: pd.DataFrame, fx: pd.DataFrame, teams: pd.DataFrame, season: str) -> dict:
    unknown = sorted(set(df.position.dropna()) - PLAYER_POSITIONS - {'AM'})
    if unknown or df.position.isna().any():
        raise ValueError(f'Unknown player positions: {unknown}; missing={df.position.isna().sum()}')
    if not df.was_home.isin([True, False]).all():
        raise ValueError('Missing or invalid was_home flag')
    p = df[df.position.isin(PLAYER_POSITIONS)].copy()
    duplicate = int(p.duplicated(['element','fixture']).sum())
    if duplicate:
        raise ValueError('Duplicate player-fixture rows; cannot aggregate safely')
    p = p.merge(fx[['id','team_h','team_a','kickoff_utc']], left_on='fixture', right_on='id', how='left', validate='many_to_one')
    p['historic_team_id'] = p.team_h.where(p.was_home, p.team_a)
    expected_opponent = p.team_a.where(p.was_home, p.team_h)
    names = teams.set_index('id')['name'].replace(TEAM_ALIASES)
    historic_name = p.historic_team_id.map(names)
    team_disagrees = historic_name.ne(p.team.replace(TEAM_ALIASES))
    starts = pd.to_numeric(p.starts, errors='coerce')
    minutes = pd.to_numeric(p.minutes, errors='coerce')
    players_started = p[starts.eq(1)].groupby(['fixture','was_home']).element.nunique()
    expected_sides = pd.MultiIndex.from_product([fx.id.tolist(), [False,True]], names=['fixture','was_home'])
    players_started = players_started.reindex(expected_sides, fill_value=0)
    complete_fixtures = players_started.eq(11).groupby(level=0).all()
    kickoff = pd.to_datetime(p.kickoff_time, utc=True, errors='coerce')
    columns = ['element','fixture','minutes','goals_scored','assists','starts','expected_goals','expected_assists','value']
    invalid_nonnegative = {}
    for c in ['minutes','goals_scored','assists','expected_goals','expected_assists']:
        x = pd.to_numeric(p[c], errors='coerce')
        invalid_nonnegative[c] = int((x.isna() | x.lt(0)).sum())
    return {
        'season':season, 'raw_rows':len(df), 'player_rows':len(p),
        'excluded_manager_rows':int(df.position.eq('AM').sum()),
        'unique_season_player_ids':int(p.element.nunique()), 'fixtures_with_player_rows':int(p.fixture.nunique()),
        'missing_fields': missing_counts(p, columns), 'duplicate_player_fixture_rows':duplicate,
        'unmapped_fixture_rows':int(p.id.isna().sum()),
        'opponent_id_mismatches':int(expected_opponent.ne(p.opponent_team).sum()),
        'kickoff_mismatches_vs_fixture_file':int((kickoff.isna() | kickoff.ne(p.kickoff_utc)).sum()),
        'team_name_mismatches_vs_fixture_side':int(team_disagrees.sum()),
        'active_player_team_name_mismatches':int((team_disagrees & minutes.gt(0)).sum()),
        'invalid_nonnegative_stats':invalid_nonnegative,
        'invalid_starts_flags':int((starts.isna() | ~starts.isin([0,1])).sum()),
        'minutes_above_90':int(minutes.gt(90).sum()),
        'player_rows_minutes_zero':int(minutes.eq(0).sum()),
        'fixture_sides_with_11_recorded_starters':int(players_started.eq(11).sum()),
        'fixtures_with_22_recorded_starters':int(complete_fixtures.sum()),
        'starter_count_histogram':{str(k):int(v) for k,v in players_started.value_counts().sort_index().items()},
        'announced_XI_at_cutoff_verified':False,
        'market_value_available':False,
        'birth_date_available':bool('birth_date' in p.columns),
        'lineup_semantics':'starts is post-match actual participation; exclude current-match starts from T-60 input',
        'performance_semantics':'historical match stats can be lagged only after availability policy; not pre-match current-row features',
    }


def main() -> None:
    records = json.loads((ROOT/'research/download_manifest.json').read_text(encoding='utf-8'))
    specs = json.loads((ROOT/'research/pilot_sources.json').read_text(encoding='utf-8'))
    for spec in specs:
        path = ROOT/spec['path']
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != records[spec['id']]['sha256']:
            raise ValueError(f"Raw checksum mismatch: {spec['id']}")
    result = {'audited_at_utc':datetime.now(timezone.utc).isoformat(),
              'runtime':{'python':platform.python_version(),'pandas':pd.__version__},
              'scope':'structural_audit_only; no model or label-distribution analysis',
              'matches':[], 'players':[], 'cross_source':[]}
    links = []
    for season in ['2015-16','2023-24','2024-25']:
        fd = pd.read_csv(ROOT/f'data/raw/football_data/{season}.csv')
        result['matches'].append(audit_matches(fd,season))
        if season == '2015-16':
            continue
        players = pd.read_csv(ROOT/f'data/raw/fpl/{season}.csv')
        fixtures = pd.read_csv(ROOT/f'data/raw/fpl/{season}-fixtures.csv')
        teams = pd.read_csv(ROOT/f'data/raw/fpl/{season}-teams.csv')
        fx = fixture_table(fixtures, teams)
        cross, linked = link_matches(fd,fx,season)
        score_check = linked.merge(fd[['FTHG','FTAG']].assign(fd_row_1based=range(1,len(fd)+1)), on='fd_row_1based', validate='one_to_one')
        score_check = score_check.merge(fixtures[['id','team_h_score','team_a_score']], on='id', validate='one_to_one')
        cross['final_score_inconsistencies_between_sources'] = int((score_check.FTHG.ne(score_check.team_h_score) | score_check.FTAG.ne(score_check.team_a_score)).sum())
        result['cross_source'].append(cross)
        links.append(linked)
        result['players'].append(audit_players(players,fx,teams,season))
    output = ROOT/'reports'
    output.mkdir(exist_ok=True)
    (output/'pilot_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # Identifier links deliberately contain no goals, results, or probabilities.
    pd.concat(links,ignore_index=True).to_csv(output/'pilot_match_links.csv',index=False)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
