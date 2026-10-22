"""Post-hoc L2 descriptive study, NOT Platform Backtest/Validation evidence.

Only the three requested instruments are extracted. No fills, PnL, trading-rule,
fee, queue or deployment model is implemented. Event times are not proven feed
availability times. All 28 days are exploratory; there is no untouched holdout.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

SYMBOLS = ("688655.SH", "688137.SH", "688122.SH")
KINDS = ("行情.csv", "逐笔委托.csv", "逐笔成交.csv")
SESSIONS = ((34_200_000, 41_400_000), (46_800_000, 53_820_000))
BUDGETS = (100_000, 500_000, 1_000_000)
PERIODS = (
    (34_200_000, 36_000_000, "09:30-10:00"),
    (36_000_000, 39_600_000, "10:00-11:00"),
    (39_600_000, 41_400_000, "11:00-11:30"),
    (46_800_000, 50_400_000, "13:00-14:00"),
    (50_400_000, 52_200_000, "14:00-14:30"),
    (52_200_000, 53_820_000, "14:30-14:57"),
)
SPEC = {
    "kind": "post_hoc_descriptive_not_platform_evidence",
    "symbols": SYMBOLS,
    "date_interval": ["20260901", "20261017"],
    "continuous_sessions_ms": SESSIONS,
    "price_divisor": 10000,
    "budgets_cny": BUDGETS,
    "signal_grid_ms": 60000,
    "feature_window_ms": 60000,
    "label_horizons_ms": [60000, 300000],
    "quote_max_age_ms": 10000,
    "strict_asof": "last quote with event time < grid; events in [grid-60s,grid)",
    "signals": {"imbalance10": 0.3, "flow60": 0.2},
    "liquidity": "prior 30min quote depth q10/spread q90, >=100 prior quotes, reset per session; cancellation D/(A+D)>=0.6 with >=10 events/60s",
    "aggregation": "equal-day conditional differences; >=5 finite observations each tail/day; fixed chronological first14/last14 descriptive split, not OOS; independently unavailable horizon labels remain missing; exclude mismatched stock-days from signal/liquidity-outcome comparisons but retain observed quote-cost descriptions and explicit quality gaps",
    "bootstrap": {"unit": "whole day", "replicates": 2000, "seed": 0, "interpretation": "exploratory; no multiple-testing adjustment"},
    "limitations": ["unknown provider availability and revisions", "unverified BS/AD vendor dictionary", "no fill/fee/PnL calculation", "no untouched holdout", "snapshot observations equal-weighted, not queue replay"],
}


def dump_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def hhmmssmmm_to_ms(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.int64)
    hour = values // 10_000_000
    minute = values // 100_000 % 100
    second = values // 1_000 % 100
    if np.any((values < 0) | (hour >= 24) | (minute >= 60) | (second >= 60)):
        raise ValueError("Invalid HHMMSSmmm time")
    return ((hour * 60 + minute) * 60 + second) * 1000 + values % 1000


def continuous(times: np.ndarray) -> np.ndarray:
    return np.logical_or.reduce([(times >= start) & (times < end) for start, end in SESSIONS])


def event_window_sum(times: np.ndarray, weights: np.ndarray, grid: np.ndarray) -> np.ndarray:
    """[t-60s,t): includes left endpoint, excludes equal-time future information."""
    if np.any(np.diff(times) < 0):
        raise ValueError("Event times must be sorted")
    prefix = np.r_[0.0, np.cumsum(weights, dtype=np.float64)]
    left = np.searchsorted(times, grid - 60000, side="left")
    right = np.searchsorted(times, grid, side="left")
    return prefix[right] - prefix[left]


def strict_asof(times: np.ndarray, grid: np.ndarray, max_age: int = 10000) -> tuple[np.ndarray, np.ndarray]:
    if len(times) == 0 or np.any(np.diff(times) < 0):
        raise ValueError("Quotes must be nonempty and sorted")
    indices = np.searchsorted(times, grid, side="left") - 1
    valid = (indices >= 0) & (grid - times[np.maximum(indices, 0)] <= max_age)
    return np.maximum(indices, 0), valid


def displayed_cost(prices: np.ndarray, quantities: np.ndarray, mids: np.ndarray, budget: float, side: str) -> np.ndarray:
    """Static displayed-price curve, fractional quantities, NOT an executable order.

    The hypothetical notional is cash distributed over visible levels. Unsupported
    notional is NaN, never filled by extrapolating beyond ten levels.
    """
    if side not in {"buy", "sell"} or budget <= 0:
        raise ValueError("Invalid quote-curve side/budget")
    prices = np.asarray(prices, dtype=float)
    quantities = np.asarray(quantities, dtype=float)
    notionals = prices * quantities
    before = np.cumsum(notionals, axis=1) - notionals
    cash = np.minimum(np.maximum(budget - before, 0), notionals)
    shares = np.divide(cash, prices, out=np.zeros_like(cash), where=prices > 0).sum(axis=1)
    supported = (notionals.sum(axis=1) >= budget) & (shares > 0) & (mids > 0)
    vwap = np.divide(budget, shares, out=np.full(len(shares), np.nan), where=supported)
    return ((vwap / mids - 1) if side == "buy" else (1 - vwap / mids)) * 10000


def list_members(archive: Path, symbols: tuple[str, ...]) -> dict[str, dict]:
    result = subprocess.run(["7z", "l", "-slt", str(archive), *[f"*/{s}/*" for s in symbols]], input="", capture_output=True, text=True, timeout=30)
    if result.returncode or "----------" not in result.stdout:
        raise RuntimeError(f"Cannot list {archive}: {result.stderr[:1000]}")
    members = {}
    for block in result.stdout.split("----------", 1)[1].strip().split("\n\n"):
        fields = dict(line.split(" = ", 1) for line in block.splitlines() if " = " in line)
        if "Path" in fields and not fields.get("Attributes", "").startswith("D"):
            members[fields["Path"]] = {"bytes": int(fields["Size"]), "crc32": fields["CRC"]}
    return members


def load_member(path: Path, meta: dict, day: str, symbol: str, kind: str) -> tuple[pd.DataFrame, dict]:
    raw = path.read_bytes()
    crc = f"{zlib.crc32(raw) & 0xffffffff:08X}"
    if len(raw) != meta["bytes"] or crc != meta["crc32"]:
        raise ValueError(f"Size/CRC mismatch: {path}")
    text = raw.decode("gb18030")
    frame = pd.read_csv(io.StringIO(text.replace("\x00", "")), dtype={"万得代码": "string", "交易所代码": "string", "自然日": "string"}, keep_default_na=False)
    expected = {"行情.csv": 67, "逐笔委托.csv": 11, "逐笔成交.csv": 13}[kind]
    if len(frame) == 0 or len(frame.columns) != expected:
        raise ValueError(f"Unexpected CSV shape: {path}, {frame.shape}")
    trailing = frame.iloc[:, -1].astype(str).str.strip()
    if not frame.columns[-1].startswith("Unnamed:") or trailing.ne("").any():
        raise ValueError(f"Unexpected trailing column: {path}")
    frame = frame.iloc[:, :-1].copy()
    if frame["自然日"].ne(day).any() or frame["万得代码"].ne(symbol).any() or frame["交易所代码"].ne(symbol[:6]).any():
        raise ValueError(f"Wrong date/instrument: {path}")
    frame["ms"] = hhmmssmmm_to_ms(pd.to_numeric(frame["时间"], errors="raise").to_numpy())
    reversals = int((frame["ms"].diff() < 0).sum())
    if reversals:
        frame = frame.sort_values("ms", kind="stable").reset_index(drop=True)
    for name in ("BS标志", "委托类型", "委托代码", "成交代码"):
        if name in frame:
            frame[name] = frame[name].astype(str).str.strip()
    detail = {"path": str(path), "bytes": len(raw), "crc32": crc, "sha256": hashlib.sha256(raw).hexdigest(), "rows": len(frame), "nul_bytes": raw.count(b"\x00"), "time_reversals": reversals}
    return frame, detail


def ordered_side(prices: np.ndarray, side: str) -> np.ndarray:
    if side not in {"buy", "sell"}:
        raise ValueError(side)
    # A zero tail is allowed; a positive level after a zero is not.
    no_gaps = ~np.any((prices[:, :-1] == 0) & (prices[:, 1:] > 0), axis=1)
    pairs = (prices[:, :-1] > 0) & (prices[:, 1:] > 0)
    ordered = prices[:, 1:] >= prices[:, :-1] if side == "buy" else prices[:, 1:] <= prices[:, :-1]
    return no_gaps & np.all(~pairs | ordered, axis=1)


def analyze_day(day: str, symbol: str, frames: dict[str, pd.DataFrame]) -> tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    quote, order, trade = (frames[k] for k in KINDS)
    trade_price = pd.to_numeric(trade["成交价格"], errors="raise").to_numpy(dtype=float) / 10000
    trade_qty = pd.to_numeric(trade["成交数量"], errors="raise").to_numpy(dtype=float)
    actual = (trade_price > 0) & (trade_qty > 0)
    expected_volume = int(quote.iloc[-1]["当日累计成交量"])
    expected_count = int(quote.iloc[-1]["成交笔数"])
    volume_matches = bool(trade_qty[actual].sum() == expected_volume)
    trade_count_matches = bool(int(actual.sum()) == expected_count)
    if (~trade["BS标志"].isin(["B", "S"]) & actual).any():
        raise ValueError(f"Unknown trade direction: {day} {symbol}")
    if (~order["委托类型"].isin(["A", "D", "S"])).any():
        raise ValueError(f"Unknown order event type: {day} {symbol}")
    order_qty = pd.to_numeric(order["委托数量"], errors="raise").to_numpy(dtype=float)
    if any(np.any(~np.isfinite(x)) for x in (trade_price, trade_qty, order_qty)) or np.any(trade_qty < 0) or np.any(order_qty < 0):
        raise ValueError("Nonfinite event value or negative quantity")

    ask = quote[[f"申卖价{i}" for i in range(1, 11)]].to_numpy(dtype=float) / 10000
    bid = quote[[f"申买价{i}" for i in range(1, 11)]].to_numpy(dtype=float) / 10000
    aq = quote[[f"申卖量{i}" for i in range(1, 11)]].to_numpy(dtype=float)
    bq = quote[[f"申买量{i}" for i in range(1, 11)]].to_numpy(dtype=float)
    if any(np.any(~np.isfinite(x)) or np.any(x < 0) for x in (ask, bid, aq, bq)):
        raise ValueError("Nonfinite or negative book price/quantity")
    t = quote["ms"].to_numpy()
    in_session = continuous(t)
    valid = (bid[:, 0] > 0) & (ask[:, 0] > bid[:, 0]) & (aq[:, 0] > 0) & (bq[:, 0] > 0) & ordered_side(ask, "buy") & ordered_side(bid, "sell")
    valid &= np.all((ask == 0) == (aq == 0), axis=1) & np.all((bid == 0) == (bq == 0), axis=1)
    mids = (ask[:, 0] + bid[:, 0]) / 2
    spread = np.divide(ask[:, 0] - bid[:, 0], mids, out=np.full(len(t), np.nan), where=mids > 0) * 10000
    depth = (ask * aq).sum(axis=1) + (bid * bq).sum(axis=1)
    imbalance = np.divide(bq.sum(axis=1) - aq.sum(axis=1), bq.sum(axis=1) + aq.sum(axis=1), out=np.full(len(t), np.nan), where=(bq.sum(axis=1) + aq.sum(axis=1)) > 0)
    q = pd.DataFrame({"day": day, "symbol": symbol, "ms": t, "valid": valid, "mid": mids, "spread_bps": spread, "depth10_cny": depth, "imbalance10": imbalance})
    for budget in BUDGETS:
        for side, prices, quantities in (("buy", ask, aq), ("sell", bid, bq)):
            cost = displayed_cost(prices, quantities, mids, budget, side)
            cost[~valid] = np.nan
            q[f"{side}_{budget}_bps"] = cost
    q = q.loc[in_session].copy()
    if q.empty or not q["valid"].any():
        raise ValueError(f"No valid continuous quotes: {day} {symbol}")
    q["period"] = ""
    for start, end, label in PERIODS:
        q.loc[(q.ms >= start) & (q.ms < end), "period"] = label

    grids = []
    for start, end in SESSIONS:
        session = q.loc[(q.ms >= start) & (q.ms < end)].copy()
        if session.empty:
            continue
        # Invalid latest quotes must remain in asof lookup: never silently skip a
        # crossed/one-sided snapshot and pretend an older valid book is current.
        prior = session.loc[session.valid].set_index(pd.to_timedelta(session.loc[session.valid, "ms"], unit="ms"))
        session["depth_q10"] = np.nan
        session["spread_q90"] = np.nan
        session.loc[session.valid, "depth_q10"] = prior.depth10_cny.rolling("30min", closed="left", min_periods=100).quantile(.1).to_numpy()
        session.loc[session.valid, "spread_q90"] = prior.spread_bps.rolling("30min", closed="left", min_periods=100).quantile(.9).to_numpy()
        times = session.ms.to_numpy()
        grid = np.arange(start + 60000, end - 300000, 60000, dtype=np.int64)
        at, good = strict_asof(times, grid)
        current = session.iloc[at].reset_index(drop=True)
        good &= current.valid.to_numpy()
        g = pd.DataFrame({"day": day, "symbol": symbol, "grid_ms": grid, "mid": current.mid.to_numpy(), "spread_bps": current.spread_bps.to_numpy(), "depth10_cny": current.depth10_cny.to_numpy(), "imbalance10": current.imbalance10.to_numpy(), "thin": current.depth10_cny.to_numpy() < current.depth_q10.to_numpy(), "wide": current.spread_bps.to_numpy() > current.spread_q90.to_numpy(), "threshold_ready": current.depth_q10.notna().to_numpy() & current.spread_q90.notna().to_numpy()})
        for horizon in (60000, 300000):
            future_at, future_good = strict_asof(times, grid + horizon)
            future = session.iloc[future_at]
            label_good = future_good & future.valid.to_numpy()
            label = (future.mid.to_numpy() / g.mid.to_numpy() - 1) * 10000
            label[~label_good] = np.nan
            g[f"ret{horizon // 60000}_bps"] = label
        tm = trade.ms.to_numpy()
        amounts = trade_price * trade_qty * actual
        direction = np.where(trade["BS标志"].to_numpy() == "B", 1.0, -1.0)
        total = event_window_sum(tm, amounts, grid)
        signed = event_window_sum(tm, amounts * direction, grid)
        g["flow60"] = np.divide(signed, total, out=np.full(len(grid), np.nan), where=total > 0)
        om = order.ms.to_numpy()
        add = order["委托类型"].eq("A").to_numpy() & order["委托代码"].isin(["B", "S"]).to_numpy()
        delete = order["委托类型"].eq("D").to_numpy() & order["委托代码"].isin(["B", "S"]).to_numpy()
        adds = event_window_sum(om, add, grid)
        deletes = event_window_sum(om, delete, grid)
        g["cancel_event_share60"] = np.divide(deletes, adds + deletes, out=np.full(len(grid), np.nan), where=(adds + deletes) > 0)
        g["cancel_high"] = (g.cancel_event_share60 >= .6) & ((adds + deletes) >= 10)
        grids.append(g.loc[good].copy())
    if not grids:
        raise ValueError(f"No grid observations: {day} {symbol}")
    grid_frame = pd.concat(grids, ignore_index=True)
    grid_frame["crossfile_verified"] = volume_matches and trade_count_matches
    ot = order.ms.to_numpy()
    ad_cont = continuous(ot) & order["委托类型"].isin(["A", "D"]).to_numpy() & order["委托代码"].isin(["B", "S"]).to_numpy()
    delete_cont = ad_cont & order["委托类型"].eq("D").to_numpy()
    sample = q.loc[q.valid]
    intervals = np.concatenate([np.diff(q.loc[(q.ms >= start) & (q.ms < end), "ms"].to_numpy()) for start, end in SESSIONS])
    day_row = {"day": day, "symbol": symbol, "quote_rows": len(quote), "order_rows": len(order), "trade_rows": len(trade), "positive_trades": int(actual.sum()), "volume_shares": int(trade_qty[actual].sum()), "turnover_cny": float((trade_price[actual] * trade_qty[actual]).sum()), "continuous_quotes": len(q), "valid_quotes": len(sample), "invalid_quotes": int((~q.valid).sum()), "quote_interval_median_ms": float(np.median(intervals)) if len(intervals) else None, "spread_median_bps": float(sample.spread_bps.median()), "spread_p90_bps": float(sample.spread_bps.quantile(.9)), "depth10_median_cny": float(sample.depth10_cny.median()), "cancel_event_share": float(delete_cont.sum() / ad_cont.sum()) if ad_cont.sum() else None, "cancel_qty_share": float(order_qty[delete_cont].sum() / order_qty[ad_cont].sum()) if order_qty[ad_cont].sum() else None, "grid_rows": len(grid_frame), "volume_matches": volume_matches, "trade_count_matches": trade_count_matches, "expected_volume_shares": expected_volume, "expected_trade_count": expected_count, "volume_gap_shares": int(expected_volume - trade_qty[actual].sum()), "trade_count_gap": int(expected_count - actual.sum()), "ask_empty_quotes": int((ask[in_session, 0] <= 0).sum()), "bid_empty_quotes": int((bid[in_session, 0] <= 0).sum())}
    day_row["label1_rows"] = int(grid_frame.ret1_bps.notna().sum())
    day_row["label5_rows"] = int(grid_frame.ret5_bps.notna().sum())
    for budget in BUDGETS:
        for side in ("buy", "sell"):
            col = f"{side}_{budget}_bps"
            day_row[f"{col}_median"] = float(sample[col].median()) if sample[col].notna().any() else None
            day_row[f"{side}_{budget}_coverage"] = float(sample[col].notna().mean())
    common = sample.loc[sample.buy_1000000_bps.notna() & sample.sell_1000000_bps.notna()]
    day_row["both_sides_1000000_common_coverage"] = float(len(common) / len(sample))
    for budget in BUDGETS:
        for side in ("buy", "sell"):
            col = f"{side}_{budget}_bps"
            day_row[f"{col}_common_median"] = float(common[col].median()) if len(common) else None
    period_rows = []
    for label, part in sample.groupby("period", sort=False):
        row = {"day": day, "symbol": symbol, "period": label, "quotes": len(part), "spread_median_bps": float(part.spread_bps.median()), "spread_p90_bps": float(part.spread_bps.quantile(.9)), "depth10_median_cny": float(part.depth10_cny.median())}
        for budget in BUDGETS:
            for side in ("buy", "sell"):
                col = f"{side}_{budget}_bps"
                row[f"{col}_median"] = float(part[col].median()) if part[col].notna().any() else None
                row[f"{side}_{budget}_coverage"] = float(part[col].notna().mean())
        period_rows.append(row)
    return day_row, grid_frame, pd.DataFrame(period_rows), q


def bootstrap(values: np.ndarray) -> list[float] | None:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) < 2:
        return None
    rng = np.random.default_rng(0)
    means = values[rng.integers(0, len(values), size=(2000, len(values)))].mean(axis=1)
    return np.quantile(means, [.025, .975]).tolist()


def summarize(daily: pd.DataFrame, grids: pd.DataFrame, periods: pd.DataFrame) -> dict:
    summary = {}
    for symbol, days in daily.groupby("symbol", sort=False):
        g = grids.loc[(grids.symbol == symbol) & grids.crossfile_verified]
        p = periods.loc[periods.symbol == symbol]
        metrics = {}
        for col in daily.columns:
            if col not in {"day", "symbol"} and pd.api.types.is_numeric_dtype(days[col]):
                metrics[col] = float(days[col].median()) if days[col].notna().any() else None
        signals = []
        for feature, cutoff in SPEC["signals"].items():
            for horizon in (1, 5):
                target = f"ret{horizon}_bps"
                differences = []
                for day, part in g.groupby("day", sort=True):
                    high, low = part.loc[part[feature] >= cutoff, target].dropna(), part.loc[part[feature] <= -cutoff, target].dropna()
                    if len(high) >= 5 and len(low) >= 5:
                        differences.append({"day": day, "difference_bps": float(high.mean() - low.mean()), "high_mean_bps": float(high.mean()), "low_mean_bps": float(low.mean()), "high_n": len(high), "low_n": len(low)})
                values = np.array([d["difference_bps"] for d in differences])
                half = sorted(days.day.unique())[len(days) // 2]
                first = [d["difference_bps"] for d in differences if d["day"] < half]
                second = [d["difference_bps"] for d in differences if d["day"] >= half]
                signals.append({"feature": feature, "cutoff": cutoff, "horizon_min": horizon, "valid_days": len(differences), "high_n": int(((g[feature] >= cutoff) & g[target].notna()).sum()), "low_n": int(((g[feature] <= -cutoff) & g[target].notna()).sum()), "daily_difference_mean_bps": float(values.mean()) if len(values) else None, "daily_difference_ci95_bps": bootstrap(values), "positive_days": int((values > 0).sum()), "first_half_bps": float(np.mean(first)) if first else None, "second_half_bps": float(np.mean(second)) if second else None, "daily": differences})
        liquidity = []
        for flag in ("thin", "wide", "cancel_high"):
            eligible = g.loc[g.threshold_ready & g.ret5_bps.notna()] if flag != "cancel_high" else g.loc[g.ret5_bps.notna()]
            day_comparisons = []
            for day, part in eligible.groupby("day", sort=True):
                state = part.loc[part[flag], "ret5_bps"].dropna().abs()
                normal = part.loc[~part[flag], "ret5_bps"].dropna().abs()
                if len(state) >= 5 and len(normal) >= 5:
                    day_comparisons.append({"day": day, "state_absret5_bps": float(state.mean()), "other_absret5_bps": float(normal.mean()), "difference_bps": float(state.mean() - normal.mean()), "state_n": len(state), "other_n": len(normal)})
            vals = np.array([d["difference_bps"] for d in day_comparisons])
            liquidity.append({"state": flag, "state_n": int(eligible[flag].sum()), "eligible_n": len(eligible), "valid_days": len(day_comparisons), "state_absret5_bps": float(np.mean([d["state_absret5_bps"] for d in day_comparisons])) if day_comparisons else None, "other_absret5_bps": float(np.mean([d["other_absret5_bps"] for d in day_comparisons])) if day_comparisons else None, "daily_difference_mean_bps": float(vals.mean()) if len(vals) else None, "ci95_bps": bootstrap(vals), "daily": day_comparisons})
        period_metrics = []
        for period, part in p.groupby("period", sort=True):
            period_metrics.append({"period": period, "days": len(part), **{c: float(part[c].median()) if part[c].notna().any() else None for c in part.select_dtypes(include="number").columns if c != "quotes"}})
        excluded = days.loc[~(days.volume_matches & days.trade_count_matches), ["day", "volume_gap_shares", "trade_count_gap", "expected_volume_shares", "expected_trade_count"]].to_dict(orient="records")
        summary[symbol] = {"days": len(days), "eligible_analysis_days": len(days) - len(excluded), "excluded_days": excluded, "grid_rows": len(g), "total_trade_rows": int(days.trade_rows.sum()), "total_order_rows": int(days.order_rows.sum()), "total_quote_rows": int(days.quote_rows.sum()), "total_continuous_quotes": int(days.continuous_quotes.sum()), "total_invalid_quotes": int(days.invalid_quotes.sum()), "median_daily_metrics": metrics, "signals": signals, "liquidity": liquidity, "periods": period_metrics}
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("/srv/bcache-8t/ygguo/quant/L2"))
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dates", nargs="+")
    parser.add_argument("--symbols", nargs="+", choices=SYMBOLS, default=list(SYMBOLS))
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Output must be new: {args.output}")
    args.output.mkdir(parents=True)
    args.cache.mkdir(parents=True, exist_ok=True)
    code_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    dump_json(args.output / "spec.json", {**SPEC, "code_sha256": code_sha, "python_dependencies": {"numpy": np.__version__, "pandas": pd.__version__}, "requested_dates": args.dates, "requested_symbols": args.symbols})
    archives = sorted(p for month in ("202609", "202610") for p in (args.source / month).glob("*.7z"))
    requested = set(args.dates or [])
    archives = [p for p in archives if "20260901" <= re.match(r"\d{8}", p.name)[0] < "20261017" and (not requested or re.match(r"\d{8}", p.name)[0] in requested)]
    if not archives or (requested and {re.match(r"\d{8}", p.name)[0] for p in archives} != requested):
        raise ValueError("Missing requested dates")
    daily_rows, grid_parts, period_parts, source_members, archive_stats = [], [], [], [], []
    for archive in archives:
        day = re.match(r"\d{8}", archive.name)[0]
        before = archive.stat()
        members = list_members(archive, tuple(args.symbols))
        expected = {f"{day}/{symbol}/{kind}" for symbol in args.symbols for kind in KINDS}
        if set(members) != expected or any(v["bytes"] <= 0 for v in members.values()):
            raise ValueError(f"Missing/extra/empty selected members: {archive}")
        missing = [name for name in sorted(expected) if not (args.cache / name).exists()]
        if missing:
            result = subprocess.run(["7z", "x", "-y", "-bd", "-bb0", f"-o{args.cache}", str(archive), *missing], input="", capture_output=True, text=True, timeout=120)
            if result.returncode:
                raise RuntimeError(f"Extract failed: {archive}: {result.stderr[:1000]}")
        for symbol in args.symbols:
            frames = {}
            for kind in KINDS:
                member = f"{day}/{symbol}/{kind}"
                frames[kind], detail = load_member(args.cache / member, members[member], day, symbol, kind)
                source_members.append({"archive": str(archive), "member": member, **detail})
            row, grid, periods, _ = analyze_day(day, symbol, frames)
            daily_rows.append(row)
            grid_parts.append(grid)
            period_parts.append(periods)
            print(json.dumps({"day": day, "symbol": symbol, "trade_rows": row["trade_rows"], "invalid_quotes": row["invalid_quotes"], "grid_rows": row["grid_rows"], "volume_check": row["volume_matches"], "count_check": row["trade_count_matches"], "volume_gap_shares": row["volume_gap_shares"]}, ensure_ascii=False), flush=True)
        after = archive.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError(f"Source archive changed: {archive}")
        archive_stats.append({"path": str(archive), "bytes": before.st_size, "mtime_ns": before.st_mtime_ns})
    daily = pd.DataFrame(daily_rows)
    grids = pd.concat(grid_parts, ignore_index=True)
    periods = pd.concat(period_parts, ignore_index=True)
    for name, frame in (("daily.csv", daily), ("minute_grid.csv", grids), ("periods.csv", periods)):
        frame.to_csv(args.output / name, index=False)
    revision_body = [{k: member[k] for k in ("member", "bytes", "crc32", "sha256")} for member in sorted(source_members, key=lambda x: x["member"])]
    revision = hashlib.sha256(json.dumps(revision_body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    dump_json(args.output / "source_manifest.json", {"selected_data_sha256": revision, "archives": archive_stats, "members": source_members})
    dump_json(args.output / "summary.json", {"status": "completed_descriptive_only", "selected_data_sha256": revision, "code_sha256": code_sha, "symbols": summarize(daily, grids, periods)})
    print(json.dumps({"status": "completed_descriptive_only", "output": str(args.output), "selected_data_sha256": revision, "stock_days": len(daily), "member_count": len(source_members), "grid_rows": len(grids)}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
