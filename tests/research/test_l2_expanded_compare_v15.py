import json
from copy import deepcopy
from fractions import Fraction

import pytest
from experiments import l2_expanded_compare_v15 as m


@pytest.fixture
def spec():
    return {'calendar':['20260831','20260901','20260902','20260903','20260904','20260907','20260908','20260909','20260910','20260911','20260914','20260915','20260916','20260917','20260918','20260921'],
            'methods':[{'id':name,'group_fraction':g,'active_fraction':a} for name,g,a in [('g3_a3',[3,5],[3,5]),('g4_a3',[4,5],[3,5]),('g5_a3',[1,1],[3,5]),('g3_a4',[3,5],[4,5]),('g3_a5',[3,5],[1,1]),('g5_a5',[1,1],[1,1])]]+[{'id':name} for name in ['price_momentum','ordinary_turnover','hash_control']],
            'top_n':20,'future_horizons':[3,5]}


def inputs(spec,symbol='000001.SZ'):
    lookup={};basic={}
    for i,day in enumerate(spec['calendar'][:11]):
        basic[day]={symbol:{'close':str(10+i),'turnover_rate':str(i),'turnover_rate_f':'999','total_mv':'6000000000' if day!='20260914' else '10000000000'}}
        if i:
            lookup[(symbol,day)]={'symbol':symbol,'day':day,'cash_ready':True,'source_fact_ready':True,
                                  'buy':11000000000,'sell':10000000000,'active_buy':4000000000,
                                  'active_sell':3000000000,'passive_buy':7000000000,'passive_sell':7000000000,
                                  'unknown_buy':0,'unknown_sell':0,'market_amount':200000000000}
    return lookup,basic


def test_earliest_window_baseline_is_aug31_never_negative_future_index(spec):
    ds,base=m.window_dates(spec['calendar'],'20260907',5)
    assert ds==spec['calendar'][1:6] and base=='20260831'
    with pytest.raises(ValueError,match='preceding close'):
        m.window_dates(spec['calendar'][1:],'20260907',5)


def test_W10_turnover_divides_by10_and_uses_its_own_asof_cap(spec):
    lookup,basic=inputs(spec)
    r=m.window_feature('000001.SZ','synthetic','20260914',10,lookup,basic,spec)
    assert r['momentum_base_day']=='20260831' and r['_momentum']==1
    assert r['_turnover']==Fraction(11,2) and r['ordinary_turnover_window_mean_pct']=='5.5'
    assert r['active_positive_days']==10 and r['_active_cap']==Fraction(10000000000,10000)/10000000000
    old=m.window_feature('000001.SZ','synthetic','20260907',5,lookup,basic,spec)
    assert old['total_mv_cny']=='6000000000' and old['_momentum']==Fraction(1,2)


def test_matched_window_data_quality_not_backpropagated_to_standalone(spec):
    lookup,basic=inputs(spec);lookup[('000001.SZ','20260901')]['cash_ready']=False
    five=m.window_feature('000001.SZ','synthetic','20260914',5,lookup,basic,spec)
    ten=m.window_feature('000001.SZ','synthetic','20260914',10,lookup,basic,spec)
    assert five['own_feature_eligible'] and not ten['own_feature_eligible']
    matched={**five};matched['common_eligible']=five['own_feature_eligible'] and ten['own_feature_eligible']
    assert not matched['common_eligible'] and five['common_eligible']
    assert ten['source_class']=='D' and ten['active_difference_1e4'] is None


@pytest.mark.parametrize('w,days',[ (5,[3,4,5]), (10,[6,8,10]) ])
def test_positive_day_fractions_scale_exactly_with_window(spec,w,days):
    name='slice';spec={**spec,'slices':[{'id':name,'cutoff':'20260914','lookback':w}]}
    fs=[]
    for i,n in enumerate(days):
        fs.append({'slice':name,'symbol':f'{i+1:06d}.SZ','asof':'20260914','common_eligible':True,
                   'source_class':'A','group_positive_days':w,'active_positive_days':n,
                   '_active_cap':Fraction(3-i),'_concentration':Fraction(3,4),'_momentum':Fraction(i),'_turnover':Fraction(i)})
    selected,counts=m.choose(fs,spec)
    get=lambda method:[r['symbol'] for r in selected if r['arm']==method]
    assert get('g3_a3')==['000001.SZ','000002.SZ','000003.SZ']
    assert get('g3_a4')==['000002.SZ','000003.SZ']
    assert get('g3_a5')==['000003.SZ'] and get('g5_a5')==['000003.SZ']
    assert all(c['underfilled'] and c['planned_n']==20 for c in counts)


def test_matched_hash_control_not_changed_by_lookback_when_common_pool_same(spec):
    r={'symbol':'000001.SZ','asof':'20260914','lookback':5}
    a=m.rank_key(r,{'id':'hash_control'});r['lookback']=10
    assert m.rank_key(r,{'id':'hash_control'})==a


def test_reused_price_bytes_reparsed_for_earlier_dates_not_legacy_usable_subset():
    raw=b'date,symbol,open,high,low,close\n2026-09-08,1,100,102,99,101\n2026-09-11,1,102,104,101,103\n2026-10-21,1,1000,1200,900,1100\n'
    records,invalid,error=m.parse_prices(raw,'000001.SZ',{'20260908','20260911'})
    assert error is None and not invalid and sorted(records)==['20260908','20260911']
    assert records['20260908']['close']=='101' and '20261021' not in records


@pytest.mark.parametrize('payload',[b'date,symbol,open,high,low,close\n2026-09-08\n',
                                    b'symbol,open,high,low,close,date\n1,100,102,99,101\n'])
def test_truncated_price_identity_is_asset_unknown_not_global_crash(payload):
    records,invalid,error=m.parse_prices(payload,'000001.SZ',{'20260908'})
    assert records=={} and error


def test_no_future_file_read_until_frozen_selection(spec,tmp_path,monkeypatch):
    sl={'id':'standalone5_20260907','cutoff':'20260907','lookback':5}
    s={**spec,'slices':[sl],'source_price_roots':[str(tmp_path/'prices')],'cutoffs_W5':['20260907']}
    f={'slice':sl['id'],'symbol':'000001.SZ','asof':'20260907','common_eligible':True,'source_class':'A',
       'group_positive_days':5,'active_positive_days':5,'_active_cap':Fraction(1),'_concentration':Fraction(1),
       '_momentum':Fraction(1),'_turnover':Fraction(1)}
    monkeypatch.setattr(m,'load_spec',lambda *a:s)
    monkeypatch.setattr(m,'build_features',lambda *a:([f],[],{'cash_mode':'synthetic'}))
    monkeypatch.setattr(m,'snapshot_prices',lambda *a:pytest.fail('future prices before freeze'))
    sp=tmp_path/'spec.json';sp.write_text('{}');out=tmp_path/'selected'
    result=m.freeze(tmp_path/'cash',out,sp)
    assert result['selected_rows']==9 and not (tmp_path/'prices').exists()
    (out/'selections.csv').write_text('changed')
    with pytest.raises(ValueError,match='frozen selection'):
        m.observe(out,tmp_path/'observed',sp)
    assert not (tmp_path/'observed').exists()


def test_missing_cube_fact_is_not_silently_zero_filled(spec):
    lookup,basic=inputs(spec);lookup.pop(('000001.SZ','20260901'))
    with pytest.raises(ValueError,match='missing requested fact'):
        m.window_feature('000001.SZ','synthetic','20260907',5,lookup,basic,spec)
