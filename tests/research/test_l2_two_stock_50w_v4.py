import csv,io,hashlib,zlib
import pandas as pd
import pytest
import experiments.run_l2_two_stock_50w_v4 as v4


def trades(symbol='300855.SZ',changes=()):
    rows=[]
    for i,update in enumerate(changes or ({},)):
        r={'成交代码':'0' if symbol.endswith('.SZ') else '\x00','成交价格':'100000','成交数量':'10','叫买序号':'10','叫卖序号':'1','BS标志':'B','成交编号':str(i+1),'时间':'93000000','_source_record':i+1,'ms':34200000}
        r.update(update);rows.append(r)
    return pd.DataFrame(rows)


def quote(qty=10,count=1):
    return pd.DataFrame([{'当日累计成交量':str(qty),'成交笔数':str(count),'成交价':'100000','当日成交额':str(qty*10),'ms':54000000}])


def test_sz_positive_price_cancel_is_never_execution():
    t=trades(changes=({}, {'成交代码':'C','成交价格':'100000','成交数量':'100','叫买序号':'0','BS标志':''}))
    r,info,ok=v4.select_executions(t,'20261019','300855.SZ')
    assert ok and len(r)==1 and info['cancel_records_excluded']==1 and info['cancel_quantity_excluded']==100
    obs,cells,diag,m=v4.analyze_day({'逐笔成交.csv':t,'行情.csv':quote()},'20261019','300855.SZ')
    assert obs['cash_fact_ready'] and obs['observed_quantity']==10 and obs['observed_amount_1e4']==1000000
    assert sum(c['amount_1e4'] for c in cells if c['side']=='B')==1000000


@pytest.mark.parametrize('symbol,code',[('300855.SZ','D'),('300855.SZ',''),('300855.SZ','F'),('688202.SH','C'),('688202.SH','D')])
def test_unexplained_market_specific_role_blocks_completeness(symbol,code):
    t=trades(symbol,({}, {'成交代码':code}))
    obs,cells,_,_=v4.analyze_day({'逐笔成交.csv':t,'行情.csv':quote(10,1)},'20261019',symbol)
    assert not obs['cash_fact_ready'] and obs['unknown_role_records']==1 and not cells


def test_sh_empty_code_and_no_A_required():
    t=trades('688202.SH');obs,c,_,m=v4.analyze_day({'逐笔成交.csv':t,'行情.csv':quote()},'20261019','688202.SH')
    assert obs['cash_fact_ready'] and m['observed_active_buy_1e4']==1000000
    assert all(x['complete_cell_ready'] for x in c)


def test_full_day_group_then_role_split_and_exact_50w_boundary():
    t=trades(changes=({'成交数量':'20000'},{'成交数量':'30000','叫卖序号':'20','BS标志':'S'}))
    o,c,_,_=v4.analyze_day({'逐笔成交.csv':t,'行情.csv':quote(50000,2)},'20261019','300855.SZ')
    b=next(x for x in c if x['side']=='B' and x['band_id']==1)
    assert o['cash_fact_ready'] and b['amount_1e4']==5000000000
    assert b['active_1e4']==2000000000 and b['passive_1e4']==3000000000


def test_unknown_both_refs_retains_unknown_buckets_not_retail():
    t=trades(changes=({'叫买序号':'0','叫卖序号':'0'},))
    o,c,_,m=v4.analyze_day({'逐笔成交.csv':t,'行情.csv':quote()},'20261019','300855.SZ')
    assert o['cash_fact_ready'] and m['observed_unclassified_1e4']==1000000
    assert all(x['amount_1e4']==1000000 for x in c if x['band_id']==-1)
    assert all(x['amount_1e4'] is None for x in c if x['band_id']!=-1)


def test_bad_cumulative_count_keeps_observed_not_full_money():
    o,c,_,_=v4.analyze_day({'逐笔成交.csv':trades(),'行情.csv':quote(11,2)},'20261019','300855.SZ')
    assert not o['cash_fact_ready'] and o['quantity_gap']==1 and o['record_count_gap']==1
    assert all(x['amount_1e4'] is None for x in c)
    assert sum(x['observed_amount_1e4'] for x in c if x['side']=='B')==1000000


def test_source_last_price_or_quote_amount_not_cash_acceptance_gate():
    q=quote();q.loc[0,'成交价']='100000.9';q.loc[0,'当日成交额']='100.5'
    o,_,_,_=v4.analyze_day({'逐笔成交.csv':trades(),'行情.csv':q},'20261019','300855.SZ')
    assert o['cash_fact_ready'] and 'source_last_price_raw' not in o and o['quote_amount_difference_cny']=='-0.5'


def test_literal_duplicate_not_deduplicated_or_qualified():
    t=trades(changes=({},{}));t.loc[1,'成交编号']='1'
    o,c,_,_=v4.analyze_day({'逐笔成交.csv':t,'行情.csv':quote(20,2)},'20261019','300855.SZ')
    assert not o['cash_fact_ready'] and o['exact_duplicate_candidates']==1 and not c


