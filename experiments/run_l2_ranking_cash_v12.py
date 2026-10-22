"""Bounded 20260911 cash cohort only; no rankings, outcomes, or forecasts."""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from uuid import uuid4

from experiments import l2_historical_cap_screen_v11 as support

ARTIFACT = Path('/srv/bcache-8t/ygguo/quant/l2-ranking-comparison-v12')
ROOT = Path(__file__).resolve().parents[1]
CALENDAR = ['20260907', '20260908', '20260909', '20260910', '20260911']
KINDS = ['行情.csv', '逐笔成交.csv']
sha = support.sha
load_json = support.load_json
atomic_json = support.atomic_json


def no_symlinks(path):
    path = Path(path)
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('symlink forbidden: ' + str(path))


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


def validate_scope(spec, mode, core):
    binding = spec[mode]
    for kind in ('scope', 'inventory'):
        no_symlinks(binding[kind + '_path'])
        if sha(binding[kind + '_path']) != binding[kind + '_sha256']:
            raise ValueError(mode + ' ' + kind + ' hash mismatch')
    scope = load_json(binding['scope_path'])
    inv = load_json(binding['inventory_path'])
    symbols = scope['symbols']
    if (scope['asof'] != '20260911' or spec['asof'] != '20260911'
            or scope['calendar'] != CALENDAR or scope['dates'] != CALENDAR
            or scope['kinds'] != KINDS or inv['dates'] != CALENDAR
            or inv['asof'] != scope['asof'] or inv['scope_sha256'] != binding['scope_sha256']
            or inv['symbols'] != len(symbols) or len(set(symbols)) != len(symbols)
            or len(symbols) != (8 if mode == 'smoke' else 2512)
            or any(not re.fullmatch(r'[0-9]{6}\.(?:SH|SZ)', s) for s in symbols)
            or any(s not in scope['names'] for s in symbols)):
        raise ValueError('cash scope/inventory identity mismatch')
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
    effective = {**scope, 'role': spec['role'],
                 **{k: spec[k] for k in ('source_reader_path', 'reader_sha256',
                                         'extract_helper_path', 'extract_helper_sha256',
                                         'core_module_path', 'core_module_sha256')}}
    core.validate_members(inv, effective)
    for archive in inv['archives']:
        no_symlinks(archive['path'])
    return effective, inv


def guard_paths(output, scope, immutable):
    paths = [Path(output), Path(scope['source']), Path(scope['cache'])]
    for p in [*paths, *map(Path, immutable)]:
        if not p.is_absolute():
            raise ValueError('absolute paths required')
        no_symlinks(p)
    out, source, cache = [p.resolve() for p in paths]
    for a, b in ((out, source), (out, cache), (source, cache)):
        if a.is_relative_to(b) or b.is_relative_to(a):
            raise ValueError('source/raw/output must be isolated in both directions')
    for p in map(Path, immutable):
        if p.resolve().is_relative_to(out) or p.resolve().is_relative_to(cache):
            raise ValueError('writable path contains immutable input')
    if out.exists():
        for p in out.rglob('*'):
            no_symlinks(p)
    return out


_STATE = None


class BoundReader:
    """Keep cache identity failures fatal across core's day-source error mask."""
    def __init__(self, reader):
        self.reader = reader

    def read_bound_v8(self, *args):
        try:
            return self.reader.read_bound_v8(*args)
        except OSError as exc:
            raise RuntimeError('bound cache unavailable') from exc
        except ValueError as exc:
            # These exact messages belong to the pinned v8 byte/path checks;
            # malformed source rows/headers remain core-handled source failures.
            if str(exc) in ('source content mismatch', 'source file changed during read',
                            'not a regular source file'):
                raise RuntimeError('bound cache identity changed') from exc
            raise


def init_worker(run_path, bound_path, deadline):
    """Load pinned code and bound metadata once per worker, never per stock."""
    global _STATE
    run = load_json(run_path)
    identity, scope = run['identity'], run['effective_scope']
    if sha(__file__) != identity['program_sha256'] or sha(bound_path) != run['bound_manifest_sha256']:
        raise ValueError('worker program/bound identity changed')
    core = support.import_pinned(scope['core_module_path'], identity['core_sha256'], 'cash_core')
    reader = core.import_pinned(scope['source_reader_path'], identity['reader_sha256'], 'cash_reader')
    v4, v3, v6, pins = core.load_analyzers()
    if pins != identity['analyzers']:
        raise ValueError('worker analyzer identity changed')
    bound = load_json(bound_path)
    _STATE = (core, scope, {m['member']: m for m in bound['members']}, BoundReader(reader), v4, v3, v6, deadline)


