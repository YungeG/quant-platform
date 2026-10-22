"""Precommitted historical ranking comparisons; raw paths, not PnL or Validation.

Selection is a separate immutable publication BEFORE any outcome OHLC is read.
The already-exposed September interval cannot establish an unseen-time winner.
"""
import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction
from pathlib import Path

from experiments.l2_historical_cap_screen_v11 import classify_profile, integer
from experiments.l2_cash_risk_wait_v10 import evaluate_path, exact_price, read_small

HOME = Path('/srv/bcache-8t/ygguo/quant/l2-ranking-comparison-v12')
ARMS = ('cash_group_turnover', 'cash_group_cap', 'cash_active_cap',
        'cash_active_cap_persistent', 'price_momentum5', 'ordinary_turnover5', 'hash_control')
PANELS = ('whole_asof_pool', 'exclude_prior_case_17_sensitivity_not_holdout')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    return sha(Path(path).read_bytes())


def load(path):
    return json.loads(Path(path).read_text())


def table(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def dump(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)


def write_csv(path, rows, fields=None):
    fields = fields or list(dict.fromkeys(k for row in rows for k in row)) or ['panel', 'arm', 'symbol']
    with Path(path).open('x', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def decimal_fraction(value):
    if not isinstance(value, (str, Decimal, Fraction)):
        raise ValueError('exact decimal text required')
    if isinstance(value, Fraction):
        return value
    try:
        number = Decimal(value)
        if not number.is_finite():
            raise ValueError('nonfinite number')
        return Fraction(number)
    except InvalidOperation as exc:
        raise ValueError('invalid decimal') from exc


def number_text(value, multiplier=1):
    if value is None:
        return None
    value = Fraction(value) * multiplier
    with localcontext() as context:
        context.prec = 50
        return str(Decimal(value.numerator) / Decimal(value.denominator))


def new_output(path, protected):
    out = Path(path)
    if any(p.is_symlink() for p in (out, *out.parents)):
        raise ValueError('output symlink')
    out = out.resolve()
    if out.exists():
        raise ValueError('new output required')
    for p in protected:
        p = Path(p).resolve()
        if out.is_relative_to(p) or p.is_relative_to(out):
            raise ValueError('output overlaps protected input')
    return out


def read_spec(path):
    spec = load(path)
    if ([a['id'] for a in spec['arms']] != list(ARMS) or spec['panels'] != list(PANELS)
            or spec['top_n'] != 20 or spec['horizons'] != [10, 20]
            or spec['adverse_limit_percent'] != '10' or len(spec['formation_dates']) != 5
            or spec['calendar'] != sorted(set(spec['calendar']))
            or spec['asof'] != spec['formation_dates'][-1]
            or spec['price_file_max_bytes'] > 512*1024 or spec['price_total_max_bytes'] > 192*1024**2
            or spec['price_max_symbols'] > 280):
        raise ValueError('unapproved finite comparison axes')
    index = spec['calendar'].index(spec['asof'])
    if spec['calendar'][index-4:index+1] != spec['formation_dates'] or index < 5:
        raise ValueError('formation must be a continuous five-session window with prior close')
    return spec


def make_feature(symbol, name, profile, basic, spec):
    dates = spec['formation_dates']
    previous = spec['calendar'][spec['calendar'].index(dates[0])-1]
    cap = decimal_fraction(basic[spec['asof']][symbol]['total_mv'])
    if not 6000000000 <= cap <= 100000000000:
        raise ValueError('as-of cap roster mismatch')
    cls = classify_profile(profile)
    errors = []
    momentum = turnover = close = None
    try:
        close = decimal_fraction(basic[spec['asof']][symbol]['close'])
        if close <= 0:
            close = None
    except (KeyError, ValueError):
        pass
    try:
        closes = [decimal_fraction(basic[d][symbol]['close']) for d in [previous]+dates]
        if any(p <= 0 for p in closes):
            raise ValueError('invalid close feature')
        momentum = closes[-1]/closes[0]-1
    except (KeyError, ValueError):
        errors.append('missing_or_invalid_formation_close_feature')
    try:
        rates = [decimal_fraction(basic[d][symbol]['turnover_rate']) for d in dates]
        if any(r < 0 for r in rates):
            raise ValueError('invalid turnover feature')
        turnover = sum(rates)/5
    except (KeyError, ValueError):
        errors.append('missing_or_invalid_formation_turnover_feature')
    if cls == 'D':
        errors.append('incomplete_or_unknown_cash_profile')
    r = {'symbol': symbol, 'name': name, 'asof': spec['asof'], 'source_class': cls,
         'total_mv_cny': number_text(cap), 'common_eligible': not errors,
         'exclusion_reason': ';'.join(errors), 'prior_case_17': symbol in spec['prior_case_symbols'],
         'group_positive_days': profile.get('group_positive_days'),
         'active_positive_days': profile.get('active_positive_days'),
         'group_positive_streak': profile.get('group_positive_streak'),
         'active_positive_streak': profile.get('active_positive_streak'),
         'raw_close_at_cutoff': number_text(close),
         'raw_momentum5_pct': number_text(momentum, 100),
         'ordinary_turnover_mean5_pct': number_text(turnover),
         '_cap': cap, '_momentum': momentum, '_turnover': turnover,
         '_group_turnover': None, '_group_cap': None, '_active_cap': None, '_concentration': None}
    for k in ('group_difference', 'active_difference', 'passive_difference', 'unknown_difference', 'market_amount'):
        r[k+'_1e4'] = integer(profile.get(k+'_1e4'))
    if cls != 'D':
        g, a, amount = (r[k+'_1e4'] for k in ('group_difference', 'active_difference', 'market_amount'))
        if amount is None or amount <= 0:
            raise ValueError('complete profile missing positive market amount')
        r['_group_turnover'] = Fraction(g, amount)
        r['_group_cap'] = Fraction(g, 10000)/cap
        r['_active_cap'] = Fraction(a, 10000)/cap
        numerator = integer(profile['top2_positive_delta_numerator_1e4'])
        denominator = integer(profile['positive_delta_denominator_1e4'])
        r['_concentration'] = Fraction(numerator, denominator) if denominator else None
    for private, public in [('_group_turnover','group_turnover_pct'),('_group_cap','group_cap_pct'),
                            ('_active_cap','active_cap_pct'),('_concentration','top2_group_positive_share_pct')]:
        r[public] = number_text(r[private], 100)
    return r


def build_features(cash_dir, spec):
    cash_dir = Path(cash_dir)
    run, summary = load(cash_dir/'run_spec.json'), load(cash_dir/'summary.json')
    audit = load(cash_dir/'independent_cash_profiles.json')
    scope = run['effective_scope']
    if (scope['asof'] != spec['asof'] or scope['calendar'] != spec['formation_dates']
            or summary['completed_symbols'] != summary['expected_symbols']
            or summary['completed_symbols'] != len(scope['symbols'])
            or file_sha(spec['cash_execution_spec_path']) != spec['cash_execution_spec_sha256']
            or run['identity']['spec_sha256'] != spec['cash_execution_spec_sha256']
            or run['identity']['program_sha256'] != file_sha(Path(__file__).with_name('run_l2_ranking_cash_v12.py'))
            or summary['formal_provider_or_forecast'] is not False
            or audit['passed'] is not True or audit['symbols'] != len(scope['symbols'])
            or audit['summary_sha256'] != file_sha(cash_dir/'summary.json')
            or run['bound_manifest_sha256'] != file_sha(cash_dir/'bound_manifest.json')):
        raise ValueError('cash coverage/identity/audit mismatch')
    basic = {}
    for path, expected in spec['selection_spec_pins'].items():
        raw = read_small(Path(path), expected, 2*1024**2)
        if Path(path).name.startswith('daily_basic_'):
            day = Path(path).stem.rsplit('_',1)[1]
            rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
            if any(r['trade_date'] != day for r in rows) or len({r['ts_code'] for r in rows}) != len(rows):
                raise ValueError('basic date/duplicate identity')
            basic[day] = {r['ts_code']:r for r in rows}
    features, hashes = [], []
    for symbol in scope['symbols']:
        path = cash_dir/'stock_results'/(symbol+'.json')
        raw = read_small(path, limit=2*1024**2)
        result = json.loads(raw)
        hashes.append((symbol,sha(raw)))
        if result['symbol'] != symbol or result['identity'] != run['identity'] or result['bound_manifest_sha256'] != run['bound_manifest_sha256']:
            raise ValueError('cash checkpoint identity mismatch')
        features.append(make_feature(symbol, scope['names'][symbol], result['profile'], basic, spec))
    digest = sha(json.dumps(hashes, separators=(',', ':')).encode())
    if digest != audit['checkpoint_set_sha256']:
        raise ValueError('cash checkpoint set changed after independent audit')
    provenance = {'cash_dir':str(cash_dir.resolve()), 'cash_summary_sha256':file_sha(cash_dir/'summary.json'),
                  'cash_run_spec_sha256':file_sha(cash_dir/'run_spec.json'),
                  'cash_checkpoint_set_sha256':digest, 'cash_mode':run['identity']['mode']}
    return features, provenance


def arm_key(row, arm, spec):
    if arm in ('cash_group_turnover', 'cash_group_cap', 'cash_active_cap', 'cash_active_cap_persistent'):
        active = arm.startswith('cash_active')
        value = row['_active_cap'] if active else row['_group_turnover'] if arm == 'cash_group_turnover' else row['_group_cap']
        days = row['active_positive_days' if active else 'group_positive_days']
        return (-value, -days, row['_concentration'], row['symbol'])
    if arm == 'price_momentum5':
        return (-row['_momentum'], row['symbol'])
    if arm == 'ordinary_turnover5':
        return (-row['_turnover'], row['symbol'])
    if arm == 'hash_control':
        return (sha(('7:'+spec['asof']+':'+row['symbol']).encode()), row['symbol'])
    raise ValueError('unknown arm')


def exported(row):
    return {k:v for k,v in row.items() if not k.startswith('_')}


def select_arms(features, spec):
    selected, counts = [], []
    for panel in spec['panels']:
        pool = [r for r in features if r['common_eligible'] and (panel == PANELS[0] or not r['prior_case_17'])]
        for arm in ARMS:
            eligible = [r for r in pool if not arm.startswith('cash_') or r['source_class'] == 'A']
            if arm == 'cash_active_cap_persistent':
                eligible = [r for r in eligible if r['active_positive_days'] >= 4]
            chosen = sorted(eligible, key=lambda r:arm_key(r,arm,spec))[:spec['top_n']]
            counts.append({'panel':panel,'arm':arm,'common_pool':len(pool),'arm_eligible':len(eligible),
                           'planned_n':spec['top_n'],'selected_n':len(chosen),'underfilled':len(chosen)<spec['top_n']})
            for i, r in enumerate(chosen,1):
                selected.append({'panel':panel,'arm':arm,'selection_rank':i,**exported(r)})
    return selected, counts


def selection_overlap(selected, spec):
    rows = []
    for panel in spec['panels']:
        sets = {a:{r['symbol'] for r in selected if r['panel']==panel and r['arm']==a} for a in ARMS}
        for i, first in enumerate(ARMS):
            for second in ARMS[i+1:]:
                a, b = sets[first], sets[second]
                union = len(a|b)
                rows.append({'panel':panel,'first_arm':first,'second_arm':second,
                             'first_n':len(a),'second_n':len(b),'intersection_n':len(a&b),
                             'union_n':union,'jaccard_pct':number_text(Fraction(len(a&b),union),100) if union else None})
    return rows


def freeze_selection(cash_dir, output, spec_path):
    spec = read_spec(spec_path)
    features, provenance = build_features(cash_dir, spec)
    out = new_output(output, [cash_dir, Path(spec_path).parent/'formation_inputs', spec['price_source_dir'],
                              *spec.get('price_allowed_resolved_roots', [])])
    selected, counts = select_arms(features, spec)
    out.mkdir(parents=True)
    write_csv(out/'feature_universe.csv', [exported(r) for r in features])
    write_csv(out/'selections.csv', selected)
    write_csv(out/'arm_selection_counts.csv', counts)
    write_csv(out/'selection_overlap.csv', selection_overlap(selected,spec))
    manifest = {'role':'selection_frozen_before_outcome_OHLC_read_not_formal_Research_publication',
                'asof':spec['asof'], 'spec_sha256':file_sha(spec_path), 'code_sha256':file_sha(__file__),
                **provenance, 'features_sha256':file_sha(out/'feature_universe.csv'),
                'selections_sha256':file_sha(out/'selections.csv'), 'counts_sha256':file_sha(out/'arm_selection_counts.csv'),
                'overlap_sha256':file_sha(out/'selection_overlap.csv'),
                'selected_rows':len(selected),'unique_selected_symbols':len({r['symbol'] for r in selected}),
                'formal_provider_or_forecast':False, 'new_trigger_status':'not_assessed'}
    dump(out/'selection_manifest.json', manifest)
    return manifest


def snapshot_prices(symbols, out, spec):
    if len(symbols) > spec['price_max_symbols']:
        raise ValueError('selected price-symbol bound exceeded')
    snapshots = out/'price_snapshot'; snapshots.mkdir()
    bars, receipts, used = {}, [], 0
    after = spec['calendar'][spec['calendar'].index(spec['asof'])+1:]
    allowed = set([spec['asof']]+after[:20])
    roots = [Path(p).resolve() for p in spec.get('price_allowed_resolved_roots', [spec['price_source_dir']])]
    for symbol in sorted(symbols):
        path = Path(spec['price_source_dir'])/(symbol[:6]+'.csv')
        meta = {'symbol':symbol,'logical_path':str(path),'price_basis_qualified':False}
        if not path.is_file():
            bars[symbol] = {}; receipts.append({**meta,'error':'missing_or_nonregular_price_file'}); continue
        resolved = path.resolve(strict=True)
        if not any(resolved.is_relative_to(root) for root in roots) or resolved.name != symbol[:6]+'.csv':
            bars[symbol] = {}; receipts.append({**meta,'error':'unapproved_price_alias_target'}); continue
        before = resolved.stat()
        raw = read_small(resolved, limit=spec['price_file_max_bytes'])
        after_read = resolved.stat()
        if (path.resolve(strict=True) != resolved
                or (before.st_size, before.st_mtime_ns) != (after_read.st_size, after_read.st_mtime_ns)):
            raise ValueError('price source changed before snapshot binding')
        used += len(raw)
        if used > spec['price_total_max_bytes']:
            raise ValueError('total price snapshot byte bound exceeded')
        target = snapshots/(symbol+'.csv'); target.write_bytes(raw)
        meta.update(resolved_path=str(resolved),logical_was_symlink=path.is_symlink(),snapshot_path=str(target),bytes=len(raw),
                    mtime_ns=before.st_mtime_ns,sha256=sha(raw))
        records, invalid = {}, []
        try:
            seen = set()
            for r in csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))):
                if not isinstance(r.get('date'), str):
                    raise ValueError('missing price identity date')
                day = r['date'].replace('-','')
                if day not in allowed:
                    continue
                if day in seen:
                    raise ValueError('duplicate scoped price date')
                seen.add(day)
                if not isinstance(r.get('symbol'), str):
                    raise ValueError('missing price identity symbol')
                if r['symbol'].strip().zfill(6) != symbol[:6]:
                    raise ValueError('price instrument mismatch')
                try:
                    p = {k:exact_price(r[k]) for k in ('open','high','low','close')}
                    if p['low'] > min(p['open'],p['close']) or p['high'] < max(p['open'],p['close']) or p['low'] > p['high']:
                        raise ValueError('inconsistent OHLC')
                except ValueError:
                    invalid.append(day); continue
                records[day] = {k:r[k] for k in p}
        except (UnicodeError, KeyError, csv.Error, ValueError) as exc:
            meta['error'] = str(exc); records = {}
        meta['invalid_bar_dates'] = invalid
        meta['usable_scoped_dates'] = sorted(records)
        bars[symbol] = records; receipts.append(meta)
    return bars, {'role':'selected_local_price_snapshots_not_adjustment_or_provider_admission',
                  'bytes':used,'symbols':len(symbols),'files':receipts,'economic_prices_qualified':False}


