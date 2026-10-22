"""Synthetic-only statistical protocol checks; no market source is qualified here."""
import numpy as np
import pandas as pd
import pytest
from experiments.l2_postclose_core_v1 import PostcloseSpec
from experiments.l2_postclose_inference_v1 import holm_adjust,infer_primary,_blocked_differences


def fixture(n=120):
    cal=tuple(pd.bdate_range('2025-01-01',periods=n).strftime('%Y%m%d'))
    cfg=PostcloseSpec(symbols=('688122.SH',),lookbacks=(2,),horizons=(1,),thresholds_cny=(1000000,))
    profiles=[];labels=[]
    for i,d in enumerate(cal):
        f=i%2==0
        profiles.append(dict(day=d,symbol='688122.SH',threshold_cny=1000000,lookback=2,structure_status='ok',price_status='ok',F=f,P=True))
        labels.append(dict(day=d,symbol='688122.SH',horizon=1,label_status='ok',return_fraction=.02 if f else -.02,up=f))
    return pd.DataFrame(profiles),pd.DataFrame(labels),cal,cfg


def test_holm_retains_missing_family_members_without_fake_pvalues():
    adjusted=holm_adjust([.01,.04,None])
    assert adjusted[:2]==pytest.approx([.03,.08]) and adjusted[2] is None
    assert holm_adjust([None,None])==[None,None]
    for x in (True,-.1,1.1,float('nan')):
        with pytest.raises(ValueError): holm_adjust([x])


def test_no_future_qualification_never_opens_even_with_perfect_synthetic_effect():
    p,l,c,s=fixture()
    r=infer_primary(p,l,c,s,repetitions=100).iloc[0]
    assert r.inference_status=='not_run_qualification_or_sample'
    assert 'no_qualified_prospective_sample' in r.inference_reasons
    assert pd.isna(r.p_raw) and pd.isna(r.p_holm)
    assert r.conclusion=='证据不足' and r.n_signal==60


def test_qualified_synthetic_protocol_is_deterministic_and_bounded():
    p,l,c,s=fixture()
    a=infer_primary(p,l,c,s,prospective_eligible=True,repetitions=1000)
    b=infer_primary(p,l,c,s,prospective_eligible=True,repetitions=1000)
    pd.testing.assert_frame_equal(a,b)
    r=a.iloc[0]
    assert r.inference_status=='computed_exploratory_only'
    assert r.ci_family_low==1 and r.ci_family_high==1
    assert r.bootstrap_valid==1000 and r.p_holm<=.05
    assert r.conclusion.startswith('附加关联迹象')


def test_short_or_sparse_samples_do_not_get_inference():
    p,l,c,s=fixture(12)
    r=infer_primary(p,l,c,s,prospective_eligible=True,repetitions=100).iloc[0]
    assert 'groups_below_20' in r.inference_reasons
    assert 'weeks_below_10' in r.inference_reasons
    assert 'complete_nonoverlap_blocks_below_8' in r.inference_reasons
    assert pd.isna(r.p_raw)


def test_block_indices_shared_across_assets_and_missing_draws_not_zero():
    g=np.tile(np.array([0,1,0,1,0,1])[:,None],(1,2))
    y=np.tile(np.array([True,True,False,False,True,False])[:,None],(1,2))
    a=_blocked_differences(g,y,3,500,0)
    assert a[0]==a[1]
    missing=_blocked_differences(np.full((6,2),-1),y,3,10,0)
    assert missing==[[],[]]


def test_auxiliary_threshold_cannot_replace_primary():
    p,l,c,_=fixture()
    s=PostcloseSpec(symbols=('688122.SH',),lookbacks=(2,),horizons=(1,))
    r=infer_primary(p,l,c,s,prospective_eligible=True,repetitions=1000)
    aux=r.loc[r.threshold_cny==500000].iloc[0]
    assert aux.inference_status=='not_tested_sensitivity' and pd.isna(aux.p_raw)
    assert len(r)==2
