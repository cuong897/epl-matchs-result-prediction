"""Read-only presentation data, with no training or test model selection."""
import csv
import hashlib
import json
import math
from pathlib import Path

FAMILY={'elo':'Elo','logistic':'Logistic Regression','random_forest':'Random Forest','xgboost':'XGBoost','frequency':'Tần suất lịch sử'}
ARM={'A_full':'Thống kê đội · lịch sử dài','A_common':'A · thống kê đội','A_plus_P':'A + P · sử dụng cầu thủ','A_plus_P_plus_F':'A + P + F · hiệu suất cầu thủ'}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read_csv(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as stream:return list(csv.DictReader(stream))


def load_delivery(root):
    root=Path(root)
    result=json.loads((root/'reports/final_test_v1/results.json').read_text(encoding='utf-8'))
    lock=json.loads((root/'research/final_lock.json').read_text(encoding='utf-8'))
    if sha(root/'research/final_lock.json')!=result['lock_sha256']:raise ValueError('Final lock changed')
    registry_path=root/'research/final_model_registry.json'
    if sha(registry_path)!=lock['files_sha256']['research\\final_model_registry.json']:raise ValueError('Registry changed')
    registry=json.loads(registry_path.read_text(encoding='utf-8'))
    before=root/'reports/final_test_v1/test_probabilities_before_labels.csv'
    if sha(before)!=result['prediction_export_sha256']:raise ValueError('Frozen prediction export changed')
    scored=read_csv(root/'reports/final_test_v1/test_predictions_scored.csv')
    bare=read_csv(before)
    if len(scored)!=11400 or len(bare)!=11400:raise ValueError('Unexpected prediction count')
    catalog=read_csv(root/'reports/delivery/match_catalog.csv')
    if len(catalog)!=380 or len({m['match_id'] for m in catalog})!=380:raise ValueError('Bad match catalog')
    truth={m['match_id']:m['result'] for m in catalog}
    keys=set()
    for row,original in zip(scored,bare):
        for field in original:
            if row[field]!=original[field]:raise ValueError('Scored predictions disagree with pre-label export')
        key=(row['model'],row['variant'],row['match_id'])
        if key in keys or row['match_id'] not in truth:raise ValueError('Duplicate or unknown prediction')
        keys.add(key)
        p=[float(row['p_'+label]) for label in ['H','D','A']]
        if not all(math.isfinite(x) and 0<=x<=1 for x in p) or abs(sum(p)-1)>1e-10:raise ValueError('Invalid probabilities')
        if row['result']!=truth[row['match_id']]:raise ValueError('Catalog outcome differs from scored archive')
    return {'result':result,'registry':registry,'matches':catalog,'predictions':scored,
            'temperatures':json.loads((root/'reports/final_calibration/temperatures.json').read_text(encoding='utf-8'))}


def demo_payload(data):
    models=[];probabilities={}
    for entry in data['registry']:
        label=FAMILY[entry['family']]+' · '+ARM[entry['arm']]
        models.append({'id':entry['id'],'label':label,'cohort':entry['cohort'],'calibrate':entry['calibrate']})
        probabilities[entry['id']]={}
    for row in data['predictions']:
        probabilities[row['model']].setdefault(row['variant'],{})[row['match_id']]=[float(row['p_'+c]) for c in ['H','D','A']]
    return {'matches':data['matches'],'models':models,'probabilities':probabilities,'metrics':data['result']['metrics'],
            'temperatures':data['temperatures'],'defaultModel':'full__elo','labelOrder':['H','D','A'],
            'runId':data['result']['run_id']}