def median_text(values):
    xs = sorted(Fraction(str(v)) for v in values)
    if not xs:
        return None
    i = len(xs)//2
    return number_text(xs[i] if len(xs)%2 else (xs[i-1]+xs[i])/2)


def summarize_paths(paths, counts, spec):
    result = []
    for c in counts:
        for horizon in spec['horizons']:
            rs = [r for r in paths if r['panel']==c['panel'] and r['arm']==c['arm'] and r['horizon_market_days']==horizon]
            n = len(rs)
            if n != int(c['selected_n']):
                raise ValueError('outcome matrix does not cover frozen selections')
            success = sum(r['raw_lowrisk_late_up_candidate'] is True for r in rs)
            unknown = sum(r['raw_lowrisk_late_up_candidate'] is None for r in rs)
            breach = sum(r['raw_risk_state']=='breached_observed' for r in rs)
            unknown_risk = sum(r['raw_risk_state'] in ('unknown_reference','unknown_incomplete') for r in rs)
            complete = [r for r in rs if r['path_complete']]
            waits = [r['first3_rising_closes_wait_sessions'] for r in rs if r.get('first3_rising_closes_wait_sessions') is not None]
            bound = lambda x: number_text(Fraction(x,n),100) if n else None
            result.append({**c,'horizon':horizon,'complete_paths':len(complete),'incomplete_paths':n-len(complete),
                           'known_breaches':breach,'unknown_risk':unknown_risk,'joint_success':success,
                           'joint_failure':n-success-unknown,'joint_unknown':unknown,
                           'joint_success_lower_pct':bound(success),'joint_success_upper_pct':bound(success+unknown),
                           'breach_lower_pct':bound(breach),'breach_upper_pct':bound(breach+unknown_risk),
                           'raw_endpoint_median_complete_only_pct':median_text([r['raw_close_change_pct_full_horizon'] for r in complete]),
                           'observed_waits':len(waits),'waiting_not_observed_or_censored':n-len(waits),
                           'median_wait_among_observed_sessions':median_text(waits),
                           'economic_risk_or_return_qualified':False})
    return result


