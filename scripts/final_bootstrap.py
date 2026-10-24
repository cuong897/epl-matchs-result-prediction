"""Paired moving-calendar-block intervals; no model fitting or selection."""
import numpy as np
import pandas as pd


def paired_intervals(dates,delta,block,repeats=2000,seed=42,family_size=1):
    dates=pd.Series(pd.to_datetime(dates)).reset_index(drop=True)
    weeks=dates.dt.to_period('W-SUN').dt.start_time
    calendar=pd.date_range(weeks.min(),weeks.max(),freq='7D')
    delta=np.asarray(delta,dtype=float)
    if len(delta)!=len(dates) or not np.isfinite(delta).all():raise ValueError('Unaligned/nonfinite paired differences')
    if not 1<=block<=len(calendar) or family_size<1 or repeats<1:raise ValueError('Bad bootstrap configuration')
    arrays=[np.flatnonzero(weeks.eq(day)) for day in calendar]
    rng=np.random.default_rng(seed);samples=[]
    while len(samples)<repeats:
        starts=rng.integers(0,len(calendar)-block+1,size=int(np.ceil(len(calendar)/block)))
        picked=[i for start in starts for i in range(start,start+block)][:len(calendar)]
        ix=np.concatenate([arrays[i] for i in picked])
        if len(ix):samples.append(float(delta[ix].mean()))
    low,high=np.quantile(samples,[.025,.975]);tail=.05/(2*family_size)
    family_low,family_high=np.quantile(samples,[tail,1-tail])
    return {'delta_log_loss':float(delta.mean()),'ci95_low':float(low),'ci95_high':float(high),
            'family_interval_level':1-.05/family_size,'family_ci_low':float(family_low),'family_ci_high':float(family_high),
            'block_weeks':block,'replicates':repeats,'family_size':family_size,'negative_favors_added_features':True}
