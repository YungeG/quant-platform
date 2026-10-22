"""Synthetic fixtures only: no retained archives, payloads, or provider calls."""
import csv
import json
import zlib
from concurrent.futures import Future
from pathlib import Path
from types import SimpleNamespace

import pytest
from experiments import run_l2_ranking_cash_v12 as m

READER = '''import pandas as pd

def read_bound_v8(path, meta, day, symbol, kind, scope):
    if kind == '行情.csv':
        frame = pd.DataFrame([{'当日累计成交量':'50000','成交笔数':'2','成交价':'100000','当日成交额':'500000','ms':54000000}])
    else:
        frame = pd.DataFrame([{'成交代码':'0','成交价格':'100000','成交数量':'25000','叫买序号':'10','叫卖序号':str(i+1),'BS标志':'B','成交编号':str(i+1),'时间':'93000000','_source_record':i+1,'ms':34200000} for i in range(2)])
    return frame, {'member':meta['member'],'sha256':meta['sha256']}
'''
HELPER = '''import hashlib,json

def extract(plan, scope, cache):
    assert scope['calendar'] == ['20260907','20260908','20260909','20260910','20260911']
    assert len(scope['symbols']) == 8 and scope['workers'] == 2
    assert scope['extraction_timeout_seconds'] == 30 and scope['archive_timeout_seconds'] == 20
    members=[]
    for m in plan['members']:
        p=cache/m['member'];p.parent.mkdir(parents=True,exist_ok=True)
        if not p.exists():p.write_bytes(b'x')
        if p.read_bytes()!=b'x':raise ValueError('cache content changed')
        members.append({**m,'path':str(p),'sha256':hashlib.sha256(b'x').hexdigest()})
    digest=hashlib.sha256(json.dumps(sorted((m['member'],m['sha256']) for m in members),separators=(',',':')).encode()).hexdigest()
    return {**plan,'members':members,'selected_data_sha256':digest}
'''


def dump(path, value):
    path.write_text(json.dumps(value))


@pytest.fixture
def packet(tmp_path, monkeypatch):
    artifact = tmp_path / 'packet'
    artifact.mkdir()
    monkeypatch.setattr(m, 'ARTIFACT', artifact)
    source = tmp_path / 'source'
    (source / '202609').mkdir(parents=True)
    symbols = [f'{i:06d}.SZ' for i in range(1, 2513)]
    names = {s: 'synthetic' for s in symbols}
    basic = artifact / 'basic.csv'
    basic.write_text('synthetic metadata only')
    reader, helper = artifact / 'reader.py', artifact / 'helper.py'
    reader.write_text(READER)
    helper.write_text(HELPER)
    *_, analyzers = m.support.load_analyzers()
    spec = {'role': 'historical_cash_cohort_only_not_forecast_validation', 'asof': '20260911',
            'core_module_path': str(Path(m.support.__file__).resolve()),
            'core_module_sha256': m.sha(m.support.__file__),
            'source_reader_path': str(reader), 'reader_sha256': m.sha(reader),
            'extract_helper_path': str(helper), 'extract_helper_sha256': m.sha(helper),
            'analyzers': analyzers, 'input_pins': {str(basic): m.sha(basic)}}
    for mode, roster in [('smoke', symbols[:8]), ('full', symbols)]:
        scope = {'asof': '20260911', 'calendar': m.CALENDAR, 'dates': m.CALENDAR,
                 'symbols': roster, 'names': names, 'kinds': m.KINDS,
                 'source': str(source), 'cache': str(tmp_path / 'raw'),
                 'file_bytes_max': 1024, 'selected_bytes_max': 512*1024**2,
                 'involved_solid_bytes_max': 4*1024**3, 'workers': 2,
                 'extraction_timeout_seconds': 30, 'archive_timeout_seconds': 20,
                 'analysis_timeout_seconds': 60}
        spath = artifact / (mode + '_scope.json')
        dump(spath, scope)
        archives, members, missing = [], [], []
        for day in m.CALENDAR:
            archive = source / '202609' / (day + '.7z')
            if not archive.exists():
                archive.write_bytes(b'not an archive; never extracted')
            st = archive.stat()
            archives.append({'path': str(archive), 'day': day, 'bytes': st.st_size,
                             'mtime_ns': st.st_mtime_ns, 'selected_member_count': 16,
                             'selected_bytes': 16, 'involved_solid_uncompressed_bytes': 16})
            members.extend({'archive': str(archive), 'member': f'{day}/{s}/{k}', 'bytes': 1,
                            'crc32': f'{zlib.crc32(b"x"):08x}', 'block': '0'} for s in roster[:8] for k in m.KINDS)
            missing.extend(f'{day}/{s}/{k}' for s in roster[8:] for k in m.KINDS)
        inv = {'asof': '20260911', 'dates': m.CALENDAR, 'symbols': len(roster),
               'scope_sha256': m.sha(spath), 'members': members, 'missing_members': missing,
               'archives': archives, 'selected_bytes': 80, 'involved_solid_bytes': 80}
        ipath = artifact / (mode + '_inventory.json')
        dump(ipath, inv)
        spec[mode] = {'scope_path': str(spath), 'scope_sha256': m.sha(spath),
                      'inventory_path': str(ipath), 'inventory_sha256': m.sha(ipath)}
    path = artifact / 'cash_execution_spec.json'
    dump(path, spec)
    return SimpleNamespace(spec=spec, path=path, tmp=tmp_path, artifact=artifact)


