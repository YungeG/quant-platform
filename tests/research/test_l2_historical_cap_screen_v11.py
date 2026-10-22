"""Synthetic only: no retained market data, archive tools, or network IO."""
import csv
import json
import time
import zlib
from concurrent.futures import Future
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from experiments import l2_historical_cap_screen_v11 as m


def test_classification_strict_flags_and_unknown():
    for profile, expected in [
        ({'cash_window_ready': False, 'group_buy_bias': True, 'active_support': True}, 'D'),
        ({'cash_window_ready': True, 'group_buy_bias': True, 'active_support': True}, 'A'),
        ({'cash_window_ready': True, 'group_buy_bias': True, 'active_support': False}, 'B'),
        ({'cash_window_ready': True, 'group_buy_bias': False, 'active_support': False}, 'C'),
        ({'cash_window_ready': 'True', 'group_buy_bias': 'False', 'active_support': 'False'}, 'C'),
        ({'cash_window_ready': True}, 'D'),
        ({'cash_window_ready': True, 'group_buy_bias': False, 'active_support': None}, 'D'),
        ({'cash_window_ready': 'false', 'group_buy_bias': True, 'active_support': True}, 'D'),
        ({'cash_window_ready': 1, 'group_buy_bias': True, 'active_support': True}, 'D'),
    ]:
        assert m.classify_profile(profile) == expected


def wide(n):
    return dict(zip(m.CASH_KEYS.values(), (str(n), '1', str(n), '1', '0', '0', '0', '0')))


def test_int_money_and_nullable_wrapper():
    n = 2**53 + 31
    r = m.daily_record('000001.SZ', '20261019', {'cash_fact_ready': 'True', 'observed_amount_1e4': n}, wide(n))
    assert type(r['buy']) is int and r['buy'] == n and r['market_amount'] == n and r['cash_ready']
    assert r['buy'] - r['sell'] == r['active_buy'] - r['active_sell'] + r['passive_buy'] - r['passive_sell'] + r['unknown_buy'] - r['unknown_sell']
    r = m.daily_record('000001.SZ', '20261019', {'cash_fact_ready': True, 'observed_amount_1e4': n}, {'buy_amount_1e4': None})
    assert r['buy'] is None and not r['cash_ready'] and r['cash_reason'] == 'side_reference_distribution_unavailable'
    assert not m.daily_record('s', 'd', {'cash_fact_ready': 'False'}, wide(n))['cash_ready']


@pytest.mark.parametrize('value', [1.0, 1.9, True, '1.9', '1.0', 'nan', {}])
def test_money_no_float_or_truncation(value):
    with pytest.raises(ValueError, match='exact integer'):
        m.integer(value)


def test_exact_rank_and_deterministic_ties():
    def row(code, delta=1, market=3, numerator=1, denominator=2, days=4, cls='A'):
        return {'symbol': code, 'class': cls, 'group_difference_1e4': delta,
                'market_amount_1e4': market, 'top2_positive_delta_numerator_1e4': numerator,
                'positive_delta_denominator_1e4': denominator, 'group_positive_days': days}
    x, y = row('000002.SZ'), row('000001.SZ', 2, 6)
    assert m.candidate_sort_key(x)[:4] == m.candidate_sort_key(y)[:4]
    assert sorted([x, y], key=m.candidate_sort_key)[0]['symbol'] == '000001.SZ'
    n = 10**30
    low = row('000009.SZ', numerator=n, denominator=2*n+1)
    high = row('000000.SZ', numerator=n, denominator=2*n-1)
    assert sorted([high, low], key=m.candidate_sort_key)[0] is low
    exact = row('b', 2**53+1, 2**53+3, cls='B')
    assert isinstance(m.candidate_sort_key(exact)[1], Fraction)
    assert sorted([exact, x], key=m.candidate_sort_key)[0] is x


def frames():
    t = pd.DataFrame([{'成交代码': '0', '成交价格': '100000', '成交数量': '25000',
                      '叫买序号': '10', '叫卖序号': str(i+1), 'BS标志': 'B',
                      '成交编号': str(i+1), '时间': '93000000', '_source_record': i+1, 'ms': 34200000}
                     for i in range(2)])
    q = pd.DataFrame([{'当日累计成交量': '50000', '成交笔数': '2', '成交价': '100000',
                       '当日成交额': '500000', 'ms': 54000000}])
    return {'逐笔成交.csv': t, '行情.csv': q}


