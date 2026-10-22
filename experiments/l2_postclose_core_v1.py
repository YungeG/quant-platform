"""Pure postclose arithmetic; no source acceptance, I/O, fills, PnL or predictions.

All *_1e4 fields are EXACT INTEGER CNY*10000, never floating CNY. Callers
must qualify source semantics/calendar separately; tests do not qualify real data.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from itertools import product
import json

import numpy as np
import pandas as pd

SUPPORTED_SYMBOLS = frozenset({'688122.SH', '688137.SH', '688655.SH'})
MAX_INT = int(np.iinfo(np.int64).max)


def _axis(name, values):
    if not isinstance(values, tuple) or not values:
        raise ValueError(f'{name} must be a nonempty tuple')
    if any(type(v) is not int or v <= 0 for v in values):
        raise ValueError(f'{name} requires positive true ints')
    if tuple(sorted(set(values))) != values:
        raise ValueError(f'{name} must be sorted unique')
    return values


@dataclass(frozen=True)
class PostcloseSpec:
    symbols: tuple[str, ...] = ('688122.SH', '688137.SH', '688655.SH')
    lookbacks: tuple[int, ...] = (3, 5, 10, 20)
    horizons: tuple[int, ...] = (1, 3, 5, 10, 20)
    thresholds_cny: tuple[int, ...] = (500000, 1000000)
    primary_threshold_cny: int = 1000000
    seed: int = 0
    max_cells: int = 120

    def __post_init__(self):
        if not isinstance(self.symbols, tuple) or not self.symbols:
            raise ValueError('symbols must be a nonempty tuple')
        if any(not isinstance(s, str) or s not in SUPPORTED_SYMBOLS for s in self.symbols):
            raise ValueError('unsupported symbol')
        if tuple(sorted(set(self.symbols))) != self.symbols:
            raise ValueError('symbols must be sorted unique')
        for name in ('lookbacks', 'horizons', 'thresholds_cny'):
            _axis(name, getattr(self, name))
        if type(self.primary_threshold_cny) is not int or self.primary_threshold_cny not in self.thresholds_cny:
            raise ValueError('primary_threshold_cny must be in thresholds_cny')
        if type(self.seed) is not int or self.seed < 0:
            raise ValueError('seed must be a nonnegative true int')
        if type(self.max_cells) is not int or not 1 <= self.max_cells <= 120:
            raise ValueError('max_cells must be within 1..120')
        if len(self.symbols) * len(self.lookbacks) * len(self.horizons) * len(self.thresholds_cny) > self.max_cells:
            raise ValueError('grid budget exceeded')


def _day(value):
    if not isinstance(value, str) or len(value) != 8 or not value.isdigit():
        raise ValueError(f'malformed day: {value!r}')
    try:
        datetime.strptime(value, '%Y%m%d')
    except ValueError as exc:
        raise ValueError(f'malformed day: {value!r}') from exc
    return value


def _calendar(calendar):
    if not isinstance(calendar, tuple) or not calendar:
        raise ValueError('calendar must be a nonempty tuple')
    for d in calendar:
        _day(d)
    if tuple(sorted(set(calendar))) != calendar:
        raise ValueError('calendar must be sorted unique')
    return calendar


def _int(value, name, minimum=0):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise ValueError(f'{name} must be integer, not bool or float')
    value = int(value)
    if value < minimum:
        raise ValueError(f'{name} must be {"positive" if minimum == 1 else "nonnegative"}')
    if value > MAX_INT:
        raise ValueError(f'{name} overflow')
    return value


def _total(values, name):
    return _int(sum(int(x) for x in values), name)


def _id(value, name):
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f'{name} must be canonical nonempty strings')
    if name != 'scope' and (value == '0.0' or (value.isdigit() and int(value) == 0)):
        raise ValueError(f'{name} cannot be zero')
    return value


def _frame(frame, columns, keys):
    if not isinstance(frame, pd.DataFrame) or not set(columns).issubset(frame.columns):
        raise ValueError(f'missing required columns: {sorted(set(columns) - set(getattr(frame, "columns", [])))}')
    if frame.duplicated(keys).any():
        raise ValueError(f'duplicate keys: {keys}')
    for d in frame.day.unique():
        _day(d)
    if set(frame.symbol.unique()) - SUPPORTED_SYMBOLS:
        raise ValueError('unsupported symbol')


def _flags(frame, names):
    for name in names:
        if any(not isinstance(v, (bool, np.bool_)) for v in frame[name]):
            raise ValueError(f'{name} must be actual bool values')


def _segment(value):
    return value if isinstance(value, str) and value.strip() and value != 'UNKNOWN' else None


def aggregate_legs(trades: pd.DataFrame) -> pd.DataFrame:
    columns = ('day', 'symbol', 'scope', 'trade_ref', 'buy_ref', 'sell_ref', 'price_raw', 'quantity')
    _frame(trades, columns, ['day', 'symbol', 'scope', 'trade_ref'])
    rows = []
    for r in trades.itertuples(index=False):
        for name in ('scope', 'trade_ref', 'buy_ref', 'sell_ref'):
            _id(getattr(r, name), name)
        price, qty = _int(r.price_raw, 'price_raw', 1), _int(r.quantity, 'quantity', 1)
        amount = _int(price * qty, 'scaled amount', 1)
        for side, ref in (('B', r.buy_ref), ('S', r.sell_ref)):
            rows.append((r.day, r.symbol, r.scope, side, ref, qty, amount))
    out_columns = ['day', 'symbol', 'scope', 'side', 'order_ref', 'quantity', 'amount_1e4', 'trade_count', 'vwap']
    if not rows:
        return pd.DataFrame(columns=out_columns)
    legs = pd.DataFrame(rows, columns=out_columns[:7])
    # Object integers prevent overflow in intermediate pandas group sums.
    for name in ('quantity', 'amount_1e4'):
        legs[name] = legs[name].astype(object)
    result = legs.groupby(out_columns[:5], sort=False, dropna=False).agg(quantity=('quantity', 'sum'), amount_1e4=('amount_1e4', 'sum'), trade_count=('order_ref', 'size')).reset_index()
    for name in ('quantity', 'amount_1e4'):
        result[name] = result[name].map(lambda x: _int(x, name, 1)).astype('int64')
    result['vwap'] = result.amount_1e4 / result.quantity / 10000
    for (day, symbol, scope), group in result.groupby(['day', 'symbol', 'scope']):
        b, s = group.loc[group.side == 'B'], group.loc[group.side == 'S']
        for name in ('quantity', 'amount_1e4'):
            if _total(b[name], name) != _total(s[name], name):
                raise ValueError('side conservation failure')
    return result[out_columns]


def daily_large_structure(trades: pd.DataFrame, legs: pd.DataFrame, spec: PostcloseSpec) -> pd.DataFrame:
    expected = aggregate_legs(trades)
    if set(expected.symbol)-set(spec.symbols):
        raise ValueError('trades outside requested symbol scope')
    keys = ['day', 'symbol', 'scope', 'side', 'order_ref']
    _frame(legs, keys + ['quantity', 'amount_1e4', 'trade_count'], keys)
    for name in ('quantity', 'amount_1e4', 'trade_count'):
        for value in legs[name]:
            _int(value, name, 1)
    a, b = expected.set_index(keys).sort_index(), legs.set_index(keys).sort_index()
    if not a.index.equals(b.index) or any(not a[c].equals(b[c].astype('int64')) for c in ('quantity', 'amount_1e4', 'trade_count')):
        raise ValueError('legs do not conserve exact per-order quantities/cash')
    output = []
    for (day, symbol), group in expected.groupby(['day', 'symbol'], sort=False):
        buy, sell = group.loc[group.side == 'B'], group.loc[group.side == 'S']
        total, qty = _total(buy.amount_1e4, 'daily amount'), _total(buy.quantity, 'daily quantity')
        if total != _total(sell.amount_1e4, 'daily amount') or qty != _total(sell.quantity, 'daily quantity'):
            raise ValueError('daily conservation failure')
        for threshold in spec.thresholds_cny:
            lb = buy.loc[buy.amount_1e4 >= threshold * 10000]
            ls = sell.loc[sell.amount_1e4 >= threshold * 10000]
            bm, sm = _total(lb.amount_1e4, 'large buy'), _total(ls.amount_1e4, 'large sell')
            bq, sq = _total(lb.quantity, 'large buy qty'), _total(ls.quantity, 'large sell qty')
            output.append({'day': day, 'symbol': symbol, 'threshold_cny': threshold, 'amount_1e4': total, 'quantity': qty, 'large_buy_1e4': bm, 'large_sell_1e4': sm, 'structure_imbalance': (bm-sm)/total, 'large_participation': (bm+sm)/(2*total), 'large_buy_vwap': bm/bq/10000 if bq else np.nan, 'large_sell_vwap': sm/sq/10000 if sq else np.nan})
    return pd.DataFrame(output, columns=['day', 'symbol', 'threshold_cny', 'amount_1e4', 'quantity', 'large_buy_1e4', 'large_sell_1e4', 'structure_imbalance', 'large_participation', 'large_buy_vwap', 'large_sell_vwap'])


def _validate_daily(daily, cal):
    fields = ['day','symbol','threshold_cny','amount_1e4','quantity','large_buy_1e4','large_sell_1e4','trade_ok','order_ok','close_raw','close_ok','price_segment']
    _frame(daily, fields, ['day', 'symbol', 'threshold_cny'])
    _flags(daily, ['trade_ok', 'order_ok', 'close_ok'])
    if set(daily.day) - set(cal):
        raise ValueError('daily date outside calendar')
    for r in daily.itertuples(index=False):
        _int(r.threshold_cny, 'threshold_cny', 1)
        if r.trade_ok:
            total = _int(r.amount_1e4, 'amount_1e4', 1)
            _int(r.quantity, 'quantity', 1)
            if r.order_ok:
                for name in ('large_buy_1e4', 'large_sell_1e4'):
                    if _int(getattr(r, name), name) > total:
                        raise ValueError('large side exceeds total')
        if r.close_ok:
            _int(r.close_raw, 'close_raw', 1)


def rolling_profiles(daily: pd.DataFrame, calendar: tuple[str,...], spec: PostcloseSpec) -> pd.DataFrame:
    cal = _calendar(calendar)
    _validate_daily(daily, cal)
    mapping = {(r.day,r.symbol,int(r.threshold_cny)):r for r in daily.itertuples(index=False)}
    rows = []
    for symbol, threshold, W in product(spec.symbols, spec.thresholds_cny, spec.lookbacks):
        for i, day in enumerate(cal):
            row = {'day':day,'symbol':symbol,'threshold_cny':threshold,'lookback':W,'structure_status':'warmup','price_status':'warmup','imbalance':np.nan,'positive_fraction':np.nan,'negative_fraction':np.nan,'vwap':np.nan,'first_close':np.nan,'close':np.nan,'F':None,'P':None,'description':'数据不足'}
            if i + 1 < W:
                rows.append(row); continue
            window = [mapping.get((d,symbol,threshold)) for d in cal[i-W+1:i+1]]
            if any(r is None for r in window):
                row.update(structure_status='missing_day',price_status='missing_day')
                rows.append(row); continue
            trade_ok = all(r.trade_ok for r in window)
            order_ok = all(r.order_ok for r in window)
            row['structure_status'] = 'trade_unqualified' if not trade_ok else ('order_unqualified' if not order_ok else 'ok')
            if row['structure_status'] == 'ok':
                total = _total((r.amount_1e4 for r in window),'window amount')
                diffs = [int(r.large_buy_1e4)-int(r.large_sell_1e4) for r in window]
                imbalance = sum(diffs)/total
                pos, neg = sum(v>0 for v in diffs)/W, sum(v<0 for v in diffs)/W
                row.update(imbalance=imbalance,positive_fraction=pos,negative_fraction=neg,F=bool(imbalance>0 and pos>.5))
            segments = [_segment(r.price_segment) for r in window]
            if not trade_ok:
                row['price_status']='trade_unqualified'
            elif not all(r.close_ok for r in window):
                row['price_status']='close_unqualified'
            elif any(s is None for s in segments):
                row['price_status']='price_basis_unknown'
            elif len(set(segments)) != 1:
                row['price_status']='action_crossed'
            else:
                amount = _total((r.amount_1e4 for r in window),'window amount')
                qty = _total((r.quantity for r in window),'window quantity')
                last_raw, first_raw = int(window[-1].close_raw), int(window[0].close_raw)
                vwap, close, first = amount/qty/10000, last_raw/10000, first_raw/10000
                row.update(vwap=vwap,close=close,first_close=first,price_status='rule_not_applicable' if W==1 else 'ok')
                if W != 1:
                    row['P']=bool(last_raw*qty>=amount and last_raw>first_raw)
            if row['structure_status']=='ok' and row['price_status']=='ok':
                if row['imbalance']<0 and row['negative_fraction']>.5 and last_raw*qty<amount and last_raw<first_raw:
                    row['description']='镜像弱势'
                elif row['F'] and row['P']:
                    row['description']='偏买且价格确认'
                elif row['F'] and not row['P']:
                    row['description']='偏买待确认'
                else:
                    row['description']='中性'
            rows.append(row)
    result = pd.DataFrame(rows)
    result['F'],result['P']=pd.array(result.F,dtype='boolean'),pd.array(result.P,dtype='boolean')
    return result


def future_labels(prices:pd.DataFrame,calendar:tuple[str,...],spec:PostcloseSpec,as_of_day:str)->pd.DataFrame:
    cal=_calendar(calendar);_day(as_of_day)
    _frame(prices,['day','symbol','close_raw','close_ok','price_segment'],['day','symbol'])
    _flags(prices,['close_ok'])
    if set(prices.day)-set(cal):
        raise ValueError('price date outside calendar')
    for r in prices.itertuples(index=False):
        if r.close_ok: _int(r.close_raw,'close_raw',1)
    mapping={(r.day,r.symbol):r for r in prices.itertuples(index=False)}
    rows=[]
    for symbol,H in product(spec.symbols,spec.horizons):
        for i,day in enumerate(cal):
            row={'day':day,'symbol':symbol,'horizon':H,'label_status':'calendar_horizon_unavailable','return_fraction':np.nan,'up':None,'worst_close_fraction':np.nan}
            if i+H>=len(cal): rows.append(row);continue
            if cal[i+H]>as_of_day:
                row['label_status']='not_matured';rows.append(row);continue
            path=[mapping.get((d,symbol)) for d in cal[i:i+H+1]]
            if path[0] is None: row['label_status']='base_price_missing'
            elif not path[0].close_ok: row['label_status']='base_price_unqualified'
            elif any(r is None for r in path): row['label_status']='price_path_missing'
            elif not all(r.close_ok for r in path): row['label_status']='price_path_unqualified'
            else:
                segments=[_segment(r.price_segment) for r in path]
                if any(s is None for s in segments): row['label_status']='price_basis_unknown'
                elif len(set(segments))!=1: row['label_status']='action_crossed'
                else:
                    closes=[int(r.close_raw) for r in path]
                    ret=(closes[-1]-closes[0])/closes[0]
                    row.update(label_status='ok',return_fraction=ret,up=bool(closes[-1]>closes[0]),worst_close_fraction=min((c-closes[0])/closes[0] for c in closes[1:]))
            rows.append(row)
    result=pd.DataFrame(rows);result['up']=pd.array(result.up,dtype='boolean')
    return result


def summarize_cells(profiles:pd.DataFrame,labels:pd.DataFrame,calendar:tuple[str,...],spec:PostcloseSpec)->pd.DataFrame:
    cal=_calendar(calendar)
    _frame(profiles,['day','symbol','threshold_cny','lookback','structure_status','price_status','F','P'],['day','symbol','threshold_cny','lookback'])
    _frame(labels,['day','symbol','horizon','label_status','return_fraction','up'],['day','symbol','horizon'])
    if set(profiles.day)-set(cal) or set(labels.day)-set(cal): raise ValueError('observation date outside calendar')
    for name in ('F','P'):
        if any(not pd.isna(v) and not isinstance(v,(bool,np.bool_)) for v in profiles[name]):
            raise ValueError(f'{name} must be nullable bool')
    valid_labels=labels.loc[labels.label_status=='ok']
    if any(not isinstance(v,(bool,np.bool_)) for v in valid_labels.up) or not np.isfinite(valid_labels.return_fraction.to_numpy(dtype=float)).all():
        raise ValueError('qualified labels require finite returns/known up')
    rows=[]
    for symbol,T,W,H in product(spec.symbols,spec.thresholds_cny,spec.lookbacks,spec.horizons):
        profile=profiles.loc[(profiles.symbol==symbol)&(profiles.threshold_cny==T)&(profiles.lookback==W)]
        qualified=profile.loc[(profile.structure_status=='ok')&(profile.price_status=='ok')&profile.F.notna()&profile.P.notna()]
        target=labels.loc[(labels.symbol==symbol)&(labels.horizon==H)]
        pre=qualified.merge(target[['day','symbol','label_status','return_fraction','up']],on=['day','symbol'],how='left',validate='one_to_one')
        pre['label_status']=pre.label_status.fillna('label_row_missing')
        common=pre.loc[pre.label_status=='ok']
        signal=common.loc[common.F.eq(True)&common.P.eq(True)]
        control=common.loc[common.F.eq(False)&common.P.eq(True)]
        row={'symbol':symbol,'threshold_cny':T,'lookback':W,'horizon':H,'n_total_anchors':len(cal),'n_profile_qualified':len(qualified),'n_common':len(common),'n_signal':len(signal),'n_control':len(control),'n_unconditional':len(common),'conclusion':'证据不足','inference_status':'not_run_by_descriptive_core'}
        for name,part in (('signal',pre.loc[pre.F.eq(True)&pre.P.eq(True)]),('control',pre.loc[pre.F.eq(False)&pre.P.eq(True)]),('unconditional',pre)):
            row[f'n_{name}_before_labels']=len(part)
            excluded=part.loc[part.label_status!='ok','label_status'].value_counts().sort_index()
            row[f'{name}_label_exclusions']=json.dumps({str(k):int(v) for k,v in excluded.items()},sort_keys=True)
        for name,part in (('signal',signal),('control',control),('unconditional',common)):
            row[f'{name}_up_fraction']=float(part.up.astype(bool).mean()) if len(part) else np.nan
            row[f'{name}_mean_return']=float(part.return_fraction.mean()) if len(part) else np.nan
        row['delta_up_fraction']=row['signal_up_fraction']-row['control_up_fraction']
        row['delta_mean_return']=row['signal_mean_return']-row['control_mean_return']
        rows.append(row)
    return pd.DataFrame(rows)
