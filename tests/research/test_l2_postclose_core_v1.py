"""Contract tests: exact money units and unknown eligibility never become signals."""
from dataclasses import FrozenInstanceError

import numpy as np
import pandas as pd
import pytest

from experiments.l2_postclose_core_v1 import (
    MAX_INT, PostcloseSpec, aggregate_legs, daily_large_structure,
    future_labels, rolling_profiles, summarize_cells,
)

DAY = ('20261001', '20261002', '20261003', '20261006', '20261007')
SYMBOL = '688122.SH'


def spec(**kw):
    return PostcloseSpec(**{'symbols':(SYMBOL,), 'lookbacks':(3,), 'horizons':(1,), 'thresholds_cny':(1000000,), **kw})


def trade(day=DAY[0], ref='t1', buy='b1', sell='s1', price=100000, quantity=60000, scope='channel-1'):
    return dict(day=day,symbol=SYMBOL,scope=scope,trade_ref=ref,buy_ref=buy,sell_ref=sell,price_raw=price,quantity=quantity)


def daily(day, **kw):
    return dict(day=day,symbol=SYMBOL,threshold_cny=1000000,amount_1e4=1000000000,quantity=10000,large_buy_1e4=600000000,large_sell_1e4=400000000,trade_ok=True,order_ok=True,close_raw=100000,close_ok=True,price_segment='action-free-verified',**kw)


def days_frame():
    rows=[daily(d) for d in DAY]
    for i,r in enumerate(rows): r['close_raw']+=i*1000
    return pd.DataFrame(rows)


def prices(frame=None):
    return (days_frame() if frame is None else frame)[['day','symbol','close_raw','close_ok','price_segment']].drop_duplicates(['day','symbol'])


@pytest.mark.parametrize('kwargs',[
    {'lookbacks':()}, {'lookbacks':[3]}, {'lookbacks':(True,)}, {'lookbacks':(0,)},
    {'lookbacks':(5,3)}, {'lookbacks':(3,3)}, {'horizons':(-1,)},
    {'thresholds_cny':(500000,)}, {'seed':True}, {'seed':-1}, {'max_cells':121},
    {'max_cells':0}, {'symbols':()}, {'symbols':(SYMBOL,SYMBOL)},
    {'symbols':('000001.SZ',)}, {'symbols':('688655.SH','688122.SH')},
])
def test_invalid_spec_before_io(kwargs):
    with pytest.raises(ValueError): spec(**kwargs)


def test_config_frozen_custom_axes_and_budget():
    assert PostcloseSpec().lookbacks==(3,5,10,20)
    assert spec(lookbacks=(2,7),horizons=(2,9)).horizons==(2,9)
    with pytest.raises(FrozenInstanceError): spec().seed=1
    with pytest.raises(ValueError,match='budget'): PostcloseSpec(max_cells=119)


def test_order_cash_is_exact_integer_scaled_and_split_prints_cross_threshold():
    t=pd.DataFrame([trade(),trade(ref='t2',sell='s2')])
    legs=aggregate_legs(t)
    b=legs.loc[legs.side=='B'].iloc[0]
    assert b.amount_1e4==12000000000 and b.quantity==120000 and b.trade_count==2
    assert b.vwap==pytest.approx(10)
    assert pd.api.types.is_integer_dtype(legs.amount_1e4)
    facts=daily_large_structure(t,legs,spec()).iloc[0]
    assert facts.amount_1e4==12000000000 and facts.large_buy_1e4==12000000000
    assert facts.large_sell_1e4==0 and facts.structure_imbalance==1
    assert facts.large_participation==.5 and pd.isna(facts.large_sell_vwap)


def test_threshold_is_per_scope_but_daily_fact_combines_scopes():
    t=pd.DataFrame([trade(),trade(ref='t2',scope='channel-2')])
    f=daily_large_structure(t,aggregate_legs(t),spec())
    assert len(f)==1 and f.iloc[0].amount_1e4==12000000000
    assert f.iloc[0].large_buy_1e4==0  # Two distinct 600k orders, not one 1.2m order.


def test_days_and_sides_not_merged():
    t=pd.DataFrame([trade(),trade(day=DAY[1])])
    legs=aggregate_legs(t)
    assert len(legs)==4
    assert set(legs.side)=={'B','S'}


@pytest.mark.parametrize('change',[
    {'buy_ref':'0'},{'sell_ref':''},{'trade_ref':'000'},{'scope':''},
    {'scope':None},{'buy_ref':123},{'trade_ref':' t1'},{'day':'20260230'},
    {'quantity':True},{'quantity':-1},{'price_raw':0},{'price_raw':100000.0},
])
def test_malformed_raw_identifiers_and_money_fail_closed(change):
    r=trade();r.update(change)
    with pytest.raises(ValueError): aggregate_legs(pd.DataFrame([r]))