def symbol_inputs():
    symbol = '000001.SZ'
    scope = {'symbols': [symbol], 'calendar': m.CALENDAR, 'kinds': m.KINDS}
    metas = {f'{d}/{symbol}/{k}': {'path': 'unused', 'member': f'{d}/{symbol}/{k}'}
             for d in m.CALENDAR for k in m.KINDS}
    reader = SimpleNamespace(read_bound_v8=lambda path, meta, day, sym, kind, scope: (frames()[kind], {'member': meta['member']}))
    return symbol, scope, metas, reader


def test_five_days_canonical_analyzers_and_missing_day():
    v4, v3, v6, pins = m.load_analyzers()
    assert all((m.ROOT / p).resolve().is_relative_to(m.ROOT) for p in pins)
    symbol, scope, metas, reader = symbol_inputs()
    r = m.process_symbol(symbol, scope, metas, reader, v4, v3, v6, time.monotonic()+30)
    assert m.classify_profile(r['profile']) == 'A'
    assert r['profile']['group_difference_1e4'] == 25000000000
    assert r['profile']['top2_positive_delta_numerator_1e4'] == 10000000000
    assert r['profile']['positive_delta_denominator_1e4'] == 25000000000
    assert len(r['daily']) == 5 and len(r['band_cells']) == 30 and r['diagnostics']
    del metas[f'{m.CALENDAR[2]}/{symbol}/行情.csv']
    r = m.process_symbol(symbol, scope, metas, reader, v4, v3, v6, time.monotonic()+30)
    assert m.classify_profile(r['profile']) == 'D' and r['daily'][2]['buy'] is None
    assert r['missing'] == [f'{m.CALENDAR[2]}/{symbol}/行情.csv']
    assert m.CALENDAR[2] in r['profile']['invalid_cash_dates']


def test_financial_classes_use_frozen_interval_profile():
    _, _, v6, _ = m.load_analyzers()
    def profile(group, active):
        daily = []
        for d, g, a in zip(m.CALENDAR, group, active):
            # Passive differences close the role identity; all amounts remain positive.
            daily.append({'symbol': '000001.SZ', 'day': d, 'cash_ready': True,
                          'buy': 100+g, 'sell': 100, 'active_buy': 50+a, 'active_sell': 50,
                          'passive_buy': 50+g-a, 'passive_sell': 50,
                          'unknown_buy': 0, 'unknown_sell': 0, 'market_amount': 1000})
        return v6.interval_profile(daily, 5)
    assert m.classify_profile(profile([10]*5, [10]*5)) == 'A'
    assert m.classify_profile(profile([10]*5, [-1]*5)) == 'B'
    assert m.classify_profile(profile([20,20,-1,-1,-1], [0]*5)) == 'C'
    assert m.classify_profile(profile([-1]*5, [0]*5)) == 'C'


@pytest.mark.parametrize('failure', ['numeric', 'role', 'cumulative'])
def test_source_numeric_role_and_cumulative_failures_stay_unknown(failure):
    v4, v3, v6, _ = m.load_analyzers()
    symbol, scope, metas, reader = symbol_inputs()
    def read(path, meta, day, sym, kind, scope):
        f = frames()
        if failure == 'numeric': f['逐笔成交.csv'].loc[0, '成交价格'] = '1.5'
        if failure == 'role': f['逐笔成交.csv'].loc[0, '成交代码'] = 'D'
        if failure == 'cumulative': f['行情.csv'].loc[0, '成交笔数'] = '9'
        return f[kind], {'member': meta['member']}
    reader.read_bound_v8 = read
    result = m.process_symbol(symbol, scope, metas, reader, v4, v3, v6, time.monotonic()+30)
    assert m.classify_profile(result['profile']) == 'D' and result['errors']
    assert all(d['buy'] is None and not d['cash_ready'] for d in result['daily'])


def test_source_failure_and_unexpected_error_distinguished():
    v4, v3, v6, _ = m.load_analyzers()
    symbol, scope, metas, reader = symbol_inputs()
    def bad(*args):
        raise ValueError('bad source header')
    reader.read_bound_v8 = bad
    r = m.process_symbol(symbol, scope, metas, reader, v4, v3, v6, time.monotonic()+30)
    assert m.classify_profile(r['profile']) == 'D' and len(r['errors']) == 10
    def bug(*args):
        raise KeyError('unexpected programming error')
    reader.read_bound_v8 = bug
    with pytest.raises(KeyError):
        m.process_symbol(symbol, scope, metas, reader, v4, v3, v6, time.monotonic()+30)
    with pytest.raises(TimeoutError):
        m.process_symbol(symbol, scope, metas, reader, v4, v3, v6, 0)


