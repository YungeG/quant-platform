import hashlib
import json
from fractions import Fraction

import pytest
from experiments import l2_cash_flat_v16 as m

CAL=['20260831','20260901','20260902','20260903','20260904','20260907','20260908','20260909','20260910','20260911','20260914','20260915']


def basic(vals,symbol='X'):
    return {d:{symbol:{'close':str(v)}} for d,v in zip(CAL,vals)}


@pytest.mark.parametrize('values,expected',[
    ([100,102,100,103,101,105],True),  # exactly +5%
    ([100,99,97,96,97,95],True),  # exactly -5%
    ([100,110,105,101,102,100],True),  # exactly 1.10 range
    (['100','110.000000000000000001',105,101,102,100],False),
    ([100,102,100,103,101,'105.000000000000000001'],False),
    ([100,99,97,96,97,'94.999999999999999999'],False),
    ([100,100,100,100,100,100],False),
    ([100,101,102,103,104,105],False),
    ([100,99,98,97,96,95],False),
    ([100,120,115,110,105,100],False),
    ([100,50,101,100,99,100],False),
])
def test_price_state_exact_inclusive_uses_C0_and_strict_directions(values,expected):
    r=m.price_state('X','20260907',basic(values),CAL)
    assert r['_flat'] is expected
    if expected:assert r['flat_strict_up_days']>=1 and r['flat_strict_down_days']>=1
    assert r['flat_close_dates'].split(';')==CAL[:6]


@pytest.mark.parametrize('bad',[None,'','NaN','Infinity','0','-1'])
def test_invalid_past_close_unknown_not_false_or_zero(bad):
    b=basic([100,101,99,100,101,100]);b[CAL[2]]['X']['close']=bad
    assert m.price_state('X','20260907',b,CAL)['_flat'] is None


def test_missing_past_date_not_skipped_or_filled():
    b=basic([100,101,99,100,101,100]);del b[CAL[2]]
    assert m.price_state('X','20260907',b,CAL)['_flat'] is None
    with pytest.raises(ValueError,match='preceding close'):m.price_state('X','20260907',b,CAL[1:])


def row(symbol,cutoff='20260907',cls='A',flat=True,score=1):
    return {'symbol':symbol,'asof':cutoff,'slice':'standalone5_'+cutoff,'lookback':5,'common_eligible':True,'own_feature_eligible':True,'source_class':cls,
            'group_positive_days':3,'active_positive_days':3,'_active_cap':Fraction(score),'_concentration':Fraction(1,2),
            '_flat':flat,'_momentum':None,'_turnover':None}


def test_choose_original_primary_only_and_sameN_counts_not_duplicate_selections():
    fs=[row('000001.SZ',flat=False,score=3),row('000002.SZ',score=2),row('000003.SZ',cls='B'),row('000004.SZ',cls='D'),row('000005.SZ',cls='C',flat=None)]
    selected,counts,matched=m.choose(fs,{'cutoffs':['20260907']})
    assert len(selected)==4
    assert [r['symbol'] for r in selected if r['arm']=='cash_base']==['000001.SZ','000002.SZ']
    assert [r['symbol'] for r in selected if r['arm']=='cash_flat']==['000002.SZ']
    assert [r['symbol'] for r in selected if r['arm']=='flat_not_cash']==['000003.SZ']
    assert all(r['panel']=='standalone5_20260907' for r in selected)
    assert len(matched)==3 and all(c['selected_n']==1 for c in matched)
    assert {c['selected_n'] for c in counts}=={1,2} and all(c['underfilled'] for c in counts)


def test_exact_ranking_ties_and_no_top20_backfill():
    fs=[row(f'{i:06d}.SZ',score=Fraction(2**60+1+i,2**60)) for i in range(1,23)]
    fs.append(row('000999.SZ',cls='C',flat=True))
    selected,counts,matched=m.choose(fs,{'cutoffs':['20260907']})
    assert [r['symbol'] for r in selected if r['arm']=='cash_flat']==[f'{i:06d}.SZ' for i in range(22,2,-1)]
    assert next(c for c in counts if c['arm']=='cash_flat')['eligible_n']==22
    assert all(c['selected_n']==1 for c in matched)


def test_zero_matching_no_fabricated_observations():
    selected,counts,matched=m.choose([row('000001.SZ',flat=False),row('000002.SZ',cls='C')],{'cutoffs':['20260907']})
    assert all(c['selected_n']==0 for c in matched)
    assert len(selected)==2


