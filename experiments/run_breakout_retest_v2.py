"""Run the breakout-level retest V2 event study and failure ledger."""

from __future__ import annotations

import argparse
import gc
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.breakout_retest import RetestBar, evaluate_retest
from experiments.run_pead import bootstrap_ci
from experiments.run_lowturn_livermore import _clean
from factormine.config import Config
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel
from factormine.research.combination import repair_point_in_time_size


FOLDS = (
    ("2016-2019", "2016-01-01", "2019-12-31"),
    ("2020-2022", "2020-01-01", "2022-12-31"),
    ("2023-2026", "2023-01-01", "2026-12-31"),
)
COST = 0.0031


def event_metrics(events: pd.DataFrame, horizon: int) -> dict:
    column = f"active{horizon}"
    clean = events[column].dropna()
    folds = {}
    for name, start, end in FOLDS:
        period = events[events["signal_date"].between(start, end)][column].dropna()
        folds[name] = {
            "count": len(period),
            "mean": float(period.mean()) if len(period) else 0.0,
            "median": float(period.median()) if len(period) else 0.0,
            "win_rate": float((period > 0).mean()) if len(period) else 0.0,
        }
    return {
        "count": len(clean),
        "mean": float(clean.mean()) if len(clean) else 0.0,
        "median": float(clean.median()) if len(clean) else 0.0,
        "win_rate": float((clean > 0).mean()) if len(clean) else 0.0,
        "bootstrap_95": bootstrap_ci(clean.to_numpy(dtype=float)),
        "folds": folds,
    }


