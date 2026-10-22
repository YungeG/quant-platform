"""Synthetic arithmetic tests, never provider or real-order admission."""
import json
import csv,io,hashlib,zlib
import importlib.util
from pathlib import Path
import pandas as pd
import pytest
from experiments.l2_postclose_core_v1 import PostcloseSpec
from experiments.l2_postclose_source_v2 import reference_group_facts
import experiments.run_l2_postclose_ladder_v3 as v3
# Reuse the retained repository-owned synthetic builder (not provider code).
_spec=importlib.util.spec_from_file_location('_v2_test_fixtures',Path(__file__).with_name('test_run_l2_postclose_fund_flow_v2.py'))
_fixtures=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fixtures)
source_fixture=_fixtures.fixture

SYMBOL='688137.SH'


def make_records(rows):
    result=[]
    for i,values in enumerate(rows):
        r={'day':'20261016','symbol':SYMBOL,'record_key':f'r{i}','price_raw':1000000,'quantity':1,'buy_ref':'10','sell_ref':'1','source_bs':'B','ms':34200000}
        r.update(values);result.append(r)
    return pd.DataFrame(result)


def facts(records,edges=v3.EDGES):
    groups,_=reference_group_facts(records,PostcloseSpec(symbols=(SYMBOL,)))
    return v3.ladder_facts(records,groups,edges)


@pytest.mark.parametrize('edges',[(1,2),(0,2,1),(0,1,1),(0,True),(0,1.0),tuple(range(13)),(0,10**19)])
def test_invalid_band_definitions(edges):
    with pytest.raises(ValueError):v3.validate_edges(edges)


@pytest.mark.parametrize('raw,index',[(1,0),(499999999,0),(500000000,1),(1999999999,1),(2000000000,2),(5000000000,3),(10000000000,4),(50000000000,5)])
def test_exact_half_open_cash_boundaries(raw,index):
    cells,_,_=facts(make_records([{'price_raw':raw}]))
    b=[r for r in cells if r['side']=='B' and r['observed_amount_1e4']]
    assert len(b)==1 and b[0]['band_id']==index and b[0]['observed_amount_1e4']==raw


def test_classify_whole_group_before_active_passive_split():
    records=make_records([{'price_raw':7000000000},{'price_raw':8000000000,'sell_ref':'20','source_bs':'S'}])
    cells,_,market=facts(records)
    c=next(c for c in cells if c['side']=='B' and c['band_id']==4)
    assert c['observed_amount_1e4']==15000000000
    assert c['observed_active_1e4']==7000000000 and c['observed_passive_1e4']==8000000000
    assert c['known_reference_groups']==1
    assert c['known_active_reference_groups']==c['known_passive_reference_groups']==1
    assert c['observed_active_quantity']==c['observed_passive_quantity']==1
    assert c['observed_active_execution_legs']==c['observed_passive_execution_legs']==1
    assert sum(c['observed_amount_1e4'] for c in cells)==2*market['observed_amount_1e4']
    assert market['observed_active_buy_1e4']==7000000000 and market['observed_active_sell_1e4']==8000000000
    assert sum(c['observed_passive_1e4'] for c in cells)==market['observed_amount_1e4']


@pytest.mark.parametrize('ms,wanted',[(34199999,'U'),(34200000,'B'),(41399999,'B'),(41400000,'U'),(46799999,'U'),(46800000,'B'),(53819999,'B'),(53820000,'U'),(33900000,'U'),(54000000,'U')])
def test_clock_scope_is_half_open_and_auction_unknown(ms,wanted):
    assert v3.source_aggressor('B',ms,'10','1')[0]==wanted


@pytest.mark.parametrize('changes,reason',[({'source_bs':''},'unsupported_or_missing_BS'),({'source_bs':'b'},'unsupported_or_missing_BS'),({'buy_ref':'0'},'reference_rule_unverifiable'),({'buy_ref':'1'},'equal_references'),({'source_bs':'S'},'BS_reference_rule_conflict'),({'buy_ref':'1\x000'},'reference_rule_unverifiable')])
def test_unexplained_activity_kept_not_repaired(changes,reason):
    cells,diag,market=facts(make_records([changes]))
    assert market['observed_unclassified_1e4']==1000000 and market['source_classified_cash_share']==0
    assert diag[0]['reason']==reason
    assert sum(c['observed_unclassified_1e4'] for c in cells)==2000000
    if changes.get('buy_ref') in ('0','1\x000'):
        c=next(c for c in cells if c['side']=='B' and c['band_id']==-1)
        assert c['observed_amount_1e4']==1000000 and c['known_reference_groups'] is None


def test_code_padding_only_and_passive_counterparty():
    cells,_,m=facts(make_records([{'source_bs':'\x00 S\x00','buy_ref':'1','sell_ref':'10'}]))
    assert m['observed_active_sell_1e4']==1000000
    assert sum(c['observed_passive_1e4'] for c in cells if c['side']=='B')==1000000
    assert sum(c['observed_active_1e4'] for c in cells if c['side']=='S')==1000000


def test_large_cash_exact_and_membership_tamper_rejected():
    big=2**60+1;r=make_records([{'price_raw':big}]);g,_=reference_group_facts(r,PostcloseSpec(symbols=(SYMBOL,)))
    cells,_,m=v3.ladder_facts(r,g)
    assert m['observed_amount_1e4']==big
    assert sum(c['observed_amount_1e4'] for c in cells if c['side']=='B')==big
    g.loc[0,'amount_1e4']+=1
    with pytest.raises(ValueError,match='membership'):v3.ladder_facts(r,g)


