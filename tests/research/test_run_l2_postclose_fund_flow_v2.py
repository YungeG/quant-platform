"""Synthetic delivery fixtures; monkeypatching pins is TEST ONLY, not admission."""
import csv,hashlib,io,json,zlib
from pathlib import Path
import pandas as pd
import pytest
import experiments.run_l2_postclose_fund_flow_v2 as adapter

SYMBOL='688137.SH'
DAYS=('20261014','20261015','20261016')


def csv_bytes(header,rows):
    out=io.StringIO();w=csv.writer(out);w.writerow(header);w.writerows(rows)
    return out.getvalue().encode('gb18030')


def fixture(tmp_path,monkeypatch,*,unknown_ref=False,bad_reconciliation=False,fraction=None,code='\x00',quote_override=None,zero_trade=False):
    raw=tmp_path/'raw';docs=tmp_path/'docs';docs.mkdir();proof=tmp_path/'proof';proof.mkdir()
    quote=['万得代码','交易所代码','自然日','时间','成交价','当日累计成交量','成交笔数','当日成交额']+[f'x{i}' for i in range(58)]+['']
    order=['万得代码','交易所代码','自然日','时间','委托编号','交易所委托号','委托类型','委托代码','委托价格','委托数量','']
    trade=['万得代码','交易所代码','自然日','时间','成交编号','成交代码','委托代码','BS标志','成交价格','成交数量','叫卖序号','叫买序号','']
    catalog={'selected_data_sha256':'synthetic_input_not_market_source','members':[]}
    for day in DAYS:
        common=[SYMBOL,'688137',day]
        total='120001' if bad_reconciliation and day==DAYS[1] else '120000.0'
        px=fraction if fraction and day==DAYS[1] else '100000.0'
        buy='0' if unknown_ref and day==DAYS[1] else '11'
        tables={
            '行情.csv':(quote,[common+['150000000.0',px,total,'2.0','1200000.0']+['0']*58+['']]),
            # No A orders at all: source selection must NOT depend on a join.
            '逐笔委托.csv':(order,[common+['80000000','0','0','S','E','0','0','']]),
            '逐笔成交.csv':(trade,[common+['92500000','900',code,'\x00','B','100000.0','60000.0','21',buy,''],common+['150000000','901',code,'\x00','S','100000.0','60000.0','22','11','']]),
        }
        if zero_trade and day==DAYS[1]:
            tables['逐笔成交.csv'][1].append(common+['150000001','902','0','\x00','','0','0','0','0',''])
        if quote_override and day==DAYS[1]:
            for field,value in quote_override.items():
                tables['行情.csv'][1][0][quote.index(field)]=value
        for kind,(header,rows) in tables.items():
            data=csv_bytes(header,rows);member=f'{day}/{SYMBOL}/{kind}';path=raw/member;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
            catalog['members'].append({'member':member,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'crc32':f'{zlib.crc32(data)&0xffffffff:08X}'})
    manifest=tmp_path/'manifest.json';manifest.write_text(json.dumps(catalog))
    (docs/'description.txt').write_text('Synthetic test only. Never source qualification.')
    (docs/'receipt.json').write_text('{}')
    (docs/'inspection-receipt.json').write_text(json.dumps({'original_share_identity_checked':True,'share_without_query_sha256':'fixture-only'}))
    (proof/'calendar.csv').write_text('cal_date,is_open\n20261014,1\n20261015,1\n20261016,1\n')
    (proof/'calendar.txt').write_text('Synthetic test calendar, not official.')
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    profile={'schema':'same_share_sh_reference_group_profile@2','profile_id':'SYNTHETIC_TEST_NOT_REAL_SOURCE','role':'test_fixture_only','symbols':[SYMBOL],'documents_root':str(docs),'documents':[{'relative_path':'description.txt','bytes':(docs/'description.txt').stat().st_size,'sha256':sha(docs/'description.txt')}],'receipt_sha256':sha(docs/'receipt.json'),'inspection_receipt_sha256':sha(docs/'inspection-receipt.json'),'share_without_query_sha256':'fixture-only','source_scope':{'start':DAYS[0],'end_exclusive':'20261017','source_manifest_sha256':sha(manifest),'selected_data_sha256':catalog['selected_data_sha256']},'calendar':{'path':str(proof/'calendar.csv'),'source_excerpt':str(proof/'calendar.txt'),'sha256':sha(proof/'calendar.csv'),'source_excerpt_sha256':sha(proof/'calendar.txt')},'definition':{'execution_codes':['','0']}}
    profile_path=proof/'profile.json';profile_path.write_text(json.dumps(profile))
    # Only a test changes the trusted software pin. Production CLI has no such option.
    monkeypatch.setattr(adapter,'PROFILE_SHA256',sha(profile_path))
    return raw,manifest,profile_path


def args(tmp_path,inputs,extra=()):
    raw,manifest,profile=inputs
    return ['--raw-root',str(raw),'--source-manifest',str(manifest),'--profile',str(profile),'--output',str(tmp_path/'out'),'--symbols',SYMBOL,'--lookbacks','2','3','--horizons','1',*extra]


