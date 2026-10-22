"""SYNTHETIC packets only: no actual archives, cash runs, gates, or providers."""
import copy
import csv
import json
import zlib
from concurrent.futures import Future
from pathlib import Path
from types import SimpleNamespace

import pytest
from experiments import l2_cash_daily_delta_v15 as m

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
    assert len(scope['symbols']) == 8 and scope['workers'] == 2
    assert len(plan['expected_fresh_fact_keys']) == 40
    assert len(plan['reuse_facts']) == 35
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
    path.write_text(json.dumps(value, ensure_ascii=False))


@pytest.fixture
def packet(tmp_path, monkeypatch):
    artifact = tmp_path / 'packet'
    artifact.mkdir()
    monkeypatch.setattr(m, 'ARTIFACT', artifact)
    source = tmp_path / 'source'
    (source / '202609').mkdir(parents=True)
    oldout = tmp_path / 'accepted_old'
    stocks = oldout / 'stock_results'
    stocks.mkdir(parents=True)
    oldcache = tmp_path / 'OLD_CACHE_DO_NOT_OPEN'
    symbols = [f'{i:06d}.SZ' for i in range(1, 9)]
    oldcalendar = m.CALENDAR[4:9]
    freshdays = m.CALENDAR[:4] + [m.CALENDAR[-1]]
    expected = sorted([f'{d}/{s}' for s in symbols for d in (m.CALENDAR if s != symbols[-1] else freshdays)])
    fresh = sorted(f'{d}/{s}' for d in freshdays for s in symbols)
    reader, helper = artifact / 'reader.py', artifact / 'intake.py'
    reader.write_text(READER)
    helper.write_text(HELPER)
    v4, v3, _, analyzers = m.support.load_analyzers()
    synthetic_reader = m.support.import_pinned(reader, m.sha(reader), 'synthetic_delta_fixture_reader')
    basic = artifact / 'metadata.csv'
    basic.write_text('synthetic metadata, no prices')
    oldidentity = {'mode': 'full', 'program_sha256': 'accepted-old-program',
                   'output': str(oldout), 'cache': str(oldcache)}
    oldbound = {'members': [], 'missing_members': []}
    oldresults = {}
    reused = {}
    for symbol in symbols[:-1]:
        facts = []
        for day in oldcalendar:
            frames = {k: synthetic_reader.read_bound_v8(None, {'member': f'{day}/{symbol}/{k}', 'sha256': m.sha(basic)}, day, symbol, k, {})[0] for k in m.KINDS}
            fact = m.analyze_one_day(day, symbol, frames, (m.support, v4, v3))
            fact['verified_files'] = [{'member': f'{day}/{symbol}/{k}', 'sha256': m.sha(basic),
                                       'source_detail': {'exact': 2**53+31, 'unknown': None}} for k in m.KINDS]
            for r in fact['verified_files']:
                oldbound['members'].append({'member': r['member'], 'sha256': r['sha256']})
            facts.append(fact)
        oldresults[symbol] = {'symbol': symbol, 'identity': oldidentity, 'profile': {},
                             'raw_source_last_at_cutoff': None, 'daily': [d['daily'] for d in facts],
                             'observations': [d['observation'] for d in facts],
                             'markets': [d['market'] for d in facts],
                             **{field: [v for d in facts for v in d[field]] for field in
                                ('band_cells', 'diagnostics', 'verified_files', 'errors')}, 'missing': []}
    oldboundpath = oldout / 'bound_manifest.json'
    dump(oldboundpath, oldbound)
    for symbol, result in oldresults.items():
        result['bound_manifest_sha256'] = m.sha(oldboundpath)
        path = stocks / (symbol + '.json')
        dump(path, result)
        for day in oldcalendar:
            reused[f'{day}/{symbol}'] = {'day': day, 'symbol': symbol,
                                        'checkpoint_path': str(path), 'checkpoint_sha256': m.sha(path)}
    oldrunpath = oldout / 'run_spec.json'
    dump(oldrunpath, {'identity': oldidentity, 'effective_scope': {'calendar': oldcalendar},
                      'bound_manifest_sha256': m.sha(oldboundpath)})
    spec = {'role': 'synthetic_daily_only', 'one_new_raw_batch_total_max': 64*1024**3,
            'core_module_path': str(Path(m.support.__file__).resolve()),
            'core_module_sha256': m.sha(m.support.__file__),
            'old_runner_path': str(Path(m.old.__file__).resolve()), 'old_runner_sha256': m.sha(m.old.__file__),
            'source_reader_path': str(reader), 'reader_sha256': m.sha(reader),
            'extract_helper_path': str(helper), 'extract_helper_sha256': m.sha(helper),
            'formation_input_pins': {str(basic): m.sha(basic)}, 'analyzers': analyzers,
            'reuse_run_spec_path': str(oldrunpath), 'reuse_run_spec_sha256': m.sha(oldrunpath),
            'reuse_source_identity': oldidentity, 'reuse_bound_manifest_path': str(oldboundpath),
            'reuse_bound_manifest_sha256': m.sha(oldboundpath)}
    for mode in ('smoke', 'full'):
        scope = {'calendar': m.CALENDAR, 'symbols': symbols, 'kinds': m.KINDS,
                 'source': str(source), 'cache': str(tmp_path / 'delta_cache'),
                 'expected_fact_keys': expected, 'file_bytes_max': 1024,
                 'selected_bytes_max': 512*1024**2, 'involved_solid_bytes_max': 4*1024**3,
                 'workers': 2, 'extraction_timeout_seconds': 30, 'archive_timeout_seconds': 20,
                 'analysis_timeout_seconds': 60}
        archives, members = [], []
        for day in m.CALENDAR:
            path = source / '202609' / (day + '.7z')
            if not path.exists():
                path.write_bytes(b'SYNTHETIC NEVER EXTRACTED')
            count = 16 if day in freshdays else 0
            archives.append({'path': str(path), 'day': day, 'bytes': path.stat().st_size,
                             'mtime_ns': path.stat().st_mtime_ns, 'selected_members': count,
                             'selected_member_count': count, 'selected_bytes': count,
                             'involved_solid_uncompressed_bytes': count})
            if day in freshdays:
                members.extend({'archive': str(path), 'member': f'{day}/{s}/{k}', 'bytes': 1,
                                'crc32': f'{zlib.crc32(b"x"):08x}', 'block': '0'} for s in symbols for k in m.KINDS)
        plan = {'archives': archives, 'members': members, 'missing_members': [],
                'selected_bytes': 80, 'involved_solid_bytes': 80, 'expected_fresh_fact_keys': fresh,
                'all_needed_fact_keys': expected, 'reuse_facts': reused}
        spath, ppath = artifact / (mode + '_scope.json'), artifact / (mode + '_plan.json')
        dump(spath, scope)
        dump(ppath, plan)
        spec[mode] = {'scope_path': str(spath), 'scope_sha256': m.sha(spath),
                      'plan_path': str(ppath), 'plan_sha256': m.sha(ppath)}
    specpath = artifact / 'daily_execution_spec.json'
    dump(specpath, spec)
    return SimpleNamespace(spec=spec, path=specpath, tmp=tmp_path, artifact=artifact,
                           oldout=oldout, symbols=symbols)