def repin(packet, mode, kind, value):
    path = Path(packet.spec[mode][kind + '_path'])
    dump(path, value)
    packet.spec[mode][kind + '_sha256'] = m.sha(path)
    dump(packet.path, packet.spec)


def args(packet, name='out'):
    return ['--spec', str(packet.path), '--mode', 'smoke', '--output', str(packet.tmp / name)]


def test_own_smoke_scope_hash_and_bounded_effective_scope(packet):
    scope, inv = m.validate_scope(packet.spec, 'smoke', m.support)
    assert inv['scope_sha256'] == packet.spec['smoke']['scope_sha256']
    assert inv['scope_sha256'] != packet.spec['full']['scope_sha256']
    assert len(scope['symbols']) == 8 and len(inv['members']) == 80
    assert scope['calendar'] == m.CALENDAR and scope['workers'] == 2
    assert scope['extraction_timeout_seconds'] == 30
    packet.spec['smoke']['scope_sha256'] = packet.spec['full']['scope_sha256']
    with pytest.raises(ValueError, match='hash mismatch'):
        m.validate_scope(packet.spec, 'smoke', m.support)


@pytest.mark.parametrize('field,value', [('workers', 3), ('analysis_timeout_seconds', 601),
                                        ('extraction_timeout_seconds', 601), ('archive_timeout_seconds', 301),
                                        ('file_bytes_max', 256*1024**2+1), ('workers', True),
                                        ('selected_bytes_max', 512*1024**2+1),
                                        ('involved_solid_bytes_max', 4*1024**3+1)])
def test_budget_rejected_before_payload(packet, field, value):
    scope = m.load_json(packet.spec['smoke']['scope_path'])
    scope[field] = value
    repin(packet, 'smoke', 'scope', scope)
    inv = m.load_json(packet.spec['smoke']['inventory_path'])
    inv['scope_sha256'] = packet.spec['smoke']['scope_sha256']
    repin(packet, 'smoke', 'inventory', inv)
    with pytest.raises(ValueError, match='budget'):
        m.main(args(packet))
    assert not (packet.tmp / 'out').exists()


