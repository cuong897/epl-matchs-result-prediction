"""Audit 12 seasons; export canonical data, temporal feature snapshots and splits.

Run offline after acquisition: python scripts/build_team_dataset.py
No fit, imputation, scaling, model selection, or target-distribution summaries.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from audit_pilot import audit_matches, parse_fd_dates
from team_features import FEATURE_COLUMNS, build_features, match_id, local_midnight_utc

ROOT=Path(__file__).resolve().parents[1]


def clean_fd(raw: pd.DataFrame) -> tuple[pd.DataFrame,dict]:
    """Drop only entirely blank rows/columns; partial records fail later QA."""
    frame=raw.replace(r'^\s*$',pd.NA,regex=True)
    empty=frame.isna().all(axis=1)
    clean=frame.loc[~empty].copy()
    removed_columns=clean.columns[clean.isna().all(axis=0)].tolist()
    clean=clean.drop(columns=removed_columns)
    # Original data-row number, not line number, survives cleaning for provenance.
    clean['source_data_row']=clean.index+1
    return clean.reset_index(drop=True),{'raw_rows':len(raw),'removed_all_empty_rows':int(empty.sum()),'removed_all_empty_columns':removed_columns}


def canonicalize(df: pd.DataFrame, season: str, source_id: str, raw_hash: str) -> pd.DataFrame:
    dates=parse_fd_dates(df.Date)
    out=pd.DataFrame({'season':season,'match_date':dates,'home_team':df.HomeTeam,'away_team':df.AwayTeam,
                      'home_goals':df.FTHG.astype(int),'away_goals':df.FTAG.astype(int),'result':df.FTR,
                      'source_id':source_id,'source_sha256':raw_hash,'source_data_row':df.source_data_row})
    out['match_id']=[match_id(season,a,b) for a,b in zip(df.HomeTeam,df.AwayTeam)]
    out['fd_clock_local']=df['Time'].astype('string') if 'Time' in df else pd.Series(pd.NA,index=df.index,dtype='string')
    naive=pd.to_datetime(dates.dt.strftime('%Y-%m-%d')+' '+out.fd_clock_local,format='%Y-%m-%d %H:%M',errors='coerce')
    out['fd_kickoff_assumed_utc']=naive.dt.tz_localize('Europe/London',ambiguous='NaT',nonexistent='NaT').dt.tz_convert('UTC')
    out['prediction_cutoff_assumed_utc']=out.fd_kickoff_assumed_utc-pd.Timedelta(hours=1)
    out['kickoff_precision']=out.fd_kickoff_assumed_utc.notna().map({True:'clock_from_archive',False:'date_only'})
    out['kickoff_publication_status']='unknown'
    out['result_available_at_assumed_utc']=[local_midnight_utc(d+pd.DateOffset(days=1),'Europe/London') for d in dates]
    out['availability_status']='reconstructed_assumption'
    return out


def assign_split(season: str) -> str:
    year=int(season[:4])
    if 2013<=year<=2014:return 'warmup'
    if 2015<=year<=2022:return 'train'
    if year==2023:return 'validation'
    if year==2024:return 'test'
    raise ValueError(f'Season outside registered study: {season}')


def main() -> None:
    specs=json.loads((ROOT/'research/team_sources.json').read_text(encoding='utf-8'))
    manifest=json.loads((ROOT/'research/download_manifest.json').read_text(encoding='utf-8'))
    config_path=ROOT/'research/team_feature_config.json'
    config=json.loads(config_path.read_text(encoding='utf-8'))
    frames=[]; audits=[]
    for spec in specs:
        path=ROOT/spec['path']; digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if digest!=manifest[spec['id']]['sha256']:
            raise ValueError(f"Raw hash mismatch: {spec['id']}")
        df,cleaning=clean_fd(pd.read_csv(path))
        audit=audit_matches(df.drop(columns='source_data_row'),spec['season'])
        audit.update(cleaning)
        audits.append(audit)
        if not audit['core_pass']:
            raise ValueError(f"QA failed: {spec['season']}: {audit}")
        frames.append(canonicalize(df,spec['season'],spec['id'],digest))
    data=pd.concat(frames,ignore_index=True).sort_values(['match_date','match_id']).reset_index(drop=True)
    if data.match_id.duplicated().any():raise ValueError('Duplicate canonical match IDs')
    data['split']=data.season.map(assign_split)
    features=build_features(data,config)
    if len(features)!=len(data) or features.match_id.duplicated().any():raise AssertionError('Feature cardinality mismatch')
    lineage=features[['match_id','feature_version','feature_asof_utc','source_max_available_at_assumed_utc','history_max_match_date','availability_status']].copy()
    if (lineage.source_max_available_at_assumed_utc>lineage.feature_asof_utc).any():raise AssertionError('Future source availability')
    model=data[['match_id','split']].merge(features[['match_id']+FEATURE_COLUMNS],on='match_id',validate='one_to_one')
    feature_values=model[FEATURE_COLUMNS]
    output=ROOT/'data/curated'; output.mkdir(parents=True,exist_ok=True)
    # Keep labels and metadata separate. Only FEATURE_COLUMNS are eligible model input.
    outcome_fields=['match_id','home_goals','away_goals','result','result_available_at_assumed_utc','availability_status']
    data[outcome_fields].to_csv(output/'match_outcomes.csv',index=False)
    data.drop(columns=['home_goals','away_goals','result','result_available_at_assumed_utc']).to_csv(output/'matches.csv',index=False)
    data[['match_id','season','split']].to_csv(output/'split_manifest.csv',index=False)
    lineage.to_csv(output/'feature_lineage_A.csv',index=False)
    for split in ['warmup','train','validation','test']:
        selected=model[model.split.eq(split)].drop(columns='split')
        selected.to_csv(output/f'features_A_{split}.csv',index=False)
    report={'built_at_utc':datetime.now(timezone.utc).isoformat(),'feature_version':config['version'],
            'feature_config_sha256':hashlib.sha256(config_path.read_bytes()).hexdigest(),
            'feature_columns':FEATURE_COLUMNS,'feature_count':len(FEATURE_COLUMNS),
            'total_rows_including_warmup':len(data),'rows_by_split':data.split.value_counts().to_dict(),
            'audits':audits,'missing_features_all_periods':feature_values.isna().sum().to_dict(),
            'verified_publication_timestamps':False,'same_day_results_used':False,
            'test_labels_used_for_training':False,'trained_models':[],
            'code_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'scripts/team_features.py',ROOT/'scripts/audit_pilot.py']}}
    (ROOT/'reports/team_dataset_build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'research/feature_columns_A.json').write_text(json.dumps(FEATURE_COLUMNS,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['feature_version','feature_count','total_rows_including_warmup','rows_by_split']},indent=2))


if __name__=='__main__':main()