def repin(packet, kind, value, mode='smoke'):
    path = Path(packet.spec[mode][kind + '_path'])
    dump(path, value)
    packet.spec[mode][kind + '_sha256'] = m.sha(path)
    dump(packet.path, packet.spec)


def argv(packet, output='out'):
    return ['--spec', str(packet.path), '--mode', 'smoke', '--output', str(packet.tmp / output)]


def run(packet):
    return m.main(argv(packet))


def test_two_worker_daily_cli_exact_coverage_and_immutable_resume(packet):
    oldfiles = {p: (m.sha(p), p.stat().st_mtime_ns) for p in packet.oldout.rglob('*.json')}
    assert run(packet) == 0
    out = packet.tmp / 'out'
    summary = m.load_json(out / 'summary.json')
    assert summary == {'mode': 'smoke', 'expected_symbols': 8, 'completed_symbols': 8,
                       'expected_facts': 75, 'completed_facts': 75, 'reused_facts': 35, 'fresh_facts': 40,
                       'ready_cash_facts': 75, 'new_verified_files': 80, 'new_missing_members': 0,
                       'new_errors': 0, 'source_full_complete': True, 'status': 'complete',
                       'formal_provider_or_forecast': False}
    stock = m.load_json(out / 'stock_results' / (packet.symbols[0] + '.json'))
    assert [d['day'] for d in stock['days']] == m.CALENDAR
    assert all(d['daily']['buy'] == 5000000000 for d in stock['days'])
    oldstock = m.load_json(packet.oldout / 'stock_results' / (packet.symbols[0] + '.json'))
    reused = stock['days'][4]
    for field, oldfield in [('daily', 'daily'), ('observation', 'observations'), ('market', 'markets')]:
        assert reused[field] == oldstock[oldfield][0]
    for field in ('band_cells', 'diagnostics', 'errors'):
        assert reused[field] == [r for r in oldstock[field] if r['day'] == reused['day']]
    assert reused['verified_files'][0]['source_detail']['exact'] == 2**53+31
    checkpoints = list((out / 'stock_results').glob('*.json'))
    before = {p: (m.sha(p), p.stat().st_mtime_ns) for p in checkpoints}
    (out / 'progress.jsonl.tmp').write_text('stranded old temp')
    progress = (out / 'progress.jsonl').read_bytes()
    assert m.main(argv(packet) + ['--resume']) == 0
    assert before == {p: (m.sha(p), p.stat().st_mtime_ns) for p in checkpoints}
    assert (out / 'progress.jsonl').read_bytes() == progress
    assert oldfiles == {p: (m.sha(p), p.stat().st_mtime_ns) for p in oldfiles}
    assert not Path(packet.spec['reuse_source_identity']['cache']).exists()
    assert len(list(csv.DictReader((out / 'daily_inputs.csv').open()))) == 75
    assert not (out / 'profiles.csv').exists()
    assert 'profile' not in stock
    assert len(m.load_json(out / 'bound_delta_manifest.json')['members']) == 80


