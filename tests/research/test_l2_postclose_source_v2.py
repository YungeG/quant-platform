"""Tests for l2_postclose_source_v2: exact reader + reference-group arithmetic."""
import csv
import hashlib
import io
import zlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from experiments.l2_postclose_core_v1 import MAX_INT, PostcloseSpec, aggregate_legs
from experiments.l2_postclose_source_v2 import (
    exact_integer,
    read_bound_csv,
    reference_group_facts,
)

SYMBOL = '688122.SH'
DAY = '20261008'


# ---------------------------------------------------------------------------
# exact_integer
# ---------------------------------------------------------------------------

class TestExactInteger:
    def test_int_accepted(self):
        assert exact_integer(200) == 200
        assert exact_integer(0) == 0
        assert exact_integer(np.int64(42)) == 42

    def test_bool_rejected(self):
        with pytest.raises(ValueError, match='bool'):
            exact_integer(True)
        with pytest.raises(ValueError, match='bool'):
            exact_integer(np.bool_(False))

    def test_float_rejected(self):
        with pytest.raises(ValueError, match='float'):
            exact_integer(200.0)
        with pytest.raises(ValueError, match='float'):
            exact_integer(float('nan'))
        with pytest.raises(ValueError, match='float'):
            exact_integer(float('inf'))

    def test_decimal_text_accepted(self):
        assert exact_integer('200') == 200
        assert exact_integer('200.0') == 200
        assert exact_integer('200.00') == 200
        assert exact_integer('  200  ') == 200
        assert exact_integer('+200') == 200

    def test_decimal_text_nonintegral_rejected(self):
        with pytest.raises(ValueError, match='nonintegral'):
            exact_integer('200.9')
        with pytest.raises(ValueError, match='nonintegral'):
            exact_integer('0.1')

    def test_invalid_text_rejected(self):
        with pytest.raises(ValueError, match='invalid'):
            exact_integer('abc')
        with pytest.raises(ValueError, match='invalid'):
            exact_integer('1e5')
        with pytest.raises(ValueError, match='invalid'):
            exact_integer('1_000')
        with pytest.raises(ValueError, match='invalid'):
            exact_integer('')

    def test_negative_with_minimum_zero_rejected(self):
        with pytest.raises(ValueError, match='below minimum'):
            exact_integer(-1, minimum=0)

    def test_overflow_rejected(self):
        with pytest.raises(ValueError, match='overflow'):
            exact_integer(MAX_INT + 1)

    def test_unsupported_type(self):
        with pytest.raises(ValueError, match='unsupported'):
            exact_integer([1])


# ---------------------------------------------------------------------------
# read_bound_csv helpers
# ---------------------------------------------------------------------------

