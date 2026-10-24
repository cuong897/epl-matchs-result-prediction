"""Build eight F features; validate current/future counterfactuals on real history."""
import hashlib
import json
from pathlib import Path
import pandas as pd
from player_performance_features import BASE,COLUMNS,build_performance

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    config_path=ROOT/'research/player_performance_config.json'
    config=json.loads(config_path.read_text())
    if config['test_feature_generation_enabled'] or config['features_per_side']!=BASE or config['history_team_matches']!=5:
        raise ValueError('Incompatible F configuration')
    audit=json.loads((ROOT/'reports/player_history/audit.json').read_text())
    path=ROOT/'data/curated/player_match_stats_P_development.csv'
    if sha(path)!=audit['curated_sha256']:raise ValueError('Player artifact changed')
    m=pd.read_csv(ROOT/'data/curated/matches.csv')
    m=m[m.season.isin(config['train_seasons']+config['validation_seasons'])]
    p=pd.read_csv(path,usecols=config['used_player_columns'])
    f,lineage=build_performance(m,p,config['rate_shrinkage_minutes'])
    outputs={}
    for split,count in [('train',1520),('validation',380)]:
        part=f[f.match_id.isin(m.loc[m['split'].eq(split),'match_id'])]
        if len(part)!=count:raise ValueError('Unexpected cohort')
        out=ROOT/f'data/curated/features_F_{split}.csv';part.to_csv(out,index=False)
        outputs[str(out.relative_to(ROOT))]=sha(out)
    lineage.to_csv(ROOT/'data/curated/feature_lineage_F.csv',index=False)
    (ROOT/'research/feature_columns_F.json').write_text(json.dumps(COLUMNS,indent=2)+'\n',encoding='utf-8')
    prefix_m=m[m.match_date.lt('2023-01-01')]
    prefix,_=build_performance(prefix_m,p[p.match_id.isin(prefix_m.match_id)])
    pd.testing.assert_frame_equal(prefix,f[f.match_id.isin(prefix_m.match_id)].reset_index(drop=True))
    changed=p.copy();future=changed.match_date.ge('2023-07-01')&changed.minutes.gt(0)
    changed.loc[future,'goals_scored']+=1;changed.loc[future,'assists']+=2
    mutated,_=build_performance(m,changed)
    prior=set(m.loc[m.match_date.lt('2023-07-01'),'match_id'])
    pd.testing.assert_frame_equal(f[f.match_id.isin(prior)].reset_index(drop=True),mutated[mutated.match_id.isin(prior)].reset_index(drop=True))
    current_id=m.sort_values(['match_date','match_id']).iloc[len(m)//2].match_id
    changed=p.copy();current=changed.match_id.eq(current_id)&changed.minutes.gt(0)
    changed.loc[current,'goals_scored']+=1;changed.loc[current,'assists']+=1
    own,_=build_performance(m,changed)
    pd.testing.assert_frame_equal(f[f.match_id.eq(current_id)].reset_index(drop=True),own[own.match_id.eq(current_id)].reset_index(drop=True))
    shuffled,_=build_performance(m.sample(frac=1,random_state=5),p.sample(frac=1,random_state=6))
    pd.testing.assert_frame_equal(f,shuffled,check_exact=False,atol=1e-12,rtol=0)
    source=pd.to_datetime(lineage.source_max_available_at,utc=True);cutoff=pd.to_datetime(lineage.asof_utc,utc=True)
    if (source.notna()&source.gt(cutoff)).any():raise ValueError('Lineage after cutoff')
    report={'feature_version':config['feature_version'],'feature_count':8,'rows':1900,'train_rows':1520,'validation_rows':380,
            'tests':{'prefix_invariance':True,'future_performance_does_not_change_training':True,
                     'current_performance_does_not_change_own_features':True,'input_order_invariance':True,'lineage_within_cutoff':True},
            'missing_by_feature':f[COLUMNS].isna().sum().to_dict(),'output_sha256':outputs,
            'input_sha256':{str(x.relative_to(ROOT)):sha(x) for x in [path,ROOT/'data/curated/matches.csv',config_path]},
            'code_sha256':{name:sha(ROOT/'scripts'/name) for name in ['player_proxy_features.py','player_performance_features.py','build_player_performance.py']},
            'test_features_generated':False,'models_trained':False}
    out=ROOT/'reports/player_performance';out.mkdir(exist_ok=True)
    (out/'feature_build.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