def test_noncontiguous_canonical_days_never_profiles(packet, monkeypatch):
    monkeypatch.setattr(m.support, 'process_symbol', lambda *a: pytest.fail('old aggregate called'))
    from experiments import l2_continuous_interval_v6 as v6
    monkeypatch.setattr(v6, 'interval_profile', lambda *a: pytest.fail('fake W5 called'))
    # Inline pool makes forbidden calls observable independently of fork behavior.
    inline_pool(monkeypatch)
    assert run(packet) == 0


def inline_pool(monkeypatch, fail_second=False):
    class Pool:
        _processes = {}
        def __init__(self, max_workers, initializer, initargs):
            assert max_workers == 2
            initializer(*initargs)
            self.count = 0
        def submit(self, fn, symbol):
            self.count += 1
            future = Future()
            try:
                if fail_second and self.count == 2:
                    raise RuntimeError('unexpected worker bug')
                future.set_result(fn(symbol))
            except BaseException as exc:
                future.set_exception(exc)
            return future
        def shutdown(self, **kwargs):
            pass
    monkeypatch.setattr(m, 'ProcessPoolExecutor', Pool)
    monkeypatch.setattr(m, 'as_completed', lambda futures, timeout: iter(futures))


def test_missing_only_fresh_requested_member_masks_entire_day(packet):
    plan = m.load_json(packet.spec['smoke']['plan_path'])
    removed = plan['members'].pop(0)
    plan['missing_members'].append(removed['member'])
    plan['selected_bytes'] -= 1
    for field in ('selected_members', 'selected_member_count', 'selected_bytes'):
        plan['archives'][0][field] -= 1
    repin(packet, 'plan', plan)
    assert run(packet) == 2
    out = packet.tmp / 'out'
    stock = m.load_json(out / 'stock_results' / (packet.symbols[0] + '.json'))
    day = stock['days'][0]
    assert day['missing'] == [removed['member']]
    assert day['daily']['buy'] is None and not day['daily']['cash_ready']
    assert len(day['band_cells']) == 6 and day['market'] == {}
    assert len(day['verified_files']) == 1
    summary = m.load_json(out / 'summary.json')
    assert summary['completed_facts'] == 75 and summary['ready_cash_facts'] == 74
    assert summary['new_missing_members'] == 1 and summary['new_verified_files'] == 79
    assert not summary['source_full_complete'] and summary['status'] == 'complete_with_unknown'


