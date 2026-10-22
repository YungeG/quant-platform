"""Continuous-window LOCAL descriptions, not single-day filtering or PnL.

Cash grouping/source-BS definitions stay frozen. Raw price values are NOT a
qualified comparable return series; the price axis is intentionally separate.
"""
from __future__ import annotations
import argparse,csv,hashlib,io,json
from collections import Counter
from decimal import Decimal,InvalidOperation
from pathlib import Path
import pandas as pd
from experiments.l2_postclose_source_v2 import exact_integer,_clock
from experiments.run_l2_postclose_fund_flow_v2 import ROOT,dump,digest,_exact_table
from experiments.run_l2_two_stock_50w_v4 import retrospective_calendar

SYMBOLS=('300855.SZ','688122.SH','688137.SH','688202.SH','688655.SH')
WINDOWS=(5,10,20)
HOME=Path('/srv/bcache-8t/ygguo/quant/l2-continuous-interval-v6')
BASE3=Path('/srv/bcache-8t/ygguo/quant/l2-postclose-ladder-active-v3/full_v1')
BASE2=Path('/srv/bcache-8t/ygguo/quant/l2-two-stock-50w-v4/full_v1')
BASIC=Path('/srv/bcache-8t/ygguo/quant/l2-turnover-price-v5/turnover_intake.json')
SPEC=ROOT/'research/l2-continuous-interval-v6-spec.md'


def streak(values):
    longest=current=0
    for flag in values:
        current=current+1 if flag else 0;longest=max(longest,current)
    return longest


def concentration(values,n):
    positive=sorted((v for v in values if v>0),reverse=True)
    return None if not positive else str(Decimal(sum(positive[:n]))/sum(positive))


def cumulative_fall(values):
    total=peak=fall=0
    for v in values:
        total+=v;peak=max(peak,total);fall=max(fall,peak-total)
    return fall


def interval_profile(days,W):
    if W not in WINDOWS or len(days)>W:raise ValueError('unsupported interval')
    if not days:raise ValueError('empty interval')
    if len({d['symbol'] for d in days})!=1 or any(a['day']>=b['day'] for a,b in zip(days,days[1:])):raise ValueError('foreign/unsorted/duplicate stock-day')
    r={'symbol':days[-1]['symbol'],'day':days[-1]['day'],'start':days[0]['day'],'lookback':W,'observed_days':len(days),'cash_window_ready':False,'activity_window_ready':False,'price_comparability_qualified':False,'price_trend_status':'pending_source_adjustment_and_corporate_action_evidence','qualified_price_change_pct':None,'qualified_price_drawdown_pct':None,'identity_kind':'delivered_reference_group_proxy_not_retained_inventory'}
    if len(days)<W:r['cash_reason']='warmup';return r
    rates=[d.get('turnover_rate') for d in days]
    if all(isinstance(x,Decimal) and x.is_finite() and x>=0 for x in rates):
        avg=sum(rates)/W;flags=[x>10 for x in rates]
        r.update(activity_window_ready=True,mean_turnover_pct=str(avg),high_turnover_days=sum(flags),longest_high_turnover_streak=streak(flags),max_daily_turnover_pct=str(max(rates)),activity_candidate=avg>10)
    else:r['activity_reason']='missing_or_invalid_turnover'
    invalid=[d['day'] for d in days if not d.get('cash_ready',False) or any(d.get(k) is None for k in ('buy','sell','active_buy','active_sell','passive_buy','passive_sell','unknown_buy','unknown_sell','market_amount'))]
    r['invalid_cash_dates']=';'.join(invalid)
    if invalid:r['cash_reason']='unqualified_day_no_skip_no_zero_fill'
    else:
        totals={k:exact_integer(sum(d[k] for d in days),k) for k in ('buy','sell','active_buy','active_sell','passive_buy','passive_sell','unknown_buy','unknown_sell','market_amount')}
        gd=[d['buy']-d['sell'] for d in days];ad=[d['active_buy']-d['active_sell'] for d in days]
        g=totals['buy']-totals['sell'];a=totals['active_buy']-totals['active_sell'];p=totals['passive_buy']-totals['passive_sell'];u=totals['unknown_buy']-totals['unknown_sell']
        if g!=a+p+u:raise ValueError('role delta conservation failed')
        npos=sum(v>0 for v in gd);apos=sum(v>0 for v in ad)
        r.update(cash_window_ready=True,cash_reason='complete_market_day_window',group_difference_1e4=g,active_difference_1e4=a,passive_difference_1e4=p,unknown_difference_1e4=u,group_positive_days=npos,group_negative_days=sum(v<0 for v in gd),active_positive_days=apos,active_negative_days=sum(v<0 for v in ad),group_positive_streak=streak([v>0 for v in gd]),active_positive_streak=streak([v>0 for v in ad]),top1_share_of_positive_deltas=concentration(gd,1),top2_share_of_positive_deltas=concentration(gd,2),max_cumulative_group_delta_fall_1e4=cumulative_fall(gd),group_buy_bias=g>0 and npos>W/2,active_support=a>0 and apos>W/2)
        r.update({k+'_1e4':v for k,v in totals.items()})
        r['group_difference_share_of_all_cash']=str(Decimal(g)/totals['market_amount']) if totals['market_amount'] else None
        r['source_cash_state']='偏买且主动支持' if r['group_buy_bias'] and r['active_support'] else ('偏买但主动未持续' if r['group_buy_bias'] else ('偏卖' if g<0 and r['group_negative_days']>W/2 else '混合'))
    prices=[d.get('raw_price') for d in days]
    if all(p is not None and p.get('last_raw') is not None for p in prices):
        r['raw_source_price_sequence_available']=True
        r['first_raw_source_last']=prices[0]['last_raw'];r['last_raw_source_last']=prices[-1]['last_raw']
        links=[(a['last_raw'],b.get('previous_raw')) for a,b in zip(prices,prices[1:])]
        r['raw_previous_close_links_checked']=sum(b is not None and b>0 for a,b in links)
        r['raw_previous_close_link_disagreements']=sum(b is not None and b>0 and a!=b for a,b in links)
        r['raw_link_match_does_not_prove_no_corporate_actions']=True
    else:r['raw_source_price_sequence_available']=False
    return r