def dump(path, value):
    path.write_text(json.dumps(value))


@pytest.fixture
def packet(tmp_path, monkeypatch):
    artifact = tmp_path / 'packet'
    artifact.mkdir()
    monkeypatch.setattr(m, 'ARTIFACT', artifact)
    source = tmp_path / 'source'
    (source / '202610').mkdir(parents=True)
    symbols = [f'{i:06d}.SZ' for i in range(1, 2426)]
    names = {s: 'synthetic' for s in symbols}
    stock = artifact / 'stock_basic.csv'
    stock.write_text('synthetic metadata only')
    basic = artifact / 'basic.csv'
    with basic.open('w') as f:
        f.write('ts_code,trade_date,total_mv\n')
        for s in symbols:
            f.write(f'{s},20261019,6000000000.01\n')
    metadata = {'asof': m.CALENDAR[-1], 'source': str(source), 'dates': m.CALENDAR,
                'symbols': symbols, 'names': names, 'kinds': m.KINDS,
                'daily_basic_sha256': m.sha(basic), 'stock_basic_source': str(stock),
                'stock_basic_sha256': m.sha(stock)}
    scope_path = artifact / 'scope.json'
    dump(scope_path, metadata)
    smoke_path = artifact / 'cap_smoke_inventory_scope.json'
    dump(smoke_path, {**metadata, 'symbols': symbols[:8]})
    fixed = artifact / 'symbols.json'
    dump(fixed, symbols[:8])
    archives, members = [], []
    for d in m.CALENDAR:
        archive = source / '202610' / (d + '.7z')
        archive.write_bytes(b'not an archive; never extracted')
        st = archive.stat()
        archives.append({'path': str(archive), 'day': d, 'bytes': st.st_size, 'mtime_ns': st.st_mtime_ns,
                         'selected_member_count': 16, 'selected_bytes': 16, 'involved_solid_uncompressed_bytes': 16})
        members.extend({'archive': str(archive), 'member': f'{d}/{s}/{k}', 'bytes': 1,
                        'crc32': f'{zlib.crc32(b"x"):08x}', 'block': '0'} for s in symbols[:8] for k in m.KINDS)
    inventory = {'asof': m.CALENDAR[-1], 'symbols': 8, 'dates': m.CALENDAR, 'archives': archives,
                 'members': members, 'missing_members': [], 'selected_bytes': 80, 'involved_solid_bytes': 80,
                 'scope_sha256': m.sha(smoke_path)}
    invpath = artifact / 'inventory.json'
    dump(invpath, inventory)
    dump(artifact / 'smoke_binding.json', {'smoke_inventory_path': str(invpath), 'smoke_inventory_sha256': m.sha(invpath),
                                         'smoke_symbols_path': str(fixed), 'smoke_symbols_sha256': m.sha(fixed)})
    reader = artifact / 'reader.py'
    reader.write_text('''import pandas as pd

def read_bound_v8(path, meta, day, symbol, kind, scope):
    if kind == '行情.csv':
        frame = pd.DataFrame([{'当日累计成交量':'50000','成交笔数':'2','成交价':'100000','当日成交额':'500000','ms':54000000}])
    else:
        frame = pd.DataFrame([{'成交代码':'0','成交价格':'100000','成交数量':'25000','叫买序号':'10','叫卖序号':str(i+1),'BS标志':'B','成交编号':str(i+1),'时间':'93000000','_source_record':i+1,'ms':34200000} for i in range(2)])
    return frame, {'member':meta['member'],'sha256':meta['sha256']}
''')
    helper = artifact / 'helper.py'
    helper.write_text('''import hashlib,json

def extract(plan, scope, cache):
    assert scope['extraction_timeout_seconds'] and scope['archive_timeout_seconds']
    assert len(scope['calendar']) == 5 and len(scope['symbols']) == 8
    members=[]
    for m in plan['members']:
        p=cache/m['member'];p.parent.mkdir(parents=True,exist_ok=True)
        if not p.exists():p.write_bytes(b'x')
        if p.read_bytes()!=b'x':raise ValueError('cache content changed')
        members.append({**m,'path':str(p),'sha256':hashlib.sha256(b'x').hexdigest()})
    digest=hashlib.sha256(json.dumps(sorted((m['member'],m['sha256']) for m in members),separators=(',',':')).encode()).hexdigest()
    return {**plan,'members':members,'selected_data_sha256':digest}
''')
    spec = {'role': 'historical_source_structure_watchlist_not_strategy_or_trade_execution',
            'asof': m.CALENDAR[-1], 'symbols': symbols, 'names': names, 'calendar': m.CALENDAR, 'kinds': m.KINDS,
            'cash_threshold_cny': 500000, 'total_cap_min_cny': '6000000000', 'total_cap_max_cny': '100000000000',
            'total_cap_bounds_inclusive': True, 'metadata_scope_path': str(scope_path), 'metadata_scope_sha256': m.sha(scope_path),
            'daily_basic_path': str(basic), 'daily_basic_sha256': m.sha(basic), 'inventory_path': str(invpath),
            'inventory_sha256': m.sha(invpath), 'sample_selected_bytes_max': 512*1024**2,
            'sample_solid_bytes_max': 4*1024**3, 'sample_workers': 2, 'sample_analysis_timeout_seconds': 60,
            'selected_bytes_max': 64*1024**3, 'involved_solid_bytes_max': 160*1024**3,
            'workers': 8, 'maximum_workers': 8, 'analysis_timeout_seconds': 60,
            'file_bytes_max': 1024, 'extraction_timeout_seconds': 30, 'archive_timeout_seconds': 30,
            'cache': str(tmp_path/'raw'), 'source_reader_path': str(reader), 'reader_sha256': m.sha(reader),
            'extract_helper_path': str(helper), 'extract_helper_sha256': m.sha(helper)}
    spec_path = artifact / 'execution_spec.json'
    dump(spec_path, spec)
    return SimpleNamespace(spec=spec, path=spec_path, artifact=artifact, inv=inventory, tmp=tmp_path)