def test_reuse_preserves_unready_invalid_details_exactly(packet):
    plan = m.load_json(packet.spec['smoke']['plan_path'])
    key = next(iter(plan['reuse_facts']))
    pin = plan['reuse_facts'][key]
    oldpath = Path(pin['checkpoint_path'])
    stock = m.load_json(oldpath)
    stock['daily'][0].update(cash_ready=False, source_fact_ready=False, buy=None,
                             cash_reason='source_volume_or_count_mismatch')
    stock['observations'][0].update(cash_fact_ready=False, custom_unknown=None)
    stock['markets'][0] = {}
    stock['errors'].append({'symbol': stock['symbol'], 'day': pin['day'], 'kind': 'cash_gate',
                            'error': 'source_volume_or_count_mismatch'})
    stock['diagnostics'].append({'symbol': stock['symbol'], 'day': pin['day'],
                                 'arbitrary_exact_detail': 2**60+17, 'unknown': None})
    dump(oldpath, stock)
    for p in plan['reuse_facts'].values():
        if p['symbol'] == pin['symbol']:
            p['checkpoint_sha256'] = m.sha(oldpath)
    repin(packet, 'plan', plan)
    before = (m.sha(oldpath), oldpath.stat().st_mtime_ns)
    assert run(packet) == 2
    result = m.load_json(packet.tmp / 'out' / 'stock_results' / oldpath.name)
    fact = next(d for d in result['days'] if d['day'] == pin['day'])
    assert fact['daily'] == stock['daily'][0]
    assert fact['observation'] == stock['observations'][0]
    assert fact['market'] == {}
    assert fact['errors'] == stock['errors']
    assert fact['diagnostics'] == [r for r in stock['diagnostics'] if r['day'] == pin['day']]
    assert before == (m.sha(oldpath), oldpath.stat().st_mtime_ns)
    summary = m.load_json(packet.tmp / 'out' / 'summary.json')
    assert summary['new_errors'] == 0 and summary['ready_cash_facts'] == 74
    assert not summary['source_full_complete']


@pytest.mark.parametrize('mutation', ['partition', 'duplicate', 'foreign', 'crc', 'size', 'totals', 'missing', 'reuse_overlap', 'own_pin'])
def test_plan_rejected_before_payload(packet, monkeypatch, mutation):
    plan = m.load_json(packet.spec['smoke']['plan_path'])
    if mutation == 'partition': plan['expected_fresh_fact_keys'].pop()
    if mutation == 'duplicate': plan['members'].append(plan['members'][0])
    if mutation == 'foreign': plan['members'][0]['member'] = '../escape'
    if mutation == 'crc': plan['members'][0]['crc32'] = 'bad'
    if mutation == 'size': plan['members'][0]['bytes'] = True
    if mutation == 'totals': plan['selected_bytes'] += 1
    if mutation == 'missing': plan['members'].pop()
    if mutation == 'reuse_overlap': plan['expected_fresh_fact_keys'].append(next(iter(plan['reuse_facts'])))
    repin(packet, 'plan', plan)
    if mutation == 'own_pin':
        packet.spec['smoke']['plan_sha256'] = '0'*64
        dump(packet.path, packet.spec)
    monkeypatch.setattr(m.support, 'import_pinned', lambda *a: pytest.fail('payload setup reached'))
    with pytest.raises(ValueError):
        run(packet)
    assert not (packet.tmp / 'out').exists()


