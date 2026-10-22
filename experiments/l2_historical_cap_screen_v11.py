"""Bounded historical source-structure watchlist, not a strategy or new trigger."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import importlib.util
import json
import os
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from decimal import Decimal
from fractions import Fraction
from pathlib import Path, PurePosixPath

ARTIFACT = Path('/srv/bcache-8t/ygguo/quant/l2-historical-candidates-v11')
ROOT = Path(__file__).resolve().parents[1]
CALENDAR = ['20261013', '20261014', '20261015', '20261016', '20261019']
KINDS = ['行情.csv', '逐笔成交.csv']
CASH_KEYS = {'buy': 'buy_amount_1e4', 'sell': 'sell_amount_1e4',
             'active_buy': 'buy_active_1e4', 'active_sell': 'sell_active_1e4',
             'passive_buy': 'buy_passive_1e4', 'passive_sell': 'sell_passive_1e4',
             'unknown_buy': 'buy_unclassified_1e4', 'unknown_sell': 'sell_unclassified_1e4'}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text())


def atomic_json(path, value):
    path = Path(path)
    if path.is_symlink() or path.with_suffix(path.suffix + '.tmp').exists():
        raise ValueError('unsafe output checkpoint')
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def import_pinned(path, expected, name):
    p = Path(path)
    if sha(p) != expected:
        raise ValueError(f'{name} hash mismatch')
    spec = importlib.util.spec_from_file_location('_bound_' + name, p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_analyzers():
    modules = [importlib.import_module('experiments.' + n) for n in
               ('run_l2_two_stock_50w_v4', 'run_l2_postclose_ladder_v3', 'l2_continuous_interval_v6')]
    # Include transitive local economic/reader helpers in the resume identity.
    pins = {}
    names = ('run_l2_two_stock_50w_v4', 'run_l2_postclose_ladder_v3', 'l2_continuous_interval_v6',
             'run_l2_postclose_fund_flow_v2', 'l2_postclose_source_v2',
             'l2_postclose_core_v1', 'l2_postclose_inference_v1')
    for name in names:
        mod = importlib.import_module('experiments.' + name)
        p = Path(mod.__file__).resolve()
        if not p.is_relative_to(ROOT):
            raise ValueError('analyzer origin outside current worktree: ' + name)
        pins[str(p.relative_to(ROOT))] = sha(p)
    return (*modules, pins)


def flag(value):
    if type(value) is bool:
        return value
    if value == 'True':
        return True
    if value == 'False':
        return False
    return None


def integer(value):
    if value is None or value == '':
        return None
    if type(value) is int:
        return value
    if isinstance(value, str) and re.fullmatch(r'-?[0-9]+', value):
        return int(value)
    raise ValueError('money must be an exact integer, not float/truncated numeric')


def classify_profile(profile):
    ready, group, active = (flag(profile.get(k)) for k in
                            ('cash_window_ready', 'group_buy_bias', 'active_support'))
    if ready is not True or group is None or active is None:
        return 'D'
    return ('A' if active else 'B') if group else 'C'


def candidate_sort_key(row):
    return (0 if row['class'] == 'A' else 1,
            -Fraction(integer(row['group_difference_1e4']), integer(row['market_amount_1e4'])),
            -integer(row['group_positive_days']),
            Fraction(integer(row['top2_positive_delta_numerator_1e4']),
                     integer(row['positive_delta_denominator_1e4'])), row['symbol'])


def daily_record(symbol, day, obs, wide):
    row = {'symbol': symbol, 'day': day, 'source_fact_ready': flag(obs.get('cash_fact_ready')),
           'cash_ready': False, 'cash_reason': obs.get('cash_reason')}
    row.update({k: integer((wide or {}).get(v)) for k, v in CASH_KEYS.items()})
    row['market_amount'] = integer(obs.get('observed_amount_1e4'))
    if any(row[k] is not None and row[k] < 0 for k in (*CASH_KEYS, 'market_amount')):
        raise ValueError('negative source cash')
    row['cash_ready'] = (row['source_fact_ready'] is True
                         and all(row[k] is not None for k in CASH_KEYS)
                         and row['market_amount'] is not None and row['market_amount'] > 0)
    if row['source_fact_ready'] is True and not row['cash_ready']:
        row['cash_reason'] = 'side_reference_distribution_unavailable'
    return row


def validate_full_gate(mode, gate_path, spec_path):
    if mode != 'full':
        return
    if not gate_path:
        raise ValueError('--full-gate required for full mode')
    gate = load_json(gate_path)
    required = {'role', 'execution_spec_sha256', 'program_sha256',
                'smoke_receipt_path', 'smoke_receipt_sha256'}
    if (set(gate) != required or gate['role'] != 'parent_smoke_accepted'
            or gate['execution_spec_sha256'] != sha(spec_path)
            or gate['program_sha256'] != sha(__file__)
            or sha(gate['smoke_receipt_path']) != gate['smoke_receipt_sha256']):
        raise ValueError('invalid parent smoke gate')


def validate_members(inv, scope):
    archives = {a['path']: a for a in inv['archives']}
    if len(archives) != len(inv['archives']) or sorted(a['day'] for a in archives.values()) != scope['calendar']:
        raise ValueError('archive dates/duplicates')
    source = Path(scope['source']).resolve()
    for a in archives.values():
        p = Path(a['path'])
        if (p.is_symlink() or not p.is_absolute() or not p.resolve().is_relative_to(source)
                or p.parent != source / a['day'][:6]
                or not re.fullmatch(a['day'] + r'(?:\(\d+\))?\.7z', p.name)):
            raise ValueError('unsafe archive path')
        if any(type(a[k]) is not int or a[k] < 0 for k in
               ('bytes', 'mtime_ns', 'selected_bytes', 'selected_member_count', 'involved_solid_uncompressed_bytes')):
            raise ValueError('invalid archive totals')
    expected = {f'{d}/{s}/{k}' for d in scope['calendar'] for s in scope['symbols'] for k in scope['kinds']}
    seen = set()
    for m in inv['members']:
        p = PurePosixPath(m['member'])
        if m['member'] not in expected or str(p) != m['member'] or m['member'] in seen:
            raise ValueError('unsafe/duplicate/foreign member')
        seen.add(m['member'])
        if m['archive'] not in archives or archives[m['archive']]['day'] != p.parts[0]:
            raise ValueError('member archive mismatch')
        if (type(m['bytes']) is not int or not 0 < m['bytes'] <= scope['file_bytes_max']
                or not re.fullmatch(r'[0-9a-fA-F]{8}', m['crc32'])):
            raise ValueError('invalid member size/CRC')
    missing = inv['missing_members']
    if len(set(missing)) != len(missing) or set(missing) != expected - seen:
        raise ValueError('undeclared missing or foreign missing member')
    for a in archives.values():
        chosen = [m for m in inv['members'] if m['archive'] == a['path']]
        if len(chosen) != a['selected_member_count'] or sum(m['bytes'] for m in chosen) != a['selected_bytes']:
            raise ValueError('archive selected totals mismatch')
        # Reused intake uses this spelling; keep the inventory's original field as evidence.
        a['selected_members'] = a['selected_member_count']
    selected = sum(m['bytes'] for m in inv['members'])
    solid = sum(a['involved_solid_uncompressed_bytes'] for a in archives.values())
    if (selected != inv['selected_bytes'] or solid != inv['involved_solid_bytes']
            or selected > scope['selected_bytes_max'] or solid > scope['involved_solid_bytes_max']):
        raise ValueError('inventory byte totals/caps mismatch')


def check_cache_paths(inv, scope):
    cache = Path(scope['cache'])
    for m in inv['members']:
        target = cache / m['member']
        if any(p.is_symlink() for p in (target, target.parent, target.parent.parent)):
            raise ValueError('cache member/ancestor symlink forbidden')
        if target.exists() and not target.is_file():
            raise ValueError('cache member is not regular')


def check_archive_stats(inv):
    for a in inv['archives']:
        p = Path(a['path'])
        st = p.stat()
        if p.is_symlink() or (st.st_size, st.st_mtime_ns) != (a['bytes'], a['mtime_ns']):
            raise ValueError('archive identity changed')


def validate_plan(spec, mode):
    full_scope = load_json(spec['metadata_scope_path'])
    if sha(spec['metadata_scope_path']) != spec['metadata_scope_sha256']:
        raise ValueError('metadata scope hash mismatch')
    if (spec['calendar'] != CALENDAR or spec['asof'] != CALENDAR[-1] or spec['kinds'] != KINDS
            or spec['cash_threshold_cny'] != 500000
            or spec['total_cap_min_cny'] != '6000000000' or spec['total_cap_max_cny'] != '100000000000'
            or spec['total_cap_bounds_inclusive'] is not True
            or spec['symbols'] != full_scope['symbols'] or len(set(spec['symbols'])) != 2425
            or full_scope['dates'] != CALENDAR or full_scope['kinds'] != KINDS
            or spec['names'] != full_scope['names']):
        raise ValueError('execution spec differs from frozen financial scope')
    if (sha(spec['daily_basic_path']) != spec['daily_basic_sha256']
            or full_scope['daily_basic_sha256'] != spec['daily_basic_sha256']
            or sha(full_scope['stock_basic_source']) != full_scope['stock_basic_sha256']):
        raise ValueError('daily-basic/metadata input hash mismatch')
    caps = {}
    seen = set()
    with Path(spec['daily_basic_path']).open(encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            symbol = row['ts_code']
            if row['trade_date'] != spec['asof'] or symbol in seen:
                raise ValueError('foreign/duplicate daily-basic row')
            seen.add(symbol)
            if symbol in spec['names']:
                value = Decimal(row['total_mv'])
                if not value.is_finite() or not Decimal('6000000000') <= value <= Decimal('100000000000'):
                    raise ValueError('frozen roster outside total-cap band')
                caps[symbol] = row['total_mv']
    if set(caps) != set(spec['symbols']):
        raise ValueError('missing total-cap input')
    pins = {'metadata_scope': spec['metadata_scope_sha256'], 'daily_basic': spec['daily_basic_sha256'],
            'stock_basic': full_scope['stock_basic_sha256']}
    if mode == 'smoke':
        binding_path = ARTIFACT / 'smoke_binding.json'
        binding = load_json(binding_path)
        invpath = Path(binding['smoke_inventory_path'])
        sympath = Path(binding['smoke_symbols_path'])
        if sha(invpath) != binding['smoke_inventory_sha256'] or sha(sympath) != binding['smoke_symbols_sha256']:
            raise ValueError('smoke inventory/symbol hash mismatch')
        symbols = load_json(sympath)
        scope_path = ARTIFACT / 'cap_smoke_inventory_scope.json'
        metadata = load_json(scope_path)
        if (len(symbols) != 8 or len(set(symbols)) != 8 or not set(symbols) <= set(spec['symbols'])
                or symbols != metadata['symbols']):
            raise ValueError('invalid fixed smoke roster')
        invhash = binding['smoke_inventory_sha256']
        pins.update(smoke_binding=sha(binding_path), smoke_symbols=sha(sympath))
        selected_max, solid_max, workers, timeout = (spec[k] for k in
            ('sample_selected_bytes_max', 'sample_solid_bytes_max', 'sample_workers', 'sample_analysis_timeout_seconds'))
        if selected_max > 512 * 1024**2 or solid_max > 4 * 1024**3 or workers != 2 or timeout > 600:
            raise ValueError('smoke execution cap exceeded')
    else:
        invpath = Path(spec['inventory_path'])
        invhash = spec['inventory_sha256']
        symbols, metadata, scope_path = spec['symbols'], full_scope, Path(spec['metadata_scope_path'])
        selected_max, solid_max, workers, timeout = (spec[k] for k in
            ('selected_bytes_max', 'involved_solid_bytes_max', 'workers', 'analysis_timeout_seconds'))
        if selected_max > 64 * 1024**3 or solid_max > 160 * 1024**3 or not 1 <= workers <= min(8, spec['maximum_workers']):
            raise ValueError('full execution cap exceeded')
    inv = load_json(invpath)
    if (sha(invpath) != invhash or inv['scope_sha256'] != sha(scope_path)
            or metadata['dates'] != CALENDAR or metadata['kinds'] != KINDS
            or metadata['source'] != full_scope['source'] or inv['dates'] != CALENDAR
            or inv['symbols'] != len(symbols) or inv['asof'] != spec['asof']):
        raise ValueError('inventory/scope identity mismatch')
    pins.update(inventory=invhash, inventory_scope=sha(scope_path))
    # extract needs execution timeouts/budgets, not the metadata-only scope.
    effective = {**spec, 'symbols': symbols, 'source': metadata['source'], 'workers': workers,
                 'selected_bytes_max': selected_max, 'involved_solid_bytes_max': solid_max,
                 'analysis_timeout_seconds': timeout}
    for key in ('file_bytes_max', 'selected_bytes_max', 'involved_solid_bytes_max', 'workers',
                'analysis_timeout_seconds', 'extraction_timeout_seconds', 'archive_timeout_seconds'):
        if type(effective[key]) is not int or effective[key] <= 0:
            raise ValueError('invalid execution budget: ' + key)
    if effective['file_bytes_max'] > 256 * 1024**2:
        raise ValueError('file byte cap exceeded')
    validate_members(inv, effective)
    return effective, inv, caps, pins


def guard_output(output, scope):
    out = Path(output)
    for p in (out, *out.parents):
        if p.is_symlink():
            raise ValueError('output symlink forbidden')
    out = out.resolve()
    for path in (scope['source'], scope['cache']):
        protected = Path(path).resolve()
        if out.is_relative_to(protected) or protected.is_relative_to(out):
            raise ValueError('output must be outside and not contain source/raw cache')
    for k in ('metadata_scope_path', 'inventory_path', 'daily_basic_path', 'source_reader_path', 'extract_helper_path'):
        if Path(scope[k]).resolve().is_relative_to(out):
            raise ValueError('output contains immutable input')
    cache = Path(scope['cache'])
    if any(p.is_symlink() for p in (cache, *cache.parents)):
        raise ValueError('cache symlink forbidden')
    return out


def validate_bound(bound, inv, scope):
    if bound['archives'] != inv['archives'] or bound['missing_members'] != inv['missing_members']:
        raise ValueError('bound archive/missing identity mismatch')
    metas = {m['member']: m for m in bound['members']}
    if len(metas) != len(bound['members']) or set(metas) != {m['member'] for m in inv['members']}:
        raise ValueError('bound member coverage mismatch')
    for original in inv['members']:
        m = metas[original['member']]
        if any(m.get(k) != v for k, v in original.items()):
            raise ValueError('bound member identity mismatch')
        expected = Path(scope['cache']) / m['member']
        if (Path(m['path']) != expected or expected.is_symlink()
                or not expected.resolve().is_relative_to(Path(scope['cache']).resolve())
                or not re.fullmatch(r'[0-9a-f]{64}', m['sha256'])):
            raise ValueError('unsafe bound path/hash')
    digest = hashlib.sha256(json.dumps(sorted((m['member'], m['sha256']) for m in metas.values()),
                                      separators=(',', ':')).encode()).hexdigest()
    if digest != bound['selected_data_sha256']:
        raise ValueError('bound data hash mismatch')


_STATE = None


def init_worker(run_path, bound_path, deadline):
    global _STATE
    run = load_json(run_path)
    if sha(bound_path) != run['bound_manifest_sha256']:
        raise ValueError('worker bound manifest changed')
    scope = run['effective_scope']
    reader = import_pinned(scope['source_reader_path'], scope['reader_sha256'], 'reader')
    v4, v3, v6, pins = load_analyzers()
    if pins != run['identity']['analyzers'] or sha(__file__) != run['identity']['program_sha256']:
        raise ValueError('worker code identity changed')
    bound = load_json(bound_path)
    _STATE = (scope, {m['member']: m for m in bound['members']}, reader, v4, v3, v6, deadline)


def process_symbol(symbol, scope, metas, reader, v4, v3, v6, deadline):
    daily, observations, cells_all, diagnostics, markets, verified, errors, missing = ([] for _ in range(8))
    for day in scope['calendar']:
        if time.monotonic() >= deadline:
            raise TimeoutError('analysis deadline exceeded')
        frames = {}
        day_failed = False
        for kind in scope['kinds']:
            member = f'{day}/{symbol}/{kind}'
            meta = metas.get(member)
            if meta is None:
                missing.append(member)
                day_failed = True
                continue
            try:
                frame, detail = reader.read_bound_v8(Path(meta['path']), meta, day, symbol, kind, scope)
            except (OSError, ValueError, UnicodeError, csv.Error) as exc:
                errors.append({'symbol': symbol, 'day': day, 'kind': kind, 'error': str(exc)[:400]})
                day_failed = True
            else:
                frames[kind] = frame
                verified.append(detail)
        # A missing/invalid declared input invalidates the whole day, never a partial zero.
        if day_failed:
            obs = {'symbol': symbol, 'day': day, 'cash_fact_ready': False, 'cash_reason': 'missing_or_invalid_source_member'}
            cells, diag, market = [], [], {}
        else:
            try:
                obs, cells, diag, market = v4.analyze_day(frames, day, symbol)
            except (ValueError, OverflowError) as exc:
                errors.append({'symbol': symbol, 'day': day, 'kind': 'analysis', 'error': str(exc)[:400]})
                obs = {'symbol': symbol, 'day': day, 'cash_fact_ready': False, 'cash_reason': 'source_numeric_or_allocation_invalid'}
                cells, diag, market = [], [], {}
        if not cells:
            cells = v4.empty_cells(day, symbol, obs['cash_reason'])
        wide = [r for r in v3.wide_rows(cells) if r['band_id'] == 1]
        if len(wide) != 1:
            raise RuntimeError('canonical analyzer returned nonunique >=50w band')
        try:
            record = daily_record(symbol, day, obs, wide[0])
        except ValueError as exc:
            errors.append({'symbol': symbol, 'day': day, 'kind': 'cash_numeric', 'error': str(exc)[:400]})
            obs = {'symbol': symbol, 'day': day, 'cash_fact_ready': False, 'cash_reason': 'source_numeric_or_allocation_invalid'}
            record = daily_record(symbol, day, obs, None)
        if not record['cash_ready'] and not day_failed:
            errors.append({'symbol': symbol, 'day': day, 'kind': 'cash_gate', 'error': record['cash_reason']})
        daily.append(record)
        observations.append(obs)
        cells_all.extend(cells)
        diagnostics.extend(diag)
        markets.append(market)
    if time.monotonic() >= deadline:
        raise TimeoutError('analysis deadline exceeded')
    profile = v6.interval_profile(daily, 5)
    positive = sorted((d['buy'] - d['sell'] for d in daily if d['cash_ready'] and d['buy'] > d['sell']), reverse=True)
    profile['top2_positive_delta_numerator_1e4'] = sum(positive[:2]) if profile['cash_window_ready'] else None
    profile['positive_delta_denominator_1e4'] = sum(positive) if profile['cash_window_ready'] else None
    return {'symbol': symbol, 'daily': daily, 'profile': profile, 'observations': observations,
            'band_cells': cells_all, 'diagnostics': diagnostics, 'markets': markets,
            'verified_files': verified, 'errors': errors, 'missing': missing,
            'raw_source_close19': observations[-1].get('source_last_price_raw')}


def _work_symbol(symbol):
    return process_symbol(symbol, *_STATE)


def stock_row(result, scope, caps):
    symbol = result['symbol']
    profile = result['profile']
    row = {**profile, 'symbol': symbol, 'name': scope['names'][symbol], 'asof': scope['asof'],
           'total_mv_cny': caps[symbol], 'class': classify_profile(profile),
           'raw_source_close19': result['raw_source_close19'], 'new_trigger_status': 'not_assessed',
           'reference_next_open': 'pending', 'followup_market_sessions': '10;20', 'risk_limit_pct': 10,
           'formal_provider_or_forecast': False}
    for key, value in profile.items():
        if key.endswith('_1e4'):
            value = integer(value)
            row[key] = value
            row[key[:-4] + '_wan'] = None if value is None else format(Decimal(value) / Decimal(100000000), 'f')
    return row


def write_csv(path, rows, fields=None):
    fields = fields or list(dict.fromkeys(k for row in rows for k in row))
    if not fields:
        fields = ['symbol', 'class']
    tmp = path.with_suffix('.csv.tmp')
    if path.is_symlink():
        raise ValueError('output CSV symlink')
    with tmp.open('x', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)


def validate_stock(result, symbol, scope, identity, bound_sha):
    if (result['symbol'] != symbol or result['identity'] != identity or result['bound_manifest_sha256'] != bound_sha
            or [(d['symbol'], d['day']) for d in result['daily']] != [(symbol, d) for d in scope['calendar']]):
        raise ValueError('stock checkpoint identity/coverage mismatch')


def run_analysis(out, run, caps):
    scope = run['effective_scope']
    deadline = time.monotonic() + scope['analysis_timeout_seconds']
    symbols = scope['symbols']
    result_dir = out / 'stock_results'
    if result_dir.is_symlink():
        raise ValueError('stock checkpoint symlink')
    result_dir.mkdir(exist_ok=True)
    results = {}
    for path in result_dir.iterdir():
        if time.monotonic() >= deadline:
            raise TimeoutError('analysis deadline exceeded')
        if path.is_symlink() or path.suffix != '.json' or path.stem not in symbols:
            raise ValueError('foreign/partial stock checkpoint')
        result = load_json(path)
        validate_stock(result, path.stem, scope, run['identity'], run['bound_manifest_sha256'])
        results[path.stem] = result
    progress = out / 'progress.jsonl'
    if progress.is_symlink():
        raise ValueError('progress symlink')
    pending = [s for s in symbols if s not in results]
    if pending:
        pool = ProcessPoolExecutor(max_workers=scope['workers'], initializer=init_worker,
                                   initargs=(out / 'run_spec.json', out / 'bound_manifest.json', deadline))
        futures = {pool.submit(_work_symbol, s): s for s in pending}
        try:
            for future in as_completed(futures, timeout=max(0, deadline - time.monotonic())):
                if time.monotonic() >= deadline:
                    raise TimeoutError('analysis deadline exceeded')
                symbol = futures[future]
                result = {**future.result(), 'identity': run['identity'],
                          'bound_manifest_sha256': run['bound_manifest_sha256']}
                validate_stock(result, symbol, scope, run['identity'], run['bound_manifest_sha256'])
                atomic_json(result_dir / (symbol + '.json'), result)
                with progress.open('a') as f:
                    f.write(json.dumps({'symbol': symbol, 'class': classify_profile(result['profile']),
                                        'checkpoint_sha256': sha(result_dir / (symbol + '.json'))}) + '\n')
                    f.flush()
                    os.fsync(f.fileno())
                results[symbol] = result
        except BaseException:
            # Python <3.14 has no public terminate_workers; do not wait past the analysis cap.
            for process in pool._processes.values():
                process.terminate()
            pool.shutdown(wait=True, cancel_futures=True)
            raise
        else:
            pool.shutdown(wait=True)
    if time.monotonic() >= deadline:
        raise TimeoutError('analysis deadline exceeded')
    if set(results) != set(symbols):
        raise RuntimeError('incomplete universe; no final output')
    ordered = [results[s] for s in symbols]
    rows = [stock_row(r, scope, caps) for r in ordered]
    candidates = sorted((r for r in rows if r['class'] in ('A', 'B')), key=candidate_sort_key)
    source = {k: [item for r in ordered for item in r[k]] for k in ('verified_files', 'errors', 'missing')}
    observations = [{**o, **d} for r in ordered for o, d in zip(r['observations'], r['daily'])]
    if len(observations) != len(symbols) * 5:
        raise RuntimeError('incomplete stock-day matrix')
    check_archive_stats(load_json(out / 'bound_manifest.json'))
    write_csv(out / 'all_stocks.csv', rows)
    write_csv(out / 'candidates.csv', candidates, list(dict.fromkeys(k for row in rows for k in row)))
    write_csv(out / 'day_observations.csv', observations)
    atomic_json(out / 'source_verification.json', source)
    summary = {'role': scope['role'], 'mode': run['identity']['mode'], 'asof': scope['asof'],
               'status': 'complete_with_unknown' if source['errors'] or source['missing'] else 'complete',
               'expected_symbols': len(symbols), 'completed_symbols': len(results),
               'symbols': symbols, 'calendar': scope['calendar'], 'stock_days': len(observations),
               'classes': {c: sum(r['class'] == c for r in rows) for c in 'ABCD'},
               'verified_files': len(source['verified_files']), 'errors': len(source['errors']),
               'missing': len(source['missing']), 'candidates': len(candidates),
               'new_trigger_status': 'not_assessed', 'reference_next_open': 'pending',
               'formal_provider_or_forecast': False}
    if time.monotonic() >= deadline:
        raise TimeoutError('analysis deadline exceeded before final receipt')
    atomic_json(out / 'summary.json', summary)
    return 2 if source['errors'] or source['missing'] else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--spec', default=str(ARTIFACT / 'execution_spec.json'))
    ap.add_argument('--output', required=True)
    ap.add_argument('--mode', choices=('smoke', 'full'), required=True)
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--full-gate')
    args = ap.parse_args(argv)
    spath = Path(args.spec)
    # This wrapper executes only the frozen packet, not an alternate financial spec.
    if sha(spath) != sha(ARTIFACT / 'execution_spec.json'):
        raise ValueError('execution spec is not the frozen packet')
    validate_full_gate(args.mode, args.full_gate, spath)
    spec = load_json(spath)
    scope, inv, caps, pins = validate_plan(spec, args.mode)
    out = guard_output(args.output, scope)
    if out.exists() and not args.resume:
        raise ValueError('output exists; explicit --resume required')
    if args.resume and not out.is_dir():
        raise ValueError('--resume requires an existing run')
    reader = import_pinned(spec['source_reader_path'], spec['reader_sha256'], 'reader')
    helper = import_pinned(spec['extract_helper_path'], spec['extract_helper_sha256'], 'intake')
    del reader
    *_, analyzers = load_analyzers()
    identity = {'mode': args.mode, 'execution_spec_sha256': sha(spath), 'program_sha256': sha(__file__),
                'reader_sha256': spec['reader_sha256'], 'extract_helper_sha256': spec['extract_helper_sha256'],
                'pins': pins, 'analyzers': analyzers, 'output': str(out), 'cache': str(Path(scope['cache']).resolve())}
    run = {'identity': identity, 'effective_scope': scope}
    if args.resume:
        saved = load_json(out / 'run_spec.json')
        if saved['identity'] != identity or saved['effective_scope'] != scope:
            raise ValueError('resume identity changed')
        run = saved
    else:
        out.mkdir(parents=True)
        atomic_json(out / 'run_spec.json', run)
    check_archive_stats(inv)
    check_cache_paths(inv, scope)
    bound_path = out / 'bound_manifest.json'
    if bound_path.exists():
        if not args.resume or sha(bound_path) != run.get('bound_manifest_sha256'):
            raise ValueError('bound checkpoint identity changed')
        bound = load_json(bound_path)
        validate_bound(bound, inv, scope)
        # Recheck immutable cached bytes before reusing any completed stock result.
        current = helper.extract(inv, scope, Path(scope['cache']))
        validate_bound(current, inv, scope)
        if current['selected_data_sha256'] != bound['selected_data_sha256']:
            raise ValueError('resume cache content changed')
    else:
        if run.get('bound_manifest_sha256'):
            raise ValueError('bound checkpoint missing')
        bound = helper.extract(inv, scope, Path(scope['cache']))
        validate_bound(bound, inv, scope)
        atomic_json(bound_path, bound)
        run['bound_manifest_sha256'] = sha(bound_path)
        atomic_json(out / 'run_spec.json', run)
    validate_bound(bound, inv, scope)
    return run_analysis(out, run, caps)


if __name__ == '__main__':
    raise SystemExit(main())
