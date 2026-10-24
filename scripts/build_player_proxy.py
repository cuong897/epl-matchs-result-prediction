"""Build and verify P development snapshots; no test feature output."""
import hashlib
import json
from pathlib import Path
import pandas as pd
from player_proxy_features import BASE,COLUMNS,build_proxy

ROOT=Path(__file__).resolve().parents[1]


def main():
    config_path=ROOT/'research/player_proxy_config.json'
    config=json.loads(config_path.read_text())
    if config['test_feature_generation_enabled'] or config['history_team_matches']!=5 or config['features_per_side']!=BASE:
        raise ValueError('Configuration is incompatible with this feature version')
    audit=json.loads((ROOT/'reports/player_history/audit.json').read_text())
    player_path=ROOT/'data/curated/player_match_stats_P_development.csv'
    if hashlib.sha256(player_path.read_bytes()).hexdigest()!=audit['curated_sha256']:raise ValueError('Player artifact changed')
    m=pd.read_csv(ROOT/'data/curated/matches.csv')
    seasons=config['train_seasons']+config['validation_seasons']
    m=m[m.season.isin(seasons)].copy()
    p=pd.read_csv(player_path,usecols=config['used_player_columns'])
    feature,lineage=build_proxy(m,p)
    expected={'train':1520,'validation':380}
    outputs={}
    for split,count in expected.items():
        ids=m.loc[m['split'].eq(split),'match_id']
        part=feature[feature.match_id.isin(ids)]
        if len(part)!=count:raise ValueError('Unexpected common cohort size')
        path=ROOT/f'data/curated/features_P_{split}.csv'
        part.to_csv(path,index=False)
        outputs[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    lineage.to_csv(ROOT/'data/curated/feature_lineage_P.csv',index=False)
    (ROOT/'research/feature_columns_P.json').write_text(json.dumps(COLUMNS,indent=2)+'\n',encoding='utf-8')
    # Real-data temporal invariance: a prefix and future minutes perturbations.
    cutoff='2023-01-01'
    prefix_m=m[m.match_date.lt(cutoff)]
    prefix_p=p[p.match_id.isin(prefix_m.match_id)]
    prefix,_=build_proxy(prefix_m,prefix_p)
    pd.testing.assert_frame_equal(prefix.reset_index(drop=True),feature[feature.match_id.isin(prefix_m.match_id)].reset_index(drop=True))
    changed=p.copy()
    future=changed.match_date.ge('2023-07-01')
    changed.loc[future,'minutes']=45
    mutated,_=build_proxy(m,changed)
    earlier_ids=set(m.loc[m.match_date.lt('2023-07-01'),'match_id'])
    pd.testing.assert_frame_equal(feature[feature.match_id.isin(earlier_ids)].reset_index(drop=True),mutated[mutated.match_id.isin(earlier_ids)].reset_index(drop=True))
    reordered,_=build_proxy(m.sample(frac=1,random_state=9),p.sample(frac=1,random_state=10))
    pd.testing.assert_frame_equal(feature,reordered,check_exact=False,atol=1e-12,rtol=0)
    source=pd.to_datetime(lineage.source_max_available_at,utc=True)
    asof=pd.to_datetime(lineage.asof_utc,utc=True)
    if (source.notna()&source.gt(asof)).any():raise ValueError('Lineage exceeds cutoff')
    report={'feature_version':config['feature_version'],'feature_count':len(COLUMNS),'rows':len(feature),
            'train_rows':1520,'validation_rows':380,'tests':{'prefix_invariance':True,'future_minutes_do_not_change_training':True,
            'input_order_invariance':True,'lineage_within_cutoff':True},
            'missing_by_feature':feature[COLUMNS].isna().sum().to_dict(),
            'zero_history_team_sides':int((feature.home_p_history_n5.eq(0)).sum()+(feature.away_p_history_n5.eq(0)).sum()),
            'output_sha256':outputs,'input_sha256':{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in
                [player_path,ROOT/'data/curated/matches.csv',config_path]},
            'code_sha256':{name:hashlib.sha256((ROOT/'scripts'/name).read_bytes()).hexdigest() for name in ['player_proxy_features.py','build_player_proxy.py']},
            'test_features_generated':False,'models_trained':False}
    out=ROOT/'reports/player_proxy';out.mkdir(exist_ok=True)
    (out/'feature_build.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