def test_full_gate_before_scope_or_extraction(packet, monkeypatch):
    monkeypatch.setattr(m, 'validate_scope', lambda *a: pytest.fail('scope reached before gate'))
    argv = args(packet)
    argv[argv.index('smoke')] = 'full'
    with pytest.raises(ValueError, match='full-gate'):
        m.main(argv)
    receipt = packet.tmp / 'synthetic_receipt.json'
    receipt.write_text('{}')
    good = {'role': 'parent_smoke_accepted', 'execution_spec_sha256': m.sha(packet.path),
            'program_sha256': m.sha(m.__file__), 'smoke_receipt_path': str(receipt),
            'smoke_receipt_sha256': m.sha(receipt)}
    gatepath = packet.tmp / 'synthetic_gate.json'
    for update in ({'extra': 1}, {'program_sha256': '0'*64}, {'execution_spec_sha256': '0'*64},
                   {'smoke_receipt_path': 'relative'}, {'smoke_receipt_sha256': '0'*64},
                   {'role': 'child_accepted'}):
        dump(gatepath, {**good, **update})
        with pytest.raises(ValueError, match='parent smoke'):
            m.main(argv + ['--full-gate', str(gatepath)])
    dump(gatepath, good)
    assert m.validate_full_gate('full', gatepath, packet.path)['role'] == 'parent_smoke_accepted'
    assert not (packet.tmp / 'out').exists()


@pytest.mark.parametrize('pair', [('output', 'source'), ('output', 'cache'), ('source', 'cache')])
@pytest.mark.parametrize('direction', [0, 1])
def test_bidirectional_isolation(packet, pair, direction):
    scope, _ = m.validate_scope(packet.spec, 'smoke', m.support)
    paths = {'source': scope['source'], 'cache': scope['cache'], 'output': str(packet.tmp / 'out')}
    a, b = pair if direction == 0 else pair[::-1]
    paths[a] = str(Path(paths[b]) / 'nested')
    with pytest.raises(ValueError, match='isolated'):
        m.guard_paths(paths['output'], {**scope, 'source': paths['source'], 'cache': paths['cache']}, [])


def test_symlinks_and_immutable_inputs(packet):
    scope, inv = m.validate_scope(packet.spec, 'smoke', m.support)
    link = packet.tmp / 'link'
    link.symlink_to(packet.tmp / 'absent')
    with pytest.raises(ValueError, match='symlink'):
        m.guard_paths(link / 'out', scope, [])
    with pytest.raises(ValueError, match='immutable'):
        m.guard_paths(packet.artifact, scope, [packet.path])
    cache = Path(scope['cache'])
    cache.mkdir()
    (cache / m.CALENDAR[0]).symlink_to(packet.tmp / 'absent')
    with pytest.raises(ValueError, match='symlink'):
        m.support.check_cache_paths(inv, scope)


@pytest.mark.parametrize('pin', ['core_module_sha256', 'reader_sha256', 'extract_helper_sha256', 'input', 'analyzers'])
def test_pins_fail_before_output(packet, pin):
    if pin == 'input':
        packet.spec['input_pins'][next(iter(packet.spec['input_pins']))] = '0'*64
    elif pin == 'analyzers':
        packet.spec['analyzers'][next(iter(packet.spec['analyzers']))] = '0'*64
    else:
        packet.spec[pin] = '0'*64
    dump(packet.path, packet.spec)
    with pytest.raises(ValueError, match='hash mismatch|pins mismatch'):
        m.main(args(packet))
    assert not (packet.tmp / 'out').exists()


