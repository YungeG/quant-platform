"""Raw OHLC-path diagnostics after source-cash labels; NOT fills, PnL or Validation."""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path

HOME = Path('/srv/bcache-8t/ygguo/quant/l2-cash-risk-wait-v10')
FAMILIES = ('group_buyer_bias', 'group_buyer_bias_with_active_support')


def exact_price(value):
    if not isinstance(value, (str, Decimal, Fraction)):
        raise ValueError('price must be exact decimal text or rational')
    try:
        result = value if isinstance(value, Fraction) else Fraction(Decimal(value))
    except (InvalidOperation, ValueError, OverflowError) as e:
        raise ValueError('invalid price') from e
    if result <= 0:
        raise ValueError('nonpositive price')
    return result


def pct(value):
    if value is None:
        return None
    return str(Decimal(value.numerator) * 100 / Decimal(value.denominator))


def flag(value):
    if value in (True, 'True'):
        return True
    if value in (False, 'False'):
        return False
    return None


def signal_events(rows, family):
    if family not in FAMILIES:
        raise ValueError('unknown cash family')
    if [r['day'] for r in rows] != sorted({r['day'] for r in rows}):
        raise ValueError('duplicate/unsorted signal dates')
    events = []
    previous = None
    current = None
    for row in rows:
        state = None
        if flag(row.get('cash_window_ready')) is True:
            state = flag(row.get('group_buy_bias'))
            if family == FAMILIES[1]:
                active = flag(row.get('active_support'))
                state = None if state is None or active is None else state and active
        if state is True:
            if previous is not True:
                event = {'signal_day': row['day'], 'family': family,
                         'boundary': 'confirmed_false_to_true' if previous is False else 'unknown_prior_boundary',
                         'visible_run_end': row['day'], 'visible_run_days': 1,
                         'first_visible_event': not events}
                events.append(event)
                current = event
            else:
                current['visible_run_end'] = row['day']
                current['visible_run_days'] += 1
        elif current is not None:
            current['run_end_reason'] = 'observed_false' if state is False else 'unknown_cash'
            current = None
        previous = state
    if current is not None:
        current['run_end_reason'] = 'sample_end'
    return events


def evaluate_path(calendar, bars, signal_day, horizon):
    if type(horizon) is not int or horizon not in (10, 20):
        raise ValueError('horizon must be10 or20')
    if calendar != sorted(set(calendar)) or signal_day not in calendar:
        raise ValueError('invalid calendar/signal date')
    start = calendar.index(signal_day) + 1
    dates = calendar[start:start+horizon]
    result = {'signal_day': signal_day, 'horizon_market_days': horizon,
              'reference_day': dates[0] if dates else None,
              'expected_days': horizon, 'observed_calendar_days': len(dates),
              'last_observed_day': dates[-1] if dates else None,
              'right_censored': len(dates) < horizon,
              'price_missing_dates': ';'.join(d for d in dates if d not in bars),
              'path_complete': False, 'raw_risk_state': 'unknown_reference',
              'raw_lowrisk_late_up_candidate': None,
              'economic_risk_or_return_qualified': False}
    if not dates or dates[0] not in bars:
        return result
    reference = exact_price(bars[dates[0]]['open'])
    observed = [(day, bars[day]) for day in dates if day in bars]
    complete = len(dates) == horizon and len(observed) == horizon
    min_low = min(exact_price(bar['low']) for _,bar in observed)
    max_high = max(exact_price(bar['high']) for _,bar in observed)
    touch = next((day for day,bar in observed if exact_price(bar['low']) * 10 <= reference * 9), None)
    breach = next((day for day,bar in observed if exact_price(bar['low']) * 10 < reference * 9), None)
    result.update(reference_raw_open=str(Decimal(reference.numerator)/Decimal(reference.denominator)),
                  path_complete=complete, observed_price_days=len(observed),
                  raw_adverse_move_pct_observed=pct(max(Fraction(0),1-min_low/reference)),
                  raw_favorable_move_pct_observed=pct(max(Fraction(0),max_high/reference-1)),
                  risk_line_first_touch_day=touch, risk_line_first_breach_day=breach,
                  risk_dates_are_first_observed_not_proven_first=True,
                  raw_risk_state='breached_observed' if breach else ('within_limit_complete' if complete else 'unknown_incomplete'))
    wait = None
    for i in range(2,len(dates)):
        window=dates[i-2:i+1]
        if all(d in bars for d in window):
            closes=[exact_price(bars[d]['close']) for d in window]
            if closes[0]<closes[1]<closes[2] and closes[2]>reference:
                wait=i+1
                break
    result['first3_rising_closes_wait_sessions']=wait
    result['first3_rising_closes_day']=dates[wait-1] if wait is not None else None
    if complete:
        first_mean=sum(exact_price(bars[d]['close']) for d in dates[:5])/5
        last_mean=sum(exact_price(bars[d]['close']) for d in dates[-5:])/5
        end=exact_price(bars[dates[-1]]['close'])
        late_up=last_mean>first_mean and end>reference
        result.update(horizon_end_day=dates[-1],raw_end_close=str(Decimal(end.numerator)/Decimal(end.denominator)),
                      raw_close_change_pct_full_horizon=pct(end/reference-1),
                      raw_late_vs_early5_mean_pct_full_horizon=pct(last_mean/first_mean-1),
                      raw_late_up_full_horizon=late_up,
                      raw_lowrisk_late_up_candidate=breach is None and late_up)
    elif breach:
        result['raw_lowrisk_late_up_candidate']=False
    return result


