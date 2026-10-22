"""Local exploratory statistics, not source acceptance or Platform Validation.

Protocol: research/l2-postclose-execution-spec-v1.md. The caller must establish
prospective eligibility; this pure function cannot authenticate that claim.
The real-data audit CLI never opens that gate for already-observed data.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd

from experiments.l2_postclose_core_v1 import PostcloseSpec, summarize_cells


def holm_adjust(pvalues):
    """Missing cells occupy the fixed family but remain missing externally."""
    for p in pvalues:
        if p is not None and (isinstance(p, bool) or not np.isfinite(p) or not 0 <= p <= 1):
            raise ValueError('invalid pvalue')
    order = sorted(range(len(pvalues)), key=lambda i: 1 if pvalues[i] is None else pvalues[i])
    out = [None] * len(pvalues)
    previous = 0.0
    for rank, i in enumerate(order):
        p = 1 if pvalues[i] is None else pvalues[i]
        previous = min(1.0, max(previous, (len(order)-rank)*p))
        if pvalues[i] is not None:
            out[i] = previous
    return out


def _blocked_differences(groups, outcomes, length, repetitions, seed):
    """Same date indices for all symbols; no missing-to-zero outcomes."""
    n, assets = groups.shape
    values = [[] for _ in range(assets)]
    rng = np.random.default_rng(seed)
    k = math.ceil(n/length)
    for begin in range(0, repetitions, 256):
        count = min(256, repetitions-begin)
        starts = rng.integers(0, n-length+1, size=(count,k))
        indices = (starts[:,:,None]+np.arange(length)).reshape(count,-1)[:,:n]
        for a in range(assets):
            g, y = groups[indices,a], outcomes[indices,a]
            signal, control = g==1, g==0
            ns, nc = signal.sum(axis=1), control.sum(axis=1)
            ok = (ns>0)&(nc>0)
            sv, cv = (signal&y).sum(axis=1), (control&y).sum(axis=1)
            delta = sv[ok]/ns[ok]-cv[ok]/nc[ok]
            values[a].extend(delta.tolist())
    return values


def infer_primary(profiles, labels, calendar, spec:PostcloseSpec, *, prospective_eligible=False, repetitions=20000):
    if type(prospective_eligible) is not bool or type(repetitions) is not int or repetitions<1:
        raise ValueError('invalid inference configuration')
    cells=summarize_cells(profiles,labels,calendar,spec)
    family=[i for i,r in cells.iterrows() if int(r.threshold_cny)==spec.primary_threshold_cny]
    family_size=len(family)
    details={i:{'inference_status':'not_tested_sensitivity','p_raw':None,'p_holm':None,'ci_family_low':None,'ci_family_high':None,'bootstrap_valid':0,'family_size':family_size,'p_resolution':None,'inference_reasons':''} for i in cells.index}
    for i in family:
        details[i]['inference_status']='not_run_qualification_or_sample'
    for W in spec.lookbacks:
        for H in spec.horizons:
            n=len(calendar);length=W+H
            groups=np.full((n,len(spec.symbols)),-1,dtype=np.int8)
            outcomes=np.zeros((n,len(spec.symbols)),dtype=bool)
            common=np.zeros((n,len(spec.symbols)),dtype=bool)
            eligible=[]
            for a,symbol in enumerate(spec.symbols):
                idx=next(i for i in family if cells.at[i,'symbol']==symbol and cells.at[i,'lookback']==W and cells.at[i,'horizon']==H)
                p=profiles.loc[(profiles.symbol==symbol)&(profiles.threshold_cny==spec.primary_threshold_cny)&(profiles.lookback==W)]
                l=labels.loc[(labels.symbol==symbol)&(labels.horizon==H)]
                joined=p.merge(l[['day','symbol','label_status','up']],on=['day','symbol'],validate='one_to_one').set_index('day')
                for j,day in enumerate(calendar):
                    if day not in joined.index: continue
                    r=joined.loc[day]
                    if r.structure_status!='ok' or r.price_status!='ok' or r.label_status!='ok' or pd.isna(r.F) or pd.isna(r.P): continue
                    common[j,a]=True;outcomes[j,a]=bool(r.up)
                    if r.P: groups[j,a]=1 if r.F else 0
                blocks=sum(bool(common[start:start+length,a].all()) for start in range(0,n-length+1,length))
                weeks=len({pd.Timestamp(calendar[j]).isocalendar()[:2] for j in range(n) if common[j,a]})
                reasons=[]
                if not prospective_eligible: reasons.append('no_qualified_prospective_sample')
                if cells.at[idx,'n_signal']<20 or cells.at[idx,'n_control']<20: reasons.append('groups_below_20')
                if weeks<10: reasons.append('weeks_below_10')
                if blocks<8: reasons.append('complete_nonoverlap_blocks_below_8')
                details[idx].update(inference_reasons=';'.join(reasons),complete_blocks=blocks,calendar_weeks=weeks)
                if not reasons: eligible.append((a,idx))
            if not eligible: continue
            draws=_blocked_differences(groups,outcomes,length,repetitions,spec.seed)
            for a,idx in eligible:
                values=np.asarray(draws[a],dtype=float)
                details[idx]['bootstrap_valid']=len(values)
                if len(values)<.95*repetitions:
                    details[idx].update(inference_status='not_run_insufficient_valid_bootstrap',inference_reasons='valid_bootstrap_below_95pct');continue
                observed=float(cells.at[idx,'delta_up_fraction'])
                centered=values-observed
                tail=.05/(2*family_size)
                low=observed-float(np.quantile(centered,1-tail))
                high=observed-float(np.quantile(centered,tail))
                p=(1+int((centered>=observed).sum()))/(len(values)+1)
                details[idx].update(inference_status='computed_exploratory_only',p_raw=p,ci_family_low=max(-1.,low),ci_family_high=min(1.,high),p_resolution=1/(len(values)+1))
    adjusted=holm_adjust([details[i]['p_raw'] for i in family])
    for idx,p in zip(family,adjusted):
        d=details[idx];d['p_holm']=p
        if p is None: continue
        if cells.at[idx,'delta_up_fraction']>=.10 and cells.at[idx,'delta_mean_return']>0 and p<=.05 and d['ci_family_low']>0:
            cells.at[idx,'conclusion']='附加关联迹象（非因果、非净收益）'
        elif d['ci_family_high']<=0:
            cells.at[idx,'conclusion']='正向关联未获支持／出现反向证据'
        else:
            cells.at[idx,'conclusion']='证据不足／未达点估计门槛'
    extra=pd.DataFrame.from_dict(details,orient='index')
    cells=cells.drop(columns=['inference_status']).join(extra)
    cells['prospective_eligible']=prospective_eligible
    cells['bootstrap_requested']=repetitions
    return cells
