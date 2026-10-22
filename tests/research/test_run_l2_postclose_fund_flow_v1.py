"""Tiny synthetic raw CSV fixtures exercise the SAME reader and report path."""
import csv,hashlib,io,json,zlib
from pathlib import Path
import pandas as pd
import pytest
from experiments.run_l2_postclose_fund_flow_v1 import main,QUAL_KEYS

SYMBOL='688122.SH'
DAYS=('20261001','20261002')  # Synthetic test calendar, not an exchange claim.


def fixture(tmp_path):
    raw=tmp_path/'raw';proof=tmp_path/'proof';proof.mkdir()
    quote=['万得代码','交易所代码','自然日','时间','成交价','当日累计成交量','成交笔数']+[f'x{i}' for i in range(59)]+['']
    order=['万得代码','交易所代码','自然日','时间','委托编号','交易所委托号','委托类型','委托代码','委托价格','委托数量','']
    trade=['万得代码','交易所代码','自然日','时间','成交编号','成交代码','委托代码','BS标志','成交价格','成交数量','叫卖序号','叫买序号','']
    manifest={'selected_data_sha256':'synthetic_fixture_not_real_source','members':[]}
    for day in DAYS:
        prefix=[SYMBOL,'688122',day]
        tables={
            '行情.csv':(quote,[prefix+['150000000','100000','200','2']+['0']*59+['']]),
            '逐笔委托.csv':(order,[prefix+['91500000','1','11','A','B','100000','200',''],prefix+['91500000','2','21','A','S','100000','100',''],prefix+['91500000','3','22','A','S','100000','100','']]),
            '逐笔成交.csv':(trade,[prefix+['92500000','900','\x00','\x00','B','100000','100','21','11',''],prefix+['150000000','901','\x00','\x00','S','100000','100','22','11','']]),
        }
        for name,(header,rows) in tables.items():
            buf=io.StringIO();w=csv.writer(buf);w.writerow(header);w.writerows(rows)
            data=buf.getvalue().encode('gb18030');member=f'{day}/{SYMBOL}/{name}';path=raw/member
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
            manifest['members'].append({'member':member,'bytes':len(data),'crc32':f'{zlib.crc32(data)&0xffffffff:08X}','sha256':hashlib.sha256(data).hexdigest()})
    catalog=tmp_path/'catalog.json';catalog.write_text(json.dumps(manifest))
    (proof/'calendar.csv').write_text('cal_date,is_open\n20261001,1\n20261002,1\n')
    (proof/'source.txt').write_text('SYNTHETIC TEST ONLY. No market authority.')
    notes={'schema':'l2_postclose_source_qualification_notes@1',**{k:False for k in QUAL_KEYS},'calendar':{'path':'calendar.csv','source_excerpt':'source.txt','scope_start':DAYS[0],'scope_end_inclusive':DAYS[-1],'status':'synthetic_test_only'},'blockers':['fixture_source_not_qualified']}
    note=proof/'notes.json';note.write_text(json.dumps(notes))
    return raw,catalog,note


def arguments(tmp_path,inputs):
    raw,catalog,note=inputs
    return ['--raw-root',str(raw),'--source-manifest',str(catalog),'--qualification-notes',str(note),'--output',str(tmp_path/'out'),'--symbols',SYMBOL,'--lookbacks','2','--horizons','1']


def test_raw_reader_to_report_keeps_semantic_gates_closed(tmp_path):
    inputs=fixture(tmp_path);assert main(arguments(tmp_path,inputs))==0
    out=tmp_path/'out'
    q=json.loads((out/'qualification_report.json').read_text())
    assert q['engineering_status']=='completed_audit_with_blocked_research'
    assert q['research_status']=='blocked' and not q['semantic_gate_opened']
    assert q['qualified_fund_flow_rows']==q['inference_cells_computed']==0
    assert q['comparison_cells']==2 and q['prospective_dates_used']==0 and q['new_dates'] is None
    run=json.loads((out/'run_spec.json').read_text())
    for name,sha in run['code_sha256'].items():
        assert hashlib.sha256((Path('experiments')/name).read_bytes()).hexdigest()==sha
    assert 'l2_three_stock_microstructure_v1.py' in run['code_sha256']
    assert {'python','pandas','numpy'}==set(run['environment'])
    verification=json.loads((out/'source_verification.json').read_text())
    assert verification['physical_complete'] and verification['selected_verified_files']==6
    r=pd.read_csv(out/'raw_daily_audit.csv')
    assert r.candidate_amount_1e4.eq(20000000).all() and r.candidate_vwap_cny.eq(10).all()
    assert r.clock_pre0930_records.eq(1).all() and r.clock_from1457_records.eq(1).all()
    d=pd.read_csv(out/'daily_inputs.csv')
    assert d.large_buy_1e4.isna().all() and not d.order_ok.any()
    p=pd.read_csv(out/'profiles.csv');m=pd.read_csv(out/'matrix.csv')
    assert p.F.isna().all() and p.P.isna().all() and p.description.eq('数据不足').all()
    assert m.n_total_anchors.eq(2).all() and m.n_common.eq(0).all()
    assert m.delta_up_fraction.isna().all() and m.p_raw.isna().all()
    assert '不是资金判断' in (out/'report.md').read_text()


