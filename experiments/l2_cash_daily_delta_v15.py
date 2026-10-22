"""One explicit raw delta plus immutable accepted daily facts; no window profiles."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import time
import zlib
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from uuid import uuid4

from experiments import l2_historical_cap_screen_v11 as support
from experiments import run_l2_ranking_cash_v12 as old

ARTIFACT = Path('/srv/bcache-8t/ygguo/quant/l2-expanded-study-v15')
ROOT = Path(__file__).resolve().parents[1]
CALENDAR = ['20260901', '20260902', '20260903', '20260904', '20260907',
            '20260908', '20260909', '20260910', '20260911', '20260914']
KINDS = ['行情.csv', '逐笔成交.csv']
sha, load_json = support.sha, support.load_json
no_symlinks, guard_paths, stop_pool = old.no_symlinks, old.guard_paths, old.stop_pool
sync_progress, atomic_progress = old.sync_progress, old.atomic_progress


def atomic_json(path, value):
    path = Path(path)
    no_symlinks(path)
    tmp = path.with_name(path.name + '.' + uuid4().hex + '.tmp')
    with tmp.open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def validate_full_gate(mode, gate_path, spec_path):
    if mode != 'full':
        return None
    if not gate_path:
        raise ValueError('--full-gate required for full mode')
    no_symlinks(gate_path)
    gate = load_json(gate_path)
    required = {'role', 'execution_spec_sha256', 'program_sha256',
                'smoke_receipt_path', 'smoke_receipt_sha256'}
    if (set(gate) != required or gate['role'] != 'parent_smoke_accepted'
            or gate['execution_spec_sha256'] != sha(spec_path)
            or gate['program_sha256'] != sha(__file__)
            or not Path(gate['smoke_receipt_path']).is_absolute()):
        raise ValueError('invalid parent smoke gate')
    no_symlinks(gate['smoke_receipt_path'])
    if sha(gate['smoke_receipt_path']) != gate['smoke_receipt_sha256']:
        raise ValueError('invalid parent smoke receipt')
    return {'gate_sha256': sha(gate_path), **gate}


def pinned_json(path, expected):
    no_symlinks(path)
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('input/checkpoint hash mismatch: ' + str(path))
    return json.loads(raw)


def validate_scope(spec, mode):
    binding = spec[mode]
    scope = pinned_json(binding['scope_path'], binding['scope_sha256'])
    plan = pinned_json(binding['plan_path'], binding['plan_sha256'])
    symbols = scope['symbols']
    if (scope['calendar'] != CALENDAR or scope['kinds'] != KINDS
            or len(set(symbols)) != len(symbols) or not symbols
            or any(not re.fullmatch(r'[0-9]{6}\.(?:SH|SZ)', s) for s in symbols)):
        raise ValueError('daily scope identity mismatch')
    limits = {'file_bytes_max': 256 * 1024**2,
              'selected_bytes_max': (512 * 1024**2 if mode == 'smoke' else 64 * 1024**3),
              'involved_solid_bytes_max': (4 if mode == 'smoke' else 160) * 1024**3,
              'workers': 2 if mode == 'smoke' else 8,
              'extraction_timeout_seconds': 600 if mode == 'smoke' else 3600,
              'archive_timeout_seconds': 300 if mode == 'smoke' else 1800,
              'analysis_timeout_seconds': 600 if mode == 'smoke' else 10800}
    for key, limit in limits.items():
        if type(scope[key]) is not int or not 0 < scope[key] <= limit:
            raise ValueError('invalid execution budget: ' + key)
    if (type(spec['one_new_raw_batch_total_max']) is not int
            or not 0 < spec['one_new_raw_batch_total_max'] <= 64 * 1024**3
            or scope['selected_bytes_max'] > spec['one_new_raw_batch_total_max']):
        raise ValueError('invalid single batch budget')
    expected = scope['expected_fact_keys']
    fresh, reuse = plan['expected_fresh_fact_keys'], plan['reuse_facts']
    allowed = {f'{d}/{s}' for d in CALENDAR for s in symbols}
    if (not expected or len(set(expected)) != len(expected) or not set(expected) <= allowed
            or {key.split('/')[1] for key in expected} != set(symbols)
            or len(set(fresh)) != len(fresh) or set(fresh) & set(reuse)
            or set(fresh) | set(reuse) != set(expected)
            or plan['all_needed_fact_keys'] != expected):
        raise ValueError('expected fact partition mismatch')
    per_symbol = {}
    old_stock_dir = Path(spec['reuse_source_identity']['output']) / 'stock_results'
    for key, pin in reuse.items():
        day, symbol = key.split('/')
        path = Path(pin['checkpoint_path'])
        if (pin['day'] != day or pin['symbol'] != symbol or not path.is_absolute()
                or path != old_stock_dir / (symbol + '.json')
                or not re.fullmatch(r'[0-9a-f]{64}', pin['checkpoint_sha256'])):
            raise ValueError('reuse checkpoint identity mismatch')
        if symbol in per_symbol and per_symbol[symbol] != pin['checkpoint_sha256']:
            raise ValueError('conflicting reuse checkpoint pins')
        per_symbol[symbol] = pin['checkpoint_sha256']
    archives = {a['path']: a for a in plan['archives']}
    if (len(archives) != len(plan['archives'])
            or sorted(a['day'] for a in archives.values()) != CALENDAR):
        raise ValueError('archive dates/duplicates')
    source = Path(scope['source'])
    for a in archives.values():
        path = Path(a['path'])
        no_symlinks(path)
        if (not path.is_absolute() or path.parent != source / a['day'][:6]
                or not re.fullmatch(a['day'] + r'(?:\(\d+\))?\.7z', path.name)
                or any(type(a[k]) is not int or a[k] < 0 for k in
                       ('bytes', 'mtime_ns', 'selected_bytes', 'selected_members',
                        'selected_member_count', 'involved_solid_uncompressed_bytes'))):
            raise ValueError('invalid archive metadata/path')
    wanted = {f'{key}/{kind}' for key in fresh for kind in KINDS}
    seen = set()
    counts = {p: [0, 0] for p in archives}
    for member in plan['members']:
        key = member['member']
        if key not in wanted or key in seen:
            raise ValueError('duplicate/foreign fresh member')
        seen.add(key)
        archive = member['archive']
        if archive not in archives or archives[archive]['day'] != key.split('/')[0]:
            raise ValueError('member archive mismatch')
        if (type(member['bytes']) is not int or not 0 < member['bytes'] <= scope['file_bytes_max']
                or not re.fullmatch(r'[0-9a-f]{8}', member['crc32'])
                or not isinstance(member['block'], str) or not re.fullmatch(r'[0-9]+', member['block'])):
            raise ValueError('invalid member size/CRC/block')
        counts[archive][0] += 1
        counts[archive][1] += member['bytes']
    missing = plan['missing_members']
    if len(set(missing)) != len(missing) or set(missing) != wanted - seen:
        raise ValueError('undeclared/foreign fresh missing member')
    for path, a in archives.items():
        if (counts[path] != [a['selected_member_count'], a['selected_bytes']]
                or a['selected_members'] != a['selected_member_count']):
            raise ValueError('archive selected totals mismatch')
    selected = sum(m['bytes'] for m in plan['members'])
    solid = sum(a['involved_solid_uncompressed_bytes'] for a in archives.values())
    if (selected != plan['selected_bytes'] or solid != plan['involved_solid_bytes']
            or selected > scope['selected_bytes_max'] or solid > scope['involved_solid_bytes_max']):
        raise ValueError('plan byte totals/caps mismatch')
    effective = {**scope, **{k: spec[k] for k in ('source_reader_path', 'reader_sha256',
                 'extract_helper_path', 'extract_helper_sha256', 'core_module_path', 'core_module_sha256')}}
    return effective, plan


def verify_reuse(spec, plan):
    run = pinned_json(spec['reuse_run_spec_path'], spec['reuse_run_spec_sha256'])
    bound = pinned_json(spec['reuse_bound_manifest_path'], spec['reuse_bound_manifest_sha256'])
    if (run['identity'] != spec['reuse_source_identity']
            or run['bound_manifest_sha256'] != spec['reuse_bound_manifest_sha256']):
        raise ValueError('reuse source run/bound identity mismatch')
    calendar = run['effective_scope']['calendar']
    if len(set(calendar)) != len(calendar):
        raise ValueError('invalid reuse calendar')
    pins = {}
    for key, pin in plan['reuse_facts'].items():
        if pin['day'] not in calendar:
            raise ValueError('reuse day outside original calendar')
        pins[pin['checkpoint_path']] = pin['checkpoint_sha256']
    # Hash only derived checkpoints, never inspect or reconstruct the old raw cache.
    for path, expected in pins.items():
        no_symlinks(path)
        if sha(path) != expected:
            raise ValueError('reuse checkpoint hash mismatch')
    return calendar, bound


def reused_days(symbol, pins, spec, calendar, bound):
    """Parse a checkpoint once per symbol; preserve original values and array order."""
    if not pins:
        return {}
    first = next(iter(pins.values()))
    result = pinned_json(first['checkpoint_path'], first['checkpoint_sha256'])
    if (result['symbol'] != symbol or result['identity'] != spec['reuse_source_identity']
            or result['bound_manifest_sha256'] != spec['reuse_bound_manifest_sha256']):
        raise ValueError('reuse checkpoint source identity mismatch')
    old.validate_stock(result, symbol,
                       {'identity': spec['reuse_source_identity'],
                        'bound_manifest_sha256': spec['reuse_bound_manifest_sha256'],
                        'effective_scope': {'calendar': calendar, 'kinds': KINDS}}, bound)
    days = {}
    for key, pin in pins.items():
        day = pin['day']
        index = calendar.index(day)
        fact = {'day': day, 'symbol': symbol, 'daily': result['daily'][index],
                'observation': result['observations'][index], 'market': result['markets'][index]}
        for field in ('band_cells', 'diagnostics', 'errors'):
            fact[field] = [r for r in result[field] if r['day'] == day]
        fact['verified_files'] = [r for r in result['verified_files'] if r['member'].split('/')[0] == day]
        fact['missing'] = [m for m in result['missing'] if m.split('/')[0] == day]
        fact['provenance'] = {'kind': 'reused', 'checkpoint_path': pin['checkpoint_path'],
                              'checkpoint_sha256': pin['checkpoint_sha256']}
        days[day] = fact
    return days


def analyze_one_day(day, symbol, frames, canonicalhelpers):
    """Use the retained canonical daily money/mask logic, never an interval profile.

    Missing keys in frames mean an explicitly requested input failed or is absent.
    Source reading and its receipts are owned by work_symbol.
    """
    core, v4, v3 = canonicalhelpers
    errors = []
    day_failed = any(kind not in frames for kind in KINDS)
    if day_failed:
        obs = {'symbol': symbol, 'day': day, 'cash_fact_ready': False,
               'cash_reason': 'missing_or_invalid_source_member'}
        cells, diag, market = [], [], {}
    else:
        try:
            obs, cells, diag, market = v4.analyze_day(frames, day, symbol)
        except (ValueError, OverflowError) as exc:
            errors.append({'symbol': symbol, 'day': day, 'kind': 'analysis', 'error': str(exc)[:400]})
            obs = {'symbol': symbol, 'day': day, 'cash_fact_ready': False,
                   'cash_reason': 'source_numeric_or_allocation_invalid'}
            cells, diag, market = [], [], {}
    if not cells:
        cells = v4.empty_cells(day, symbol, obs['cash_reason'])
    wide = [r for r in v3.wide_rows(cells) if r['band_id'] == 1]
    if len(wide) != 1:
        raise RuntimeError('canonical analyzer returned nonunique >=50w band')
    try:
        record = core.daily_record(symbol, day, obs, wide[0])
    except ValueError as exc:
        errors.append({'symbol': symbol, 'day': day, 'kind': 'cash_numeric', 'error': str(exc)[:400]})
        obs = {'symbol': symbol, 'day': day, 'cash_fact_ready': False,
               'cash_reason': 'source_numeric_or_allocation_invalid'}
        record = core.daily_record(symbol, day, obs, None)
    if not record['cash_ready'] and not day_failed:
        errors.append({'symbol': symbol, 'day': day, 'kind': 'cash_gate', 'error': record['cash_reason']})
    return {'day': day, 'symbol': symbol, 'daily': record, 'observation': obs,
            'band_cells': cells, 'diagnostics': diag, 'market': market, 'errors': errors}


class BoundReader(old.BoundReader):
    def read_bound_v8(self, *args):
        try:
            return super().read_bound_v8(*args)
        except ValueError as exc:
            if str(exc) == 'source date/instrument mismatch':
                raise RuntimeError('source identity mismatch') from exc
            raise


_STATE = None


def init_worker(run_spec_path, bound_path, deadline):
    global _STATE
    run = load_json(run_spec_path)
    identity, scope = run['identity'], run['effective_scope']
    if (sha(__file__) != identity['program_sha256']
            or sha(bound_path) != run['bound_delta_manifest_sha256']
            or sha(old.__file__) != identity['old_runner_sha256']):
        raise ValueError('worker program/bound identity changed')
    core = support.import_pinned(scope['core_module_path'], identity['core_sha256'], 'delta_core')
    reader = core.import_pinned(scope['source_reader_path'], identity['reader_sha256'], 'delta_reader')
    v4, v3, _, pins = core.load_analyzers()
    if pins != identity['analyzers']:
        raise ValueError('worker analyzer identity changed')
    spec = pinned_json(identity['spec_path'], identity['spec_sha256'])
    plan = pinned_json(identity['scope_plan_pins']['plan_path'], identity['scope_plan_pins']['plan_sha256'])
    reuse_run = pinned_json(spec['reuse_run_spec_path'], spec['reuse_run_spec_sha256'])
    old_bound = pinned_json(spec['reuse_bound_manifest_path'], spec['reuse_bound_manifest_sha256'])
    if (reuse_run['identity'] != spec['reuse_source_identity']
            or reuse_run['bound_manifest_sha256'] != spec['reuse_bound_manifest_sha256']):
        raise ValueError('worker reuse identity changed')
    by_symbol = {s: [] for s in scope['symbols']}
    reuse_by_symbol = {s: {} for s in scope['symbols']}
    for key in scope['expected_fact_keys']:
        day, symbol = key.split('/')
        by_symbol[symbol].append(day)
    for key, pin in plan['reuse_facts'].items():
        reuse_by_symbol[pin['symbol']][key] = pin
    _STATE = (core, scope, {m['member']: m for m in load_json(bound_path)['members']},
              BoundReader(reader), v4, v3, deadline, spec, reuse_run['effective_scope']['calendar'],
              old_bound, by_symbol, reuse_by_symbol)


def work_symbol(symbol):
    core, scope, metas, reader, v4, v3, deadline, spec, calendar, bound, by_symbol, pins = _STATE
    def check():
        if time.monotonic() >= deadline:
            raise TimeoutError('daily analysis deadline exceeded')
    check()
    reused = reused_days(symbol, pins[symbol], spec, calendar, bound)
    days = []
    for day in sorted(by_symbol[symbol]):
        check()
        if day in reused:
            days.append(reused[day])
            continue
        frames, verified, errors, missing = {}, [], [], []
        for kind in KINDS:
            check()
            member = f'{day}/{symbol}/{kind}'
            meta = metas.get(member)
            if meta is None:
                missing.append(member)
                continue
            try:
                frame, detail = reader.read_bound_v8(Path(meta['path']), meta, day, symbol, kind, scope)
            except (ValueError, UnicodeError, csv.Error) as exc:
                errors.append({'symbol': symbol, 'day': day, 'kind': kind, 'error': str(exc)[:400]})
            else:
                frames[kind] = frame
                verified.append(detail)
        fact = analyze_one_day(day, symbol, frames, (core, v4, v3))
        fact['errors'] = errors + fact['errors']
        fact.update(verified_files=verified, missing=missing, provenance={'kind': 'fresh'})
        days.append(fact)
    check()
    return {'symbol': symbol, 'days': days}


def validate_stock(result, symbol, run, bound, plan):
    scope = run['effective_scope']
    if (set(result) != {'symbol', 'identity', 'bound_delta_manifest_sha256', 'days'}
            or result['symbol'] != symbol or result['identity'] != run['identity']
            or result['bound_delta_manifest_sha256'] != run['bound_delta_manifest_sha256']):
        raise ValueError('stock checkpoint identity mismatch')
    expected = sorted(key.split('/')[0] for key in scope['expected_fact_keys'] if key.split('/')[1] == symbol)
    if [(r['symbol'], r['day']) for r in result['days']] != [(symbol, d) for d in expected]:
        raise ValueError('stock checkpoint exact day coverage mismatch')
    metas = {m['member']: m for m in bound['members']}
    for fact in result['days']:
        day = fact['day']
        key = f'{day}/{symbol}'
        for field in ('daily', 'observation'):
            if (fact[field]['symbol'], fact[field]['day']) != (symbol, day):
                raise ValueError('foreign daily/observation')
        if not isinstance(fact['market'], dict):
            raise ValueError('market detail missing')
        for field in ('band_cells', 'diagnostics', 'verified_files', 'errors', 'missing'):
            if not isinstance(fact[field], list):
                raise ValueError('detail array missing: ' + field)
        for field in ('band_cells', 'diagnostics', 'errors'):
            if any((r.get('symbol'), r.get('day')) != (symbol, day) for r in fact[field]):
                raise ValueError('foreign day detail')
        if any(r.get('kind') not in (*KINDS, 'analysis', 'cash_numeric', 'cash_gate') for r in fact['errors']):
            raise ValueError('foreign source error mask')
        members = {f'{key}/{kind}' for kind in KINDS}
        verified = [r['member'] for r in fact['verified_files']]
        missing = fact['missing']
        if (len(set(verified)) != len(verified) or len(set(missing)) != len(missing)
                or not set(verified) <= members or not set(missing) <= members
                or set(verified) & set(missing)):
            raise ValueError('day source coverage mismatch')
        if key in plan['reuse_facts']:
            pin = plan['reuse_facts'][key]
            provenance = {'kind': 'reused', 'checkpoint_path': pin['checkpoint_path'],
                          'checkpoint_sha256': pin['checkpoint_sha256']}
        else:
            provenance = {'kind': 'fresh'}
            if set(missing) != members & set(bound['missing_members']):
                raise ValueError('fresh missing coverage mismatch')
            if any(r.get('sha256') != metas[r['member']]['sha256'] for r in fact['verified_files']):
                raise ValueError('fresh verified hash mismatch')
        if fact['provenance'] != provenance:
            raise ValueError('day provenance mismatch')
        if not fact['errors'] and set(verified) | set(missing) != members:
            raise ValueError('unexplained day source gap')


def validate_delta_bound(bound, plan, scope):
    # The retained validator covers members, paths and selected-data digest. Also
    # bind all delta-only metadata (including selected bytes and the partition).
    support.validate_bound(bound, plan, scope)
    if any(bound.get(key) != value for key, value in plan.items() if key != 'members'):
        raise ValueError('bound delta plan metadata mismatch')
    originals = {m['member']: m for m in plan['members']}
    for meta in bound['members']:
        if set(meta) != set(originals[meta['member']]) | {'path', 'sha256'}:
            raise ValueError('bound delta member metadata mismatch')


def reverify_cache(bound, scope):
    deadline = time.monotonic() + scope['extraction_timeout_seconds']
    support.check_cache_paths(bound, scope)
    for meta in bound['members']:
        if time.monotonic() >= deadline:
            raise TimeoutError('delta cache verification deadline exceeded')
        path = Path(meta['path'])
        no_symlinks(path)
        if not path.is_file() or path.stat().st_size != meta['bytes']:
            raise ValueError('delta cache content changed or missing')
        before = path.stat()
        digest, crc = hashlib.sha256(), 0
        with path.open('rb') as f:
            for raw in iter(lambda: f.read(1024 * 1024), b''):
                digest.update(raw)
                crc = zlib.crc32(raw, crc)
                if time.monotonic() >= deadline:
                    raise TimeoutError('delta cache verification deadline exceeded')
        after = path.stat()
        if (digest.hexdigest() != meta['sha256'] or f'{crc & 0xffffffff:08x}' != meta['crc32']
                or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)):
            raise ValueError('delta cache content changed')


def write_daily(path, rows):
    tmp = path.with_name(path.name + '.' + uuid4().hex + '.tmp')
    with tmp.open('x', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        writer.writeheader()
        writer.writerows(rows)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def analyze(out, run, bound, plan, core):
    scope = run['effective_scope']
    deadline = time.monotonic() + scope['analysis_timeout_seconds']
    def check():
        if time.monotonic() >= deadline:
            raise TimeoutError('daily analysis deadline exceeded')
    result_dir = out / 'stock_results'
    result_dir.mkdir(exist_ok=True)
    results = {}
    for path in result_dir.iterdir():
        check()
        owned_temp = re.fullmatch(r'([0-9]{6}\.(?:SH|SZ))\.json\.[0-9a-f]{32}\.tmp', path.name)
        if owned_temp and owned_temp.group(1) in scope['symbols']:
            no_symlinks(path)
            if not path.is_file():
                raise ValueError('nonregular interrupted checkpoint temp')
            # Keep uncommitted bytes as evidence; only validated .json files count.
            continue
        if path.suffix != '.json' or path.stem not in scope['symbols'] or not path.is_file():
            raise ValueError('foreign/partial stock checkpoint')
        result = load_json(path)
        validate_stock(result, path.stem, run, bound, plan)
        results[path.stem] = result
    lines = sync_progress(out, results)
    pending = [s for s in scope['symbols'] if s not in results]
    if pending:
        pool = ProcessPoolExecutor(max_workers=scope['workers'], initializer=init_worker,
                                   initargs=(out / 'run_spec.json', out / 'bound_delta_manifest.json', deadline))
        try:
            futures = {pool.submit(work_symbol, s): s for s in pending}
            for future in as_completed(futures, timeout=max(0, deadline - time.monotonic())):
                check()
                symbol = futures[future]
                result = {**future.result(), 'identity': run['identity'],
                          'bound_delta_manifest_sha256': run['bound_delta_manifest_sha256']}
                validate_stock(result, symbol, run, bound, plan)
                atomic_json(result_dir / (symbol + '.json'), result)
                results[symbol] = result
                lines.append(json.dumps({'symbol': symbol,
                                         'checkpoint_sha256': sha(result_dir / (symbol + '.json'))}))
                atomic_progress(out / 'progress.jsonl', lines)
        except BaseException:
            stop_pool(pool)
            raise
        else:
            pool.shutdown(wait=True)
    check()
    facts = [d for s in scope['symbols'] for d in results[s]['days']]
    keys = [f"{d['day']}/{d['symbol']}" for d in facts]
    if (set(results) != set(scope['symbols']) or len(keys) != len(set(keys))
            or set(keys) != set(scope['expected_fact_keys'])):
        raise RuntimeError('incomplete exact fact coverage; no final tables')
    source = {kind: {field: [v for d in facts if d['provenance']['kind'] == kind for v in d[field]]
                      for field in ('verified_files', 'errors', 'missing')}
              for kind in ('reused', 'fresh')}
    ready = sum(core.flag(d['daily'].get('cash_ready')) is True for d in facts)
    complete = (ready == len(facts) and all(not s['errors'] and not s['missing'] for s in source.values())
                and sum(len(s['verified_files']) for s in source.values()) == 2 * len(facts))
    core.check_archive_stats(bound)
    core.check_cache_paths(bound, scope)
    check()
    write_daily(out / 'daily_inputs.csv', [d['daily'] for d in facts])
    atomic_json(out / 'source_verification.json', source)
    summary = {'mode': run['identity']['mode'], 'expected_symbols': len(scope['symbols']),
               'completed_symbols': len(results), 'expected_facts': len(scope['expected_fact_keys']),
               'completed_facts': len(facts), 'reused_facts': sum(d['provenance']['kind'] == 'reused' for d in facts),
               'fresh_facts': sum(d['provenance']['kind'] == 'fresh' for d in facts), 'ready_cash_facts': ready,
               'new_verified_files': len(source['fresh']['verified_files']),
               'new_missing_members': len(source['fresh']['missing']), 'new_errors': len(source['fresh']['errors']),
               'source_full_complete': complete, 'status': 'complete' if complete else 'complete_with_unknown',
               'formal_provider_or_forecast': False}
    check()
    atomic_json(out / 'summary.json', summary)
    return 0 if complete else 2


def run_daily(spec_path, output, mode, resume=False, full_gate=None):
    if mode not in ('smoke', 'full'):
        raise ValueError('invalid mode')
    spec_path = Path(spec_path).absolute()
    no_symlinks(spec_path)
    if sha(spec_path) != sha(ARTIFACT / 'daily_execution_spec.json'):
        raise ValueError('execution spec is not the frozen daily packet')
    gate = validate_full_gate(mode, full_gate, spec_path)  # Before payload or output creation.
    spec = load_json(spec_path)
    if (Path(spec['core_module_path']) != ROOT / 'experiments/l2_historical_cap_screen_v11.py'
            or Path(spec['old_runner_path']) != Path(old.__file__).resolve()):
        raise ValueError('core/old runner must be in this worktree')
    scope, plan = validate_scope(spec, mode)
    immutable = [spec_path, Path(__file__).resolve(), spec['core_module_path'], spec['old_runner_path'], spec['source_reader_path'],
                 spec['extract_helper_path'], spec['reuse_run_spec_path'], spec['reuse_bound_manifest_path'],
                 *spec['formation_input_pins'], *[ROOT / p for p in spec['analyzers']],
                 *[spec[m][k + '_path'] for m in ('smoke', 'full') for k in ('scope', 'plan')],
                 *[pin['checkpoint_path'] for pin in plan['reuse_facts'].values()]]
    if gate is not None:
        immutable += [Path(full_gate).absolute(), gate['smoke_receipt_path']]
    # Protect entire accepted output/cache trees, not just the selected checkpoint files.
    immutable += [spec['reuse_source_identity']['output'], spec['reuse_source_identity']['cache']]
    out = guard_paths(Path(output).absolute(), scope, immutable)
    for protected in immutable:
        p = Path(protected).resolve()
        for writable in (out, Path(scope['cache']).resolve()):
            if writable.is_relative_to(p):
                raise ValueError('writable path nested inside immutable input')
    if out.exists() and not resume:
        raise ValueError('output exists; explicit --resume required')
    if resume and not out.is_dir():
        raise ValueError('--resume requires an existing run')
    for path, expected in spec['formation_input_pins'].items():
        if sha(path) != expected:
            raise ValueError('formation input hash mismatch')
    if sha(spec['old_runner_path']) != spec['old_runner_sha256']:
        raise ValueError('old runner hash mismatch')
    core = support.import_pinned(spec['core_module_path'], spec['core_module_sha256'], 'delta_core_parent')
    core.import_pinned(spec['source_reader_path'], spec['reader_sha256'], 'delta_reader_parent')
    helper = core.import_pinned(spec['extract_helper_path'], spec['extract_helper_sha256'], 'delta_intake')
    *_, pins = core.load_analyzers()
    if pins != spec['analyzers']:
        raise ValueError('analyzer pins mismatch')
    verify_reuse(spec, plan)
    core.check_archive_stats(plan)
    core.check_cache_paths(plan, scope)
    identity = {'mode': mode, 'spec_path': str(spec_path), 'spec_sha256': sha(spec_path),
                'program_sha256': sha(__file__), 'core_sha256': spec['core_module_sha256'],
                'old_runner_sha256': spec['old_runner_sha256'], 'reader_sha256': spec['reader_sha256'],
                'extract_helper_sha256': spec['extract_helper_sha256'], 'analyzers': pins,
                'scope_plan_pins': spec[mode], 'input_pins': spec['formation_input_pins'],
                'reuse_run_spec_sha256': spec['reuse_run_spec_sha256'],
                'reuse_bound_manifest_sha256': spec['reuse_bound_manifest_sha256'],
                'reuse_source_identity': spec['reuse_source_identity'], 'parent_gate': gate,
                'output': str(out), 'cache': str(Path(scope['cache']).resolve())}
    run = {'identity': identity, 'effective_scope': scope}
    bound_path = out / 'bound_delta_manifest.json'
    if resume:
        saved = load_json(out / 'run_spec.json')
        if saved['identity'] != identity or saved['effective_scope'] != scope:
            raise ValueError('resume identity changed')
        run = saved
        if not bound_path.is_file() or sha(bound_path) != run.get('bound_delta_manifest_sha256'):
            raise ValueError('bound delta checkpoint identity changed or missing')
        bound = load_json(bound_path)
        validate_delta_bound(bound, plan, scope)
        reverify_cache(bound, scope)  # Never call extract on resume; lost caches are fatal.
    else:
        out.mkdir(parents=True)
        atomic_json(out / 'run_spec.json', run)
        bound = helper.extract(plan, scope, Path(scope['cache']))
        validate_delta_bound(bound, plan, scope)
        core.check_cache_paths(bound, scope)
        core.check_archive_stats(bound)
        atomic_json(bound_path, bound)
        run['bound_delta_manifest_sha256'] = sha(bound_path)
        atomic_json(out / 'run_spec.json', run)
    return analyze(out, run, bound, plan, core)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', default=str(ARTIFACT / 'daily_execution_spec.json'))
    parser.add_argument('--mode', choices=('smoke', 'full'), required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--full-gate')
    args = parser.parse_args(argv)
    return run_daily(args.spec, args.output, args.mode, args.resume, args.full_gate)


if __name__ == '__main__':
    raise SystemExit(main())