def test_two_worker_cli_complete_fields_and_resume(packet):
    assert m.main(args(packet)) == 0
    out = packet.tmp / 'out'
    summary = m.load_json(out / 'summary.json')
    assert summary == {'asof': '20260911', 'mode': 'smoke', 'status': 'complete',
                       'expected_symbols': 8, 'completed_symbols': 8, 'stock_days': 40,
                       'complete_cash_profiles': 8, 'verified_files': 80, 'errors': 0, 'missing': 0,
                       'source_full_complete': True, 'formal_provider_or_forecast': False}
    rows = list(csv.DictReader((out / 'profiles.csv').open()))
    assert all(r['group_difference_1e4'] == '25000000000' and r['class'] == 'A' for r in rows)
    assert len(list(csv.DictReader((out / 'daily_inputs.csv').open()))) == 40
    checkpoints = list((out / 'stock_results').glob('*.json'))
    before = {p.name: (m.sha(p), p.stat().st_mtime_ns) for p in checkpoints}
    for p in checkpoints:
        result = m.load_json(p)
        assert result['band_cells'] and result['diagnostics'] and len(result['markets']) == 5
        assert 'raw_source_close19' not in result and result['raw_source_last_at_cutoff'] == 100000
    assert m.main(args(packet) + ['--resume']) == 0
    assert before == {p.name: (m.sha(p), p.stat().st_mtime_ns) for p in checkpoints}
    assert len((out / 'progress.jsonl').read_text().splitlines()) == 8
    assert not (out / 'candidates.csv').exists()
    with pytest.raises(ValueError, match='explicit --resume'):
        m.main(args(packet))
    saved = m.load_json(out / 'run_spec.json')
    for key in saved['identity']:
        changed = json.loads(json.dumps(saved))
        changed['identity'][key] = 'changed'
        dump(out / 'run_spec.json', changed)
        with pytest.raises(ValueError, match='resume identity'):
            m.main(args(packet) + ['--resume'])
    dump(out / 'run_spec.json', saved)
    cached = Path(m.load_json(out / 'bound_manifest.json')['members'][0]['path'])
    cached.write_bytes(b'y')
    with pytest.raises(ValueError, match='cache content'):
        m.main(args(packet) + ['--resume'])
    cached.unlink()
    with pytest.raises(ValueError, match='cache content'):
        m.main(args(packet) + ['--resume'])
    assert not cached.exists()
    assert before == {p.name: (m.sha(p), p.stat().st_mtime_ns) for p in checkpoints}


def test_missing_day_mask_and_status_two(packet):
    inv = m.load_json(packet.spec['smoke']['inventory_path'])
    missing = inv['members'].pop(0)
    inv['missing_members'].append(missing['member'])
    inv['selected_bytes'] -= 1
    inv['archives'][0]['selected_bytes'] -= 1
    inv['archives'][0]['selected_member_count'] -= 1
    repin(packet, 'smoke', 'inventory', inv)
    assert m.main(args(packet)) == 2
    out = packet.tmp / 'out'
    result = m.load_json(out / 'stock_results' / '000001.SZ.json')
    assert m.support.classify_profile(result['profile']) == 'D'
    assert result['daily'][0]['buy'] is None and not result['daily'][0]['cash_ready']
    summary = m.load_json(out / 'summary.json')
    assert summary['stock_days'] == 40 and summary['completed_symbols'] == 8
    assert summary['missing'] == 1 and not summary['source_full_complete']
    assert summary['complete_cash_profiles'] == 7


@pytest.mark.parametrize('failure', ['ValueError', 'KeyError'])
def test_source_error_vs_programming_exception(packet, failure):
    reader = Path(packet.spec['source_reader_path'])
    reader.write_text(READER.replace("    if kind == '行情.csv':", f"    raise {failure}('synthetic failure')\n    if kind == '行情.csv':"))
    packet.spec['reader_sha256'] = m.sha(reader)
    dump(packet.path, packet.spec)
    if failure == 'KeyError':
        with pytest.raises(KeyError, match='synthetic failure'):
            m.main(args(packet))
        assert not (packet.tmp / 'out' / 'summary.json').exists()
    else:
        assert m.main(args(packet)) == 2
        summary = m.load_json(packet.tmp / 'out' / 'summary.json')
        assert summary['errors'] == 80 and summary['complete_cash_profiles'] == 0
        assert summary['stock_days'] == 40 and not summary['source_full_complete']


