"""Finite exploratory window/horizon probe. No new simulator or L2 payload intake.

The short-horizon phase reuses immutable v12 selections/price snapshots. The
long-window phase is metadata-only until a new bounded execution is approved.
"""
import argparse
import csv
import hashlib
import io
import json
import re
import subprocess
import time
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

from experiments.l2_cash_risk_wait_v10 import evaluate_path, exact_price, pct, read_small

HOME = Path('/srv/bcache-8t/ygguo/quant/l2-window-horizon-v13')
HORIZONS = (3, 5, 10, 20)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, data):
    with Path(path).open('x') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)


def write_csv(path, rows):
    fields = list(dict.fromkeys(k for r in rows for k in r)) or ['panel', 'arm']
    with Path(path).open('x', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def evaluate_probe(calendar, bars, signal_day, horizon):
    if type(horizon) is not int or horizon not in HORIZONS:
        raise ValueError('unsupported finite horizon')
    if calendar != sorted(set(calendar)) or signal_day not in calendar:
        raise ValueError('invalid calendar/signal')
    start = calendar.index(signal_day)+1
    dates = calendar[start:start+horizon]
    # Reuse the frozen risk/clock/gap arithmetic on precisely the requested slice.
    # Its old late-up completion labels are discarded, NOT reinterpreted for H<10.
    clipped = calendar[:start] + dates
    observed = evaluate_path(clipped, bars, signal_day, 10 if horizon <= 10 else 20)
    fields = ('reference_day','reference_raw_open','observed_price_days',
              'raw_adverse_move_pct_observed','raw_favorable_move_pct_observed',
              'risk_line_first_touch_day','risk_line_first_breach_day',
              'first3_rising_closes_wait_sessions','first3_rising_closes_day')
    result = {k:observed.get(k) for k in fields}
    complete = len(dates)==horizon and all(d in bars for d in dates)
    result.update(signal_day=signal_day,horizon_market_days=horizon,
                  expected_days=horizon,observed_calendar_days=len(dates),
                  price_missing_dates=';'.join(d for d in dates if d not in bars),
                  right_censored=len(dates)<horizon,path_complete=complete,
                  raw_risk_state='unknown_reference',raw_endpoint_up=None,
                  raw_within_limit_and_endpoint_up=None,
                  legacy_late_up=None,legacy_within_limit_and_late_up=None,
                  economic_risk_or_return_qualified=False)
    if not dates or dates[0] not in bars:
        return result
    breached = observed.get('risk_line_first_breach_day') is not None
    result['raw_risk_state'] = 'breached_observed' if breached else 'within_limit_complete' if complete else 'unknown_incomplete'
    if complete:
        reference = exact_price(bars[dates[0]]['open'])
        end = exact_price(bars[dates[-1]]['close'])
        up = end > reference
        result.update(horizon_end_day=dates[-1],raw_close_change_pct_full_horizon=pct(end/reference-1),
                      raw_endpoint_up=up,raw_within_limit_and_endpoint_up=not breached and up)
    elif breached:
        result['raw_within_limit_and_endpoint_up'] = False
    if horizon in (10,20):
        result['legacy_late_up'] = observed.get('raw_late_up_full_horizon')
        result['legacy_within_limit_and_late_up'] = observed.get('raw_lowrisk_late_up_candidate')
    return result


def median_text(values):
    xs = sorted(Fraction(str(v)) for v in values)
    if not xs:
        return None
    i = len(xs)//2
    value = xs[i] if len(xs)%2 else (xs[i-1]+xs[i])/2
    with localcontext() as context:
        context.prec = 50
        return str(Decimal(value.numerator)/Decimal(value.denominator))


def summarize(paths, counts, horizons):
    result = []
    for count in counts:
        for horizon in horizons:
            rs = [r for r in paths if r['panel']==count['panel'] and r['arm']==count['arm'] and r['horizon_market_days']==horizon]
            n = len(rs)
            if n != int(count['selected_n']):
                raise ValueError('frozen selection exact cover failure')
            breaches = sum(r['raw_risk_state']=='breached_observed' for r in rs)
            unknown_risk = sum(r['raw_risk_state'].startswith('unknown') for r in rs)
            joint = sum(r['raw_within_limit_and_endpoint_up'] is True for r in rs)
            unknown_joint = sum(r['raw_within_limit_and_endpoint_up'] is None for r in rs)
            complete = [r for r in rs if r['path_complete']]
            ratio = lambda k: pct(Fraction(k,n)) if n else None
            result.append({**count,'lookback':5,'horizon':horizon,'complete_paths':len(complete),
                           'known_breaches':breaches,'unknown_risk':unknown_risk,
                           'joint_endpoint_positive':joint,'joint_unknown':unknown_joint,
                           'joint_lower_pct':ratio(joint),'joint_upper_pct':ratio(joint+unknown_joint),
                           'breach_lower_pct':ratio(breaches),'breach_upper_pct':ratio(breaches+unknown_risk),
                           'raw_endpoint_median_complete_only_pct':median_text([r['raw_close_change_pct_full_horizon'] for r in complete]),
                           'economic_risk_or_return_qualified':False})
    return result


def run_short(spec_path, output, smoke=False):
    spec = json.loads(Path(spec_path).read_text())
    if spec['asof']!='20260911' or spec['lookback']!=5 or spec['horizons']!=list(HORIZONS):
        raise ValueError('unapproved short probe axes')
    out = Path(output)
    if out.exists() or any(p.is_symlink() for p in (out,*out.parents)):
        raise ValueError('new regular output required')
    for p, expected in spec['input_sha256'].items():
        read_small(Path(p),expected,4*1024**2)
    read_small(Path(spec['outcome_helper_path']),spec['outcome_helper_sha256'],128*1024)
    read_small(Path(spec['probe_spec_path']),spec['probe_spec_sha256'],128*1024)
    with Path(spec['selected_path']).open(encoding='utf-8-sig') as stream:
        selections = list(csv.DictReader(stream))
    with Path(spec['counts_path']).open(encoding='utf-8-sig') as stream:
        counts = list(csv.DictReader(stream))
    if smoke:
        selections = selections[:20]
        counts = [{**counts[0],'selected_n':len(selections)}]
    chosen = {r['symbol'] for r in selections}
    receipt = json.loads(Path(spec['prices_receipt_path']).read_text())
    bars, total = {}, 0
    for meta in receipt['files']:
        symbol = meta['symbol']
        if symbol not in chosen:
            continue
        bars[symbol] = {}
        if 'snapshot_path' not in meta:
            continue
        raw = read_small(Path(meta['snapshot_path']),meta['sha256'],512*1024)
        total += len(raw)
        if total > 32*1024**2:
            raise ValueError('retained price byte bound exceeded')
        allowed = set(meta['usable_scoped_dates'])
        for r in csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))):
            day = r['date'].replace('-','')
            if day in allowed:
                bars[symbol][day] = {k:r[k] for k in ('open','high','low','close')}
    if set(bars)!=chosen:
        raise ValueError('retained price registry incomplete; no replacement allowed')
    paths = [{**r,**evaluate_probe(spec['calendar'],bars[r['symbol']],spec['asof'],h)} for r in selections for h in spec['horizons']]
    summaries = summarize(paths,counts,spec['horizons'])
    out.mkdir(parents=True)
    write_csv(out/'raw_paths.csv',paths)
    write_csv(out/'comparison_summary.csv',summaries)
    result = {'role':'adaptive_exploratory_short_horizon_raw_endpoint_probe_not_validation',
              'mode':'smoke' if smoke else 'full','asof':spec['asof'],'lookback':5,
              'horizons':spec['horizons'],'selected_rows':len(selections),'unique_symbols':len(chosen),
              'path_rows':len(paths),'summary_rows':len(summaries),'retained_price_bytes':total,
              'new_L2_payload_read':False,'selection_unchanged':True,
              'new_endpoint_not_old_late_up':True,'unseen_OOS_or_effectiveness_validated':False,
              'code_sha256':sha(Path(__file__).read_bytes()),'spec_sha256':sha(Path(spec_path).read_bytes()),
              'outputs':{p.name:sha(p.read_bytes()) for p in [out/'raw_paths.csv',out/'comparison_summary.csv']}}
    dump(out/'summary.json',result)
    return result