def build_events(start: str, end: str) -> tuple[pd.DataFrame, dict]:
    cfg = Config()
    connection = connect(cfg, read_only=True)
    try:
        built = load_or_build_panel(cfg, "2014-11-27", end, con=connection)
    finally:
        connection.close()
    panel = repair_point_in_time_size(built.df)
    panel["TradingDay"] = pd.to_datetime(panel["TradingDay"])
    panel = panel.sort_values(["Symbol", "TradingDay"]).reset_index(drop=True)
    grouped = panel.groupby("Symbol", sort=False)
    previous_close = grouped["adj_close"].shift(1)
    true_range = pd.concat(
        [
            panel["adj_high"] - panel["adj_low"],
            (panel["adj_high"] - previous_close).abs(),
            (panel["adj_low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    panel["_atr5"] = true_range.groupby(panel["Symbol"], sort=False).transform(
        lambda series: series.rolling(5, min_periods=5).mean()
    )
    panel["_atr20"] = true_range.groupby(panel["Symbol"], sort=False).transform(
        lambda series: series.rolling(20, min_periods=20).mean()
    )
    panel["_level"] = grouped["adj_high"].transform(
        lambda series: series.shift(1).rolling(20, min_periods=20).max()
    )
    panel["_amount_med20"] = grouped["Amount"].transform(
        lambda series: series.shift(1).rolling(20, min_periods=20).median()
    )
    adv_pct = panel.groupby("TradingDay")["adv20"].rank(pct=True, method="first")
    size_rank = panel.groupby("TradingDay")["CircMV"].rank(
        method="first", ascending=False
    )
    panel["_universe"] = (
        (~panel["suspended"].fillna(True))
        & (panel["age"] >= 252)
        & (panel["Close"] >= 5.0)
        & (panel["Volume"] > 0)
        & panel["_atr20"].notna()
        & (adv_pct > 0.50)
        & (size_rank <= 500)
    )
    location = (panel["adj_close"] - panel["adj_low"]) / (
        panel["adj_high"] - panel["adj_low"]
    ).replace(0, np.nan)
    one_word_up = (
        (panel["Open"] == panel["High"])
        & (panel["High"] == panel["Low"])
        & (panel["Low"] == panel["Close"])
        & (panel["PctChange"] >= 4.5)
    )
    preliminary = (
        panel["_universe"]
        & (panel["adj_close"] > panel["_level"] + 0.5 * panel["_atr20"])
        & (panel["Amount"] >= 1.5 * panel["_amount_med20"])
        & (location >= 0.70)
        & (~one_word_up)
        & panel["TradingDay"].between(pd.Timestamp(start), pd.Timestamp(end))
    )
    panel["_breakout_candidate"] = preliminary
    panel["_one_word_up"] = one_word_up
    panel["_close_location"] = location

    rows = []
    for symbol, group in panel.groupby("Symbol", sort=False):
        group = group.sort_values("TradingDay").reset_index(drop=True)
        candidate_indices = set(group.index[group["_breakout_candidate"]])
        skip_through = -1
        for index in sorted(candidate_indices):
            if index <= skip_through or index < 40 or index + 1 >= len(group):
                continue
            prior20 = group.iloc[index - 20 : index]
            resistance_position = int(np.argmax(prior20["adj_high"].to_numpy()))
            resistance_age = 20 - resistance_position
            prior40 = group.iloc[index - 40 : index]
            range_width = (
                float(prior40["adj_high"].max() - prior40["adj_low"].min())
                / float(prior40["adj_high"].max())
            )
            if resistance_age < 5 or range_width > 0.30:
                continue
            breakout = group.iloc[index]
            future = group.iloc[index + 1 : index + 13]
            bars = [
                RetestBar(
                    high=float(item["adj_high"]),
                    low=float(item["adj_low"]),
                    close=float(item["adj_close"]),
                    previous_close=float(group.iloc[index + offset - 1].adj_close),
                    amount=float(item["Amount"]),
                    atr5=(
                        float(item["_atr5"])
                        if np.isfinite(item["_atr5"])
                        else float("inf")
                    ),
                    one_word_up=bool(item["_one_word_up"]),
                )
                for offset, (_, item) in enumerate(future.iterrows(), start=1)
            ]
            outcome = evaluate_retest(
                bars,
                breakout_level=float(breakout["_level"]),
                breakout_atr=float(breakout["_atr20"]),
                breakout_amount=float(breakout.Amount),
            )
            terminal_offset = outcome.trigger_index or 12
            skip_through = index + terminal_offset
            trigger_index = index + outcome.trigger_index if outcome.trigger_index else None
            signal_date = group.iloc[trigger_index].TradingDay if trigger_index is not None else pd.NaT
            execution_reason = "not_triggered"
            entry_date = pd.NaT
            entry_open = np.nan
            entry_gap_atr = np.nan
            if trigger_index is not None and trigger_index + 1 < len(group):
                trigger = group.iloc[trigger_index]
                entry = group.iloc[trigger_index + 1]
                entry_date = entry.TradingDay
                entry_open = float(entry.adj_open)
                entry_gap_atr = float(
                    (entry.adj_open - trigger.adj_close) / breakout["_atr20"]
                )
                if entry.Volume <= 0 or not np.isfinite(entry.adj_open):
                    execution_reason = "missing_or_suspended_open"
                elif bool(entry["_one_word_up"]):
                    execution_reason = "entry_limit_up"
                elif entry.adj_open > trigger.adj_close + 0.5 * breakout["_atr20"]:
                    execution_reason = "entry_gap_above_half_atr"
                elif entry.adj_open <= outcome.pullback_low:
                    execution_reason = "entry_below_pullback_low"
                else:
                    execution_reason = "executed"
            retest_amount_ratio = np.nan
            retest_atr_ratio = np.nan
            if outcome.retest_index is not None:
                retest_window = future.iloc[: outcome.retest_index]
                retest_amount_ratio = float(
                    retest_window["Amount"].median() / breakout.Amount
                )
                retest_atr_ratio = float(
                    future.iloc[outcome.retest_index - 1]["_atr5"] / breakout["_atr20"]
                )
            rows.append(
                {
                    "event_id": f"{symbol}-{breakout.TradingDay.date().isoformat()}",
                    "symbol": str(symbol),
                    "breakout_date": breakout.TradingDay,
                    "breakout_level": float(breakout["_level"]),
                    "breakout_atr": float(breakout["_atr20"]),
                    "breakout_amount": float(breakout.Amount),
                    "breakout_amount_ratio": float(
                        breakout.Amount / breakout["_amount_med20"]
                    ),
                    "breakout_extension_atr": float(
                        (breakout.adj_close - breakout["_level"]) / breakout["_atr20"]
                    ),
                    "breakout_close_location": float(breakout["_close_location"]),
                    "range_width40": range_width,
                    "resistance_age": resistance_age,
                    "terminal_reason": outcome.terminal_reason,
                    "retest_date": (
                        group.iloc[index + outcome.retest_index].TradingDay
                        if outcome.retest_index is not None
                        else pd.NaT
                    ),
                    "signal_date": signal_date,
                    "entry_date": entry_date,
                    "execution_reason": execution_reason,
                    "pullback_low": outcome.pullback_low,
                    "pullback_depth_atr": float(
                        (breakout["_level"] - outcome.pullback_low) / breakout["_atr20"]
                    ),
                    "days_to_retest": outcome.retest_index,
                    "days_to_trigger": outcome.trigger_index,
                    "retest_amount_ratio": retest_amount_ratio,
                    "retest_atr_ratio": retest_atr_ratio,
                    "entry_open": entry_open,
                    "entry_gap_atr": entry_gap_atr,
                    "signal_index": trigger_index,
                }
            )
    events = pd.DataFrame(rows)

    sessions = sorted(panel["TradingDay"].drop_duplicates())
    simulation_panel = panel[panel["TradingDay"].between(pd.Timestamp(start), pd.Timestamp(end))]
    wide_open = simulation_panel.pivot(index="TradingDay", columns="Symbol", values="adj_open")
    wide_universe = simulation_panel.pivot(index="TradingDay", columns="Symbol", values="_universe").fillna(False)
    fwd = {
        horizon: wide_open.shift(-(horizon + 1)) / wide_open.shift(-1) - 1.0
        for horizon in (5, 10, 20)
    }
    benchmarks = {
        horizon: matrix.where(wide_universe).mean(axis=1) for horizon, matrix in fwd.items()
    }
    date_positions = {date: pos for pos, date in enumerate(wide_open.index)}
    symbol_positions = {symbol: pos for pos, symbol in enumerate(wide_open.columns)}
    executed = events[events["execution_reason"] == "executed"].copy()
    if len(executed):
        row_index = executed["signal_date"].map(date_positions)
        col_index = executed["symbol"].map(symbol_positions)
        valid = row_index.notna() & col_index.notna()
        executed = executed.loc[valid].copy()
        row_values = row_index.loc[valid].astype(int).to_numpy()
        col_values = col_index.loc[valid].astype(int).to_numpy()
        for horizon in (5, 10, 20):
            executed[f"return{horizon}"] = fwd[horizon].to_numpy()[row_values, col_values]
            executed[f"benchmark{horizon}"] = executed["signal_date"].map(benchmarks[horizon])
            executed[f"active{horizon}"] = (
                executed[f"return{horizon}"] - executed[f"benchmark{horizon}"] - COST
            )
        executed["outcome_reason"] = np.select(
            [
                executed["active20"] > 0,
                (executed["active5"] <= 0) & (executed["active20"] <= 0),
            ],
            ["successful_20d", "early_failure"],
            default="failed_after_initial_strength",
        )
        events = events.merge(
            executed[
                [
                    "event_id",
                    "return5",
                    "return10",
                    "return20",
                    "benchmark5",
                    "benchmark10",
                    "benchmark20",
                    "active5",
                    "active10",
                    "active20",
                    "outcome_reason",
                ]
            ],
            on="event_id",
            how="left",
        )
    else:
        for column in (
            "return5", "return10", "return20", "benchmark5", "benchmark10", "benchmark20",
            "active5", "active10", "active20", "outcome_reason",
        ):
            events[column] = np.nan
    metadata = {
        "panel_version": built.version_hash,
        "panel_rows": len(panel),
        "event_count": len(events),
        "executed_count": int((events["execution_reason"] == "executed").sum()),
        "start": start,
        "end": end,
    }
    del panel, simulation_panel, wide_open, wide_universe, fwd
    gc.collect()
    return events, metadata


def decide(events: pd.DataFrame) -> tuple[dict, dict]:
    executed = events[events["execution_reason"] == "executed"].copy()
    metrics = {horizon: event_metrics(executed, horizon) for horizon in (5, 10, 20)}
    rejected = events[events["terminal_reason"] == "triggered"]
    rejection_rate = (
        float((rejected["execution_reason"] != "executed").mean()) if len(rejected) else 1.0
    )
    checks = {
        "count": metrics[20]["count"] >= 300,
        "active10": metrics[10]["mean"] >= 0.01,
        "active20": metrics[20]["mean"] >= 0.01,
        "median20": metrics[20]["median"] > 0,
        "win_rate20": metrics[20]["win_rate"] > 0.52,
        "positive_folds": sum(fold["mean"] > 0 for fold in metrics[20]["folds"].values()) >= 2,
        "bootstrap": metrics[20]["bootstrap_95"][0] > 0,
        "execution": rejection_rate <= 0.15,
    }
    if all(checks.values()):
        verdict = "GO"
    elif metrics[20]["mean"] > 0:
        verdict = "MARGINAL"
    else:
        verdict = "NO-GO"
    failure_summary = {
        "terminal_reasons": dict(Counter(events["terminal_reason"])),
        "execution_reasons": dict(Counter(events["execution_reason"])),
        "outcome_reasons": dict(Counter(events["outcome_reason"].dropna())),
        "rejection_rate": rejection_rate,
    }
    return {"verdict": verdict, "checks": checks, "metrics": metrics}, failure_summary


def render_markdown(payload: dict) -> str:
    metrics = payload["decision"]["metrics"]
    lines = [
        "# A股突破位回踩V2结果", "",
        f"- verdict: **{payload['decision']['verdict']}**",
        f"- events/executed: {payload['data']['event_count']}/{payload['data']['executed_count']}", "",
        "| Horizon | Mean active | Median | Win rate | Bootstrap 95% |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for horizon in (5, 10, 20):
        row = metrics[str(horizon)] if str(horizon) in metrics else metrics[horizon]
        lines.append(
            f"| {horizon}d | {row['mean']:.2%} | {row['median']:.2%} | "
            f"{row['win_rate']:.2%} | [{row['bootstrap_95'][0]:.2%}, {row['bootstrap_95'][1]:.2%}] |"
        )
    lines.extend(["", "## Failure reasons", ""])
    for reason, count in sorted(payload["failure_summary"]["terminal_reasons"].items(), key=lambda item: -item[1]):
        lines.append(f"- `{reason}`: {count}")
    return "\n".join(lines)


def run(start: str, end: str, ledger_path: str) -> dict:
    events, metadata = build_events(start, end)
    events.to_csv(ledger_path, index=False, date_format="%Y-%m-%d")
    decision, failures = decide(events)
    return _clean(
        {
            "study": "a-share-breakout-level-retest-v2",
            "data": metadata,
            "decision": decision,
            "failure_summary": failures,
            "ledger": ledger_path,
            "limitations": [
                "historical ST authority is unavailable",
                "daily bars cannot observe intraday retest order or auction queue position",
                "one event per symbol is suppressed for twelve sessions after breakout",
                "the interval is not virgin OOS",
            ],
        }
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2016-01-01")
    parser.add_argument("--end", default="2026-08-25")
    parser.add_argument("--ledger", default="overall/a-share-breakout-retest-v2-events.csv")
    parser.add_argument("--out-json", default="overall/a-share-breakout-retest-v2.json")
    parser.add_argument("--out-md", default="overall/a-share-breakout-retest-v2.md")
    args = parser.parse_args(argv)
    payload = run(args.start, args.end, args.ledger)
    Path(args.out_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = render_markdown(payload)
    Path(args.out_md).write_text(markdown + "\n", encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