@pytest.mark.parametrize('field,value', [('workers', 3), ('workers', True), ('analysis_timeout_seconds', 601),
                                        ('extraction_timeout_seconds', 601), ('archive_timeout_seconds', 301),
                                        ('selected_bytes_max', 512*1024**2+1), ('involved_solid_bytes_max', 4*1024**3+1)])
def test_budgets_before_payload(packet, field, value):
    scope = m.load_json(packet.spec['smoke']['scope_path'])
    scope[field] = value
    repin(packet, 'scope', scope)
    with pytest.raises(ValueError, match='budget'):
        run(packet)
    assert not (packet.tmp / 'out').exists()


def test_own_mode_pins_and_no_full_gate_before_payload(packet, monkeypatch):
    scope, _ = m.validate_scope(packet.spec, 'smoke')
    assert scope['workers'] == 2
    monkeypatch.setattr(m, 'validate_scope', lambda *a: pytest.fail('scope reached before gate'))
    args = argv(packet)
    args[args.index('smoke')] = 'full'
    with pytest.raises(ValueError, match='full-gate'):
        m.main(args)
    receipt = packet.tmp / 'SYNTHETIC_receipt.json'
    receipt.write_text('{}')
    gate = {'role': 'parent_smoke_accepted', 'execution_spec_sha256': m.sha(packet.path),
            'program_sha256': m.sha(m.__file__), 'smoke_receipt_path': str(receipt),
            'smoke_receipt_sha256': m.sha(receipt)}
    path = packet.tmp / 'SYNTHETIC_gate.json'
    for update in ({'extra': 1}, {'program_sha256': '0'*64}, {'execution_spec_sha256': '0'*64},
                   {'role': 'child'}, {'smoke_receipt_path': 'relative'}, {'smoke_receipt_sha256': '0'*64}):
        dump(path, {**gate, **update})
        with pytest.raises(ValueError, match='parent smoke'):
            m.main(args + ['--full-gate', str(path)])
    dump(path, gate)
    assert m.validate_full_gate('full', path, packet.path)['role'] == gate['role']
    assert not (packet.tmp / 'out').exists()


@pytest.mark.parametrize('what', ['old_checkpoint', 'old_bound', 'old_run', 'old_identity'])
def test_reuse_source_tamper_fatal_before_extract(packet, what):
    if what == 'old_checkpoint':
        path = next((packet.oldout / 'stock_results').glob('*.json'))
    elif what == 'old_bound':
        path = Path(packet.spec['reuse_bound_manifest_path'])
    else:
        path = Path(packet.spec['reuse_run_spec_path'])
    if what == 'old_identity':
        value = m.load_json(path)
        value['identity'] = {'foreign': True}
        dump(path, value)
        packet.spec['reuse_run_spec_sha256'] = m.sha(path)
        dump(packet.path, packet.spec)
    else:
        path.write_text('{}')
    with pytest.raises(ValueError, match='hash mismatch|identity mismatch'):
        run(packet)
    assert not (packet.tmp / 'out').exists()


@pytest.mark.parametrize('pair', [('output', 'source'), ('output', 'cache'), ('source', 'cache')])
@pytest.mark.parametrize('direction', [0, 1])
def test_bidirectional_isolation(packet, pair, direction):
    scope, _ = m.validate_scope(packet.spec, 'smoke')
    paths = {'source': scope['source'], 'cache': scope['cache'], 'output': str(packet.tmp / 'out')}
    a, b = pair if direction == 0 else pair[::-1]
    paths[a] = str(Path(paths[b]) / 'nested')
    with pytest.raises(ValueError, match='isolated'):
        m.guard_paths(paths['output'], {**scope, 'source': paths['source'], 'cache': paths['cache']}, [])


def test_symlinks_and_immutable_trees(packet):
    scope, _ = m.validate_scope(packet.spec, 'smoke')
    link = packet.tmp / 'link'
    link.symlink_to(packet.tmp / 'absent')
    with pytest.raises(ValueError, match='symlink'):
        m.guard_paths(link / 'out', scope, [])
    with pytest.raises(ValueError, match='immutable'):
        m.guard_paths(packet.artifact, scope, [packet.path])
    with pytest.raises(ValueError, match='immutable'):
        m.run_daily(packet.path, packet.oldout / 'nested', 'smoke')


