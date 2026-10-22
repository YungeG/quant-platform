import csv
import json
from copy import deepcopy
from fractions import Fraction
from pathlib import Path

import pytest
from experiments import l2_ranking_compare_v12 as m


@pytest.fixture
def spec(tmp_path):
    formation = ['20260907','20260908','20260909','20260910','20260911']
    future = ['20260914','20260915','20260916','20260917','20260918','20260921','20260922','20260923','20260924','20260928','20260929','20260930','20261008','20261009','20261012','20261013','20261014','20261015','20261016','20261019']
    return {'asof':'20260911','formation_dates':formation,'calendar':['20260904']+formation+future,
            'arms':[{'id':a} for a in m.ARMS],'panels':list(m.PANELS),'top_n':20,
            'horizons':[10,20],'adverse_limit_percent':'10','main_arm':'cash_active_cap_persistent',
            'prior_case_symbols':['000001.SZ'],'price_source_dir':str(tmp_path/'prices'),
            'price_file_max_bytes':512*1024,'price_total_max_bytes':192*1024**2,'price_max_symbols':280}


def basic(spec, symbol='000001.SZ'):
    return {d:{symbol:{'close':str(10+i),'total_mv':'6000000000.01','turnover_rate':'3','turnover_rate_f':'1000'}}
            for i,d in enumerate(spec['calendar'][:6])}


def profile(active_days=4):
    return {'cash_window_ready':True,'group_buy_bias':True,'active_support':True,
            'group_positive_days':3,'active_positive_days':active_days,
            'group_positive_streak':2,'active_positive_streak':active_days,
            'group_difference_1e4':1000000000,'active_difference_1e4':500000000,
            'passive_difference_1e4':400000000,'unknown_difference_1e4':100000000,
            'market_amount_1e4':100000000000,'top2_positive_delta_numerator_1e4':70,
            'positive_delta_denominator_1e4':100}


def feature(spec, symbol='000001.SZ', active_days=4):
    return m.make_feature(symbol,'synthetic',profile(active_days),basic(spec,symbol),spec)


def test_basic_feature_units_exact_cap_and_momentum_base(spec):
    r=feature(spec)
    assert r['_momentum']==Fraction(1,2) and r['raw_momentum5_pct']=='50'
    assert r['_turnover']==3 and r['ordinary_turnover_mean5_pct']=='3'
    assert r['_active_cap']==Fraction(500000000,10000)/Fraction('6000000000.01')
    assert r['_group_turnover']==Fraction(1,100)
    assert r['common_eligible'] and r['source_class']=='A'


@pytest.mark.parametrize('bad',['','NaN','Infinity','-1'])
def test_missing_turnover_excludes_every_arm_without_erasing_valid_price(spec,bad):
    b=basic(spec);b['20260909']['000001.SZ']['turnover_rate']=bad
    r=m.make_feature('000001.SZ','synthetic',profile(),b,spec)
    assert not r['common_eligible'] and r['_momentum']==Fraction(1,2)
    assert r['raw_close_at_cutoff']=='15' and r['_turnover'] is None
    selected,counts=m.select_arms([r],spec)
    assert not selected and all(c['selected_n']==0 and c['underfilled'] for c in counts)


def test_missing_close_and_cash_remain_separate_unknowns(spec):
    b=basic(spec);b['20260904']['000001.SZ']['close']=''
    r=m.make_feature('000001.SZ','synthetic',profile(),b,spec)
    assert not r['common_eligible'] and r['_momentum'] is None and r['_turnover']==3
    assert r['raw_close_at_cutoff']=='15' and r['active_difference_1e4']==500000000
    p={'cash_window_ready':False}
    r=m.make_feature('000001.SZ','synthetic',p,basic(spec),spec)
    assert r['source_class']=='D' and not r['common_eligible']
    assert r['_active_cap'] is None and r['_momentum']==Fraction(1,2)
    assert r['group_difference_1e4'] is None


@pytest.mark.parametrize('bad',[1.5,True,'1.5'])
def test_money_and_basic_float_never_truncated(spec,bad):
    p=profile();p['active_difference_1e4']=bad
    with pytest.raises(ValueError):m.make_feature('000001.SZ','synthetic',p,basic(spec),spec)
    with pytest.raises(ValueError):m.decimal_fraction(1.0)


