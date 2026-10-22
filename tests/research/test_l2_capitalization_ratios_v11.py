import csv
import hashlib
import json
from fractions import Fraction
from pathlib import Path

import pytest
from experiments import l2_capitalization_ratios_v11 as m


def test_units_missing_zero_negative_and_large_integer():
    assert m.cap_ratio('1000000000000', '10000000000') == Fraction(1, 100)
    assert m.percentage(Fraction(1, 100)) == '1.000000'
    assert m.cap_ratio('', '6000000000') is None
    assert m.percentage(None) == ''
    assert m.cap_ratio('0', '6000000000') == 0
    assert m.cap_ratio('-100000000', '10000000000') == Fraction(-1, 1000000)
    n = 2**60 + 1
    assert m.cap_ratio(str(n), '6000000000.01') == Fraction(n, 60000000000100)


@pytest.mark.parametrize('value', [1.1, 1.0, True, '1.1', '1.0', 'NaN', 'inf'])
def test_money_never_truncated_or_float(value):
    with pytest.raises(ValueError):
        m.money(value)


@pytest.mark.parametrize('value', [1.0, True, '0', '-1', 'NaN', 'Infinity'])
def test_invalid_caps_rejected(value):
    with pytest.raises(ValueError):
        m.cap_ratio('100', value)


def row(symbol, amount, cap='6000000000', cls='A'):
    return {'symbol': symbol, 'class': cls, 'asof': '20261019', 'day': '20261019', 'start': '20261013',
            'total_mv_cny': cap, 'group_difference_1e4': str(amount), 'active_difference_1e4': str(amount),
            'group_positive_days': '4', 'active_positive_days': '4',
            'top2_positive_delta_numerator_1e4': '3', 'positive_delta_denominator_1e4': '4',
            'new_trigger_status': 'not_assessed', 'reference_next_open': 'pending'}


def test_rank_uses_exact_not_rounded_ratios_and_keeps_classes_separate():
    first = row('000001.SZ', 100000000)
    second = row('000002.SZ', 100000001)
    assert m.percentage(m.cap_ratio(first['group_difference_1e4'], first['total_mv_cny'])) == m.percentage(m.cap_ratio(second['group_difference_1e4'], second['total_mv_cny']))
    assert sorted([first, second], key=lambda r: m.sort_key(r, 'group')) == [second, first]
    huge_b = row('000003.SZ', 10**15, cls='B')
    assert sorted([huge_b, first], key=lambda r: m.sort_key(r, 'active')) == [first, huge_b]
    tied = row('000004.SZ', 100000000)
    tied['group_positive_days'] = '5'
    assert m.sort_key(tied, 'group') < m.sort_key(first, 'group')


def test_small_cli_projection_preserves_originals_unknowns_and_all_views(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    a, b = row('000001.SZ', 100000000), row('000002.SZ', 200000000)
    unknown = row('000003.SZ', '', cls='D')
    tables = {'all_stocks.csv': [a, b, unknown], 'candidates.csv': [a, b],
              'candidates_readable.csv': [{'股票代码': a['symbol'], '冻结排序': '1'}, {'股票代码': b['symbol'], '冻结排序': '2'}]}
    hashes = {}
    for name, rs in tables.items():
        p = source / name
        with p.open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(rs[0]))
            writer.writeheader()
            writer.writerows(rs)
        hashes[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    spec = {'source_dir': str(source), 'inputs': hashes, 'expected_symbols': 3, 'expected_candidates': 2,
            'expected_classes': {'A': 2, 'D': 1}, 'smoke_symbols': [a['symbol'], b['symbol'], unknown['symbol']]}
    sp = tmp_path / 'spec.json'
    sp.write_text(json.dumps(spec))
    out = tmp_path / 'out'
    result = m.run(sp, out)
    assert result['symbols'] == 3 and result['candidates'] == 2
    def rows(name):
        with (out / name).open(encoding='utf-8-sig') as f:
            return list(csv.DictReader(f))
    original = rows('candidates_enriched.csv')
    assert [r['symbol'] for r in original] == [a['symbol'], b['symbol']]
    assert [r['original_formation_rank'] for r in original] == ['1', '2']
    for component in ('group', 'active'):
        comparison = rows('candidates_by_' + component + '_cap.csv')
        assert [r['symbol'] for r in comparison] == [b['symbol'], a['symbol']]
        assert all(r[component + '_cap_pct'] for r in comparison)
        assert [r[component + '_cap_rank_within_class'] for r in comparison] == ['1', '2']
    assert rows('all_stocks_enriched.csv')[-1]['group_cap_pct'] == ''
    assert rows('all_stocks_enriched.csv')[-1]['active_cap_pct'] == ''
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == digest for p, digest in hashes.items())
    with pytest.raises(ValueError, match='new output'):
        m.run(sp, out)
    with pytest.raises(ValueError, match='new output'):
        m.run(sp, source / 'forbidden')
    (source / 'candidates.csv').write_text('changed')
    with pytest.raises(ValueError, match='frozen input changed'):
        m.run(sp, tmp_path / 'changed')
    assert not (tmp_path / 'changed').exists()