def work_symbol(symbol):
    core, scope, metas, reader, v4, v3, v6, deadline = _STATE
    result = core.process_symbol(symbol, scope, metas, reader, v4, v3, v6, deadline)
    # The old key names the old calendar, not the value's actual supplied cutoff.
    result['raw_source_last_at_cutoff'] = result.pop('raw_source_close19')
    return result


def validate_stock(result, symbol, run, bound):
    scope = run['effective_scope']
    if (result['symbol'] != symbol or result['identity'] != run['identity']
            or result['bound_manifest_sha256'] != run['bound_manifest_sha256']
            or 'raw_source_close19' in result or 'raw_source_last_at_cutoff' not in result
            or not isinstance(result['profile'], dict)):
        raise ValueError('stock checkpoint identity mismatch')
    expected = [(symbol, d) for d in scope['calendar']]
    for key in ('daily', 'observations'):
        if [(d['symbol'], d['day']) for d in result[key]] != expected:
            raise ValueError('stock checkpoint exact day coverage mismatch')
    for key in ('band_cells', 'diagnostics', 'markets', 'verified_files', 'errors', 'missing'):
        if not isinstance(result[key], list):
            raise ValueError('stock checkpoint detail array missing: ' + key)
    if len(result['markets']) != len(expected):
        raise ValueError('stock checkpoint market coverage mismatch')
    for error in result['errors']:
        if (error.get('symbol') != symbol or error.get('day') not in scope['calendar']
                or error.get('kind') not in (*scope['kinds'], 'analysis', 'cash_numeric', 'cash_gate')):
            raise ValueError('stock checkpoint foreign error mask')
    members = {f'{d}/{symbol}/{k}' for d in scope['calendar'] for k in scope['kinds']}
    absent = members & set(bound['missing_members'])
    if set(result['missing']) != absent or len(result['missing']) != len(absent):
        raise ValueError('stock checkpoint missing-member mismatch')
    verified = [m['member'] for m in result['verified_files']]
    if len(verified) != len(set(verified)) or not set(verified) <= members - absent:
        raise ValueError('stock checkpoint verified coverage mismatch')
    metas = {m['member']: m for m in bound['members']}
    for detail in result['verified_files']:
        if detail.get('sha256') != metas[detail['member']]['sha256']:
            raise ValueError('stock checkpoint verified hash mismatch')
    if not result['errors'] and set(verified) != members - absent:
        raise ValueError('stock checkpoint unexplained source gap')


def sync_progress(out, results):
    """Parent-only atomic log replacement; recover checkpoint-before-log crashes."""
    path = out / 'progress.jsonl'
    lines = path.read_text().splitlines() if path.exists() else []
    seen = set()
    for line in lines:
        entry = json.loads(line)
        symbol = entry['symbol']
        if (symbol not in results or symbol in seen
                or entry['checkpoint_sha256'] != sha(out / 'stock_results' / (symbol + '.json'))):
            raise ValueError('progress/checkpoint identity mismatch')
        seen.add(symbol)
    for symbol in sorted(set(results) - seen):
        lines.append(json.dumps({'symbol': symbol,
                                'checkpoint_sha256': sha(out / 'stock_results' / (symbol + '.json'))}))
    atomic_progress(path, lines)
    return lines


def atomic_progress(path, lines):
    # Preserve abandoned writes as evidence; a new unique temp cannot block resume.
    tmp = path.with_name(path.name + '.' + uuid4().hex + '.tmp')
    with tmp.open('x') as f:
        f.write(''.join(line + '\n' for line in lines))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def stop_pool(pool):
    # Python <3.14: terminate, then kill stragglers without an unbounded shutdown wait.
    processes = list(pool._processes.values())
    for process in processes:
        process.terminate()
    for process in processes:
        process.join(timeout=0.1)
        if process.is_alive():
            process.kill()
    pool.shutdown(wait=False, cancel_futures=True)