def hypothesis_screen(summaries, spec):
    details = []
    for panel in spec['panels']:
        for horizon in spec['horizons']:
            lookup = {r['arm']:r for r in summaries if r['panel']==panel and r['horizon']==horizon}
            main = lookup[spec['main_arm']]
            for baseline in ('price_momentum5','ordinary_turnover5'):
                b = lookup[baseline]
                if int(main['selected_n']) != 20 or int(b['selected_n']) != 20:
                    passed = None
                else:
                    passed = (Decimal(main['joint_success_lower_pct']) > Decimal(b['joint_success_upper_pct'])
                              and Decimal(main['breach_upper_pct']) <= Decimal(b['breach_lower_pct']))
                details.append({'panel':panel,'horizon':horizon,'baseline':baseline,'bounded_raw_screen_passed':passed})
    states = [r['bounded_raw_screen_passed'] for r in details]
    status = 'inconclusive_underfilled' if any(v is None for v in states) else 'descriptive_support_only' if all(states) else 'not_supported_in_this_bounded_diagnostic'
    return {'status':status,'details':details,'validated_algorithm_winner':False,
            'reason':'already-exposed single time cohort, correlated stocks and unqualified economic prices'}


def observe_paths(selection_dir, output, spec_path):
    spec = read_spec(spec_path); selection_dir = Path(selection_dir)
    manifest = load(selection_dir/'selection_manifest.json')
    if (manifest['spec_sha256'] != file_sha(spec_path) or manifest['code_sha256'] != file_sha(__file__)
            or manifest['selections_sha256'] != file_sha(selection_dir/'selections.csv')
            or manifest['features_sha256'] != file_sha(selection_dir/'feature_universe.csv')
            or manifest['counts_sha256'] != file_sha(selection_dir/'arm_selection_counts.csv')
            or manifest['overlap_sha256'] != file_sha(selection_dir/'selection_overlap.csv')):
        raise ValueError('frozen selection changed before outcome reads')
    selected = table(selection_dir/'selections.csv'); counts = table(selection_dir/'arm_selection_counts.csv')
    if len(selected) != manifest['selected_rows']:
        raise ValueError('selection row coverage mismatch')
    out = new_output(output,[selection_dir,spec['price_source_dir'],*spec.get('price_allowed_resolved_roots',[])]); out.mkdir(parents=True)
    dump(out/'selection_read_receipt.json', {'selection_manifest_sha256':file_sha(selection_dir/'selection_manifest.json'),
                                           'spec_sha256':file_sha(spec_path),'code_sha256':file_sha(__file__)})
    bars, prices = snapshot_prices({r['symbol'] for r in selected},out,spec)
    dump(out/'price_snapshot_receipt.json',prices)
    paths = []
    for r in selected:
        for horizon in spec['horizons']:
            outcome = evaluate_path(spec['calendar'],bars[r['symbol']],spec['asof'],horizon)
            paths.append({**r,**outcome})
    summaries = summarize_paths(paths,counts,spec)
    write_csv(out/'raw_path_outcomes.csv',paths)
    write_csv(out/'comparison_summary.csv',summaries)
    dump(out/'hypothesis_screen.json',hypothesis_screen(summaries,spec))
    summary = {'role':'retrospective_raw_path_comparison_not_strategy_effectiveness_validation',
               'asof':spec['asof'],'source_selected_rows':len(selected),'path_rows':len(paths),
               'summary_rows':len(summaries),'price_snapshot_bytes':prices['bytes'],
               'price_source_files_missing_or_invalid':sum(bool(r.get('error') or r.get('invalid_bar_dates')) for r in prices['files']),
               'raw_complete_paths':sum(r['path_complete'] for r in paths),
               'unseen_temporal_OOS':False,'formal_provider_or_forecast':False,'validated_algorithm_winner':False,
               'spec_sha256':file_sha(spec_path),'code_sha256':file_sha(__file__),
               'selection_manifest_sha256':file_sha(selection_dir/'selection_manifest.json')}
    dump(out/'summary.json',summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('select','observe'))
    parser.add_argument('--spec', default=str(HOME/'comparison_spec.json'))
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = freeze_selection(args.input,args.output,args.spec) if args.phase=='select' else observe_paths(args.input,args.output,args.spec)
    print(json.dumps(result,ensure_ascii=False))