def test_smoke_own_scope_effective_execution_and_integrity(packet):
    scope, inv, caps, pins = m.validate_plan(packet.spec, 'smoke')
    assert inv['scope_sha256'] != packet.spec['metadata_scope_sha256']
    assert pins['inventory_scope'] == inv['scope_sha256'] and len(scope['symbols']) == 8
    assert scope['calendar'] == m.CALENDAR and scope['extraction_timeout_seconds'] == 30
    assert len(inv['members']) == 80 and caps[scope['symbols'][0]] == '6000000000.01'
    for mutation in ('crc', 'total', 'missing', 'path'):
        bad = json.loads(json.dumps(inv))
        if mutation == 'crc': bad['members'][0]['crc32'] = 'x'
        if mutation == 'total': bad['selected_bytes'] += 1
        if mutation == 'missing': bad['members'].pop()
        if mutation == 'path': bad['members'][0]['member'] = '../escape'
        with pytest.raises(ValueError):
            m.validate_members(bad, scope)
    Path(packet.spec['daily_basic_path']).write_text('changed')
    with pytest.raises(ValueError, match='hash'):
        m.validate_plan(packet.spec, 'smoke')


def test_full_gate_rejects_before_extraction(packet, monkeypatch):
    def forbidden(*args):
        raise AssertionError('payload/plan reached before parent gate')
    monkeypatch.setattr(m, 'validate_plan', forbidden)
    args = ['--spec', str(packet.path), '--output', str(packet.tmp/'out'), '--mode', 'full']
    with pytest.raises(ValueError, match='full-gate'):
        m.main(args)
    gate = packet.artifact / 'bad_gate.json'
    dump(gate, {'role': 'parent_smoke_accepted'})
    with pytest.raises(ValueError, match='invalid parent'):
        m.main(args + ['--full-gate', str(gate)])
    receipt = packet.artifact / 'synthetic_receipt.json'
    receipt.write_text('{}')
    invalid_gate = {'role': 'parent_smoke_accepted', 'execution_spec_sha256': m.sha(packet.path),
                    'program_sha256': '0'*64, 'smoke_receipt_path': str(receipt), 'smoke_receipt_sha256': m.sha(receipt)}
    dump(gate, invalid_gate)
    with pytest.raises(ValueError, match='invalid parent'):
        m.main(args + ['--full-gate', str(gate)])
    dump(gate, {**invalid_gate, 'program_sha256': m.sha(m.__file__), 'smoke_receipt_sha256': '0'*64})
    with pytest.raises(ValueError, match='invalid parent'):
        m.main(args + ['--full-gate', str(gate)])
    assert not (packet.tmp/'out').exists()


