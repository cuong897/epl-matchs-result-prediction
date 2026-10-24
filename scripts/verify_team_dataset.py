"""Real-data integration checks; never mutate raw files or fit a model."""
import hashlib
import json
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal

from team_features import FEATURE_COLUMNS,build_features

ROOT=Path(__file__).resolve().parents[1]


def normalized(frame):
    return frame.set_index('match_id')[FEATURE_COLUMNS].sort_index()


def main():
    curated=ROOT/'data/curated'
    matches=pd.read_csv(curated/'matches.csv')
    outcomes=pd.read_csv(curated/'match_outcomes.csv')
    data=matches.merge(outcomes[['match_id','home_goals','away_goals','result']],on='match_id',validate='one_to_one')
    config=json.loads((ROOT/'research/team_feature_config.json').read_text(encoding='utf-8'))
    full=normalized(build_features(data,config))
    prefix=data[data.split.isin(['warmup','train'])]
    prefix_features=normalized(build_features(prefix,config))
    assert_frame_equal(full.loc[prefix_features.index],prefix_features)
    changed=data.copy()
    changed.loc[changed.split.eq('test'),['home_goals','away_goals']]=[8,9]
    altered=normalized(build_features(changed,config))
    earlier_ids=data.loc[~data.split.eq('test'),'match_id']
    assert_frame_equal(full.loc[earlier_ids].sort_index(),altered.loc[earlier_ids].sort_index())
    # Existing exported values must match rebuilding the current version, not stale output.
    exports=pd.concat([pd.read_csv(curated/f'features_A_{s}.csv') for s in ['warmup','train','validation','test']],ignore_index=True)
    assert_frame_equal(full,normalized(exports),check_dtype=False,rtol=1e-12,atol=1e-12)
    assert len(full)==4560
    assert data.split.value_counts().to_dict()=={'train':3040,'warmup':760,'validation':380,'test':380}
    assert set(exports.columns)=={'match_id',*FEATURE_COLUMNS}
    report={
        'status':'passed',
        'real_data_checks':[
            'training_and_warmup_features_equal_full_history_prefix',
            'mutating_every_test_outcome_does_not_change_pretest_features',
            'exported_features_match_current_code_rebuild',
            'registered_split_counts_and_feature_allowlist_match'],
        'rows':len(full),'features':len(FEATURE_COLUMNS),
        'test_outcomes_modified_only_in_memory':True,
        'raw_data_modified':False,'models_fitted':0,
        'output_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(curated.glob('*.csv'))}}
    (ROOT/'reports/team_dataset_verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='output_sha256'},indent=2))


if __name__=='__main__':main()