def test_persistence_arm_is_four_of_five_not_three_and_panels_not_holdouts(spec):
    r3=feature(spec,'000001.SZ',3);r4=feature(spec,'000002.SZ',4)
    selected,counts=m.select_arms([r3,r4],spec)
    get=lambda arm,panel=m.PANELS[0]:[r['symbol'] for r in selected if r['panel']==panel and r['arm']==arm]
    assert set(get('cash_active_cap'))=={'000001.SZ','000002.SZ'}
    assert get('cash_active_cap_persistent')==['000002.SZ']
    assert get('price_momentum5',m.PANELS[1])==['000002.SZ']
    assert all(c['planned_n']==20 and c['underfilled'] for c in counts)


def test_baselines_use_same_common_pool_not_cash_A_only(spec):
    a=feature(spec,'000001.SZ');c=feature(spec,'000002.SZ')
    c['source_class']='C';c['_momentum']=Fraction(10)
    selected,_=m.select_arms([a,c],spec)
    cash=[r['symbol'] for r in selected if r['panel']==m.PANELS[0] and r['arm']=='cash_group_cap']
    momentum=[r['symbol'] for r in selected if r['panel']==m.PANELS[0] and r['arm']=='price_momentum5']
    assert cash==['000001.SZ'] and momentum==['000002.SZ','000001.SZ']


def test_exact_rank_ties_and_hash_control_independent_of_money(spec):
    a=feature(spec,'000001.SZ');b=feature(spec,'000002.SZ')
    b['_group_cap']=a['_group_cap']+Fraction(1,10**60)
    assert m.arm_key(b,'cash_group_cap',spec)<m.arm_key(a,'cash_group_cap',spec)
    first=m.arm_key(a,'hash_control',spec)
    a['_momentum']=Fraction(10**10);a['_active_cap']=Fraction(10**20)
    assert m.arm_key(a,'hash_control',spec)==first


def test_overlap_counts_common_names_not_independent_samples(spec):
    rs=[{'panel':m.PANELS[0],'arm':'cash_group_cap','symbol':'000001.SZ'},
        {'panel':m.PANELS[0],'arm':'cash_group_cap','symbol':'000002.SZ'},
        {'panel':m.PANELS[0],'arm':'cash_active_cap','symbol':'000002.SZ'}]
    result=m.selection_overlap(rs,spec)
    r=next(r for r in result if r['panel']==m.PANELS[0] and r['first_arm']=='cash_group_cap' and r['second_arm']=='cash_active_cap')
    assert r['intersection_n']==1 and r['union_n']==2 and r['jaccard_pct']=='50'
    assert len(result)==42 and any(r['jaccard_pct'] is None for r in result)


def test_selection_freezes_before_any_outcome_read(spec,tmp_path,monkeypatch):
    sp=tmp_path/'spec.json';sp.write_text(json.dumps(spec))
    f=feature(spec)
    monkeypatch.setattr(m,'build_features',lambda *a:([f],{'cash_mode':'smoke'}))
    monkeypatch.setattr(m,'snapshot_prices',lambda *a:pytest.fail('future prices read before selection'))
    out=tmp_path/'selected'
    manifest=m.freeze_selection(tmp_path/'cash',out,sp)
    assert manifest['selected_rows']==7 and manifest['unique_selected_symbols']==1
    assert m.file_sha(out/'selections.csv')==manifest['selections_sha256']
    assert not (tmp_path/'prices').exists()
    (out/'selections.csv').write_text('changed')
    with pytest.raises(ValueError,match='frozen selection changed'):
        m.observe_paths(out,tmp_path/'outcomes',sp)
    assert not (tmp_path/'outcomes').exists()


def make_prices(root,symbol,dates,change=None):
    root.mkdir(exist_ok=True)
    rs=[]
    for d in dates:
        r={'date':d[:4]+'-'+d[4:6]+'-'+d[6:],'symbol':symbol[:6].lstrip('0'),
           'open':'100','high':'101','low':'99','close':'100'}
        if change:change(d,r)
        rs.append(r)
    with (root/(symbol[:6]+'.csv')).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)