def profiles(daily,calendar):
    lookup={(d['symbol'],d['day']):d for d in daily}
    if len(lookup)!=len(daily):raise ValueError('duplicate day input')
    if tuple(sorted(set(calendar)))!=tuple(calendar):raise ValueError('calendar must be sorted unique')
    out=[]
    for symbol in SYMBOLS:
        for i,day in enumerate(calendar):
            for W in WINDOWS:
                ds=calendar[max(0,i-W+1):i+1]
                # Missing expected days are explicit placeholders, never compressed.
                window=[lookup.get((symbol,d),{'symbol':symbol,'day':d,'cash_ready':False}) for d in ds]
                out.append(interval_profile(window,W))
    return out


def csv_rows(path):
    with path.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))


def strict_sum(values):return None if any(v is None for v in values) else sum(values)

CASH_ALIASES={'buy':'buy_amount_1e4','sell':'sell_amount_1e4','active_buy':'buy_active_1e4','active_sell':'sell_active_1e4','passive_buy':'buy_passive_1e4','passive_sell':'sell_passive_1e4','unknown_buy':'buy_unclassified_1e4','unknown_sell':'sell_unclassified_1e4'}


def merge_cash_input(m,parts,expected_bands):
    result={'cash_ready':False}
    if m is not None:result['market_amount']=exact_integer(str(m['observed_amount_1e4']),'market cash',minimum=1)
    ids=[] if parts is None else [int(r['band_id']) for r in parts]
    if sorted(ids)!=sorted(expected_bands):
        result['cash_input_reason']='missing_or_duplicate_amount_bands'
        result.update({name:None for name in CASH_ALIASES});return result
    result['cash_ready']=m is not None and m['cash_fact_ready'] in (True,'True')
    for name,field in CASH_ALIASES.items():result[name]=strict_sum([None if r[field] in ('',None) else exact_integer(str(r[field]),field) for r in parts])
    return result


def bounded_price_read(path,expected_bytes,remaining_bytes):
    if path.is_symlink() or not path.is_file():raise ValueError('not a regular quote file')
    before=path.stat()
    if type(expected_bytes) is not int or expected_bytes<=0 or before.st_size!=expected_bytes or expected_bytes>min(256*1024**2,remaining_bytes):raise ValueError('price preflight size/budget mismatch')
    with path.open('rb') as stream:raw=stream.read(expected_bytes)
    after=path.stat()
    if len(raw)!=expected_bytes or (after.st_size,after.st_mtime_ns)!=(before.st_size,before.st_mtime_ns):raise ValueError('quote file size/content changed during read')
    return raw


