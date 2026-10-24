"""Prepare test covariates with frozen definitions; no estimator fit/test scoring."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from final_models import sha
from audit_player_history import normalize_players
from player_proxy_features import build_proxy,COLUMNS as P_COLUMNS
from player_performance_features import build_performance,COLUMNS as F_COLUMNS
from team_features import build_features,FEATURE_COLUMNS

ROOT=Path(__file__).resolve().parents[1]


def main():
    records=json.loads((ROOT/'research/download_manifest.json').read_text())
    inputs={}
    def verified(relative):
        path=ROOT/relative;digest=sha(path)
        rec=[r for r in records.values() if r.get('path')==relative and r.get('status')=='downloaded']
        if len(rec)!=1 or rec[0]['sha256']!=digest:raise ValueError('Unverified test cache')
        inputs[relative]=digest;return path
    matches=pd.read_csv(ROOT/'data/curated/matches.csv')
    test=matches[matches['split'].eq('test')].copy()
    if len(test)!=380 or set(test.season)!={'2024-25'}:raise ValueError('Unexpected test metadata')
    raw=pd.read_csv(verified('data/raw/fpl/2024-25.csv'))
    positions={'GK','DEF','MID','FWD','AM'}
    if raw.position.isna().any() or not set(raw.position).issubset(positions):raise ValueError('Unknown FPL positions')
    players=raw[raw.position.ne('AM')].copy()
    fixtures=pd.read_csv(verified('data/raw/fpl/2024-25-fixtures.csv'))
    teams=pd.read_csv(verified('data/raw/fpl/2024-25-teams.csv'))
    normalized=normalize_players(players,fixtures,teams,test,'2024-25')
    p,lineage=build_proxy(test,normalized)
    f,_=build_performance(test,normalized)
    # Independent rebuild of A from sequential outcomes; no label-based scoring.
    outcomes=pd.read_csv(ROOT/'data/curated/match_outcomes.csv')
    full=matches.merge(outcomes[['match_id','home_goals','away_goals','result']],on='match_id',validate='one_to_one')
    a=build_features(full,json.loads((ROOT/'research/team_feature_config.json').read_text()))
    exported=pd.read_csv(ROOT/'data/curated/features_A_test.csv')
    expected=a[a.match_id.isin(test.match_id)].set_index('match_id')[FEATURE_COLUMNS].sort_index()
    pd.testing.assert_frame_equal(expected,exported.set_index('match_id')[FEATURE_COLUMNS].sort_index(),check_dtype=False,atol=1e-12,rtol=1e-12)
    # Prefix replay tests on completed previous dates, never current fixture statistics.
    cutoff=sorted(test.match_date.unique())[len(test.match_date.unique())//2]
    prefix=test[test.match_date.lt(cutoff)];subset=normalized[normalized.match_id.isin(prefix.match_id)]
    pp,_=build_proxy(prefix,subset);ff,_=build_performance(prefix,subset)
    pd.testing.assert_frame_equal(pp,p[p.match_id.isin(prefix.match_id)].reset_index(drop=True))
    pd.testing.assert_frame_equal(ff,f[f.match_id.isin(prefix.match_id)].reset_index(drop=True))
    changed=normalized.copy();future=changed.match_date.ge(cutoff)&changed.minutes.gt(0)
    changed.loc[future,'goals_scored']+=1;changed.loc[future,'assists']+=1
    mutated,_=build_performance(test,changed)
    pd.testing.assert_frame_equal(mutated[mutated.match_id.isin(prefix.match_id)].reset_index(drop=True),ff)
    source=pd.to_datetime(lineage.source_max_available_at,utc=True);asof=pd.to_datetime(lineage.asof_utc,utc=True)
    if (source.notna()&source.gt(asof)).any():raise ValueError('Test lineage after cutoff')
    outputs={}
    for group,frame in [('P',p),('F',f)]:
        path=ROOT/f'data/curated/features_{group}_test.csv';frame.to_csv(path,index=False)
        outputs[str(path.relative_to(ROOT))]=sha(path)
    path=ROOT/'data/curated/feature_lineage_PF_test.csv';lineage.to_csv(path,index=False);outputs[str(path.relative_to(ROOT))]=sha(path)
    inputs.update({str(path.relative_to(ROOT)):sha(path) for path in [ROOT/'data/curated/matches.csv',ROOT/'data/curated/match_outcomes.csv',ROOT/'data/curated/features_A_test.csv',
        ROOT/'research/team_feature_config.json',ROOT/'research/player_proxy_config.json',ROOT/'research/player_performance_config.json']})
    result={'test_matches':380,'excluded_manager_rows':int(raw.position.eq('AM').sum()),'test_player_rows':len(normalized),
            'checks':{'A_rebuild_matches_export':True,'P_prefix_invariance':True,'F_prefix_invariance':True,
                      'future_test_performance_does_not_change_prior_features':True,'lineage_within_cutoff':True},
            'input_sha256':inputs,'output_sha256':outputs,
            'code_sha256':{name:sha(ROOT/'scripts'/name) for name in ['prepare_final_features.py','audit_player_history.py','player_proxy_features.py','player_performance_features.py','team_features.py']},
            'models_fitted':0,'test_predictions_generated':False,'test_metrics_computed':False,
            'availability_status':'reconstructed_assumption','player_state_reset_for_test_season':True}
    out=ROOT/'reports/final_preparation';out.mkdir(exist_ok=True)
    (out/'feature_verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if 'sha256' not in k},indent=2))


if __name__=='__main__':main()
