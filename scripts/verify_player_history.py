"""Verify curated development player history without training or test metrics."""
import hashlib
import json
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]


def main():
    audit=json.loads((ROOT/'reports/player_history/audit.json').read_text())
    path=ROOT/'data/curated/player_match_stats_P_development.csv'
    assert hashlib.sha256(path.read_bytes()).hexdigest()==audit['curated_sha256']
    assert hashlib.sha256((ROOT/'scripts/audit_player_history.py').read_bytes()).hexdigest()==audit['code_sha256']
    assert hashlib.sha256((ROOT/'research/player_history_corrections.json').read_bytes()).hexdigest()==audit['corrections_sha256']
    assert hashlib.sha256((ROOT/'data/curated/matches.csv').read_bytes()).hexdigest()==audit['canonical_matches_sha256']
    for relative,expected in audit['input_sha256'].items():
        assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==expected,relative
    d=pd.read_csv(path)
    assert len(d)==128543 and d.match_id.nunique()==1900
    assert not d.duplicated(['season','match_id','element']).any()
    assert set(d.season)==set(audit['normalized_seasons'])
    assert d.season.str[:4].astype(int).between(2019,2023).all()
    bad=d.advanced_stats_quality.eq('fixture_wide_zero_starts_xg_xa_unusable')
    assert d.loc[bad,['starts','expected_goals','expected_assists']].isna().all().all()
    assert d.loc[bad,'match_id'].nunique()==136
    assert d[['minutes','goals_scored','assists']].notna().all().all()
    coverage=pd.read_csv(ROOT/'reports/player_history/coverage_by_team_season.csv')
    assert len(coverage)==100 and coverage.matches.eq(38).all()
    report={'rows':len(d),'matches':int(d.match_id.nunique()),'unique_player_match_keys':True,
            'all_100_team_seasons_have_38_matches':True,'invalid_advanced_fixture_count':136,
            'invalid_advanced_values_are_null':True,'curated_hash_matches':True,
            'source_code_and_correction_hashes_match':True,'test_season_absent':True,
            'mandatory_performance_fields_complete':True}
    (ROOT/'reports/player_history/artifact_verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