def test_explained_zero_price_cancel_allowed_but_zero_trade_not():
    t=trades(changes=({}, {'成交代码':'C','成交价格':'0','成交数量':'100','BS标志':''}))
    assert v4.analyze_day({'逐笔成交.csv':t,'行情.csv':quote()},'20261019','300855.SZ')[0]['cash_fact_ready']
    t.loc[1,'成交代码']='0'
    assert not v4.analyze_day({'逐笔成交.csv':t,'行情.csv':quote()},'20261019','300855.SZ')[0]['cash_fact_ready']


def test_reader_is_new_scope_and_preserves_nul(tmp_path):
    day='20261019';sym='300855.SZ';header=list(v4._TRADE_HEADER);row=[sym,'300855',day,'93000000.0','1','0','\x00','B','100000.0','10.0','1','1\x000','']
    text=io.StringIO();w=csv.writer(text);w.writerow(header);w.writerow(row);raw=text.getvalue().encode('gb18030');p=tmp_path/'t.csv';p.write_bytes(raw)
    meta={'bytes':len(raw),'crc32':f'{zlib.crc32(raw)&0xffffffff:08x}','sha256':hashlib.sha256(raw).hexdigest(),'member':f'{day}/{sym}/逐笔成交.csv'}
    f,d=v4.read_bound_v4(p,meta,day,sym,'逐笔成交.csv');assert f.loc[0,'叫买序号']=='1\x000' and f.loc[0,'ms']==34200000
    with pytest.raises(ValueError,match='scope'):v4.read_bound_v4(p,meta,day,'688137.SH','逐笔成交.csv')
    with pytest.raises(ValueError,match='content'):v4.read_bound_v4(p,{**meta,'sha256':'0'*64},day,sym,'逐笔成交.csv')


def test_subset_inventory_recomputes_selection_accounting():
    plan={'archives':[{'day':'20261016','involved_solid_uncompressed_bytes':100},{'day':'20261019','involved_solid_uncompressed_bytes':200}],'members':[{'member':'20261016/300855.SZ/行情.csv','bytes':10},{'member':'20261019/300855.SZ/行情.csv','bytes':20}],'missing_members':['20261016/688202.SH/逐笔成交.csv'],'selected_bytes':30,'involved_solid_bytes':300}
    sub=v4.subset_inventory(plan,('20261019',))
    assert sub['selected_bytes']==20 and sub['involved_solid_bytes']==200 and sub['missing_members']==[]
    assert sub['all_local_inventory_totals']['selected_bytes']==30 and len(plan['archives'])==2


def test_final_archive_cannot_report_success_after_global_deadline(tmp_path,monkeypatch):
    from types import SimpleNamespace
    archive=tmp_path/'a.7z';archive.write_bytes(b'x');stat=archive.stat();member='20261019/300855.SZ/行情.csv';payload=b'abc';cache=tmp_path/'raw'
    plan={'archives':[{'path':str(archive),'day':'20261019','bytes':stat.st_size,'mtime_ns':stat.st_mtime_ns}],'members':[{'archive':str(archive),'member':member,'bytes':3,'crc32':f'{zlib.crc32(payload)&0xffffffff:08x}'}]}
    state={'calls':0,'done':False};timeouts=[]
    def clock():
        state['calls']+=1
        return 0 if state['calls']==1 else (1849 if state['done'] else 1799)
    def extract(*args,**kwargs):
        timeouts.append(kwargs['timeout']);path=cache/member;path.parent.mkdir(parents=True);path.write_bytes(payload);state['done']=True
        return SimpleNamespace(returncode=0,stderr='')
    monkeypatch.setattr(v4.time,'monotonic',clock);monkeypatch.setattr(v4.subprocess,'run',extract)
    with pytest.raises(ValueError,match='elapsed budget'):v4.extract_selected(plan,cache)
    assert timeouts==[1]


def test_calendar_holidays_and_new_oct19_not_prospective():
    cal=v4.retrospective_calendar();assert len(cal)==29 and cal[-1]=='20261019'
    assert '20260925' not in cal and '20261010' not in cal and '20261017' not in cal and '20261018' not in cal
    assert '20261008' in cal


def test_windows_preserve_missing_day_and_do_not_merge_refs_across_days():
    cal=('20261014','20261015','20261016','20261019');obs=[];wide=[]
    for d in cal:
        o,c,_,_=v4.analyze_day({'逐笔成交.csv':trades(changes=({'成交数量':'25000'},{'成交数量':'25000','叫卖序号':'2'})),'行情.csv':quote(50000,2)},d,'300855.SZ');obs.append(o);wide.extend(v4.wide_rows(c))
    windows=v4.period_windows(wide,obs,cal);latest=next(w for w in windows if w['symbol']=='300855.SZ' and w['day']=='20261019' and w['lookback']==3)
    assert latest['window_ready'] and latest['positive_group_days']==3 and latest['group_difference_1e4']==15000000000
    obs[1]['cash_fact_ready']=False
    latest=next(w for w in v4.period_windows(wide,obs,cal) if w['symbol']=='300855.SZ' and w['day']=='20261019' and w['lookback']==3)
    assert not latest['window_ready'] and 'group_difference_1e4' not in latest
    assert all(not w['window_ready'] for w in windows if w['lookback'] in (5,10,20))