def analyze(out, run, bound, core):
    scope = run['effective_scope']
    deadline = time.monotonic() + scope['analysis_timeout_seconds']
    def check_deadline():
        if time.monotonic() >= deadline:
            raise TimeoutError('cash analysis deadline exceeded')
    result_dir = out / 'stock_results'
    result_dir.mkdir(exist_ok=True)
    results = {}
    for path in result_dir.iterdir():
        check_deadline()
        if path.suffix != '.json' or path.stem not in scope['symbols'] or not path.is_file():
            raise ValueError('foreign/partial stock checkpoint')
        result = load_json(path)
        validate_stock(result, path.stem, run, bound)
        results[path.stem] = result
    progress_lines = sync_progress(out, results)
    pending = [s for s in scope['symbols'] if s not in results]
    if pending:
        pool = ProcessPoolExecutor(max_workers=scope['workers'], initializer=init_worker,
                                   initargs=(out / 'run_spec.json', out / 'bound_manifest.json', deadline))
        try:
            futures = {pool.submit(work_symbol, s): s for s in pending}
            for future in as_completed(futures, timeout=max(0, deadline - time.monotonic())):
                check_deadline()
                symbol = futures[future]
                result = {**future.result(), 'identity': run['identity'],
                          'bound_manifest_sha256': run['bound_manifest_sha256']}
                validate_stock(result, symbol, run, bound)
                atomic_json(result_dir / (symbol + '.json'), result)
                results[symbol] = result
                progress_lines.append(json.dumps({'symbol': symbol,
                                                  'checkpoint_sha256': sha(result_dir / (symbol + '.json'))}))
                atomic_progress(out / 'progress.jsonl', progress_lines)
        except BaseException:
            stop_pool(pool)
            raise
        else:
            pool.shutdown(wait=True)
    check_deadline()
    if set(results) != set(scope['symbols']):
        raise RuntimeError('incomplete universe; no final tables')
    ordered = [results[s] for s in scope['symbols']]
    daily = [d for r in ordered for d in r['daily']]
    if [(d['symbol'], d['day']) for d in daily] != [(s, d) for s in scope['symbols'] for d in CALENDAR]:
        raise RuntimeError('incomplete stock-day matrix')
    source = {k: [item for r in ordered for item in r[k]] for k in ('verified_files', 'errors', 'missing')}
    profiles = [{**r['profile'], 'symbol': r['symbol'], 'asof': scope['asof'],
                 'class': core.classify_profile(r['profile']),
                 'raw_source_last_at_cutoff': r['raw_source_last_at_cutoff']} for r in ordered]
    ready = sum(core.flag(r['profile'].get('cash_window_ready')) is True for r in ordered)
    source_complete = (not source['errors'] and not source['missing']
                       and len(source['verified_files']) == len(scope['symbols']) * len(CALENDAR) * len(KINDS)
                       and all(core.flag(d.get('cash_ready')) is True for d in daily)
                       and ready == len(ordered))
    success = source_complete
    core.check_archive_stats(bound)
    core.check_cache_paths(bound, scope)
    check_deadline()
    core.write_csv(out / 'daily_inputs.csv', daily)
    core.write_csv(out / 'profiles.csv', profiles)
    atomic_json(out / 'source_verification.json', source)
    summary = {'asof': scope['asof'], 'mode': run['identity']['mode'],
               'status': 'complete' if success else 'complete_with_unknown',
               'expected_symbols': len(scope['symbols']), 'completed_symbols': len(ordered),
               'stock_days': len(daily), 'complete_cash_profiles': ready,
               'verified_files': len(source['verified_files']), 'errors': len(source['errors']),
               'missing': len(source['missing']), 'source_full_complete': source_complete,
               'formal_provider_or_forecast': False}
    check_deadline()
    atomic_json(out / 'summary.json', summary)
    return 0 if success else 2