@pytest.mark.parametrize('failure,pattern', [("KeyError('unexpected')", 'unexpected'),
    ("ValueError('source content mismatch')", 'bound cache'),
    ("OSError('cache removed')", 'bound cache'),
    ("ValueError('source date/instrument mismatch')", 'source identity')])
def test_programming_cache_and_source_identity_errors_fatal(packet, failure, pattern):
    path = Path(packet.spec['source_reader_path'])
    path.write_text('def read_bound_v8(*args):\n    raise ' + failure + '\n')
    packet.spec['reader_sha256'] = m.sha(path)
    dump(packet.path, packet.spec)
    with pytest.raises((KeyError, RuntimeError), match=pattern):
        run(packet)
    assert not (packet.tmp / 'out' / 'summary.json').exists()


def test_known_source_schema_failure_is_unready_not_fatal(packet):
    path = Path(packet.spec['source_reader_path'])
    path.write_text("def read_bound_v8(*args):\n    raise ValueError('source header shape')\n")
    packet.spec['reader_sha256'] = m.sha(path)
    dump(packet.path, packet.spec)
    assert run(packet) == 2
    summary = m.load_json(packet.tmp / 'out' / 'summary.json')
    assert summary['completed_facts'] == 75 and summary['new_errors'] == 80
    assert summary['ready_cash_facts'] == 35


def test_resume_identity_cache_bound_and_old_checkpoint_rechecked(packet):
    assert run(packet) == 0
    out = packet.tmp / 'out'
    saved = m.load_json(out / 'run_spec.json')
    for key in saved['identity']:
        changed = copy.deepcopy(saved)
        changed['identity'][key] = 'changed'
        dump(out / 'run_spec.json', changed)
        with pytest.raises(ValueError, match='resume identity'):
            m.main(argv(packet) + ['--resume'])
    dump(out / 'run_spec.json', saved)
    boundpath = out / 'bound_delta_manifest.json'
    boundbytes = boundpath.read_bytes()
    boundpath.write_text('{}')
    with pytest.raises(ValueError, match='bound delta checkpoint'):
        m.main(argv(packet) + ['--resume'])
    boundpath.write_bytes(boundbytes)
    cached = Path(m.load_json(boundpath)['members'][0]['path'])
    cached.write_bytes(b'y')
    with pytest.raises(ValueError, match='cache content'):
        m.main(argv(packet) + ['--resume'])
    cached.unlink()
    with pytest.raises(ValueError, match='cache content'):
        m.main(argv(packet) + ['--resume'])
    assert not cached.exists()
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(b'x')
    path = next((packet.oldout / 'stock_results').glob('*.json'))
    path.write_text('{}')
    with pytest.raises(ValueError, match='reuse checkpoint'):
        m.main(argv(packet) + ['--resume'])


def test_partial_progress_and_unique_temps_resume(packet, monkeypatch):
    real_pool, real_completed = m.ProcessPoolExecutor, m.as_completed
    inline_pool(monkeypatch, fail_second=True)
    with pytest.raises(RuntimeError, match='unexpected worker bug'):
        run(packet)
    out = packet.tmp / 'out'
    checkpoint = out / 'stock_results' / (packet.symbols[0] + '.json')
    before = (m.sha(checkpoint), checkpoint.stat().st_mtime_ns)
    assert len(list((out / 'stock_results').glob('*.json'))) == 1
    assert len((out / 'progress.jsonl').read_text().splitlines()) == 1
    assert not (out / 'summary.json').exists()
    (out / 'progress.jsonl').write_text('')
    (out / 'progress.jsonl.tmp').write_text('interrupted')
    monkeypatch.setattr(m, 'ProcessPoolExecutor', real_pool)
    monkeypatch.setattr(m, 'as_completed', real_completed)
    assert m.main(argv(packet) + ['--resume']) == 0
    assert before == (m.sha(checkpoint), checkpoint.stat().st_mtime_ns)
    assert len((out / 'progress.jsonl').read_text().splitlines()) == 8


