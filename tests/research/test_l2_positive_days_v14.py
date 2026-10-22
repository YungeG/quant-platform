import hashlib
import json
from fractions import Fraction

import pytest
from experiments import l2_positive_days_v14 as m


def config():
    return {'top_n':20,'variants':[{'id':f'g{g}_a{a}','group_min':g,'active_min':a} for g,a in m.PAIRS]}


def row(symbol,g,a,score):
    return {'symbol':symbol,'name':'synthetic','common_eligible':True,'source_class':'A',
            'group_positive_days':g,'active_positive_days':a,'_active_cap':Fraction(score),
            '_concentration':Fraction(3,4)}


def test_group_and_active_day_counts_are_independent_not_same_inflow():
    fs=[row('000001.SZ',3,5,4),row('000002.SZ',5,3,3),row('000003.SZ',4,4,2),row('000004.SZ',5,5,1)]
    selected,counts=m.select_counts(fs,config(),{})
    get=lambda name:[r['symbol'] for r in selected if r['arm']==name]
    assert get('g3_a3')==['000001.SZ','000002.SZ','000003.SZ','000004.SZ']
    assert get('g4_a3')==['000002.SZ','000003.SZ','000004.SZ']
    assert get('g5_a3')==['000002.SZ','000004.SZ']
    assert get('g3_a4')==['000001.SZ','000003.SZ','000004.SZ']
    assert get('g3_a5')==['000001.SZ','000004.SZ']
    assert get('g5_a5')==['000004.SZ']
    assert all(c['underfilled'] and c['planned_n']==20 for c in counts)


def test_same_exact_rank_in_every_variant_not_resorted_by_future_or_group_count():
    a=row('000001.SZ',5,5,1);b=row('000002.SZ',5,5,1)
    b['_active_cap']+=Fraction(1,10**50)
    rs,_=m.select_counts([a,b],config(),{})
    assert all([r['symbol'] for r in rs if r['arm']==v['id']]==['000002.SZ','000001.SZ'] for v in config()['variants'])


def test_non_A_and_incomplete_features_not_backfilled():
    a=row('000001.SZ',5,5,1);b=row('000002.SZ',5,3,100);b['source_class']='B'
    c=row('000003.SZ',5,5,1000);c['common_eligible']=False
    rs,counts=m.select_counts([a,b,c],config(),{})
    assert {r['symbol'] for r in rs}=={'000001.SZ'}
    assert all(c['selected_n']==1 and c['underfilled'] for c in counts)


def test_empty_variants_preserved_not_lowered_to_three_days():
    rs,counts=m.select_counts([row('000001.SZ',3,3,1)],config(),{})
    assert len(rs)==1 and rs[0]['arm']=='g3_a3'
    assert len(counts)==6 and sum(c['selected_n']==0 for c in counts)==5


def test_selection_freezes_before_any_price_calls(tmp_path,monkeypatch):
    cfg={**config(),'asof':'20260911','base_spec_path':'unused'}
    monkeypatch.setattr(m,'load_spec',lambda *a:cfg)
    monkeypatch.setattr(m.base,'read_spec',lambda *a:{'price_source_dir':str(tmp_path/'prices')})
    monkeypatch.setattr(m.base,'build_features',lambda *a:([row('000001.SZ',5,5,1)],{'cash_mode':'synthetic'}))
    monkeypatch.setattr(m.base,'snapshot_prices',lambda *a:pytest.fail('prices before fixed selection'))
    monkeypatch.setattr(m,'retained_prices',lambda *a:pytest.fail('old prices before fixed selection'))
    sp=tmp_path/'spec.json';sp.write_text('{}');out=tmp_path/'selection'
    result=m.freeze(tmp_path/'cash',out,sp)
    assert result['selected_rows']==6 and result['unique_symbols']==1
    assert result['selections_sha256']==m.sha(out/'selections.csv')
    (out/'selections.csv').write_text('changed')
    with pytest.raises(ValueError,match='frozen selections changed'):
        m.observe(out,tmp_path/'outcomes',sp)
    assert not (tmp_path/'outcomes').exists()


def test_old_missing_price_not_selectively_requeried_and_new_symbol_separate(tmp_path):
    p=tmp_path/'snapshot.csv';p.write_text('date,symbol,open,high,low,close\n2026-09-14,2,100,101,99,100\n')
    receipt={'files':[{'symbol':'000001.SZ','error':'missing_file'},
                      {'symbol':'000002.SZ','snapshot_path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'usable_scoped_dates':['20260914']}]}
    symbols={'000001.SZ','000002.SZ','000003.SZ'}
    bars,files,total=m.retained_prices(symbols,receipt)
    assert bars['000001.SZ']=={} and files['000001.SZ']['error']=='missing_file'
    assert '20260914' in bars['000002.SZ'] and total==p.stat().st_size
    assert symbols-set(bars)=={'000003.SZ'}