def run_cash(spec_path, output, mode, resume=False, full_gate=None):
    if mode not in ('smoke', 'full'):
        raise ValueError('invalid mode')
    spec_path = Path(spec_path).absolute()
    no_symlinks(spec_path)
    if sha(spec_path) != sha(ARTIFACT / 'cash_execution_spec.json'):
        raise ValueError('execution spec is not the frozen cash packet')
    gate = validate_full_gate(mode, full_gate, spec_path)  # Before any extraction or output creation.
    spec = load_json(spec_path)
    if Path(spec['core_module_path']).resolve() != ROOT / 'experiments/l2_historical_cap_screen_v11.py':
        raise ValueError('core must be in this worktree')
    no_symlinks(spec['core_module_path'])
    core = support.import_pinned(spec['core_module_path'], spec['core_module_sha256'], 'cash_core_parent')
    scope, inv = validate_scope(spec, mode, core)
    immutable = [spec_path, spec['core_module_path'], spec['source_reader_path'], spec['extract_helper_path'],
                 *spec['input_pins'], *[ROOT / p for p in spec['analyzers']],
                 *[spec[m][k + '_path'] for m in ('smoke', 'full') for k in ('scope', 'inventory')]]
    out = guard_paths(Path(output).absolute(), scope, immutable)
    if out.exists() and not resume:
        raise ValueError('output exists; explicit --resume required')
    if resume and not out.is_dir():
        raise ValueError('--resume requires an existing run')
    for path, expected in spec['input_pins'].items():
        if sha(path) != expected:
            raise ValueError('formation input hash mismatch')
    reader = core.import_pinned(spec['source_reader_path'], spec['reader_sha256'], 'cash_reader_parent')
    del reader
    helper = core.import_pinned(spec['extract_helper_path'], spec['extract_helper_sha256'], 'cash_intake')
    *_, pins = core.load_analyzers()
    if pins != spec['analyzers']:
        raise ValueError('analyzer pins mismatch')
    identity = {'mode': mode, 'spec_sha256': sha(spec_path), 'program_sha256': sha(__file__),
                'core_sha256': spec['core_module_sha256'], 'reader_sha256': spec['reader_sha256'],
                'extract_helper_sha256': spec['extract_helper_sha256'], 'analyzers': pins,
                'scope_inventory_pins': spec[mode], 'input_pins': spec['input_pins'],
                'parent_gate': gate, 'output': str(out), 'cache': str(Path(scope['cache']).resolve())}
    run = {'identity': identity, 'effective_scope': scope}
    if resume:
        saved = load_json(out / 'run_spec.json')
        if saved['identity'] != identity or saved['effective_scope'] != scope:
            raise ValueError('resume identity changed')
        run = saved
    else:
        out.mkdir(parents=True)
        atomic_json(out / 'run_spec.json', run)
    core.check_archive_stats(inv)
    core.check_cache_paths(inv, scope)
    bound_path = out / 'bound_manifest.json'
    if bound_path.exists():
        if not resume or sha(bound_path) != run.get('bound_manifest_sha256'):
            raise ValueError('bound checkpoint identity changed')
        bound = load_json(bound_path)
        core.validate_bound(bound, inv, scope)
        # Never regenerate a lost cache member when resuming completed checkpoints.
        for meta in bound['members']:
            p = Path(meta['path'])
            if not p.is_file() or p.stat().st_size != meta['bytes'] or sha(p) != meta['sha256']:
                raise ValueError('resume cache content changed or missing')
        current = helper.extract(inv, scope, Path(scope['cache']))
        core.validate_bound(current, inv, scope)
        if current['selected_data_sha256'] != bound['selected_data_sha256']:
            raise ValueError('resume cache content changed')
    else:
        if run.get('bound_manifest_sha256') or (out / 'stock_results').exists():
            raise ValueError('bound checkpoint missing')
        bound = helper.extract(inv, scope, Path(scope['cache']))
        core.validate_bound(bound, inv, scope)
        core.check_cache_paths(inv, scope)
        atomic_json(bound_path, bound)
        run['bound_manifest_sha256'] = sha(bound_path)
        atomic_json(out / 'run_spec.json', run)
    return analyze(out, run, bound, core)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', default=str(ARTIFACT / 'cash_execution_spec.json'))
    parser.add_argument('--mode', choices=('smoke', 'full'), required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--full-gate')
    args = parser.parse_args(argv)
    return run_cash(args.spec, args.output, args.mode, args.resume, args.full_gate)


if __name__ == '__main__':
    raise SystemExit(main())