def inputs(calendar=None):
    calendar=tuple(calendar or retrospective_calendar())
    intake=json.loads(BASIC.read_text());rates={}
    for m in intake['sources']:
        if digest(Path(m['path']))!=m['sha256']:raise ValueError('turnover source changed')
    for r in intake['selected']:
        try:rates[(r['ts_code'],r['trade_date'])]=Decimal(r['turnover_rate'])
        except InvalidOperation:rates[(r['ts_code'],r['trade_date'])]=None
    markets={};parts={};quote_meta={};sources=[];expected_parts={}
    for base in (BASE3,BASE2):
        for name in ('market_activity.csv','source_verification.json'):
            sources.append({'path':str(base/name),'sha256':digest(base/name)})
        for m in json.loads((base/'source_verification.json').read_text())['verified_files']:
            if m['member'].endswith('/行情.csv'):
                day,symbol,_=m['member'].split('/');quote_meta[(symbol,day)]=m
        for r in csv_rows(base/'market_activity.csv'):markets[(r['symbol'],r['day'])]=r
        path=base/('bands_wide.csv' if base==BASE3 else 'daily_wide.csv');sources.append({'path':str(path),'sha256':digest(path)})
        for r in csv_rows(path):
            if (base==BASE3 and int(r['band_id']) in (3,4,5)) or (base==BASE2 and r['band_id']=='1'):
                key=(r['symbol'],r['day']);parts.setdefault(key,[]).append(r);expected_parts[key]=(3,4,5) if base==BASE3 else (1,)
    supfile=HOME/'supplement-20261019.json';sup=json.loads(supfile.read_text());sources.append({'path':str(supfile),'sha256':digest(supfile)})
    for m in sup['verified_files']:
        if m['member'].endswith('/行情.csv'):
            day,symbol,_=m['member'].split('/');quote_meta[(symbol,day)]=m
    for record in sup['stock_results']:
        m=record['market'];markets[(m['symbol'],m['day'])]=m
        for r in record['wide']:
            if r['band_id']==1:
                key=(r['symbol'],r['day']);parts.setdefault(key,[]).append(r);expected_parts[key]=(1,)
    daily=[];price_bytes=0;verified=[]
    for symbol in SYMBOLS:
        for day in calendar:
            key=(symbol,day);m=markets.get(key);rs=parts.get(key)
            d={'symbol':symbol,'day':day,'turnover_rate':rates.get(key),'cash_ready':False}
            expected=expected_parts.get(key,(1,) if symbol in ('300855.SZ','688202.SH') or day=='20261019' else (3,4,5))
            d.update(merge_cash_input(m,rs,expected))
            meta=quote_meta.get(key)
            if meta is not None:
                path=Path(meta['path']);raw=bounded_price_read(path,meta['bytes'],384*1024**2-price_bytes);price_bytes+=len(raw)
                if hashlib.sha256(raw).hexdigest()!=meta['sha256']:raise ValueError('price content hash mismatch')
                qr=list(csv.DictReader(io.StringIO(raw.decode('gb18030'))));last=max(enumerate(qr),key=lambda v:(_clock(v[1]['时间']),v[0]))[1]
                if last['万得代码']!=symbol or last['自然日']!=day:raise ValueError('price stock/day mismatch')
                p={}
                for name,field in (('open_raw','开盘价'),('high_raw','最高价'),('low_raw','最低价'),('last_raw','成交价'),('previous_raw','前收盘')):
                    try:p[name]=exact_integer(last[field],field,minimum=1)
                    except ValueError:p[name]=None
                d['raw_price']=p
                verified.append({'day':day,'symbol':symbol,'path':str(path),'sha256':meta['sha256'],'bytes':len(raw)})
            daily.append(d)
    return daily,{'sources':sources,'price_files':verified,'price_bytes':price_bytes,'turnover_intake_sha256':digest(BASIC),'supplement_sha256':digest(supfile)}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--smoke',action='store_true');args=p.parse_args(argv)
    if args.output.exists():raise ValueError('new output directory required')
    calendar=retrospective_calendar()
    if args.smoke:calendar=tuple(d for d in calendar if '20260923'<=d<='20260930')
    daily,receipt=inputs(calendar)
    out=profiles(daily,calendar);args.output.mkdir(parents=True)
    def serial(v):
        if isinstance(v,dict):return {k:serial(x) for k,x in v.items()}
        if isinstance(v,list):return [serial(x) for x in v]
        return str(v) if isinstance(v,Decimal) else v
    dump(args.output/'daily_inputs.json',serial(daily));dump(args.output/'input_verification.json',receipt)
    frame=_exact_table(out,('first_raw_source_last','last_raw_source_last','group_positive_days','group_negative_days','active_positive_days','active_negative_days','group_positive_streak','active_positive_streak','high_turnover_days','longest_high_turnover_streak'))
    frame.to_csv(args.output/'intervals.csv',index=False)
    run={'role':'continuous_interval_source_description_not_forecast','windows':WINDOWS,'symbols':SYMBOLS,'calendar':calendar,'activity_rule':'mean ordinary turnover_rate >10%; report high-day count without deleting low days','source_spec_sha256':digest(SPEC),'code_sha256':digest(Path(__file__)),'source_price_trend_qualified':False,'official_price_or_corporate_action_complete':False,'prospective_eligible':False}
    dump(args.output/'run_spec.json',run)
    summary={'stock_days':len(daily),'interval_rows':len(out),'cash_ready_windows':sum(r['cash_window_ready'] for r in out),'activity_ready_windows':sum(r['activity_window_ready'] for r in out),'activity_candidate_windows':sum(r.get('activity_candidate',False) for r in out),'cash_and_activity_candidates':sum(r.get('activity_candidate',False) and r['cash_window_ready'] for r in out),'qualified_price_windows':0,'price_gap':'independent upstream/adjustments and corporate action coverage remain unqualified','input_price_bytes':receipt['price_bytes']}
    dump(args.output/'summary.json',summary);print(json.dumps(summary,ensure_ascii=False))
    return 0


if __name__=='__main__':raise SystemExit(main())