@pytest.mark.parametrize('unfinished', [False, True])
def test_owned_interrupted_stock_temp_preserved_and_valid_resume(packet, unfinished):
    assert run(packet) == 0
    out = packet.tmp / 'out'
    symbol = packet.symbols[0]
    stale = out / 'stock_results' / (symbol + '.json.' + 'a'*32 + '.tmp')
    stale.write_text('{interrupted checkpoint')
    committed = out / 'stock_results' / (symbol + '.json')
    if unfinished:
        committed.unlink()
        lines = [line for line in (out/'progress.jsonl').read_text().splitlines() if json.loads(line)['symbol'] != symbol]
        (out/'progress.jsonl').write_text(''.join(line+'\n' for line in lines))
    before = {p.name: (m.sha(p), p.stat().st_mtime_ns) for p in (out/'stock_results').glob('*.json')}
    assert m.main(argv(packet) + ['--resume']) == 0
    assert stale.read_text() == '{interrupted checkpoint'
    assert committed.is_file()
    for name, value in before.items():
        p = out/'stock_results'/name
        assert (m.sha(p), p.stat().st_mtime_ns) == value
    assert len((out/'progress.jsonl').read_text().splitlines()) == 8


def test_deadline_terminate_kill_bounded(packet, monkeypatch):
    calls = []
    class Process:
        def terminate(self): calls.append('terminate')
        def join(self, timeout): calls.append(('join', timeout))
        def is_alive(self): return True
        def kill(self): calls.append('kill')
    class Pool:
        _processes = {1: Process(), 2: Process()}
        def __init__(self, **kwargs): pass
        def submit(self, *args): return Future()
        def shutdown(self, **kwargs): calls.append(kwargs)
    def timeout(*args, **kwargs):
        raise TimeoutError('synthetic deadline')
    monkeypatch.setattr(m, 'ProcessPoolExecutor', Pool)
    monkeypatch.setattr(m, 'as_completed', timeout)
    with pytest.raises(TimeoutError, match='deadline'):
        run(packet)
    assert calls.count('terminate') == calls.count('kill') == 2
    assert calls[-1] == {'wait': False, 'cancel_futures': True}
    assert not (packet.tmp / 'out' / 'summary.json').exists()


def test_checkpoint_detail_and_exact_coverage_validation(packet):
    assert run(packet) == 0
    out = packet.tmp / 'out'
    run_spec = m.load_json(out / 'run_spec.json')
    bound = m.load_json(out / 'bound_delta_manifest.json')
    plan = m.load_json(packet.spec['smoke']['plan_path'])
    original = m.load_json(out / 'stock_results' / (packet.symbols[0] + '.json'))
    for mutation in ('coverage', 'provenance', 'details', 'foreign_error'):
        stock = copy.deepcopy(original)
        if mutation == 'coverage': stock['days'].pop()
        if mutation == 'provenance': stock['days'][4]['provenance']['checkpoint_sha256'] = '0'*64
        if mutation == 'details': stock['days'][0]['band_cells'] = None
        if mutation == 'foreign_error': stock['days'][0]['errors'] = [{'symbol': 'other', 'day': 'wrong'}]
        with pytest.raises(ValueError):
            m.validate_stock(stock, stock['symbol'], run_spec, bound, plan)


def test_reuse_checkpoint_identity_and_bound_checked_in_worker(packet):
    scope, plan = m.validate_scope(packet.spec, 'smoke')
    calendar, bound = m.verify_reuse(packet.spec, plan)
    symbol = packet.symbols[0]
    pins = {k: v for k, v in plan['reuse_facts'].items() if v['symbol'] == symbol}
    path = Path(next(iter(pins.values()))['checkpoint_path'])
    for field in ('identity', 'bound_manifest_sha256'):
        original = m.load_json(path)
        changed = copy.deepcopy(original)
        changed[field] = 'foreign'
        dump(path, changed)
        for pin in pins.values(): pin['checkpoint_sha256'] = m.sha(path)
        with pytest.raises(ValueError, match='source identity'):
            m.reused_days(symbol, pins, packet.spec, calendar, bound)
        dump(path, original)


