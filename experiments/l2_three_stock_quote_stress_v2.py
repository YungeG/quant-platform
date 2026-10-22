"""Exploratory quote-space stress check, NOT fills, net PnL or Platform evidence.

The previous 28 days have ALL been observed. This is not a new holdout. Quote
crossing space is algebra on displayed prices, not executable round-trip profit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.l2_three_stock_microstructure_v1 import (
    SESSIONS, SYMBOLS, bootstrap, continuous, displayed_cost, dump_json,
    load_member, ordered_side, strict_asof,
)

DELAYS = (0, 3000, 6000)
HORIZONS = (60000, 300000)
AMOUNTS = (50000, 100000, 200000, 500000, 1000000)
CUT = 0.3
SPEC = {
    "kind": "post_hoc_quote_space_stress_not_backtest",
    "not_new_dates_or_holdout": True,
    "symbols": SYMBOLS,
    "signal": "original frozen imbalance10 >=0.3 buy-side, <=-0.3 sell-side",
    "delays_ms": DELAYS,
    "horizons_ms": HORIZONS,
    "entry_reference": "last quote strictly before signal time + delay, at most 10s old",
    "exit_reference": "last quote strictly before signal time + horizon, at most 10s old",
    "buy_quote_space_bps": "(future bid1 / delayed ask1 - 1) * 10000",
    "sell_quote_space_bps": "(delayed bid1 / future ask1 - 1) * 10000",
    "amounts_cny": AMOUNTS,
    "extra_cost_headroom_scenarios_bps": [0, 5, 10],
    "cost_budget_scenarios_bps": [5, 10],
    "daily_quote_guard": ">=90% of all continuous snapshots priceable in valid bilateral ten-level book; conditional cost p90 <= budget",
    "uniform_amount_description": ">=90% of observed days pass daily quote guard, separate sides; NOT a trading-authorized cap",
    "aggregation": "equal day means; >=5 finite observations/day/group; 2000 day bootstrap draws, seed0; no multiple-test adjustment",
    "source_gaps": "exclude failed cross-file stock-days from quote-space comparisons, retain quote-cost descriptions",
    "limitations": ["all input dates previously observed", "no provider availability proof", "no fee, fill, quantity-lattice, queue or portfolio model", "short-sale and T+1 feasibility not assumed", "quote costs are not guaranteed fills", "fractional mathematical quantities only"],
}


def books(quote: pd.DataFrame, day: str, symbol: str) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    ask = quote[[f"申卖价{i}" for i in range(1, 11)]].to_numpy(dtype=float) / 10000
    bid = quote[[f"申买价{i}" for i in range(1, 11)]].to_numpy(dtype=float) / 10000
    aq = quote[[f"申卖量{i}" for i in range(1, 11)]].to_numpy(dtype=float)
    bq = quote[[f"申买量{i}" for i in range(1, 11)]].to_numpy(dtype=float)
    if any(np.any(~np.isfinite(a)) or np.any(a < 0) for a in (ask, bid, aq, bq)):
        raise ValueError("Nonfinite or negative book value")
    mask = continuous(quote.ms.to_numpy())
    ask, bid, aq, bq = (a[mask] for a in (ask, bid, aq, bq))
    ms = quote.ms.to_numpy()[mask]
    valid = (bid[:, 0] > 0) & (ask[:, 0] > bid[:, 0]) & (aq[:, 0] > 0) & (bq[:, 0] > 0)
    valid &= ordered_side(ask, "buy") & ordered_side(bid, "sell")
    valid &= np.all((ask == 0) == (aq == 0), axis=1) & np.all((bid == 0) == (bq == 0), axis=1)
    mids = (ask[:, 0] + bid[:, 0]) / 2
    spread = np.divide(ask[:, 0] - bid[:, 0], mids, out=np.full(len(ms), np.nan), where=mids > 0) * 10000
    return pd.DataFrame({"day": day, "symbol": symbol, "ms": ms, "valid": valid, "ask1": ask[:, 0], "bid1": bid[:, 0], "mid": mids, "spread_bps": spread}), {"ask": ask, "bid": bid, "aq": aq, "bq": bq}


def quote_space(q: pd.DataFrame, grid: pd.DataFrame, delay: int, horizon: int) -> pd.DataFrame:
    """Displayed price differences only; no orders, holdings or cash flows."""
    t = grid.grid_ms.to_numpy(dtype=np.int64)
    times = q.ms.to_numpy(dtype=np.int64)
    entry_i, entry_ok = strict_asof(times, t + delay)
    exit_i, exit_ok = strict_asof(times, t + horizon)
    signal_i, signal_ok = strict_asof(times, t)
    entry, future = q.iloc[entry_i], q.iloc[exit_i]
    ok = entry_ok & exit_ok & signal_ok & entry.valid.to_numpy() & future.valid.to_numpy() & q.iloc[signal_i].valid.to_numpy()
    for start, end in SESSIONS:
        belongs = (t >= start) & (t < end)
        ok[belongs] &= (entry.ms.to_numpy()[belongs] >= start) & (entry.ms.to_numpy()[belongs] < end) & (future.ms.to_numpy()[belongs] >= start) & (future.ms.to_numpy()[belongs] < end)
    result = grid[["day", "symbol", "grid_ms", "imbalance10"]].reset_index(drop=True).copy()
    result["delay_ms"] = delay
    result["horizon_min"] = horizon // 60000
    result["entry_quote_ms"] = entry.ms.to_numpy()
    result["exit_quote_ms"] = future.ms.to_numpy()
    result["entry_quote_changed"] = entry.ms.to_numpy() > q.iloc[signal_i].ms.to_numpy()
    for name, numerator, denominator in (("buy_quote_space_bps", future.bid1.to_numpy(), entry.ask1.to_numpy()), ("sell_quote_space_bps", entry.bid1.to_numpy(), future.ask1.to_numpy()), ("delayed_mid_change_bps", future.mid.to_numpy(), entry.mid.to_numpy())):
        ratio = np.divide(numerator, denominator, out=np.full(len(t), np.nan), where=denominator > 0)
        result[name] = (ratio - 1) * 10000
    return result.loc[ok].copy()


def daily_space(observations: pd.DataFrame) -> list[dict]:
    rows = []
    for (day, symbol, delay, horizon), part in observations.groupby(["day", "symbol", "delay_ms", "horizon_min"], sort=False):
        for side in ("buy", "sell"):
            take = part.imbalance10 >= CUT if side == "buy" else part.imbalance10 <= -CUT
            group = part.loc[take]
            if len(group) < 5:
                continue
            values = group[f"{side}_quote_space_bps"]
            row = {"day": day, "symbol": symbol, "delay_ms": int(delay), "horizon_min": int(horizon), "side": side, "n": len(group), "quote_space_mean_bps": float(values.mean()), "quote_space_median_bps": float(values.median()), "unfiltered_quote_space_mean_bps": float(part[f"{side}_quote_space_bps"].mean()), "entry_quote_changed_share": float(group.entry_quote_changed.mean())}
            for extra in (0, 5, 10):
                row[f"headroom_gt_{extra}_share"] = float((values > extra).mean())
            rows.append(row)
    return rows


def quote_cost_rows(q: pd.DataFrame, arrays: dict[str, np.ndarray]) -> list[dict]:
    rows = []
    for side, prices, qty in (("buy", arrays["ask"], arrays["aq"]), ("sell", arrays["bid"], arrays["bq"])):
        for amount in AMOUNTS:
            cost = displayed_cost(prices, qty, q.mid.to_numpy(), amount, side)
            cost[~q.valid.to_numpy()] = np.nan
            finite = np.isfinite(cost)
            row = {"day": q.iloc[0].day, "symbol": q.iloc[0].symbol, "side": side, "amount_cny": amount, "all_continuous_quotes": len(q), "bilateral_quote_share": float(q.valid.mean()), "priceable_share_all_snapshots": float(finite.mean()), "cost_p50_bps": float(np.nanmedian(cost)) if finite.any() else None, "cost_p90_bps": float(np.nanquantile(cost, .9)) if finite.any() else None}
            for ceiling in (5, 10):
                row[f"cost_le_{ceiling}_share_all_snapshots"] = float((cost <= ceiling).mean())
                row[f"daily_guard_{ceiling}_pass"] = bool(finite.mean() >= .9 and finite.any() and np.nanquantile(cost, .9) <= ceiling)
            rows.append(row)
    return rows


def aggregate(space_days: pd.DataFrame, cost_days: pd.DataFrame) -> dict:
    spaces, costs = [], []
    for key, part in space_days.groupby(["symbol", "delay_ms", "horizon_min", "side"], sort=False):
        values = part.quote_space_mean_bps.to_numpy()
        row = {"symbol": key[0], "delay_ms": int(key[1]), "horizon_min": int(key[2]), "side": key[3]}
        row.update(days=len(part), n=int(part.n.sum()), quote_space_mean_bps=float(values.mean()), quote_space_day_mean_ci95_bps=bootstrap(values), positive_quote_space_days=int((values > 0).sum()), unfiltered_quote_space_mean_bps=float(part.unfiltered_quote_space_mean_bps.mean()), entry_quote_changed_share=float(part.entry_quote_changed_share.mean()))
        for extra in (0, 5, 10):
            row[f"headroom_gt_{extra}_share"] = float(part[f"headroom_gt_{extra}_share"].mean())
        latest = part.loc[part.day.astype(str) >= "20261008"]
        row["october_days"] = len(latest)
        row["october_quote_space_mean_bps"] = float(latest.quote_space_mean_bps.mean()) if len(latest) else None
        spaces.append(row)
    for key, part in cost_days.groupby(["symbol", "side", "amount_cny"], sort=False):
        row = {"symbol": key[0], "side": key[1], "amount_cny": int(key[2])}
        row.update(days=len(part), priceable_share_daily_median=float(part.priceable_share_all_snapshots.median()), cost_p50_daily_median_bps=float(part.cost_p50_bps.median()) if part.cost_p50_bps.notna().any() else None, cost_p90_daily_median_bps=float(part.cost_p90_bps.median()) if part.cost_p90_bps.notna().any() else None)
        for ceiling in (5, 10):
            row[f"cost_le_{ceiling}_share_daily_median"] = float(part[f"cost_le_{ceiling}_share_all_snapshots"].median())
            row[f"daily_guard_{ceiling}_pass_days"] = int(part[f"daily_guard_{ceiling}_pass"].sum())
        costs.append(row)
    return {"quote_space": spaces, "quote_cost": costs}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--basis", type=Path, default=Path("/srv/bcache-8t/ygguo/quant/l2-three-stock-20260901-20261016-v1/full_v2"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True)
    old_spec = json.loads((args.basis / "spec.json").read_text())
    old_code = Path(__file__).with_name("l2_three_stock_microstructure_v1.py")
    if hashlib.sha256(old_code.read_bytes()).hexdigest() != old_spec["code_sha256"]:
        raise ValueError("Basis code changed; review before reuse")
    manifest = json.loads((args.basis / "source_manifest.json").read_text())
    code_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    dump_json(args.output / "spec.json", {**SPEC, "code_sha256": code_sha, "basis_code_sha256": old_spec["code_sha256"], "selected_data_sha256": manifest["selected_data_sha256"], "smoke": args.smoke})
    daily = pd.read_csv(args.basis / "daily.csv", dtype={"day": str, "symbol": str})
    grid = pd.read_csv(args.basis / "minute_grid.csv", dtype={"day": str, "symbol": str})
    if args.smoke:
        daily = daily.loc[(daily.day == "20261016") & (daily.symbol == "688137.SH")]
    observations, costs, provenance = [], [], []
    for row in daily.itertuples(index=False):
        member = next(m for m in manifest["members"] if m["member"] == f"{row.day}/{row.symbol}/行情.csv")
        quote, detail = load_member(Path(member["path"]), {"bytes": member["bytes"], "crc32": member["crc32"]}, row.day, row.symbol, "行情.csv")
        if detail["sha256"] != member["sha256"]:
            raise ValueError("Selected source changed")
        q, arrays = books(quote, row.day, row.symbol)
        if int(q.valid.sum()) != row.valid_quotes or len(q) != row.continuous_quotes:
            raise ValueError("Book validity differs from frozen basis")
        provenance.append(detail)
        costs.extend(quote_cost_rows(q, arrays))
        g = grid.loc[(grid.day == row.day) & (grid.symbol == row.symbol) & grid.crossfile_verified]
        if not g.empty:
            for delay in DELAYS:
                for horizon in HORIZONS:
                    observations.append(quote_space(q, g, delay, horizon))
        print(json.dumps({"day": row.day, "symbol": row.symbol, "continuous_quotes": len(q), "signal_grid_rows": len(g)}, ensure_ascii=False), flush=True)
    obs = pd.concat(observations, ignore_index=True)
    space_days = pd.DataFrame(daily_space(obs))
    cost_days = pd.DataFrame(costs)
    if space_days.empty or cost_days.empty:
        raise ValueError("Insufficient observations")
    for name, frame in (("quote_space_observations.csv", obs), ("quote_space_daily.csv", space_days), ("quote_cost_daily.csv", cost_days)):
        frame.to_csv(args.output / name, index=False)
    dump_json(args.output / "source_quotes.json", provenance)
    result = {"status": "completed_exploratory_only", "new_dates": 0, "stock_days": len(daily), "code_sha256": code_sha, "selected_data_sha256": manifest["selected_data_sha256"], **aggregate(space_days, cost_days)}
    dump_json(args.output / "summary.json", result)
    print(json.dumps({k: result[k] for k in ("status", "new_dates", "stock_days", "code_sha256")}), flush=True)


if __name__ == "__main__":
    main()