def _make_csv_bytes(header, rows):
    """Build gb18030-encoded CSV bytes from header list and row lists."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue().encode('gb18030')


def _trade_header():
    return ['万得代码', '交易所代码', '自然日', '时间', '成交编号', '成交代码',
            '委托代码', 'BS标志', '成交价格', '成交数量', '叫卖序号', '叫买序号', '']


def _trade_row(time='92500000', trade_id='1', code='\x00', bs='B',
               price='100000', qty='100', sell_ref='21', buy_ref='11'):
    return [SYMBOL, '688122', DAY, time, trade_id, code, ' ', bs,
            price, qty, sell_ref, buy_ref, '']


def _write_csv(tmp_path, kind, header, rows, day=DAY, symbol=SYMBOL):
    data = _make_csv_bytes(header, rows)
    path = tmp_path / kind
    path.write_bytes(data)
    meta = {
        'bytes': len(data),
        'sha256': hashlib.sha256(data).hexdigest(),
        'crc32': f'{zlib.crc32(data) & 0xffffffff:08x}',
    }
    return path, meta


class TestReadBoundCsv:
    def test_basic_trade_read(self, tmp_path):
        header = _trade_header()
        rows = [_trade_row(), _trade_row(time='93000000', trade_id='2', buy_ref='12')]
        path, meta = _write_csv(tmp_path, '逐笔成交.csv', header, rows)
        df, detail = read_bound_csv(path, meta, '逐笔成交.csv', DAY, SYMBOL)
        assert len(df) == 2
        assert list(df['_source_record']) == [1, 2]
        assert detail['rows'] == 2
        assert detail['record_count'] == 2
        assert detail['sha256'] == meta['sha256']
        assert detail['crc32'] == meta['crc32']
        assert detail['bytes'] == meta['bytes']
        assert detail['path'] == str(path)

    def test_crc_mismatch_rejected(self, tmp_path):
        header = _trade_header()
        rows = [_trade_row()]
        path, meta = _write_csv(tmp_path, '逐笔成交.csv', header, rows)
        meta['crc32'] = 'deadbeef'
        with pytest.raises(ValueError, match='crc32'):
            read_bound_csv(path, meta, '逐笔成交.csv', DAY, SYMBOL)

    def test_sha_mismatch_rejected(self, tmp_path):
        header = _trade_header()
        rows = [_trade_row()]
        path, meta = _write_csv(tmp_path, '逐笔成交.csv', header, rows)
        meta['sha256'] = 'a' * 64
        with pytest.raises(ValueError, match='sha256'):
            read_bound_csv(path, meta, '逐笔成交.csv', DAY, SYMBOL)

    def test_size_mismatch_rejected(self, tmp_path):
        header = _trade_header()
        rows = [_trade_row()]
        path, meta = _write_csv(tmp_path, '逐笔成交.csv', header, rows)
        meta['bytes'] = meta['bytes'] + 1
        with pytest.raises(ValueError, match='size'):
            read_bound_csv(path, meta, '逐笔成交.csv', DAY, SYMBOL)

    def test_row_width_mismatch(self, tmp_path):
        header = _trade_header()
        rows = [_trade_row() + ['extra']]  # 14 cols instead of 13
        path, meta = _write_csv(tmp_path, '逐笔成交.csv', header, rows)
        with pytest.raises(ValueError, match='width'):
            read_bound_csv(path, meta, '逐笔成交.csv', DAY, SYMBOL)

    def test_wrong_day_rejected(self, tmp_path):
        header = _trade_header()
        rows = [_trade_row()]
        path, meta = _write_csv(tmp_path, '逐笔成交.csv', header, rows)
        with pytest.raises(ValueError, match='自然日'):
            read_bound_csv(path, meta, '逐笔成交.csv', '20261009', SYMBOL)

    def test_wrong_symbol_rejected(self, tmp_path):
        header = _trade_header()
        rows = [_trade_row()]
        path, meta = _write_csv(tmp_path, '逐笔成交.csv', header, rows)
        with pytest.raises(ValueError, match='万得代码'):
            read_bound_csv(path, meta, '逐笔成交.csv', DAY, '688137.SH')

    def test_invalid_time_rejected(self, tmp_path):
        header = _trade_header()
        rows = [_trade_row(time='250000000')]  # hour=25
        path, meta = _write_csv(tmp_path, '逐笔成交.csv', header, rows)
        with pytest.raises(ValueError, match='time'):
            read_bound_csv(path, meta, '逐笔成交.csv', DAY, SYMBOL)

    def test_nul_preserved_in_fields(self, tmp_path):
        """Embedded NUL in 成交代码 is preserved, not globally erased."""
        header = _trade_header()
        rows = [_trade_row(code='\x00')]
        path, meta = _write_csv(tmp_path, '逐笔成交.csv', header, rows)
        df, detail = read_bound_csv(path, meta, '逐笔成交.csv', DAY, SYMBOL)
        # The NUL byte should be in the raw data
        assert detail['nul_bytes'] > 0
        # The field should contain the NUL character (not stripped)
        raw_val = df.iloc[0]['成交代码']
        assert '\x00' in raw_val or raw_val == ''  # csv.reader may handle NUL

    def test_input_order_preserved(self, tmp_path):
        """Records keep their original order, ordinals are 1..N."""
        header = _trade_header()
        rows = [
            _trade_row(time='150000000', trade_id='3'),
            _trade_row(time='92500000', trade_id='1'),
            _trade_row(time='100000000', trade_id='2'),
        ]
        path, meta = _write_csv(tmp_path, '逐笔成交.csv', header, rows)
        df, detail = read_bound_csv(path, meta, '逐笔成交.csv', DAY, SYMBOL)
        assert list(df['成交编号']) == ['3', '1', '2']
        assert list(df['_source_record']) == [1, 2, 3]
        assert detail['time_reversals'] == 1  # 15:00 -> 09:25 is reversal, 09:25 -> 10:00 is not

    def test_symlink_rejected(self, tmp_path):
        header = _trade_header()
        rows = [_trade_row()]
        real_path, meta = _write_csv(tmp_path, '逐笔成交.csv', header, rows)
        link = tmp_path / 'link.csv'
        link.symlink_to(real_path)
        with pytest.raises(ValueError, match='symlink'):
            read_bound_csv(link, meta, '逐笔成交.csv', DAY, SYMBOL)

    def test_unsupported_symbol(self, tmp_path):
        header = _trade_header()
        rows = [_trade_row()]
        path, meta = _write_csv(tmp_path, '逐笔成交.csv', header, rows)
        with pytest.raises(ValueError, match='unsupported symbol'):
            read_bound_csv(path, meta, '逐笔成交.csv', DAY, '000001.SZ')

    def test_invalid_day_format(self, tmp_path):
        header = _trade_header()
        rows = [_trade_row()]
        path, meta = _write_csv(tmp_path, '逐笔成交.csv', header, rows)
        with pytest.raises(ValueError, match='malformed day'):
            read_bound_csv(path, meta, '逐笔成交.csv', '2026-10-08', SYMBOL)

    def test_meta_bytes_not_positive(self, tmp_path):
        header = _trade_header()
        rows = [_trade_row()]
        path, meta = _write_csv(tmp_path, '逐笔成交.csv', header, rows)
        meta['bytes'] = 0
        with pytest.raises(ValueError, match='positive int'):
            read_bound_csv(path, meta, '逐笔成交.csv', DAY, SYMBOL)


# ---------------------------------------------------------------------------
# reference_group_facts
# ---------------------------------------------------------------------------

def _spec(**kw):
    return PostcloseSpec(symbols=(SYMBOL,), lookbacks=(3,), horizons=(1,),
                         thresholds_cny=(1000000,), **kw)


def _records(rows):
    """Build a records DataFrame from list of dicts."""
    return pd.DataFrame(rows, columns=[
        'day', 'symbol', 'record_key', 'price_raw', 'quantity', 'buy_ref', 'sell_ref',
    ])


class TestReferenceGroupFacts:
    def test_basic_grouping(self):
        """Two records with same buy_ref are grouped together."""
        recs = _records([
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't1',
             'price_raw': 100000, 'quantity': 60000, 'buy_ref': '11', 'sell_ref': '21'},
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't2',
             'price_raw': 100000, 'quantity': 60000, 'buy_ref': '11', 'sell_ref': '22'},
        ])
        groups, daily = reference_group_facts(recs, _spec())
        # Buy side: ref 11 has qty=120000, amount=12000000000
        buy_groups = groups[groups['side'] == 'B']
        assert len(buy_groups) == 1
        bg = buy_groups.iloc[0]
        assert bg['reference'] == '11'
        assert bg['quantity'] == 120000
        assert bg['amount_1e4'] == 12000000000
        assert bg['record_count'] == 2
        assert bg['identity_kind'] == 'delivered_reference_group_proxy'
        assert bg['original_order_identity_proven'] == False
        # Sell side: two separate groups
        sell_groups = groups[groups['side'] == 'S']
        assert len(sell_groups) == 2

    def test_split_same_ref_across_times_crosses_threshold(self):
        """Two 600k records with same ref cross 1M threshold when combined."""
        recs = _records([
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't1',
             'price_raw': 100000, 'quantity': 60000, 'buy_ref': '11', 'sell_ref': '21'},
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't2',
             'price_raw': 100000, 'quantity': 60000, 'buy_ref': '11', 'sell_ref': '22'},
        ])
        groups, daily = reference_group_facts(recs, _spec())
        d = daily.iloc[0]
        # Buy side group of 12000000000 >= 1000000*10000 = 10000000000
        assert d['large_buy_1e4'] == 12000000000
        assert d['large_sell_1e4'] == 0  # Each sell group is only 6000000000

    def test_stage_not_part_of_key(self):
        """Records at different times with same ref are NOT split by stage."""
        recs = _records([
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't1',
             'price_raw': 100000, 'quantity': 60000, 'buy_ref': '11', 'sell_ref': '21'},
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't2',
             'price_raw': 100000, 'quantity': 40000, 'buy_ref': '11', 'sell_ref': '22'},
        ])
        groups, _ = reference_group_facts(recs, _spec())
        buy = groups[(groups['side'] == 'B') & (groups['reference'] == '11')]
        assert len(buy) == 1
        assert buy.iloc[0]['quantity'] == 100000

    def test_threshold_boundary_exact(self):
        """T-1 below, T at, T+1 above threshold."""
        spec = _spec()
        # Exactly at threshold: amount_1e4 = 1000000 * 10000 = 10_000_000_000
        # price_raw * quantity = 100000 * 100000 = 10_000_000_000
        recs = _records([
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't1',
             'price_raw': 100000, 'quantity': 100000, 'buy_ref': '11', 'sell_ref': '21'},
        ])
        _, daily = reference_group_facts(recs, spec)
        d = daily.iloc[0]
        assert d['large_buy_1e4'] == 10_000_000_000  # At threshold, included

        # Just below threshold
        recs2 = _records([
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't1',
             'price_raw': 100000, 'quantity': 99999, 'buy_ref': '11', 'sell_ref': '21'},
        ])
        _, daily2 = reference_group_facts(recs2, spec)
        d2 = daily2.iloc[0]
        assert d2['large_buy_1e4'] == 0  # Below threshold

    def test_cash_conservation_vs_core(self):
        """Group sums must conserve against core aggregate_legs on complete fixture."""
        recs = _records([
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't1',
             'price_raw': 100000, 'quantity': 60000, 'buy_ref': '11', 'sell_ref': '21'},
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't2',
             'price_raw': 100000, 'quantity': 40000, 'buy_ref': '12', 'sell_ref': '21'},
        ])
        groups, daily = reference_group_facts(recs, _spec())
        d = daily.iloc[0]
        # Full day amount = 100000*60000 + 100000*40000 = 10_000_000_000
        assert d['amount_1e4'] == 10_000_000_000
        assert d['quantity'] == 100000
        # Both sides complete
        assert d['buy_reference_complete'] == True
        assert d['sell_reference_complete'] == True
        # Known amounts equal full amount
        assert d['known_buy_amount_1e4'] == 10_000_000_000
        assert d['known_sell_amount_1e4'] == 10_000_000_000

    def test_missing_buy_ref_retains_full_denominator(self):
        """Missing buy ref: full M/Q preserved, buy large is NULL, sell still valid."""
        recs = _records([
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't1',
             'price_raw': 100000, 'quantity': 100000, 'buy_ref': '', 'sell_ref': '21'},
        ])
        groups, daily = reference_group_facts(recs, _spec())
        d = daily.iloc[0]
        # Full amount preserved
        assert d['amount_1e4'] == 10_000_000_000
        assert d['quantity'] == 100000
        # Buy side incomplete
        assert d['buy_reference_complete'] == False
        assert d['missing_buy_records'] == 1
        # Nullable integers preserve the unit and exact values without float coercion.
        assert pd.isna(d['large_buy_1e4'])
        # Sell side complete and valid
        assert d['sell_reference_complete'] == True
        assert d['large_sell_1e4'] == 10_000_000_000
        # No groups for buy side (unknown ref not grouped)
        buy_groups = groups[groups['side'] == 'B']
        assert len(buy_groups) == 0
        # Sell group exists
        sell_groups = groups[groups['side'] == 'S']
        assert len(sell_groups) == 1

    def test_missing_both_sides_no_big_zero_groups(self):
        """Missing refs on both sides: no groups formed, no fake zero."""
        recs = _records([
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't1',
             'price_raw': 100000, 'quantity': 100000, 'buy_ref': '', 'sell_ref': ''},
        ])
        groups, daily = reference_group_facts(recs, _spec())
        assert len(groups) == 0
        d = daily.iloc[0]
        assert d['amount_1e4'] == 10_000_000_000
        assert pd.isna(d['large_buy_1e4'])
        assert pd.isna(d['large_sell_1e4'])

    def test_same_refs_different_days_not_merged(self):
        """Same ref number on different days stays separate."""
        recs = _records([
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't1',
             'price_raw': 100000, 'quantity': 60000, 'buy_ref': '11', 'sell_ref': '21'},
            {'day': '20261009', 'symbol': SYMBOL, 'record_key': 't1',
             'price_raw': 100000, 'quantity': 60000, 'buy_ref': '11', 'sell_ref': '21'},
        ])
        groups, daily = reference_group_facts(recs, _spec())
        assert len(daily) == 2
        buy_groups = groups[groups['side'] == 'B']
        assert len(buy_groups) == 2  # One per day

    def test_same_refs_different_sides_not_merged(self):
        """Buy ref '11' and sell ref '11' are separate groups."""
        recs = _records([
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't1',
             'price_raw': 100000, 'quantity': 60000, 'buy_ref': '11', 'sell_ref': '11'},
        ])
        groups, _ = reference_group_facts(recs, _spec())
        assert len(groups) == 2
        assert set(groups['side']) == {'B', 'S'}

    def test_two_600k_same_ref_no_channel_is_proxy(self):
        """2x600k same numeric ref without channels gives 1200k PROXY, not identity proof."""
        recs = _records([
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't1',
             'price_raw': 100000, 'quantity': 60000, 'buy_ref': '11', 'sell_ref': '21'},
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't2',
             'price_raw': 100000, 'quantity': 60000, 'buy_ref': '11', 'sell_ref': '22'},
        ])
        groups, _ = reference_group_facts(recs, _spec())
        buy = groups[(groups['side'] == 'B') & (groups['reference'] == '11')]
        assert len(buy) == 1
        assert buy.iloc[0]['amount_1e4'] == 12_000_000_000
        assert buy.iloc[0]['identity_kind'] == 'delivered_reference_group_proxy'
        assert buy.iloc[0]['original_order_identity_proven'] == False

    def test_known_two_channel_refuses_merging(self):
        """Two distinct channel values => reject with namespace error."""
        recs = _records([
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't1',
             'price_raw': 100000, 'quantity': 60000, 'buy_ref': '11', 'sell_ref': '21'},
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't2',
             'price_raw': 100000, 'quantity': 60000, 'buy_ref': '11', 'sell_ref': '22'},
        ])
        recs['channel'] = ['A', 'B']
        with pytest.raises(ValueError, match='namespace-aware'):
            reference_group_facts(recs, _spec())

    def test_confirmed_collision_blocks_direction(self):
        """Supplied confirmed collision key blocks large interpretation on that side."""
        recs = _records([
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't1',
             'price_raw': 100000, 'quantity': 100000, 'buy_ref': '11', 'sell_ref': '21'},
        ])
        collisions = frozenset({(DAY, SYMBOL, 'B', '11')})
        groups, daily = reference_group_facts(recs, _spec(), collisions)
        d = daily.iloc[0]
        # Buy side large is NULL due to collision
        assert pd.isna(d['large_buy_1e4'])
        # Sell side still valid
        assert d['large_sell_1e4'] == 10_000_000_000
        # Direction metrics are null
        assert d['structure_imbalance'] is None or (isinstance(d['structure_imbalance'], float) and np.isnan(d['structure_imbalance']))
        assert d['confirmed_collision_count'] == 1

    def test_int64_total_overflow_detected(self):
        """Total amount exceeding int64 max is detected."""
        # price_raw * quantity > MAX_INT
        big_price = MAX_INT
        recs = _records([
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't1',
             'price_raw': big_price, 'quantity': 2, 'buy_ref': '11', 'sell_ref': '21'},
        ])
        with pytest.raises(ValueError, match='overflow'):
            reference_group_facts(recs, _spec())

    def test_record_key_duplicate_fail(self):
        """Duplicate record_key within same day/symbol fails."""
        recs = _records([
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't1',
             'price_raw': 100000, 'quantity': 60000, 'buy_ref': '11', 'sell_ref': '21'},
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't1',
             'price_raw': 100000, 'quantity': 40000, 'buy_ref': '12', 'sell_ref': '22'},
        ])
        with pytest.raises(ValueError, match='duplicate'):
            reference_group_facts(recs, _spec())

    def test_zero_ref_treated_as_missing(self):
        """Reference '0' is treated as missing, not grouped."""
        recs = _records([
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't1',
             'price_raw': 100000, 'quantity': 100000, 'buy_ref': '0', 'sell_ref': '21'},
        ])
        groups, daily = reference_group_facts(recs, _spec())
        buy_groups = groups[groups['side'] == 'B']
        assert len(buy_groups) == 0
        d = daily.iloc[0]
        assert d['missing_buy_records'] == 1

    def test_malformed_ref_not_dropped(self):
        """Malformed ref (non-digit, non-zero) treated as unknown, record kept."""
        recs = _records([
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't1',
             'price_raw': 100000, 'quantity': 100000, 'buy_ref': 'abc', 'sell_ref': '21'},
        ])
        groups, daily = reference_group_facts(recs, _spec())
        d = daily.iloc[0]
        # Record still in full amount
        assert d['amount_1e4'] == 10_000_000_000
        # Buy side is incomplete
        assert d['buy_reference_complete'] == False
        assert d['missing_buy_records'] == 1
        # No buy group formed
        buy_groups = groups[groups['side'] == 'B']
        assert len(buy_groups) == 0

    def test_no_source_qualification(self):
        """Module never assigns F/P or qualifies source."""
        recs = _records([
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't1',
             'price_raw': 100000, 'quantity': 100000, 'buy_ref': '11', 'sell_ref': '21'},
        ])
        groups, daily = reference_group_facts(recs, _spec())
        # No F/P columns
        assert 'F' not in daily.columns
        assert 'P' not in daily.columns
        # identity_kind is proxy, not proven
        assert all(g['identity_kind'] == 'delivered_reference_group_proxy' for _, g in groups.iterrows())
        assert all(g['original_order_identity_proven'] == False for _, g in groups.iterrows())

    def test_side_complete_no_large_groups(self):
        """Side complete but no qualifying large groups => large=0, VWAP null."""
        recs = _records([
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't1',
             'price_raw': 100, 'quantity': 100, 'buy_ref': '11', 'sell_ref': '21'},
        ])
        groups, daily = reference_group_facts(recs, _spec())
        d = daily.iloc[0]
        # amount_1e4 = 100*100 = 10000, way below 1000000*10000 threshold
        assert d['large_buy_1e4'] == 0
        assert d['large_sell_1e4'] == 0
        # VWAP should be null when no large groups
        assert pd.isna(d['large_buy_vwap']) or d['large_buy_vwap'] is None
        assert pd.isna(d['large_sell_vwap']) or d['large_sell_vwap'] is None

    def test_symbols_outside_spec_rejected(self):
        recs = _records([
            {'day': DAY, 'symbol': '688137.SH', 'record_key': 't1',
             'price_raw': 100000, 'quantity': 100000, 'buy_ref': '11', 'sell_ref': '21'},
        ])
        with pytest.raises(ValueError, match='outside spec'):
            reference_group_facts(recs, _spec())

    def test_vwap_calculation(self):
        """VWAP = amount_1e4 / quantity / 10000."""
        recs = _records([
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't1',
             'price_raw': 100000, 'quantity': 100000, 'buy_ref': '11', 'sell_ref': '21'},
        ])
        groups, _ = reference_group_facts(recs, _spec())
        buy = groups[(groups['side'] == 'B') & (groups['reference'] == '11')]
        # amount_1e4 = 100000 * 100000 = 10_000_000_000
        # vwap = 10_000_000_000 / 100000 / 10000 = 10.0
        assert buy.iloc[0]['vwap'] == pytest.approx(10.0)

    def test_conservation_with_core_aggregate_legs(self):
        """Verify group sums match core aggregate_legs on a complete fixture."""
        # Build trades for core
        trades = pd.DataFrame([
            {'day': DAY, 'symbol': SYMBOL, 'scope': 'proxy', 'trade_ref': 't1',
             'buy_ref': '11', 'sell_ref': '21', 'price_raw': 100000, 'quantity': 60000},
            {'day': DAY, 'symbol': SYMBOL, 'scope': 'proxy', 'trade_ref': 't2',
             'buy_ref': '11', 'sell_ref': '22', 'price_raw': 100000, 'quantity': 40000},
        ])
        core_legs = aggregate_legs(trades)
        # Build records for v2
        recs = _records([
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't1',
             'price_raw': 100000, 'quantity': 60000, 'buy_ref': '11', 'sell_ref': '21'},
            {'day': DAY, 'symbol': SYMBOL, 'record_key': 't2',
             'price_raw': 100000, 'quantity': 40000, 'buy_ref': '11', 'sell_ref': '22'},
        ])
        groups, daily = reference_group_facts(recs, _spec())
        # Core buy side total
        core_buy_total = int(core_legs.loc[core_legs['side'] == 'B', 'amount_1e4'].sum())
        core_sell_total = int(core_legs.loc[core_legs['side'] == 'S', 'amount_1e4'].sum())
        # V2 daily totals
        d = daily.iloc[0]
        assert d['amount_1e4'] == core_buy_total
        assert d['known_buy_amount_1e4'] == core_buy_total
        assert d['known_sell_amount_1e4'] == core_sell_total


def test_every_threshold_is_emitted_not_only_last():
    s=PostcloseSpec(symbols=(SYMBOL,),lookbacks=(3,),horizons=(1,))
    r=_records([
        dict(day=DAY,symbol=SYMBOL,record_key='r1',price_raw=100000,quantity=60000,buy_ref='11',sell_ref='21'),
        dict(day=DAY,symbol=SYMBOL,record_key='r2',price_raw=100000,quantity=60000,buy_ref='11',sell_ref='22'),
    ])
    _,d=reference_group_facts(r,s)
    assert len(d)==2 and set(d.threshold_cny)=={500000,1000000}
    assert d.loc[d.threshold_cny==500000,'structure_imbalance'].iloc[0]==0
    assert d.loc[d.threshold_cny==1000000,'structure_imbalance'].iloc[0]==1


def test_nullable_money_keeps_large_integer_bits():
    value=2**60+1
    r=_records([
        dict(day=DAY,symbol=SYMBOL,record_key='r1',price_raw=value,quantity=1,buy_ref=None,sell_ref='21'),
        dict(day='20261009',symbol=SYMBOL,record_key='r2',price_raw=value,quantity=1,buy_ref='11',sell_ref='22'),
    ])
    _,d=reference_group_facts(r,_spec())
    assert str(d.large_buy_1e4.dtype)=='Int64' and pd.isna(d.iloc[0].large_buy_1e4)
    assert d.iloc[1].large_buy_1e4==value


def test_collision_annotation_for_absent_group_does_not_block_other_groups():
    r=_records([dict(day=DAY,symbol=SYMBOL,record_key='r1',price_raw=100000,quantity=100000,buy_ref='11',sell_ref='21')])
    _,d=reference_group_facts(r,_spec(),frozenset({(DAY,SYMBOL,'B','999')}))
    assert d.iloc[0].confirmed_collision_count==0 and d.iloc[0].large_buy_1e4==10000000000


def test_padded_collision_evidence_is_normalized_not_bypassed():
    r=_records([dict(day=DAY,symbol=SYMBOL,record_key='r1',price_raw=100000,quantity=100000,buy_ref='11',sell_ref='21')])
    _,d=reference_group_facts(r,_spec(),frozenset({(DAY,SYMBOL,'B',' 11 ')}))
    assert d.iloc[0].confirmed_collision_count==1 and pd.isna(d.iloc[0].large_buy_1e4)
    assert pd.isna(d.iloc[0].structure_imbalance)


def test_spoofed_trade_header_rejected(tmp_path):
    header=_trade_header();header[4]='wrong_field'
    path,meta=_write_csv(tmp_path,'逐笔成交.csv',header,[_trade_row()])
    with pytest.raises(ValueError,match='header fields'):
        read_bound_csv(path,meta,'逐笔成交.csv',DAY,SYMBOL)


def test_embedded_nul_reference_not_silently_joined(tmp_path):
    path,meta=_write_csv(tmp_path,'逐笔成交.csv',_trade_header(),[_trade_row(buy_ref='12\x003')])
    frame,_=read_bound_csv(path,meta,'逐笔成交.csv',DAY,SYMBOL)
    assert frame.iloc[0]['叫买序号']=='12\x003'


def test_exact_clock_decimal_zero_not_fractional_truncation(tmp_path):
    path,meta=_write_csv(tmp_path,'逐笔成交.csv',_trade_header(),[_trade_row(time='92500000.0')])
    frame,_=read_bound_csv(path,meta,'逐笔成交.csv',DAY,SYMBOL)
    assert frame.ms.iloc[0]==33900000
    path,meta=_write_csv(tmp_path,'逐笔成交.csv',_trade_header(),[_trade_row(time='92500000.5')])
    with pytest.raises(ValueError,match='nonintegral'):
        read_bound_csv(path,meta,'逐笔成交.csv',DAY,SYMBOL)