def test_source_proxy_cash_survives_no_A_unknown_E_and_unknown_price_basis(tmp_path,monkeypatch):
    inputs=fixture(tmp_path,monkeypatch)
    assert adapter.main(args(tmp_path,inputs))==0
    out=tmp_path/'out';d=pd.read_csv(out/'daily_proxy.csv');p=pd.read_csv(out/'profiles.csv');m=pd.read_csv(out/'matrix.csv');diag=pd.read_csv(out/'order_diagnostics.csv')
    assert len(d)==6 and d.cash_fact_ready.all() and d.proxy_ready.all()
    main=d.loc[d.threshold_cny==1000000]
    aux=d.loc[d.threshold_cny==500000]
    assert main.large_buy_1e4.eq(12000000000).all() and main.large_sell_1e4.eq(0).all()
    assert aux.large_sell_1e4.eq(12000000000).all()
    latest=p.loc[(p.day==20261016)&(p.lookback==3)&(p.threshold_cny==1000000)].iloc[0]
    assert latest.cash_structure_state=='偏买' and bool(latest.F) and pd.isna(latest.P)
    assert p.price_confirmation_state.str.startswith('待核').all()
    assert diag.matched_buy_quantity_share.eq(0).all() and diag.unknown_zero_phase_codes.str.contains('E').all()
    assert m.p_raw.isna().all() and m.n_common.eq(0).all()
    c=json.loads((out/'capabilities.json').read_text());assert c['cash_fact_ready_days']==3 and c['ready_proxy_daily_rows']==6 and c['inference_cells_computed']==0
    binding=json.loads((out/'source_profile_binding.json').read_text());assert not binding['provider_authenticated'] and not binding['original_order_identity_proven']


def test_reconciliation_failure_masks_complete_proxy_and_propagates(tmp_path,monkeypatch):
    inputs=fixture(tmp_path,monkeypatch,bad_reconciliation=True)
    assert adapter.main(args(tmp_path,inputs))==0
    d=pd.read_csv(tmp_path/'out/daily_proxy.csv');p=pd.read_csv(tmp_path/'out/profiles.csv')
    bad=d.loc[d.day==20261015];assert not bad.cash_fact_ready.any() and bad.large_buy_1e4.isna().all()
    assert bad.amount_1e4.eq(12000000000).all()  # observed denominator not filled or deleted
    latest=p.loc[p.day==20261016];assert latest.cash_structure_state.eq('不可用').all() and latest.F.isna().all()


def test_missing_buy_ref_keeps_full_M_and_sell_but_no_direction(tmp_path,monkeypatch):
    inputs=fixture(tmp_path,monkeypatch,unknown_ref=True)
    assert adapter.main(args(tmp_path,inputs))==0
    d=pd.read_csv(tmp_path/'out/daily_proxy.csv');bad=d.loc[d.day==20261015]
    assert bad.cash_fact_ready.all() and not bad.proxy_ready.any()
    assert bad.amount_1e4.eq(12000000000).all() and bad.large_buy_1e4.isna().all()
    assert bad.loc[bad.threshold_cny==500000,'large_sell_1e4'].iloc[0]==12000000000


def test_missing_auxiliary_file_reports_error_without_discarding_cash(tmp_path,monkeypatch):
    inputs=fixture(tmp_path,monkeypatch);(inputs[0]/DAYS[1]/SYMBOL/'逐笔委托.csv').unlink()
    assert adapter.main(args(tmp_path,inputs))==2
    d=pd.read_csv(tmp_path/'out/daily_proxy.csv');assert d.cash_fact_ready.all() and d.proxy_ready.all()
    v=json.loads((tmp_path/'out/source_verification.json').read_text());assert any(x['role']=='auxiliary' for x in v['source_errors'])


def test_missing_quote_keeps_observed_execution_denominator_not_complete_direction(tmp_path,monkeypatch):
    inputs=fixture(tmp_path,monkeypatch);(inputs[0]/DAYS[1]/SYMBOL/'行情.csv').unlink()
    assert adapter.main(args(tmp_path,inputs))==2
    d=pd.read_csv(tmp_path/'out/daily_proxy.csv');bad=d.loc[d.day==20261015]
    assert bad.amount_1e4.eq(12000000000).all() and not bad.cash_fact_ready.any() and bad.large_buy_1e4.isna().all()


@pytest.mark.parametrize('value',['100000.9','100000.0001'])
def test_fractional_quote_price_is_not_truncated_and_does_not_erase_cash(tmp_path,monkeypatch,value):
    inputs=fixture(tmp_path,monkeypatch,fraction=value)
    assert adapter.main(args(tmp_path,inputs))==2
    d=pd.read_csv(tmp_path/'out/daily_proxy.csv');day=d.loc[d.day==20261015]
    assert day.cash_fact_ready.all() and day.proxy_ready.all() and day.close_raw.isna().all()
    v=json.loads((tmp_path/'out/source_verification.json').read_text())
    assert any(e['role']=='price_observation_only' for e in v['source_errors'])


