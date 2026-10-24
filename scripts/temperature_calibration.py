"""One-parameter probability calibration with explicit validation-only fitting."""
import numpy as np
from scipy.optimize import minimize_scalar
from scipy.special import softmax
from modeling import label_indices,per_match_log_loss,validate_probabilities


def transform_temperature(p,temperature,epsilon=1e-15):
    p=validate_probabilities(p)
    if not np.isfinite(temperature) or temperature<=0:raise ValueError('Temperature must be positive')
    if not 0<epsilon<1/3:raise ValueError('Invalid probability floor')
    return validate_probabilities(softmax(np.log(np.clip(p,epsilon,1))/temperature,axis=1))


def fit_temperature(y,p,metadata,settings):
    p=validate_probabilities(p);label_indices(y)
    if len(y)!=len(p) or len(metadata)!=len(p) or not len(p):raise ValueError('Calibration length mismatch')
    if not metadata.season.eq(settings['fit_season']).all() or not metadata['split'].eq('validation').all():
        raise ValueError('Calibrator fit only on registered validation season')
    if metadata.match_id.duplicated().any():raise ValueError('Duplicate calibration match')
    low,high=settings['temperature_bounds']
    if not 0<low<=1<=high:raise ValueError('Bounds must include identity')
    epsilon=settings['probability_floor']
    def objective(beta):return float(per_match_log_loss(y,transform_temperature(p,1/beta,epsilon)).mean())
    solved=minimize_scalar(objective,bounds=(1/high,1/low),method='bounded',options={'xatol':settings['xatol']})
    if not solved.success:raise RuntimeError('Calibration optimizer failed')
    candidates=[1.,1/high,1/low,float(solved.x)]
    beta=min(candidates,key=lambda b:(objective(b),abs(b-1)))
    temperature=float(1/beta)
    calibrated=transform_temperature(p,temperature,epsilon)
    if not np.array_equal(p.argmax(axis=1),calibrated.argmax(axis=1)):raise ValueError('Temperature changed argmax')
    return {'temperature':temperature,'inverse_temperature':float(beta),'fit_rows':len(p),
            'raw_log_loss':objective(1),'calibrated_fit_log_loss':objective(beta),
            'at_bound':bool(np.isclose(temperature,low) or np.isclose(temperature,high)),
            'optimizer_success':True,'epsilon':epsilon,'fit_scope':'validation_2023_24_in_sample_diagnostic'}