def test_corrupted_source_is_failure_not_zero_or_complete(tmp_path):
    inputs=fixture(tmp_path)
    path=inputs[0]/DAYS[0]/SYMBOL/'逐笔成交.csv'
    path.write_bytes(path.read_bytes()+b'bad')
    assert main(arguments(tmp_path,inputs))==2
    q=json.loads((tmp_path/'out/qualification_report.json').read_text())
    assert q['physical_failed_stock_days']==1 and q['research_status']=='blocked'
    assert q['reconciliation_failed_stock_days']==0
    v=json.loads((tmp_path/'out/source_verification.json').read_text())
    assert not v['physical_complete'] and len(v['failures'])==1
    r=pd.read_csv(tmp_path/'out/raw_daily_audit.csv')
    assert r.loc[r.audit_status=='file_or_schema_failed','candidate_vwap_cny'].isna().all()


def test_editing_a_qualification_boolean_cannot_admit_a_supplier(tmp_path):
    inputs=fixture(tmp_path);note=inputs[2];d=json.loads(note.read_text());d['order_scope_qualified']=True;note.write_text(json.dumps(d))
    with pytest.raises(ValueError,match='cannot admit'): main(arguments(tmp_path,inputs))
    assert not (tmp_path/'out').exists()


def test_budget_rejected_before_missing_manifest_is_read(tmp_path):
    with pytest.raises(ValueError,match='budget'):
        main(['--source-manifest','/missing/catalog.json','--output',str(tmp_path/'out'),'--lookbacks','1','2','3','4','5'])
    assert not (tmp_path/'out').exists()


def test_catalog_escape_rejected_before_any_raw_file_is_read(tmp_path):
    inputs=fixture(tmp_path);m=json.loads(inputs[1].read_text());m['members'][0]['member']='../private/行情.csv';inputs[1].write_text(json.dumps(m))
    with pytest.raises(ValueError,match='catalog'): main(arguments(tmp_path,inputs))
    assert not (tmp_path/'out').exists()


def test_symlink_source_is_not_followed(tmp_path):
    inputs=fixture(tmp_path);p=inputs[0]/DAYS[0]/SYMBOL/'行情.csv'
    outside=tmp_path/'not_source.txt';outside.write_text('not source data')
    p.unlink();p.symlink_to(outside)
    assert main(arguments(tmp_path,inputs))==2
    v=json.loads((tmp_path/'out/source_verification.json').read_text())
    assert len(v['failures'])==1 and 'escapes raw root' in v['failures'][0]['error']


def test_no_overwrite(tmp_path):
    inputs=fixture(tmp_path);(tmp_path/'out').mkdir()
    with pytest.raises(ValueError,match='output must be new'): main(arguments(tmp_path,inputs))


@pytest.mark.parametrize('field,value',[
    ('当日累计成交量','200.9'),('成交笔数','2.9'),('成交价','100000.5'),('时间','150000000.5'),
])
def test_manifest_consistent_fractional_quote_never_reconciles_by_truncation(tmp_path,field,value):
    inputs=fixture(tmp_path);member=f'{DAYS[0]}/{SYMBOL}/行情.csv';path=inputs[0]/member
    rows=list(csv.reader(io.StringIO(path.read_bytes().decode('gb18030'))))
    rows[1][rows[0].index(field)]=value
    buf=io.StringIO();csv.writer(buf).writerows(rows);raw=buf.getvalue().encode('gb18030');path.write_bytes(raw)
    manifest=json.loads(inputs[1].read_text())
    m=next(x for x in manifest['members'] if x['member']==member)
    m.update(bytes=len(raw),crc32=f'{zlib.crc32(raw)&0xffffffff:08X}',sha256=hashlib.sha256(raw).hexdigest())
    inputs[1].write_text(json.dumps(manifest))
    assert main(arguments(tmp_path,inputs))==2
    audit=pd.read_csv(tmp_path/'out/raw_daily_audit.csv',dtype={'day':str})
    broken=audit.loc[audit.day==DAYS[0]].iloc[0]
    assert broken.audit_status=='file_or_schema_failed' and not broken.raw_reconciliation_ok
    assert pd.isna(broken.candidate_vwap_cny)