def test_immutable_output_containment_both_directions(packet):
    scope, inv, *_ = m.validate_plan(packet.spec, 'smoke')
    for path in [Path(scope['source'])/'child', Path(scope['source']), Path(scope['source']).parent,
                 Path(scope['cache'])/'child', Path(scope['cache'])]:
        with pytest.raises(ValueError, match='source/raw'):
            m.guard_output(path, scope)
    link = packet.tmp / 'link'
    link.symlink_to(packet.tmp/'other')
    with pytest.raises(ValueError, match='symlink'):
        m.guard_output(link/'out', scope)
    assert m.guard_output(packet.tmp/'out', scope) == packet.tmp/'out'
    cache = Path(scope['cache'])
    cache.mkdir()
    (cache/m.CALENDAR[0]).symlink_to(packet.tmp/'another')
    with pytest.raises(ValueError, match='symlink'):
        m.check_cache_paths(inv, scope)


def test_helper_pin_rejected_before_payload(packet):
    helper = Path(packet.spec['extract_helper_path'])
    helper.write_text(helper.read_text() + '\n# changed\n')
    with pytest.raises(ValueError, match='intake hash mismatch'):
        m.main(['--spec', str(packet.path), '--output', str(packet.tmp/'out'), '--mode', 'smoke'])
    assert not (packet.tmp/'out').exists()


def test_tiny_mocked_five_day_cli_parallel_outputs_resume(packet):
    out = packet.tmp / 'out'
    args = ['--spec', str(packet.path), '--output', str(out), '--mode', 'smoke']
    assert m.main(args) == 0
    rows = list(csv.DictReader((out/'all_stocks.csv').open()))
    candidates = list(csv.DictReader((out/'candidates.csv').open()))
    assert len(rows) == len(candidates) == 8
    assert all(r['class'] == 'A' and r['group_difference_1e4'] == '25000000000' for r in rows)
    assert rows[0]['group_difference_wan'] == '250' and rows[0]['total_mv_cny'] == '6000000000.01'
    assert all(r['new_trigger_status'] == 'not_assessed' and r['reference_next_open'] == 'pending' for r in rows)
    observations = list(csv.DictReader((out/'day_observations.csv').open()))
    assert len(observations) == 40 and sorted({r['day'] for r in observations}) == m.CALENDAR
    assert len(m.load_json(out/'source_verification.json')['verified_files']) == 80
    checkpoint = m.load_json(next((out/'stock_results').glob('*.json')))
    assert checkpoint['band_cells'] and checkpoint['diagnostics']
    assert len((out/'progress.jsonl').read_text().splitlines()) == 8
    before = {p.name: m.sha(p) for p in (out/'stock_results').iterdir()}
    with pytest.raises(ValueError, match='explicit --resume'):
        m.main(args)
    assert m.main(args + ['--resume']) == 0
    assert before == {p.name: m.sha(p) for p in (out/'stock_results').iterdir()}
    assert len((out/'progress.jsonl').read_text().splitlines()) == 8
    assert m.load_json(out/'summary.json')['completed_symbols'] == 8
    saved = m.load_json(out/'run_spec.json')
    changed = json.loads(json.dumps(saved))
    changed['identity']['program_sha256'] = 'changed'
    dump(out/'run_spec.json', changed)
    with pytest.raises(ValueError, match='resume identity'):
        m.main(args + ['--resume'])
    dump(out/'run_spec.json', saved)
    (Path(packet.spec['cache'])/packet.inv['members'][0]['member']).write_bytes(b'y')
    with pytest.raises(ValueError, match='cache content changed'):
        m.main(args + ['--resume'])
    assert before == {p.name: m.sha(p) for p in (out/'stock_results').iterdir()}


def test_partial_progress_preserved_and_explicit_resume(packet, monkeypatch):
    class Pool:
        _processes = {}
        def __init__(self, max_workers, initializer, initargs):
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
    out = packet.tmp/'partial'
    args = ['--spec', str(packet.path), '--output', str(out), '--mode', 'smoke']
    with pytest.raises(RuntimeError, match='unexpected worker'):
        m.main(args)
    assert len(list((out/'stock_results').glob('*.json'))) == 1
    assert len((out/'progress.jsonl').read_text().splitlines()) == 1
    assert not (out/'summary.json').exists() and not (out/'all_stocks.csv').exists()
    # Resume with the real two-worker executor; completed stock must not be rewritten.
    monkeypatch.undo()
    monkeypatch.setattr(m, 'ARTIFACT', packet.artifact)
    assert m.main(args + ['--resume']) == 0
    assert len((out/'progress.jsonl').read_text().splitlines()) == 8