def test_exact_money_and_unexpected_canonical_bug():
    n = 2**53+31
    wide = {k: str(n) for k in m.support.CASH_KEYS.values()}
    row = m.support.daily_record('000001.SZ', m.CALENDAR[0],
                                 {'cash_fact_ready': True, 'observed_amount_1e4': n}, wide)
    assert row['buy'] == n and type(row['buy']) is int
    def bug(*args): raise KeyError('canonical programming bug')
    with pytest.raises(KeyError, match='programming bug'):
        m.analyze_one_day(m.CALENDAR[0], '000001.SZ', dict.fromkeys(m.KINDS, object()),
                          (m.support, SimpleNamespace(analyze_day=bug), None))


def test_reused_missing_state_and_one_json_load_per_symbol(packet, monkeypatch):
    _, plan = m.validate_scope(packet.spec, 'smoke')
    symbol = packet.symbols[0]
    pins = {k: v for k, v in plan['reuse_facts'].items() if v['symbol'] == symbol}
    calendar, bound = m.verify_reuse(packet.spec, plan)
    first = next(iter(pins.values()))
    path = Path(first['checkpoint_path'])
    stock = m.load_json(path)
    member = stock['verified_files'].pop(0)['member']
    stock['missing'] = [member]
    stock['daily'][0].update(cash_ready=False, buy=None, market_amount=None,
                             cash_reason='missing_or_invalid_source_member')
    stock['observations'][0] = {'symbol': symbol, 'day': first['day'], 'cash_fact_ready': False,
                                 'cash_reason': 'missing_or_invalid_source_member'}
    stock['markets'][0] = {}
    bound['members'] = [r for r in bound['members'] if r['member'] != member]
    bound['missing_members'] = [member]
    dump(path, stock)
    for pin in pins.values(): pin['checkpoint_sha256'] = m.sha(path)
    original = m.pinned_json
    reads = []
    def counted(path, digest):
        reads.append(str(path))
        return original(path, digest)
    monkeypatch.setattr(m, 'pinned_json', counted)
    before = path.read_bytes()
    reused = m.reused_days(symbol, pins, packet.spec, calendar, bound)
    assert reads == [str(path)]
    assert reused[first['day']]['missing'] == [member]
    assert reused[first['day']]['daily'] == stock['daily'][0]
    assert reused[first['day']]['observation'] == stock['observations'][0]
    assert reused[first['day']]['market'] == {}
    assert path.read_bytes() == before


def test_delta_bound_exact_metadata_and_digest(packet):
    assert run(packet) == 0
    out = packet.tmp / 'out'
    bound = m.load_json(out / 'bound_delta_manifest.json')
    scope, plan = m.validate_scope(packet.spec, 'smoke')
    m.validate_delta_bound(bound, plan, scope)
    for key in ('selected_bytes', 'expected_fresh_fact_keys', 'reuse_facts', 'selected_data_sha256'):
        changed = copy.deepcopy(bound)
        changed[key] = 'foreign'
        with pytest.raises(ValueError):
            m.validate_delta_bound(changed, plan, scope)


def test_own_smoke_scope_pin_not_full_pin(packet):
    assert packet.spec['smoke']['scope_sha256'] == packet.spec['full']['scope_sha256']
    # Give full a different, still valid metadata identity, then deliberately bind
    # the smoke path to the full hash. Scope/plan pins cannot be mixed across modes.
    full = m.load_json(packet.spec['full']['scope_path'])
    full['workers'] = 3
    repin(packet, 'scope', full, mode='full')
    packet.spec['smoke']['scope_sha256'] = packet.spec['full']['scope_sha256']
    dump(packet.path, packet.spec)
    with pytest.raises(ValueError, match='hash mismatch'):
        run(packet)
    assert not (packet.tmp / 'out').exists()
