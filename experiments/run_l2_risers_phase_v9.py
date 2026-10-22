"""Price-only hindsight anchors followed by exact source-cash case alignment.

Not a simulator, adjusted return, prospective signal, or formal Validation.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from experiments.l2_risers_phase_v9 import observed_up_leg, anchor_views
from experiments.l2_continuous_interval_v6 import interval_profile

HOME = Path('/srv/bcache-8t/ygguo/quant/l2-risers-phase-v9')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_write(path, rows):
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)


def load_small_json(path, limit, expected_sha=None):
    before=path.stat()
    if path.is_symlink() or not path.is_file() or not 0<before.st_size<=limit:
        raise ValueError('input preflight type/size budget')
    with path.open('rb') as f:raw=f.read(before.st_size)
    after=path.stat()
    if len(raw)!=before.st_size or (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
        raise ValueError('input changed during read')
    if expected_sha is not None and hashlib.sha256(raw).hexdigest()!=expected_sha:
        raise ValueError('input fingerprint changed')
    return json.loads(raw)


def run(output, smoke=False):
    if output.exists():raise ValueError('new output directory required')
    specfile=HOME/'phase_study_spec.json';spec=load_small_json(specfile,128*1024)
    pricefile=HOME/'price_input_snapshot.json';price=load_small_json(pricefile,512*1024)
    cashfile=Path(spec['cash_input_path']);cash=load_small_json(cashfile,2*1024**2,spec['cash_input_sha256'])
    calendar=spec['calendar'];symbols=['301313.SZ'] if smoke else spec['symbols']
    if tuple(calendar)!=tuple(sorted(set(calendar))):raise ValueError('invalid calendar')
    all_cash={(d['symbol'],d['day']):d for d in cash}
    if len(all_cash)!=len(cash):raise ValueError('duplicate cash day')
    if set(all_cash)!={(s,d) for s in spec['symbols'] for d in calendar}:raise ValueError('cash source not exact calendar cover')
    metas={r['symbol']:r for r in price['files']}
    for s in symbols:
        p=Path(metas[s]['snapshot_path'])
        if p.is_symlink() or not p.is_file() or p.stat().st_size!=metas[s]['bytes'] or digest(p)!=metas[s]['sha256']:
            raise ValueError('raw-price snapshot changed')
    anchors=[];views=[];timeline=[];timing=[];daily=[]
    for symbol in symbols:
        points=[{'day':r['day'],'close':r['close']} for r in price['observations'] if r['symbol']==symbol]
        points.sort(key=lambda p:p['day'])
        if not {r['day'] for r in points}<=set(calendar):raise ValueError('foreign price date')
        anchor=observed_up_leg(points)
        if anchor is None:raise ValueError('selected rising case has no observed up-leg')
        full=len(points)==len(calendar);by_price={p['day']:p['close'] for p in points}
        if len(by_price)!=len(points):raise ValueError('duplicate price day')
        lift=next((p['day'] for p in points if p['day']>anchor['trough_day'] and Decimal(p['close'])>Decimal(anchor['trough_raw_close'])),None)
        anchor.update(symbol=symbol,name=spec['names'][symbol],first_observed_lift_day=lift,price_path_complete=full,price_missing_dates=';'.join(d for d in calendar if d not in by_price),trough_left_boundary=anchor['trough_day']==calendar[0],peak_right_boundary=anchor['peak_day']==calendar[-1],qualification='raw_observed_hindsight_not_economic_return')
        anchors.append(anchor)
        for day in calendar:
            row=dict(all_cash[symbol,day]);row['raw_source_close_yuan']=by_price.get(day);daily.append(row)
        by_cash={d:all_cash[symbol,d] for d in calendar}
        stock_timeline=[]
        for i,day in enumerate(calendar):
            for W in spec['cash_windows']:
                ds=[by_cash[d] for d in calendar[max(0,i-W+1):i+1]]
                r=interval_profile(ds,W);r.update(view='rolling_lookback',calendar_status='complete' if i+1>=W else 'left_censored')
                stock_timeline.append(r)
        timeline.extend(stock_timeline)
        for W in spec['cash_windows']:
            for v in anchor_views(calendar,anchor['trough_day'],anchor['peak_day'],W):
                r={'symbol':symbol,'view':v['view'],'lookback':W,'calendar_status':v['status'],'expected_days':W,'observed_market_days':len(v['days']),'start':v['days'][0] if v['days'] else None,'end':v['days'][-1] if v['days'] else None,'cash_window_ready':False,'price_anchor_path_complete':full}
                if v['status']=='complete':
                    r.update(interval_profile([by_cash[d] for d in v['days']],W))
                else:r['cash_reason']=v['status']
                r['contains_observed_peak']=anchor['peak_day'] in v['days'];views.append(r)
        primary=[r for r in stock_timeline if r['lookback']==spec['primary_cash_window']]
        pre_lift=[r for r in primary if lift is not None and r['day']<lift and r['calendar_status']=='complete']
        observed_pre_lift=[r for r in pre_lift if r['cash_window_ready']]
        t={'pre_lift_full_calendar_windows':len(pre_lift),'pre_lift_complete_cash_windows':len(observed_pre_lift),'pre_lift_unknown_cash_windows':len(pre_lift)-len(observed_pre_lift),'date_order_not_leading_evidence':True,'pre_lift_observation_available':bool(full and observed_pre_lift),'symbol':symbol,'name':spec['names'][symbol],'price_trough_day':anchor['trough_day'],'first_observed_lift_day':lift,'price_peak_day':anchor['peak_day'],'price_path_complete':full,'observed_complete_primary_windows':sum(r['cash_window_ready'] for r in primary),'unknown_full_primary_windows':sum(r['calendar_status']=='complete' and not r['cash_window_ready'] for r in primary),'left_censored_primary_windows':sum(r['calendar_status']=='left_censored' for r in primary)}
        for label,predicate in (('group',lambda r:r.get('group_buy_bias') is True),('active',lambda r:r.get('active_support') is True),('joint',lambda r:r.get('group_buy_bias') is True and r.get('active_support') is True)):
            hits=[r for r in primary if r['cash_window_ready'] and predicate(r)]
            first=hits[0]['day'] if hits else None
            t['first_observed_'+label+'_hit']=first;t[label+'_hit_windows']=len(hits)
            previous=next((r for r in primary if lift is not None and r['day']==calendar[max(0,calendar.index(lift)-1)]),None)
            t[label+'_last_pre_lift_window_hit']=None if previous is None or not previous['cash_window_ready'] else predicate(previous)
            t[label+'_prior_unknown_full_windows']=sum(r['calendar_status']=='complete' and not r['cash_window_ready'] and (first is None or r['day']<first) for r in primary)
            delta=calendar.index(first)-calendar.index(lift) if first and lift else None
            t[label+'_offset_to_first_observed_lift_sessions']=delta
            t[label+'_observed_timing']='no_hit_in_observed_complete_windows' if first is None else ('earlier_than_observed_lift' if delta<0 else ('same_day_as_observed_lift' if delta==0 else 'later_than_observed_lift'))
        timing.append(t)
    output.mkdir(parents=True)
    for name,rows in (('price_anchors.csv',anchors),('aligned_cash_windows.csv',views),('rolling_cash_windows.csv',timeline),('first_observed_cash_timing.csv',timing),('daily_price_cash.csv',daily)):
        csv_write(output/name,rows)
    codefiles=[Path(__file__),Path(__file__).with_name('l2_risers_phase_v9.py'),Path(__file__).with_name('l2_continuous_interval_v6.py')]
    result={'role':spec['role'],'worktree':spec['worktree'],'price_cutoff':spec['price_cutoff'],'cash_cutoff':spec['cash_cutoff'],'stocks':len(symbols),'complete_raw_price_paths':sum(r['price_path_complete'] for r in anchors),'partial_raw_price_paths':sum(not r['price_path_complete'] for r in anchors),'aligned_window_rows':len(views),'complete_aligned_cash_windows':sum(r['cash_window_ready'] for r in views),'rolling_window_rows':len(timeline),'qualified_economic_price_or_forecast':False,'price_anchors_and_cash_cases_already_seen_not_OOS':True,'source_pins':{str(p):digest(p) for p in (specfile,pricefile,cashfile)},'code_pins':{str(p):digest(p) for p in codefiles}}
    (output/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('source_pins','code_pins')},ensure_ascii=False))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--smoke',action='store_true');a=parser.parse_args();run(a.output,a.smoke)