def test_price_missing_invalid_and_after19_ignored_without_reselection(spec,tmp_path):
    root=tmp_path/'prices';days=spec['calendar'][5:]+['20261020']
    def change(d,r):
        if d=='20260916':r['low']='105'
        if d=='20261020':r['close']='999999'
    make_prices(root,'000001.SZ',days,change)
    out=tmp_path/'observations';out.mkdir()
    bars,receipt=m.snapshot_prices({'000001.SZ','000002.SZ'},out,spec)
    assert '20261020' not in bars['000001.SZ'] and '20260916' not in bars['000001.SZ']
    assert bars['000002.SZ']=={} and len(receipt['files'])==2
    assert any(r.get('error')=='missing_or_nonregular_price_file' for r in receipt['files'])
    path=m.evaluate_path(spec['calendar'],bars['000001.SZ'],spec['asof'],20)
    assert not path['path_complete'] and path['raw_risk_state']=='unknown_incomplete'
    assert path['raw_lowrisk_late_up_candidate'] is None


@pytest.mark.parametrize('short_row',['missing_symbol','missing_date'])
def test_truncated_price_identity_keeps_frozen_selections_as_unknown(spec,tmp_path,monkeypatch,short_row):
    sp=tmp_path/'spec.json';sp.write_text(json.dumps(spec))
    f=feature(spec,'000002.SZ')
    monkeypatch.setattr(m,'build_features',lambda *a:([f],{'cash_mode':'smoke'}))
    selection=tmp_path/'selected';manifest=m.freeze_selection(tmp_path/'cash',selection,sp)
    root=tmp_path/'prices';root.mkdir()
    payload='date,symbol,open,high,low,close\n2026-09-14\n' if short_row=='missing_symbol' else 'symbol,open,high,low,close,date\n2,100,101,99,100\n'
    (root/'000002.csv').write_text(payload)
    out=tmp_path/'outcomes';result=m.observe_paths(selection,out,sp)
    assert result['source_selected_rows']==manifest['selected_rows']==14
    assert result['path_rows']==28 and result['raw_complete_paths']==0
    assert m.file_sha(selection/'selections.csv')==manifest['selections_sha256']
    assert all(r['symbol']=='000002.SZ' and r['raw_risk_state']=='unknown_reference' for r in m.table(out/'raw_path_outcomes.csv'))
    price=m.load(out/'price_snapshot_receipt.json')['files'][0]
    assert 'identity' in price['error']


@pytest.mark.parametrize('approved',[True,False])
def test_declared_price_alias_resolves_to_stable_regular_snapshot(spec,tmp_path,approved):
    logical=tmp_path/'prices';logical.mkdir()
    target=tmp_path/'target'
    make_prices(target,'000001.SZ',spec['calendar'][5:])
    (logical/'000001.csv').symlink_to(target/'000001.csv')
    if approved:spec['price_allowed_resolved_roots']=[str(logical),str(target)]
    out=tmp_path/'observations';out.mkdir()
    bars,receipt=m.snapshot_prices({'000001.SZ'},out,spec)
    if approved:
        assert '20260914' in bars['000001.SZ'] and receipt['bytes']>0
        assert receipt['files'][0]['logical_was_symlink'] is True
        assert not Path(receipt['files'][0]['snapshot_path']).is_symlink()
    else:
        assert bars['000001.SZ']=={} and receipt['bytes']==0
        assert receipt['files'][0]['error']=='unapproved_price_alias_target'


def test_price_alias_change_during_read_is_fatal(spec,tmp_path,monkeypatch):
    logical=tmp_path/'prices';logical.mkdir()
    target=tmp_path/'target';make_prices(target,'000001.SZ',spec['calendar'][5:])
    other=target/'other.csv';other.write_bytes((target/'000001.csv').read_bytes())
    link=logical/'000001.csv';link.symlink_to(target/'000001.csv')
    spec['price_allowed_resolved_roots']=[str(logical),str(target)]
    original=m.read_small
    def changed(*args,**kwargs):
        raw=original(*args,**kwargs);link.unlink();link.symlink_to(other);return raw
    monkeypatch.setattr(m,'read_small',changed)
    out=tmp_path/'observations';out.mkdir()
    with pytest.raises(ValueError,match='changed before snapshot'):
        m.snapshot_prices({'000001.SZ'},out,spec)