def inventory(scope_path, output):
    scope_bytes = Path(scope_path).read_bytes();scope = json.loads(scope_bytes)
    out = Path(output)
    if out.exists() or scope.get('metadata_only') is not True or scope['dates']!=sorted(set(scope['dates'])):
        raise ValueError('new metadata-only ordered inventory required')
    members, missing, archives, listing_bytes = [], [], [], 0
    for day in scope['dates']:
        choices = [p for p in (Path(scope['source'])/day[:6]).glob(day+'*.7z') if re.fullmatch(day+r'(?:\([0-9]+\))?\.7z',p.name)]
        if len(choices)!=1 or choices[0].is_symlink():
            raise ValueError('missing/ambiguous/nonregular archive date: '+day)
        path=choices[0];before=path.stat()
        cp=subprocess.run(['7z','l','-slt',str(path)],capture_output=True,text=True,timeout=scope['per_listing_timeout_seconds'])
        n=len(cp.stdout.encode());listing_bytes+=n
        if cp.returncode or n>scope['single_listing_max_bytes'] or listing_bytes>scope['metadata_stdout_budget_bytes'] or '----------' not in cp.stdout:
            raise ValueError('listing/metadata budget failure')
        files=[]
        for block in cp.stdout.split('----------',1)[1].strip().split('\n\n'):
            r=dict(line.split(' = ',1) for line in block.splitlines() if ' = ' in line)
            if 'Path' in r and not r.get('Attributes','').startswith('D'):
                files.append(r)
        wanted={f'{day}/{s}/{k}' for s in scope['symbols'] for k in scope['kinds']}
        chosen=[r for r in files if r['Path'] in wanted]
        if len({r['Path'] for r in chosen})!=len(chosen):
            raise ValueError('duplicate selected metadata member')
        touched={r['Block'] for r in chosen};solid=sum(int(r['Size']) for r in files if r.get('Block') in touched)
        for r in chosen:
            size=int(r['Size'])
            if r.get('Encrypted')!='-' or not 0<size<=scope['file_bytes_max'] or not re.fullmatch('[0-9A-Fa-f]{8}',r.get('CRC','')):
                raise ValueError('unsupported selected member metadata')
            members.append({'archive':str(path),'member':r['Path'],'bytes':size,'crc32':r['CRC'].lower(),'block':r['Block']})
        missing.extend(sorted(wanted-{r['Path'] for r in chosen}))
        after=path.stat()
        if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
            raise ValueError('archive changed while listing')
        archives.append({'path':str(path),'day':day,'bytes':before.st_size,'mtime_ns':before.st_mtime_ns,
                         'selected_member_count':len(chosen),'selected_bytes':sum(int(r['Size']) for r in chosen),
                         'involved_solid_uncompressed_bytes':solid})
    result={'role':'metadata_only_estimate_NOT_payload_execution_authority','asof':scope['asof'],
            'symbols':len(scope['symbols']),'dates':scope['dates'],'members':members,'missing_members':missing,
            'archives':archives,'selected_bytes':sum(m['bytes'] for m in members),
            'involved_solid_bytes':sum(a['involved_solid_uncompressed_bytes'] for a in archives),
            'listing_output_bytes':listing_bytes,'scope_sha256':sha(scope_bytes),'payload_extracted':False}
    result['exceeds_previous_selected_budget']=result['selected_bytes']>scope['selected_bytes_max']
    result['exceeds_previous_solid_budget']=result['involved_solid_bytes']>scope['involved_solid_bytes_max']
    dump(out,result)
    return {k:v for k,v in result.items() if k not in ('members','missing_members','archives')}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase',choices=('short','inventory'))
    p.add_argument('--spec',default=str(HOME/'short_horizon_spec.json'))
    p.add_argument('--scope',default=str(HOME/'inventory_scope.json'))
    p.add_argument('--output',required=True)
    p.add_argument('--smoke',action='store_true')
    a=p.parse_args()
    print(json.dumps(run_short(a.spec,a.output,a.smoke) if a.phase=='short' else inventory(a.scope,a.output),ensure_ascii=False))