@pytest.mark.parametrize('field,value',[('当日累计成交量','120000.9'),('成交笔数','2.9')])
def test_fractional_required_quote_counters_block_complete_cash(tmp_path,monkeypatch,field,value):
    inputs=fixture(tmp_path,monkeypatch,quote_override={field:value})
    assert adapter.main(args(tmp_path,inputs))==2
    d=pd.read_csv(tmp_path/'out/daily_proxy.csv')
    assert not d.loc[d.day==20261015,'cash_fact_ready'].any()


def test_quote_turnover_diagnostic_precision_not_an_unproved_acceptance_gate(tmp_path,monkeypatch):
    inputs=fixture(tmp_path,monkeypatch,quote_override={'当日成交额':'1200000.50'})
    assert adapter.main(args(tmp_path,inputs))==0
    d=pd.read_csv(tmp_path/'out/daily_proxy.csv');assert d.cash_fact_ready.all()
    o=pd.read_csv(tmp_path/'out/day_observations.csv',dtype={'day':str})
    assert o.loc[o.day=='20261015','quote_amount_difference_cny'].iloc[0]==-.5


def test_unexplained_zero_zero_trade_row_cannot_pass_complete_day(tmp_path,monkeypatch):
    inputs=fixture(tmp_path,monkeypatch,zero_trade=True)
    assert adapter.main(args(tmp_path,inputs))==0
    d=pd.read_csv(tmp_path/'out/daily_proxy.csv');bad=d.loc[d.day==20261015]
    assert bad.amount_1e4.eq(12000000000).all() and not bad.cash_fact_ready.any()
    assert bad.large_buy_1e4.isna().all()
    o=pd.read_csv(tmp_path/'out/day_observations.csv')
    assert o.loc[o.day==20261015,'zero_value_records'].iloc[0]==1
    # Quote counters still match: the unexplained role, not arithmetic, blocks.
    assert bool(o.loc[o.day==20261015,'volume_count_reconciled'].iloc[0])


def test_unknown_execution_code_does_not_get_silently_dropped_or_accepted(tmp_path,monkeypatch):
    inputs=fixture(tmp_path,monkeypatch,code='F')
    assert adapter.main(args(tmp_path,inputs))==0
    d=pd.read_csv(tmp_path/'out/daily_proxy.csv');assert d.amount_1e4.eq(12000000000).all() and not d.cash_fact_ready.any()
    assert d.large_buy_1e4.isna().all()


def test_binding_tamper_or_edited_true_flag_does_not_open_source(tmp_path,monkeypatch):
    inputs=fixture(tmp_path,monkeypatch);p=inputs[2];j=json.loads(p.read_text());j['provider_authenticated']=True;p.write_text(json.dumps(j))
    with pytest.raises(ValueError,match='identity changed'): adapter.main(args(tmp_path,inputs))
    assert not (tmp_path/'out').exists()


def test_changed_document_content_rejected_before_source_read(tmp_path,monkeypatch):
    inputs=fixture(tmp_path,monkeypatch);(tmp_path/'docs/description.txt').write_text('changed')
    with pytest.raises(ValueError,match='content changed'): adapter.main(args(tmp_path,inputs))
    assert not (tmp_path/'out').exists()


def test_parameter_budget_before_input_io(tmp_path):
    with pytest.raises(ValueError,match='budget'):
        adapter.main(['--output',str(tmp_path/'out'),'--profile','/missing/profile.json','--lookbacks','1','2','3','4','5'])
    assert not (tmp_path/'out').exists()


def test_nullable_diagnostics_do_not_round_exact_raw_money():
    big=2**60+1
    rows=[{'observed_amount_1e4':big,'source_cumulative_quantity':big},{'observed_amount_1e4':None}]
    result=adapter._exact_table(rows,('source_cumulative_quantity',))
    assert int(result.loc[0,'observed_amount_1e4'])==big
    assert int(result.loc[0,'source_cumulative_quantity'])==big
    assert str(result.observed_amount_1e4.dtype)=='Int64' and pd.isna(result.loc[1,'observed_amount_1e4'])


def test_group_output_is_reproducible_and_never_original_order_identity(tmp_path,monkeypatch):
    inputs=fixture(tmp_path,monkeypatch)
    assert adapter.main(args(tmp_path,inputs))==0
    paths=list((tmp_path/'out/groups').rglob('*.gz'));hashes={p.relative_to(tmp_path/'out'):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    replay=args(tmp_path,inputs);replay[replay.index('--output')+1]=str(tmp_path/'replay')
    assert adapter.main(replay)==0
    for rel,sha in hashes.items():
        p=tmp_path/'replay'/rel;assert hashlib.sha256(p.read_bytes()).hexdigest()==sha
        g=pd.read_csv(p);assert not g.original_order_identity_proven.any() and g.identity_kind.eq('delivered_reference_group_proxy').all()
