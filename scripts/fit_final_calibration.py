"""Fit 14 temperatures on validation only; no test feature loading."""
from datetime import datetime,timezone
import json
from pathlib import Path
import numpy as np
from final_models import sha,feature_frame,registered_validation
from temperature_calibration import fit_temperature,transform_temperature
from modeling import evaluate

ROOT=Path(__file__).resolve().parents[1]


def main():
    config_path=ROOT/'research/final_evaluation_config.json';registry_path=ROOT/'research/final_model_registry.json'
    config=json.loads(config_path.read_text());registry=json.loads(registry_path.read_text())
    out=ROOT/'reports/final_calibration'
    if out.exists():raise FileExistsError('Calibration run exists')
    frame=feature_frame(ROOT,'validation')
    if len(frame)!=380 or not frame.season.eq('2023-24').all():raise ValueError('Wrong calibration cohort')
    frozen={'config_sha256':sha(config_path),'registry_sha256':sha(registry_path),
            'started_at_utc':datetime.now(timezone.utc).isoformat(),
            'code_sha256':{n:sha(ROOT/'scripts'/n) for n in ['temperature_calibration.py','fit_final_calibration.py','final_models.py']}}
    out.mkdir();(out/'fit_manifest.json').write_text(json.dumps(frozen,indent=2)+'\n',encoding='utf-8')
    temperatures={};diagnostics={};truth_reference=None
    for entry in registry:
        y,p=registered_validation(ROOT,entry,frame)
        if truth_reference is None:truth_reference=y
        else:np.testing.assert_array_equal(y,truth_reference)
        if not entry['calibrate']:continue
        fitted=fit_temperature(y,p,frame,config['calibration'])
        temperatures[entry['id']]=fitted
        diagnostics[entry['id']]={'raw':evaluate(y,p),'temperature_fit_diagnostic':evaluate(y,transform_temperature(p,fitted['temperature']))}
        print(f"{entry['id']}: T={fitted['temperature']:.6f}; validation-fit diagnostics only",flush=True)
    (out/'temperatures.json').write_text(json.dumps(temperatures,indent=2)+'\n',encoding='utf-8')
    (out/'diagnostics_in_sample.json').write_text(json.dumps({'status':'in_sample_validation_diagnostics_only',
          'test_features_loaded':False,'test_metrics_computed':False,'models':diagnostics},indent=2)+'\n',encoding='utf-8')
    print('Calibration complete; no final-test prediction or scoring.')


if __name__=='__main__':main()