@pytest.mark.parametrize('mutation',['duplicate','foreign'])
def test_ambiguous_price_file_whole_asset_unknown(spec,tmp_path,mutation):
    dates=[spec['asof'],'20260914']
    if mutation=='duplicate':dates.append('20260914')
    def change(d,r):
        if mutation=='foreign':r['symbol']='2'
    make_prices(tmp_path/'prices','000001.SZ',dates,change)
    out=tmp_path/'observations';out.mkdir()
    bars,receipt=m.snapshot_prices({'000001.SZ'},out,spec)
    assert bars['000001.SZ']=={} and receipt['files'][0]['error']


def test_next_market_open_no_shift_exact_touch_and_partial_known_breach(spec):
    dates=spec['calendar'][6:];bars={d:{'open':'100','high':'101','low':'90','close':'100'} for d in dates}
    complete=m.evaluate_path(spec['calendar'],bars,spec['asof'],20)
    assert complete['reference_day']=='20260914' and complete['raw_risk_state']=='within_limit_complete'
    assert complete['risk_line_first_touch_day']=='20260914' and complete['risk_line_first_breach_day'] is None
    missing=dict(bars);missing.pop('20260914')
    assert m.evaluate_path(spec['calendar'],missing,spec['asof'],20)['raw_risk_state']=='unknown_reference'
    partial=dict(bars);partial['20260915']={**bars['20260915'],'low':'89.999'};partial.pop('20260916')
    r=m.evaluate_path(spec['calendar'],partial,spec['asof'],20)
    assert not r['path_complete'] and r['raw_risk_state']=='breached_observed' and r['raw_lowrisk_late_up_candidate'] is False


def test_waiting_never_bridges_missing_dates(spec):
    days=spec['calendar'][6:]
    bars={d:{'open':'100','high':'120','low':'95','close':'99'} for d in days}
    bars[days[0]]['close']='100';bars[days[1]]['close']='102';bars[days[3]]['close']='104';bars.pop(days[2])
    r=m.evaluate_path(spec['calendar'],bars,spec['asof'],20)
    assert r['first3_rising_closes_wait_sessions'] is None


def test_fixed_denominator_bounds_and_zero_not_complete_case_winrate(spec):
    spec={**spec,'horizons':[10]}
    base={'panel':m.PANELS[0],'arm':'cash_active_cap','horizon_market_days':10,
          'path_complete':False,'first3_rising_closes_wait_sessions':None}
    paths=[{**base,'raw_lowrisk_late_up_candidate':True,'raw_risk_state':'within_limit_complete'},
           {**base,'raw_lowrisk_late_up_candidate':False,'raw_risk_state':'breached_observed'},
           {**base,'raw_lowrisk_late_up_candidate':None,'raw_risk_state':'unknown_reference'}]
    counts=[{'panel':m.PANELS[0],'arm':'cash_active_cap','selected_n':3,'planned_n':20,'underfilled':True}]
    r=m.summarize_paths(paths,counts,spec)[0]
    assert Fraction(r['joint_success_lower_pct'])==Fraction('33.333333333333333333333333333333333333333333333333')
    assert r['joint_success']==1 and r['joint_unknown']==1 and r['joint_failure']==1
    assert Fraction(r['joint_success_upper_pct'])>66
    assert r['raw_endpoint_median_complete_only_pct'] is None
    zero=m.summarize_paths([], [{**counts[0],'selected_n':0}],spec)[0]
    assert zero['joint_success_lower_pct'] is None and zero['breach_upper_pct'] is None


def test_even_median_no_float_and_screen_never_declares_validated_winner(spec):
    assert m.median_text([1,2])=='1.5' and m.median_text([]) is None
    rs=[]
    for panel in spec['panels']:
        for horizon in spec['horizons']:
            for arm in m.ARMS:
                rs.append({'panel':panel,'horizon':horizon,'arm':arm,'selected_n':20,
                           'joint_success_lower_pct':'40' if arm==spec['main_arm'] else '20',
                           'joint_success_upper_pct':'40' if arm==spec['main_arm'] else '20',
                           'breach_lower_pct':'10','breach_upper_pct':'10'})
    r=m.hypothesis_screen(rs,spec)
    assert r['status']=='descriptive_support_only' and r['validated_algorithm_winner'] is False
    rs[0]['selected_n']=1
    # Underfilling a required main/baseline, not an unrelated comparison, is inconclusive.
    for row in rs:
        if row['arm']==spec['main_arm']:row['selected_n']=1
    assert m.hypothesis_screen(rs,spec)['status']=='inconclusive_underfilled'