def test_exact_money_uses_retained_core():
    n = 2**53 + 31
    wide = dict(zip(m.support.CASH_KEYS.values(), (str(n), '1', str(n), '1', '0', '0', '0', '0')))
    result = m.support.daily_record('000001.SZ', m.CALENDAR[-1],
                                    {'cash_fact_ready': True, 'observed_amount_1e4': n}, wide)
    assert type(result['buy']) is int and result['buy'] == n
    assert result['market_amount'] == n


def test_partial_progress_preserved_and_resumed(packet, monkeypatch):
    real_pool, real_completed = m.ProcessPoolExecutor, m.as_completed
    class Pool:
        _processes = {}
        def __init__(self, max_workers, initializer, initargs):
            assert max_workers == 2
            self.count = 0
            initializer(*initargs)
        def submit(self, fn, symbol):
            self.count += 1
            future = Future()
            if self.count == 2:
                future.set_exception(RuntimeError('unexpected worker error'))
            else:
                future.set_result(fn(symbol))
            return future
        def shutdown(self, **kwargs):
            pass
    monkeypatch.setattr(m, 'ProcessPoolExecutor', Pool)
    monkeypatch.setattr(m, 'as_completed', lambda futures, timeout: iter(futures))
    with pytest.raises(RuntimeError, match='unexpected worker error'):
        m.main(args(packet))
    out = packet.tmp / 'out'
    checkpoint = out / 'stock_results' / '000001.SZ.json'
    before = (m.sha(checkpoint), checkpoint.stat().st_mtime_ns)
    assert len(list((out / 'stock_results').glob('*.json'))) == 1
    assert len((out / 'progress.jsonl').read_text().splitlines()) == 1
    assert not (out / 'summary.json').exists()
    monkeypatch.setattr(m, 'ProcessPoolExecutor', real_pool)
    monkeypatch.setattr(m, 'as_completed', real_completed)
    # Simulate the atomic checkpoint committed just before the progress receipt.
    (out / 'progress.jsonl').write_text('')
    assert m.main(args(packet) + ['--resume']) == 0
    assert before == (m.sha(checkpoint), checkpoint.stat().st_mtime_ns)
    assert len((out / 'progress.jsonl').read_text().splitlines()) == 8


def test_interrupted_progress_temp_does_not_block_valid_resume(packet):
    assert m.main(args(packet)) == 0
    out = packet.tmp / 'out'
    checkpoints = list((out / 'stock_results').glob('*.json'))
    before = {p.name: (m.sha(p), p.stat().st_mtime_ns) for p in checkpoints}
    stale = out / 'progress.jsonl.tmp'
    stale.write_text('{interrupted progress write')
    (out / 'progress.jsonl').write_text('')
    assert m.main(args(packet) + ['--resume']) == 0
    assert stale.read_text() == '{interrupted progress write'
    assert before == {p.name: (m.sha(p), p.stat().st_mtime_ns) for p in checkpoints}
    assert len((out / 'progress.jsonl').read_text().splitlines()) == 8


def test_deadline_stops_workers_without_waiting(packet, monkeypatch):
    calls = []
    class Process:
        def terminate(self): calls.append('terminate')
        def join(self, timeout): calls.append(('join', timeout))
        def is_alive(self): return True
        def kill(self): calls.append('kill')
    class Pool:
        _processes = {1: Process(), 2: Process()}
        def __init__(self, **kwargs): pass
        def submit(self, *a): return Future()
        def shutdown(self, **kwargs): calls.append(kwargs)
    def timeout(*a, **kw):
        raise TimeoutError('synthetic deadline')
    monkeypatch.setattr(m, 'ProcessPoolExecutor', Pool)
    monkeypatch.setattr(m, 'as_completed', timeout)
    with pytest.raises(TimeoutError, match='deadline'):
        m.main(args(packet))
    assert calls.count('terminate') == calls.count('kill') == 2
    assert calls[-1] == {'wait': False, 'cancel_futures': True}
    assert not (packet.tmp / 'out' / 'summary.json').exists()