def test_duplicate_trade_and_exact_integer_overflow_rejected():
    with pytest.raises(ValueError,match='duplicate'): aggregate_legs(pd.DataFrame([trade(),trade()]))
    with pytest.raises(ValueError,match='overflow'):
        aggregate_legs(pd.DataFrame([trade(price=MAX_INT,quantity=2)]))
    with pytest.raises(ValueError,match='overflow'):
        aggregate_legs(pd.DataFrame([trade(price=MAX_INT//2+1,quantity=1),trade(ref='t2',price=MAX_INT//2+1,quantity=1)]))


def test_daily_structure_rejects_supported_but_unrequested_symbol():
    t=pd.DataFrame([trade()]);t['symbol']='688655.SH'
    with pytest.raises(ValueError,match='requested symbol scope'):
        daily_large_structure(t,aggregate_legs(t),spec())


def test_tampered_legs_cash_rejected_even_when_quantities_match():
    t=pd.DataFrame([trade()]);legs=aggregate_legs(t);legs.loc[0,'amount_1e4']+=1
    with pytest.raises(ValueError,match='conserve'): daily_large_structure(t,legs,spec())


def test_exact_aggregation_to_rolling_vwap_end_to_end():
    facts=[]
    for i,d in enumerate(DAY[:3]):
        t=pd.DataFrame([trade(day=d,price=100000+i*1000),trade(day=d,ref='t2',sell='s2',price=100000+i*1000)])
        f=daily_large_structure(t,aggregate_legs(t),spec())
        f=f.assign(trade_ok=True,order_ok=True,close_raw=101000+i*1000,close_ok=True,price_segment='verified')
        facts.append(f)
    r=rolling_profiles(pd.concat(facts),DAY[:3],spec()).iloc[-1]
    assert r.vwap==pytest.approx(10.1) and r.close==pytest.approx(10.3)
    assert bool(r.F) and bool(r.P) and r.description=='偏买且价格确认'


def test_contiguous_calendar_gap_propagates_without_compression():
    d=days_frame().loc[lambda x:x.day!=DAY[1]]
    r=rolling_profiles(d,DAY,spec(lookbacks=(3,5)))
    assert r.loc[(r.day==DAY[3])&(r.lookback==3),'structure_status'].iloc[0]=='missing_day'
    assert r.loc[(r.day==DAY[4])&(r.lookback==3),'structure_status'].iloc[0]=='ok'
    assert r.loc[(r.day==DAY[4])&(r.lookback==5),'structure_status'].iloc[0]=='missing_day'


def test_failed_trade_contaminates_window_but_not_later_short_window():
    d=days_frame();d.loc[1,'trade_ok']=False
    r=rolling_profiles(d,DAY,spec(lookbacks=(3,5)))
    assert r.loc[(r.day==DAY[3])&(r.lookback==3),'structure_status'].iloc[0]=='trade_unqualified'
    assert r.loc[(r.day==DAY[4])&(r.lookback==3),'structure_status'].iloc[0]=='ok'
    assert r.loc[(r.day==DAY[4])&(r.lookback==5),'structure_status'].iloc[0]=='trade_unqualified'


def test_order_unknown_does_not_destroy_independent_price_confirmation():
    d=days_frame();d['order_ok']=False
    r=rolling_profiles(d,DAY,spec()).iloc[-1]
    assert r.structure_status=='order_unqualified' and pd.isna(r.F)
    assert r.price_status=='ok' and bool(r.P)
    assert r.description=='数据不足'


@pytest.mark.parametrize('segment', [None,'','UNKNOWN','different-segment'])
def test_unknown_or_crossed_lookback_comparability_keeps_structure(segment):
    d=days_frame();d.loc[2,'price_segment']=segment
    r=rolling_profiles(d,DAY,spec(lookbacks=(5,))).iloc[-1]
    assert r.structure_status=='ok' and bool(r.F) and pd.isna(r.P)
    assert r.price_status in {'price_basis_unknown','action_crossed'}


def test_w1_only_price_rule_not_applicable():
    r=rolling_profiles(days_frame(),DAY,spec(lookbacks=(1,))).iloc[0]
    assert bool(r.F) and pd.isna(r.P) and r.price_status=='rule_not_applicable'


def test_false_f_true_p_is_neutral_not_data_missing():
    d=days_frame();d['large_buy_1e4']=0;d['large_sell_1e4']=0
    r=rolling_profiles(d,DAY,spec()).iloc[-1]
    assert not bool(r.F) and bool(r.P) and r.description=='中性'


def test_mirror_weak_and_no_future_leakage():
    d=days_frame();d['large_buy_1e4']=100000000;d['large_sell_1e4']=900000000
    d['close_raw']=[95000,94000,93000,92000,91000]
    r=rolling_profiles(d,DAY,spec())
    assert r.iloc[-1].description=='镜像弱势'
    later=d.copy();later.loc[4,'large_buy_1e4']=900000000;later.loc[4,'close_raw']=200000
    changed=rolling_profiles(later,DAY,spec())
    pd.testing.assert_frame_equal(r.loc[r.day<DAY[4]],changed.loc[changed.day<DAY[4]])


@pytest.mark.parametrize('cal',[(),list(DAY),('20260230',),tuple(reversed(DAY)),(DAY[0],DAY[0])])
def test_calendar_rejected_not_inferred_from_rows(cal):
    with pytest.raises(ValueError): rolling_profiles(days_frame(),cal,spec())


def test_bool_flags_and_qualified_close_integer_validation():
    d=days_frame();d['order_ok']='False'
    with pytest.raises(ValueError): rolling_profiles(d,DAY,spec())
    p=prices();p['close_raw']=p.close_raw.astype(float)
    with pytest.raises(ValueError): future_labels(p,DAY,spec(),DAY[-1])


def test_labels_use_independent_price_path_and_exact_calendar_horizon():
    p=prices();p.loc[1,'close_raw']=95000
    r=future_labels(p,DAY,spec(horizons=(2,)),DAY[-1]).iloc[0]
    assert r.label_status=='ok' and r.return_fraction==pytest.approx(.02)
    assert r.worst_close_fraction==pytest.approx(-.05)
    assert bool(r.up)


@pytest.mark.parametrize('mutation,expected',[
    ('gap','price_path_missing'),('unqualified','price_path_unqualified'),
    ('action','action_crossed'),('unknown','price_basis_unknown'),
])
def test_future_path_is_not_forward_filled(mutation,expected):
    p=prices()
    if mutation=='gap': p=p.drop(index=1)
    elif mutation=='unqualified': p.loc[1,'close_ok']=False
    elif mutation=='action': p.loc[1,'price_segment']='after-split'
    else: p.loc[1,'price_segment']=None
    r=future_labels(p,DAY,spec(horizons=(2,)),DAY[-1]).iloc[0]
    assert r.label_status==expected and pd.isna(r.return_fraction) and pd.isna(r.up)


def test_maturity_calendar_endpoint_and_flat_prices_not_confused():
    p=prices();p['close_raw']=100000
    r=future_labels(p,DAY,spec(horizons=(1,3)),DAY[0])
    assert r.iloc[0].label_status=='not_matured'
    flat=future_labels(p,DAY,spec(),DAY[-1]).iloc[0]
    assert flat.return_fraction==0 and not bool(flat.up)
    assert future_labels(p,DAY,spec(horizons=(20,)),DAY[-1]).iloc[0].label_status=='calendar_horizon_unavailable'


def test_full_family_and_unknown_f_not_control_empty_means_null():
    d=days_frame();d['order_ok']=False
    cfg=spec(lookbacks=(2,3),horizons=(1,2))
    profiles=rolling_profiles(d,DAY,cfg);labels=future_labels(prices(),DAY,cfg,DAY[-1])
    result=summarize_cells(profiles,labels,DAY,cfg)
    assert len(result)==4 and result.n_total_anchors.eq(len(DAY)).all()
    assert result.n_common.eq(0).all() and result.n_control.eq(0).all()
    assert result.signal_up_fraction.isna().all() and result.delta_mean_return.isna().all()
    assert result.conclusion.eq('证据不足').all()


def test_profile_label_duplicates_rejected_and_known_control_counted():
    d=days_frame();cfg=spec(lookbacks=(2,))
    profiles=rolling_profiles(d,DAY,cfg);labels=future_labels(prices(),DAY,cfg,DAY[-1])
    profiles.loc[profiles.day==DAY[2],'F']=False
    out=summarize_cells(profiles,labels,DAY,cfg).iloc[0]
    assert out.n_control==1 and out.n_signal>0
    with pytest.raises(ValueError,match='duplicate'):
        summarize_cells(profiles,pd.concat([labels,labels.iloc[:1]]),DAY,cfg)


def test_integer_price_confirmation_preserves_one_tick_at_large_values():
    base=2**60
    d=pd.DataFrame([daily(DAY[0]),daily(DAY[1])])
    d['amount_1e4']=[base,base+1];d['quantity']=1
    d['close_raw']=[base,base+1]
    d['large_buy_1e4']=1;d['large_sell_1e4']=0
    r=rolling_profiles(d,DAY[:2],spec(lookbacks=(2,))).iloc[-1]
    assert bool(r.P)


def test_one_tick_increase_not_rounded_to_flat_label():
    p=prices().iloc[:2].copy();p['close_raw']=[2**60,2**60+1]
    r=future_labels(p,DAY[:2],spec(),DAY[1]).iloc[0]
    assert bool(r.up) and r.return_fraction>0 and r.worst_close_fraction>0


def test_summary_retains_signal_label_attrition_by_reason():
    import json
    d=days_frame();cfg=spec(lookbacks=(2,))
    profiles=rolling_profiles(d,DAY,cfg)
    profiles.loc[profiles.day==DAY[2],'F']=False
    labels=future_labels(prices(),DAY,cfg,DAY[-1])
    labels.loc[labels.day==DAY[1],'label_status']='action_crossed'
    out=summarize_cells(profiles,labels,DAY,cfg).iloc[0]
    assert out.n_signal_before_labels>out.n_signal
    assert json.loads(out.signal_label_exclusions)['action_crossed']==1
    assert out.n_control_before_labels==out.n_control==1
