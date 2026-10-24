"""Freeze paths, columns, saved validation predictions and estimator hashes."""
import json
from pathlib import Path
import pandas as pd
from final_models import sha

ROOT=Path(__file__).resolve().parents[1]


def main():
    path=ROOT/'research/final_model_registry.json'
    if path.exists():raise FileExistsError('Registry already exists')
    a=json.loads((ROOT/'research/feature_columns_A.json').read_text())
    p=json.loads((ROOT/'research/feature_columns_P.json').read_text())
    f=json.loads((ROOT/'research/feature_columns_F.json').read_text())
    entries=[]
    def add(model_id,cohort,family,arm,run,source,columns=None,frequency=False):
        report_run='model_A_development' if run=='A_dev_v1' else run
        pred=ROOT/f'reports/{report_run}/validation_predictions.csv'
        result=json.loads((ROOT/f'reports/{report_run}/results.json').read_text())
        entry={'id':model_id,'cohort':cohort,'family':family,'arm':arm,'type':'frequency' if frequency else 'estimator',
               'source_run':run,'source_model':source,'columns':columns or [],
               'validation_predictions_path':str(pred.relative_to(ROOT)), 'validation_predictions_sha256':sha(pred),
               'expected_validation_metrics':result['validation_metrics'][source], 'calibrate':not frequency}
        if frequency:
            data=pd.read_csv(pred);values=data.loc[data.model.eq(source),['p_H','p_D','p_A']]
            if not values.nunique().eq(1).all():raise ValueError('Frequency baseline is not constant')
            entry['probabilities']=values.iloc[0].tolist()
        else:
            model=ROOT/f'models/{run}/{source}.joblib'
            entry.update(model_path=str(model.relative_to(ROOT)),model_sha256=sha(model))
        entries.append(entry)
    add('full__elo','full','elo','A_full','A_dev_v1','elo_threeway',['elo_diff'])
    add('full__logistic','full','logistic','A_full','A_dev_v1','logistic_A',a)
    for family in ['random_forest','xgboost']:
        add(f'full__{family}','full',family,'A_full','A_trees_v1',family,a)
    add('full__frequency','full','frequency','A_full','A_dev_v1','frequency',frequency=True)
    add('common__elo','common','elo','A_common','AP_dev_v1','elo_common',['elo_diff'])
    add('common__frequency','common','frequency','A_common','AP_dev_v1','frequency_common',frequency=True)
    for family in ['logistic','random_forest','xgboost']:
        for arm,columns in [('A_common',a),('A_plus_P',a+p),('A_plus_P_plus_F',a+p+f)]:
            run='APF_dev_v1' if arm.endswith('_F') else 'AP_dev_v1'
            add(f'common__{family}__{arm}','common',family,arm,run,f'{family}__{arm}',columns)
    if len(entries)!=16 or sum(e['calibrate'] for e in entries)!=14:raise ValueError('Unexpected final registry size')
    path.write_text(json.dumps(entries,indent=2)+'\n',encoding='utf-8')
    print('Registered 14 frozen estimators and two uncalibrated frequency baselines.')


if __name__=='__main__':main()