def read_small(path, expected=None, limit=4*1024**2):
    before=path.stat()
    if path.is_symlink() or not path.is_file() or not 0<before.st_size<=limit:
        raise ValueError('input preflight size/type failure')
    with path.open('rb') as f:raw=f.read(before.st_size)
    after=path.stat()
    if len(raw)!=before.st_size or (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
        raise ValueError('input changed during read')
    if expected and hashlib.sha256(raw).hexdigest()!=expected:
        raise ValueError('input hash mismatch')
    return raw


def write_csv(path,rows):
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)


def run(output, smoke=False):
    if output.exists():raise ValueError('new output directory required')
    spec_path=HOME/'risk_wait_spec.json';spec=json.loads(read_small(spec_path));loaded={}
    if spec['risk_limit_pct']!='10' or spec['future_horizons_market_days']!=[10,20] or spec['families']!=list(FAMILIES) or spec['lookback_cash_days']!=5:
        raise ValueError('unapproved risk/horizon/signal configuration')
    for p,pin in spec['input_pins'].items():loaded[p]=read_small(Path(p),pin['sha256'],spec['max_source_bytes'])
    timeline_path=next(p for p in loaded if p.endswith('rolling_cash_windows.csv'))
    price_path=next(p for p in loaded if p.endswith('price_input_snapshot.json'))
    timeline=list(csv.DictReader(io.StringIO(loaded[timeline_path].decode('utf-8-sig'))));price=json.loads(loaded[price_path]);calendar=spec['calendar'];symbols=['002343.SZ'] if smoke else spec['symbols'];bars={};read_bytes=0
    for meta in price['files']:
        if meta['symbol'] not in symbols:continue
        raw=read_small(Path(meta['snapshot_path']),meta['sha256'],512*1024);read_bytes+=len(raw)
        if read_bytes>spec['max_source_bytes']:raise ValueError('total OHLC byte budget')
        records={}
        for row in csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))):
            day=row['date'].replace('-','')
            if day not in calendar:continue
            if day in records:raise ValueError('duplicate OHLC day')
            values={k:exact_price(row[k]) for k in ('open','high','low','close')}
            if values['low']>min(values['open'],values['close']) or values['high']<max(values['open'],values['close']) or values['low']>values['high']:
                raise ValueError('OHLC consistency failure')
            records[day]={k:row[k] for k in values}
        bars[meta['symbol']]=records
    events=[];outcomes=[]
    for s in symbols:
        rows=sorted((r for r in timeline if r['symbol']==s and r['lookback']=='5'),key=lambda r:r['day'])
        if [r['day'] for r in rows]!=calendar:raise ValueError('cash timeline not exact calendar cover')
        for family in spec['families']:
            for event in signal_events(rows,family):
                e={**event,'symbol':s,'name':spec['names'][s]};events.append(e)
                for horizon in spec['future_horizons_market_days']:
                    outcomes.append({**e,**evaluate_path(calendar,bars[s],event['signal_day'],horizon)})
    output.mkdir(parents=True);write_csv(output/'events.csv',events);write_csv(output/'raw_path_outcomes.csv',outcomes)
    summary={'role':spec['role'],'stocks':len(symbols),'events':len(events),'path_rows':len(outcomes),'complete_raw_paths':sum(r['path_complete'] for r in outcomes),'observed_raw_limit_breaches':sum(r['raw_risk_state']=='breached_observed' for r in outcomes),'pending_raw_limit_no_breach':sum(r['raw_risk_state']=='unknown_incomplete' for r in outcomes),'raw_lowrisk_late_up_candidates':sum(r['raw_lowrisk_late_up_candidate'] is True for r in outcomes),'OHLC_source_bytes':read_bytes,'economic_risk_or_forecast_qualified':False,'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'spec_sha256':hashlib.sha256(spec_path.read_bytes()).hexdigest(),'input_pins':spec['input_pins']}
    (output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='input_pins'},ensure_ascii=False));return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--smoke',action='store_true');a=p.parse_args();run(a.output,a.smoke)