def test_smoke_hashes_64_unique_symbols_not_64_repeated_feature_rows(tmp_path,monkeypatch):
    symbols=[f'{i:06d}.SZ' for i in range(100)]
    fs=[row(s,cut) for cut in ['20260907','20260908'] for s in symbols]
    cfg={'base_spec_path':'base','cutoffs':['20260907','20260908'],'formation_input_pins':{},'cash_dir':'cash','calendar':CAL,'smoke_hash_seed':'cash-flat-smoke-v16:','smoke_symbol_count':64}
    monkeypatch.setattr(m,'load_spec',lambda p:cfg);monkeypatch.setattr(m.base,'load_spec',lambda p:{'slices':[]})
    monkeypatch.setattr(m.base,'build_features',lambda *args:(fs,[],{}));monkeypatch.setattr(m,'price_state',lambda *args:{'_flat':True})
    actual,_,_=m.build_features('cfg','smoke')
    expected=set(sorted(symbols,key=lambda s:hashlib.sha256(('cash-flat-smoke-v16:'+s).encode()).hexdigest())[:64])
    assert {r['symbol'] for r in actual}==expected


def fixture_selection(tmp_path,monkeypatch):
    cfg={'base_spec_path':'base','cutoffs':['20260907','20260908'],'source_pins':{},'formation_input_pins':{},'prior_price_receipts':{'newest-v15':'pin'},
         'cash_dir':str(tmp_path/'cash'),'calendar':CAL,'future_horizons':[3,5],'price_file_max_bytes':524288,'price_total_max_bytes':536870912,'price_max_symbols':1024}
    fs=[row(symbol,cut,cls=cls) for cut in cfg['cutoffs'] for symbol,cls in [('000001.SZ','A'),('000002.SZ','A'),('000003.SZ','C'),('000004.SZ','C')]]
    monkeypatch.setattr(m,'load_spec',lambda p:cfg)
    monkeypatch.setattr(m,'build_features',lambda *args:(fs,[],{'cash_mode':'full'}))
    monkeypatch.setattr(m.base,'load_spec',lambda p:{'source_price_roots':[str(tmp_path/'prices')],'prior_price_receipts':{'old':'oldpin'}})
    spec=tmp_path/'spec.json';spec.write_text('{}');sel=tmp_path/'selected'
    m.freeze(spec,sel,'smoke')
    return cfg,spec,sel


def test_frozen_selection_precedes_future_intake_and_mutation_is_fatal(tmp_path,monkeypatch):
    monkeypatch.setattr(m.base,'snapshot_prices',lambda *a:pytest.fail('price payload before/after invalid freeze'))
    cfg,spec,sel=fixture_selection(tmp_path,monkeypatch)
    assert not (tmp_path/'prices').exists()
    (sel/'selections.csv').write_text('mutated')
    with pytest.raises(ValueError,match='frozen selection'):m.observe(spec,sel,tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_observe_preserves_date_panels_newest_prior_prices_and_writes_summary(tmp_path,monkeypatch):
    cfg,spec,sel=fixture_selection(tmp_path,monkeypatch)
    def snapshot(symbols,out,s):
        assert s['prior_price_receipts']==cfg['prior_price_receipts']
        bar={'open':'100','high':'102','low':'99','close':'101'}
        return {symbol:{d:bar for d in CAL} for symbol in symbols},{'symbols':len(symbols),'bytes':0,'new_local_price_bytes':0,'files':[]}
    monkeypatch.setattr(m.base,'snapshot_prices',snapshot)
    result=m.observe(spec,sel,tmp_path/'out')
    assert result['selected_rows']==12 and result['path_rows']==24
    assert (tmp_path/'out/summary.json').is_file()
    primary=m.helpers.table(tmp_path/'out/comparison_summary.csv');matched=m.helpers.table(tmp_path/'out/matched_summary.csv')
    assert len(primary)==len(matched)==12
    assert {r['panel'] for r in primary}=={'standalone5_20260907','standalone5_20260908'}
    assert all(r['selected_n']=='2' and r['joint_endpoint_positive']=='2' for r in primary)


@pytest.mark.parametrize('bad',['role','relative_receipt'])
def test_invalid_full_gate_stops_before_cash_payload(tmp_path,monkeypatch,bad):
    cfg={'source_pins':{},'formation_input_pins':{}}
    monkeypatch.setattr(m,'load_spec',lambda *a:cfg);monkeypatch.setattr(m,'build_features',lambda *a:pytest.fail('cash payload before valid gate'))
    spec=tmp_path/'spec';spec.write_text('{}');receipt=tmp_path/'receipt';receipt.write_text('{}')
    gate={'role':'parent_smoke_accepted','execution_spec_sha256':m.sha(spec),'program_sha256':m.sha(m.__file__),'smoke_receipt_path':str(receipt),'smoke_receipt_sha256':m.sha(receipt)}
    if bad=='role':gate['role']='not_parent'
    else:monkeypatch.chdir(tmp_path);gate['smoke_receipt_path']='receipt'
    gp=tmp_path/'gate';gp.write_text(json.dumps(gate))
    with pytest.raises(ValueError):m.freeze(spec,tmp_path/'out','full',gp)
    assert not (tmp_path/'out').exists()
