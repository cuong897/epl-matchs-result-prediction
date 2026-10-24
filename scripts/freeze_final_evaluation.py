"""Lock all predictions' inputs/code/model/calibration BEFORE test scoring."""
from datetime import datetime,timezone
import json
import importlib.metadata
from pathlib import Path
import subprocess
from final_models import sha

ROOT=Path(__file__).resolve().parents[1]


def main():
    out=ROOT/'research/final_lock.json'
    if out.exists():raise FileExistsError('Final lock is immutable')
    config_path=ROOT/'research/final_evaluation_config.json';registry_path=ROOT/'research/final_model_registry.json'
    config=json.loads(config_path.read_text());registry=json.loads(registry_path.read_text())
    if (ROOT/'reports'/config['run_id']).exists():raise ValueError('Test scoring directory already exists before lock')
    calibration=json.loads((ROOT/'reports/final_calibration/fit_manifest.json').read_text())
    if sha(config_path)!=calibration['config_sha256'] or sha(registry_path)!=calibration['registry_sha256']:raise ValueError('Calibration config changed')
    for name,digest in calibration['code_sha256'].items():
        if sha(ROOT/'scripts'/name)!=digest:raise ValueError('Calibration fit code changed')
    preparation=json.loads((ROOT/'reports/final_preparation/feature_verification.json').read_text())
    if not all(preparation['checks'].values()) or preparation['test_metrics_computed']:raise ValueError('Final feature checks failed')
    files={str(p.relative_to(ROOT)):sha(p) for p in [config_path,registry_path,
        ROOT/'reports/final_calibration/temperatures.json',ROOT/'reports/final_calibration/fit_manifest.json',
        ROOT/'reports/final_preparation/feature_verification.json']}
    for group in ['input_sha256','output_sha256']:
        for relative,digest in preparation[group].items():
            if sha(ROOT/relative)!=digest:raise ValueError('Prepared test artifact changed')
            files[relative]=digest
    for entry in registry:
        if entry['type']=='estimator':
            if sha(ROOT/entry['model_path'])!=entry['model_sha256']:raise ValueError('Estimator changed')
            files[entry['model_path']]=entry['model_sha256']
    code_names=['final_models.py','temperature_calibration.py','final_bootstrap.py','run_final_test.py','report_final_test.py',
                'freeze_final_evaluation.py','modeling.py','tree_modeling.py','team_features.py','player_proxy_features.py','player_performance_features.py']
    code={name:sha(ROOT/'scripts'/name) for name in code_names}
    lock={'run_id':config['run_id'],'locked_at_utc':datetime.now(timezone.utc).isoformat(),
          'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
          'files_sha256':files,'code_sha256':code,'test_metrics_computed_at_lock':False,
          'estimator_count':14,'frequency_baselines':2,'expected_probability_outputs':30,
          'test_matches':380,'no_refit_in_test':True,'primary_reference':config['primary_practical_reference_chosen_before_test']}
    lock['runtime']={n:importlib.metadata.version(n) for n in ['numpy','pandas','scikit-learn','scipy','joblib','xgboost']}
    out.write_text(json.dumps(lock,indent=2)+'\n',encoding='utf-8')
    print('Final lock written: 14 estimators, two frequency baselines, 30 probability outputs, 380 test matches.')


if __name__=='__main__':main()