def test_days_never_merged_into_one_size_bucket():
    r=make_records([{}, {'day':'20261015'}]);g,_=reference_group_facts(r,PostcloseSpec(symbols=(SYMBOL,)))
    with pytest.raises(ValueError,match='one stock/day'):v3.ladder_facts(r,g)


def cli_args(tmp_path,inputs):
    raw,manifest,profile=inputs
    return ['--output',str(tmp_path/'out'),'--raw-root',str(raw),'--source-manifest',str(manifest),'--profile',str(profile),'--symbols',SYMBOL]


def test_cli_disjoint_amounts_no_A_all_auction_unknown(tmp_path,monkeypatch):
    inputs=source_fixture(tmp_path,monkeypatch)
    assert v3.main(cli_args(tmp_path,inputs))==0
    o=tmp_path/'out';b=pd.read_csv(o/'bands.csv');m=pd.read_csv(o/'market_activity.csv')
    assert len(b)==42 and b.complete_cell_ready.all()
    assert m.source_classified_cash_share.eq(0).all() and m.observed_unclassified_1e4.eq(12000000000).all()
    assert b.loc[(b.side=='B')&(b.band_id==4),'amount_1e4'].eq(12000000000).all()
    assert b.loc[(b.side=='S')&(b.band_id==3),'amount_1e4'].eq(12000000000).all()
    run=json.loads((o/'run_spec.json').read_text());assert not run['formal_provider_admitted'] and not run['price_capability_enabled']
    assert len(json.loads((o/'source_verification.json').read_text())['verified_files'])==6


def test_bad_day_observation_kept_complete_cash_not_filled(tmp_path,monkeypatch):
    inputs=source_fixture(tmp_path,monkeypatch,bad_reconciliation=True)
    assert v3.main(cli_args(tmp_path,inputs))==0
    b=pd.read_csv(tmp_path/'out/bands.csv');bad=b.loc[b.day==20261015]
    assert bad.amount_1e4.isna().all() and not bad.complete_cell_ready.any()
    assert bad.loc[bad.side=='B','observed_amount_1e4'].sum()==12000000000
    w=pd.read_csv(tmp_path/'out/bands_wide.csv');assert w.loc[w.day==20261015,'difference_1e4'].isna().all()


def test_unknown_reference_bucket_is_not_retail_and_other_side_survives(tmp_path,monkeypatch):
    inputs=source_fixture(tmp_path,monkeypatch,unknown_ref=True)
    assert v3.main(cli_args(tmp_path,inputs))==0
    b=pd.read_csv(tmp_path/'out/bands.csv');bad=b.loc[b.day==20261015]
    assert bad.loc[(bad.side=='B')&(bad.band_id!=-1),'amount_1e4'].isna().all()
    assert bad.loc[(bad.side=='B')&(bad.band_id==-1),'amount_1e4'].iloc[0]==6000000000
    assert bad.loc[(bad.side=='S')&(bad.band_id==3),'amount_1e4'].iloc[0]==12000000000


def test_all_unknown_references_retain_full_unknown_buckets(tmp_path,monkeypatch):
    inputs=source_fixture(tmp_path,monkeypatch);raw,manifest,profile=inputs
    catalog=json.loads(manifest.read_text())
    for meta in catalog['members']:
        if not meta['member'].endswith('逐笔成交.csv'):continue
        path=raw/meta['member'];rows=list(csv.reader(io.StringIO(path.read_bytes().decode('gb18030'))))
        for row in rows[1:]:row[10]=row[11]='0'
        text=io.StringIO();csv.writer(text).writerows(rows);data=text.getvalue().encode('gb18030');path.write_bytes(data)
        meta.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),crc32=f'{zlib.crc32(data)&0xffffffff:08X}')
    manifest.write_text(json.dumps(catalog));p=json.loads(profile.read_text());p['source_scope']['source_manifest_sha256']=hashlib.sha256(manifest.read_bytes()).hexdigest();profile.write_text(json.dumps(p))
    # Only synthetic test software can replace a pin; production CLI cannot.
    monkeypatch.setattr(_fixtures.adapter,'PROFILE_SHA256',hashlib.sha256(profile.read_bytes()).hexdigest())
    assert v3.main(cli_args(tmp_path,inputs))==0
    b=pd.read_csv(tmp_path/'out/bands.csv');unknown=b.loc[b.band_id==-1]
    assert unknown.amount_1e4.eq(12000000000).all() and unknown.complete_cell_ready.all()
    assert b.loc[b.band_id!=-1,'amount_1e4'].isna().all()
    assert unknown.known_reference_groups.isna().all()
    m=pd.read_csv(tmp_path/'out/market_activity.csv');assert m.observed_unclassified_1e4.eq(12000000000).all()


def test_missing_required_source_reports_failure_without_zero_cash(tmp_path,monkeypatch):
    inputs=source_fixture(tmp_path,monkeypatch);(inputs[0]/'20261015'/SYMBOL/'行情.csv').unlink()
    assert v3.main(cli_args(tmp_path,inputs))==2
    b=pd.read_csv(tmp_path/'out/bands.csv');bad=b.loc[b.day==20261015]
    assert bad.amount_1e4.isna().all() and bad.observed_amount_1e4.sum()==24000000000


def test_bad_config_before_source_io_and_output_never_overwritten(tmp_path,monkeypatch):
    with pytest.raises(ValueError,match='sorted unique'):
        v3.main(['--output',str(tmp_path/'out'),'--profile','/missing','--band-edges-cny','0','1','1'])
    assert not (tmp_path/'out').exists()
    inputs=source_fixture(tmp_path,monkeypatch)
    assert v3.main(cli_args(tmp_path,inputs))==0
    with pytest.raises(ValueError,match='must be new'):v3.main(cli_args(tmp_path,inputs))