def test_resume_rejects_checkpoint_matrix_and_detail_loss(packet):
    assert m.main(args(packet)) == 0
    out = packet.tmp / 'out'
    run = m.load_json(out / 'run_spec.json')
    bound = m.load_json(out / 'bound_manifest.json')
    result = m.load_json(out / 'stock_results' / '000001.SZ.json')
    for key in ('daily', 'observations', 'markets', 'verified_files'):
        changed = json.loads(json.dumps(result))
        changed[key].pop()
        with pytest.raises(ValueError, match='coverage|gap'):
            m.validate_stock(changed, result['symbol'], run, bound)
    for key in ('band_cells', 'diagnostics', 'errors', 'missing'):
        changed = json.loads(json.dumps(result))
        changed[key] = None
        with pytest.raises(ValueError, match='detail array'):
            m.validate_stock(changed, result['symbol'], run, bound)


@pytest.mark.parametrize('mutation', ['crc', 'totals', 'missing', 'foreign', 'scope'])
def test_inventory_rejected_before_extraction(packet, mutation):
    inv = m.load_json(packet.spec['smoke']['inventory_path'])
    if mutation == 'crc': inv['members'][0]['crc32'] = 'bad'
    if mutation == 'totals': inv['selected_bytes'] += 1
    if mutation == 'missing': inv['members'].pop()
    if mutation == 'foreign': inv['members'][0]['member'] = '../escape'
    if mutation == 'scope': inv['scope_sha256'] = packet.spec['full']['scope_sha256']
    repin(packet, 'smoke', 'inventory', inv)
    with pytest.raises(ValueError):
        m.main(args(packet))
    assert not (packet.tmp / 'out').exists()


def test_unready_profile_without_source_errors_is_not_success(packet):
    assert m.main(args(packet)) == 0
    out = packet.tmp / 'out'
    checkpoint = out / 'stock_results' / '000001.SZ.json'
    result = m.load_json(checkpoint)
    result['profile']['cash_window_ready'] = False
    assert not result['errors'] and not result['missing']
    dump(checkpoint, result)
    (out / 'progress.jsonl').write_text('')
    run = m.load_json(out / 'run_spec.json')
    bound = m.load_json(out / 'bound_manifest.json')
    assert m.analyze(out, run, bound, m.support) == 2
    summary = m.load_json(out / 'summary.json')
    assert summary['stock_days'] == 40 and summary['complete_cash_profiles'] == 7
    assert not summary['source_full_complete'] and summary['status'] == 'complete_with_unknown'


def test_bound_checkpoint_identity_and_foreign_error_masks(packet):
    assert m.main(args(packet)) == 0
    out = packet.tmp / 'out'
    run = m.load_json(out / 'run_spec.json')
    bound = m.load_json(out / 'bound_manifest.json')
    result = m.load_json(out / 'stock_results' / '000001.SZ.json')
    result['errors'] = [{'symbol': 'other', 'day': m.CALENDAR[0], 'kind': m.KINDS[0]}]
    with pytest.raises(ValueError, match='error mask'):
        m.validate_stock(result, result['symbol'], run, bound)
    bound['selected_data_sha256'] = '0'*64
    dump(out / 'bound_manifest.json', bound)
    with pytest.raises(ValueError, match='bound checkpoint identity'):
        m.main(args(packet) + ['--resume'])


@pytest.mark.parametrize('exception', ["ValueError('source content mismatch')",
                                      "ValueError('source file changed during read')",
                                      "ValueError('not a regular source file')",
                                      "OSError('synthetic cache removed')"])
def test_worker_cache_identity_failure_is_fatal_not_source_unknown(packet, exception):
    reader = Path(packet.spec['source_reader_path'])
    reader.write_text('def read_bound_v8(*args):\n    raise ' + exception + '\n')
    packet.spec['reader_sha256'] = m.sha(reader)
    dump(packet.path, packet.spec)
    with pytest.raises(RuntimeError, match='bound cache'):
        m.main(args(packet))
    assert not (packet.tmp / 'out' / 'summary.json').exists()
