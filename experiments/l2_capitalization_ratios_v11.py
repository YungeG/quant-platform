"""Exact, historical-only capitalization views of the accepted v11 tables.

No source reread, cash reclassification, future outcomes, or changed membership.
Ratios divide five-day differences by the single 20261019 total market cap.
"""
import argparse
import csv
import hashlib
import io
import json
import re
from collections import Counter
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

HOME = Path('/srv/bcache-8t/ygguo/quant/l2-historical-candidates-v11')


def money(value):
    if value is None or value == '':
        return None
    if type(value) is int:
        return value
    if isinstance(value, str) and re.fullmatch(r'[+-]?[0-9]+', value):
        return int(value)
    raise ValueError('money must be an exact integer, not float/truncated input')


def cap_ratio(amount_1e4, total_mv_cny):
    if isinstance(total_mv_cny, (float, bool)):
        raise ValueError('market cap must not pass through float')
    cap = Decimal(total_mv_cny)
    if not cap.is_finite() or cap <= 0:
        raise ValueError('invalid market cap')
    amount = money(amount_1e4)
    return None if amount is None else Fraction(amount, 10000) / Fraction(cap)


def percentage(value):
    if value is None:
        return ''
    with localcontext() as ctx:
        ctx.prec = 80
        return format((Decimal(value.numerator) * 100 / Decimal(value.denominator)).quantize(Decimal('.000001')), 'f')


def sort_key(row, component):
    days = 'group_positive_days' if component == 'group' else 'active_positive_days'
    ratio = cap_ratio(row[component + '_difference_1e4'], row['total_mv_cny'])
    if row['class'] not in ('A', 'B') or ratio is None:
        raise ValueError('only complete A/B candidates can enter comparison ranks')
    concentration = Fraction(money(row['top2_positive_delta_numerator_1e4']), money(row['positive_delta_denominator_1e4']))
    return (row['class'], -ratio, -money(row[days]), concentration, row['symbol'])


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(spec_path, output, smoke=False):
    spec_bytes = Path(spec_path).read_bytes()
    spec = json.loads(spec_bytes)
    source = Path(spec['source_dir']).resolve()
    output = Path(output).resolve()
    if output.exists() or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError('use a new output outside the original results')
    frozen = {}
    for name, expected in spec['inputs'].items():
        path = Path(name)
        if path.is_symlink() or path.stat().st_size > 8 * 1024**2:
            raise ValueError('unsafe/oversized derived input')
        data = path.read_bytes()
        if sha(data) != expected:
            raise ValueError('frozen input changed: ' + name)
        frozen[name] = data
    if sum(map(len, frozen.values())) > 16 * 1024**2:
        raise ValueError('input byte budget exceeded')

    def rows(name):
        return list(csv.DictReader(io.StringIO(frozen[str(source / name)].decode('utf-8-sig'))))

    all_rows, candidates, readable = (rows(n) for n in ('all_stocks.csv', 'candidates.csv', 'candidates_readable.csv'))
    if (len(all_rows) != spec['expected_symbols'] or len(candidates) != spec['expected_candidates']
            or Counter(r['class'] for r in all_rows) != spec['expected_classes']):
        raise ValueError('source coverage/classes changed')
    lookup = {r['symbol']: r for r in all_rows}
    if len(lookup) != len(all_rows) or len(readable) != len(candidates):
        raise ValueError('duplicate or incomplete source tables')
    original_rank = {r['symbol']: i for i, r in enumerate(candidates, 1)}
    if len(original_rank) != len(candidates) or any(r != lookup[r['symbol']] for r in candidates):
        raise ValueError('candidate projection/membership mismatch')
    if [r['股票代码'] for r in readable] != [r['symbol'] for r in candidates]:
        raise ValueError('readable candidate order changed')
    for r in all_rows:
        cap = Decimal(r['total_mv_cny'])
        if (r['asof'] != '20261019' or r['start'] != '20261013' or r['day'] != '20261019'
                or not cap.is_finite() or not Decimal('6000000000') <= cap <= Decimal('100000000000')
                or r['new_trigger_status'] != 'not_assessed' or r['reference_next_open'] != 'pending'):
            raise ValueError('formation cutoff/capability mismatch')
        for component in ('group', 'active'):
            value = cap_ratio(r[component + '_difference_1e4'], r['total_mv_cny'])
            if (value is None) != (r['class'] == 'D'):
                raise ValueError('unexpected money mask')
    # Share the canonical row objects so every exported view receives the new columns.
    candidates = [lookup[r['symbol']] for r in candidates]
    if smoke:
        selected = set(spec['smoke_symbols'])
        all_rows = [r for r in all_rows if r['symbol'] in selected]
        candidates = [r for r in candidates if r['symbol'] in selected]
        readable = [r for r in readable if r['股票代码'] in selected]
        if len(all_rows) != len(selected):
            raise ValueError('smoke roster missing')
    comparisons, ranks = {}, {}
    for component in ('group', 'active'):
        comparisons[component] = sorted(candidates, key=lambda r: sort_key(r, component))
        counts = Counter()
        ranks[component] = {}
        for r in comparisons[component]:
            counts[r['class']] += 1
            ranks[component][r['symbol']] = counts[r['class']]
    for r in all_rows:
        r['original_formation_rank'] = original_rank.get(r['symbol'], '')
        for component in ('group', 'active'):
            ratio = cap_ratio(r[component + '_difference_1e4'], r['total_mv_cny'])
            r[component + '_cap_pct'] = percentage(ratio)
            r[component + '_cap_rank_within_class'] = ranks[component].get(r['symbol'], '')
    for r in readable:
        raw = lookup[r['股票代码']]
        for component, label in [('group', '组差'), ('active', '主动差')]:
            r[label + '_总市值_pct'] = raw[component + '_cap_pct']
            r[label + '市值比_类内排名'] = raw[component + '_cap_rank_within_class']
    output.mkdir(parents=True)
    outputs = {}

    def save(name, data):
        with (output / name).open('x', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(data[0]))
            writer.writeheader()
            writer.writerows(data)
        outputs[name] = sha((output / name).read_bytes())

    save('all_stocks_enriched.csv', all_rows)
    save('candidates_enriched.csv', candidates)
    save('candidates_readable.csv', readable)
    for component in ('group', 'active'):
        save('candidates_by_' + component + '_cap.csv', comparisons[component])
    result = {'role': 'local_historical_ratio_comparison_not_new_selection_or_backtest',
              'mode': 'smoke' if smoke else 'full', 'asof': '20261019', 'symbols': len(all_rows),
              'candidates': len(candidates), 'classes': dict(Counter(r['class'] for r in all_rows)),
              'original_selection_and_order_preserved': True, 'source_full_complete': False,
              'rank_precision': 'exact Fraction; percentages displayed to six decimals',
              'code_sha256': sha(Path(__file__).read_bytes()), 'spec_sha256': sha(spec_bytes),
              'inputs': spec['inputs'], 'outputs': outputs,
              'formal_provider_or_forecast': False, 'new_trigger_status': 'not_assessed'}
    (output / 'summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', default=str(HOME / 'capitalization_ratio_spec_v1.json'))
    parser.add_argument('--output', required=True)
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    print(json.dumps(run(args.spec, args.output, args.smoke), ensure_ascii=False))
