"""Run the frozen management earnings-forecast drift study."""

from __future__ import annotations

import argparse
import gc
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.lowturn_livermore import Bar
from experiments.pead import POSITIVE_FORECAST_TYPES
from experiments.quarterly_portfolio import BasketConfig, simulate_basket
from experiments.run_largecap_lowvol import simulate_index, summarize_basket
from experiments.run_lowturn_livermore import _clean, _metrics, _returns
from factormine.config import Config
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel
from factormine.research.combination import repair_point_in_time_size


FOLDS = (
    ("2016-2019", "2016-01-01", "2019-12-31"),
    ("2020-2022", "2020-01-01", "2022-12-31"),
    ("2023-2026", "2023-01-01", "2026-12-31"),
)
ROUND_TRIP_COST = 0.0031
INITIAL_NAV = 400_000.0


def bootstrap_ci(values: np.ndarray, seed: int = 20260826, repetitions: int = 2_000) -> list[float]:
    clean = values[np.isfinite(values)]
    if len(clean) == 0:
        return [0.0, 0.0]
    rng = np.random.default_rng(seed)
    means = np.empty(repetitions)
    for index in range(repetitions):
        means[index] = rng.choice(clean, size=len(clean), replace=True).mean()
    return [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))]


def event_summary(events: pd.DataFrame, horizon: int) -> dict:
    column = f"active{horizon}"
    clean = events[column].dropna().to_numpy(dtype=float)
    by_fold = {}
    for name, start, end in FOLDS:
        period = events[events["signal_day"].between(start, end)][column].dropna()
        by_fold[name] = {
            "count": len(period),
            "mean": float(period.mean()) if len(period) else 0.0,
            "median": float(period.median()) if len(period) else 0.0,
            "win_rate": float((period > 0).mean()) if len(period) else 0.0,
        }
    return {
        "count": len(clean),
        "mean": float(clean.mean()) if len(clean) else 0.0,
        "median": float(np.median(clean)) if len(clean) else 0.0,
        "win_rate": float((clean > 0).mean()) if len(clean) else 0.0,
        "bootstrap_95": bootstrap_ci(clean),
        "folds": by_fold,
    }


def build_inputs(start: str, end: str, forecast_path: str) -> tuple:
    cfg = Config()
    connection = connect(cfg, read_only=True)
    try:
        built = load_or_build_panel(cfg, "2014-11-27", end, con=connection)
    finally:
        connection.close()
    panel = repair_point_in_time_size(built.df)
    panel["TradingDay"] = pd.to_datetime(panel["TradingDay"])
    panel = panel.sort_values(["TradingDay", "Symbol"]).reset_index(drop=True)
    adv_pct = panel.groupby("TradingDay")["adv20"].rank(pct=True, method="first")
    size_pct = panel.groupby("TradingDay")["log_size"].rank(pct=True, method="first")
    panel["practical"] = (
        (~panel["suspended"].fillna(True))
        & (panel["age"] >= 252)
        & (panel["Close"] >= 5.0)
        & (panel["Volume"] > 0)
        & (adv_pct > 0.50)
        & (size_pct > 0.50)
    )
    panel["_entry_blocked"] = (
        panel["one_word"].fillna(False) & (panel["PctChange"] > 0)
    )

    sessions = sorted(panel["TradingDay"].drop_duplicates())
    session_values = np.array(sessions, dtype="datetime64[ns]")
    event_source = pd.read_csv(forecast_path, dtype=str)
    event_source = event_source[
        event_source["type"].isin(POSITIVE_FORECAST_TYPES)
        & event_source["ann_date"].notna()
        & event_source["first_ann_date"].notna()
        & (event_source["ann_date"] == event_source["first_ann_date"])
    ].copy()
    event_source = event_source.drop_duplicates(["ts_code", "end_date", "ann_date", "type"])
    event_source["ann_date"] = pd.to_datetime(event_source["ann_date"], format="%Y%m%d")
    event_source["Symbol"] = event_source["ts_code"].str[:6]
    positions = np.searchsorted(session_values, event_source["ann_date"].to_numpy(dtype="datetime64[ns]"))
    valid_position = positions < len(sessions)
    event_source = event_source.loc[valid_position].copy()
    event_source["signal_day"] = [sessions[position] for position in positions[valid_position]]
    event_source = event_source[
        event_source["signal_day"].between(pd.Timestamp(start), pd.Timestamp(end))
    ].copy()
    for column in ("p_change_min", "p_change_max"):
        event_source[column] = pd.to_numeric(event_source[column], errors="coerce")
    event_source["p_change_mid"] = event_source[["p_change_min", "p_change_max"]].mean(axis=1)

    wide_open = panel.pivot(index="TradingDay", columns="Symbol", values="adj_open")
    wide_practical = panel.pivot(index="TradingDay", columns="Symbol", values="practical").fillna(False)
    wide_blocked = panel.pivot(index="TradingDay", columns="Symbol", values="_entry_blocked").fillna(False)
    entry = wide_open.shift(-1)
    forward20 = wide_open.shift(-21) / entry - 1.0
    forward60 = wide_open.shift(-61) / entry - 1.0
    benchmark20 = forward20.where(wide_practical).mean(axis=1)
    benchmark60 = forward60.where(wide_practical).mean(axis=1)
    blocked_next = wide_blocked.shift(-1).fillna(True)

    date_positions = {date: index for index, date in enumerate(wide_open.index)}
    symbol_positions = {symbol: index for index, symbol in enumerate(wide_open.columns)}
    row_index = event_source["signal_day"].map(date_positions)
    col_index = event_source["Symbol"].map(symbol_positions)
    valid_lookup = row_index.notna() & col_index.notna()
    event_source = event_source.loc[valid_lookup].copy()
    rows = row_index.loc[valid_lookup].astype(int).to_numpy()
    cols = col_index.loc[valid_lookup].astype(int).to_numpy()
    practical_values = wide_practical.to_numpy(dtype=bool)[rows, cols]
    blocked_values = blocked_next.to_numpy(dtype=bool)[rows, cols]
    event_source["practical"] = practical_values
    event_source["entry_blocked"] = blocked_values
    event_source["return20"] = forward20.to_numpy()[rows, cols]
    event_source["return60"] = forward60.to_numpy()[rows, cols]
    event_source["benchmark20"] = event_source["signal_day"].map(benchmark20)
    event_source["benchmark60"] = event_source["signal_day"].map(benchmark60)
    event_source = event_source[event_source["practical"]].copy()
    event_source["active20"] = (
        event_source["return20"] - event_source["benchmark20"] - ROUND_TRIP_COST
    )
    event_source["active60"] = (
        event_source["return60"] - event_source["benchmark60"] - ROUND_TRIP_COST
    )
    event_source.loc[event_source["entry_blocked"], ["active20", "active60"]] = np.nan

    simulation_sessions = [date for date in sessions if pd.Timestamp(start) <= date <= pd.Timestamp(end)]
    month_ends = (
        pd.Series(simulation_sessions)
        .groupby(pd.Series(simulation_sessions).dt.to_period("M"))
        .max()
        .tolist()
    )
    targets: dict[str, list[str]] = {}
    cap_targets: dict[str, dict[str, float]] = {}
    all_symbols: set[str] = set()
    for day in month_ends:
        month = pd.Timestamp(day).to_period("M")
        cohort = event_source[
            (event_source["signal_day"].dt.to_period("M") == month)
            & (~event_source["entry_blocked"])
        ].copy()
        cohort = cohort.sort_values(
            ["p_change_mid", "Symbol"], ascending=[False, True], na_position="last"
        ).drop_duplicates("Symbol")
        key = pd.Timestamp(day).date().isoformat()
        targets[key] = cohort["Symbol"].head(20).tolist()
        day_rows = panel[(panel["TradingDay"] == day) & panel["practical"]].nlargest(500, "CircMV")
        cap_sum = float(day_rows["CircMV"].sum())
        cap_targets[key] = {
            str(symbol): float(value / cap_sum)
            for symbol, value in zip(day_rows["Symbol"], day_rows["CircMV"], strict=True)
            if cap_sum > 0
        }
        all_symbols.update(day_rows["Symbol"].astype(str))
        all_symbols.update(targets[key])

    market = panel[
        panel["Symbol"].isin(all_symbols) & panel["TradingDay"].isin(simulation_sessions)
    ][
        [
            "TradingDay",
            "Symbol",
            "adj_open",
            "adj_close",
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
            "PctChange",
        ]
    ].copy()
    market = market.set_index(["TradingDay", "Symbol"]).sort_index()
    dates = [date.date().isoformat() for date in simulation_sessions]
    metadata = {
        "panel_version": built.version_hash,
        "forecast_rows": len(pd.read_csv(forecast_path, usecols=["ts_code"])),
        "first_positive_events": len(event_source),
        "start": dates[0],
        "end": dates[-1],
        "month_count": len(targets),
    }
    del panel, wide_open, wide_practical, wide_blocked, entry, forward20, forward60
    gc.collect()

    def lookup(date: str, symbol: str) -> Bar | None:
        try:
            row = market.loc[(pd.Timestamp(date), symbol)]
        except KeyError:
            return None
        return Bar(
            adj_open=float(row["adj_open"]),
            adj_close=float(row["adj_close"]),
            raw_open=float(row["Open"]),
            raw_high=float(row["High"]),
            raw_low=float(row["Low"]),
            raw_close=float(row["Close"]),
            volume=float(row["Volume"]),
            pct_change=float(row["PctChange"]),
        )

    return dates, lookup, event_source, targets, cap_targets, metadata


def decide(events: dict, portfolio: dict) -> dict:
    event_checks = {
        "active20": events["combined20"]["mean"] >= 0.01,
        "active60": events["combined60"]["mean"] >= 0.015,
        "positive_folds": sum(
            fold["mean"] > 0 for fold in events["combined20"]["folds"].values()
        )
        >= 2,
        "win_rate": events["combined20"]["win_rate"] > 0.52,
        "entry_coverage": events["blocked_rate"] <= 0.10,
    }
    portfolio_checks = {
        "cagr_margin": portfolio["excess_cagr"] >= 0.01,
        "sharpe_margin": (
            portfolio["metrics"]["sharpe"]
            >= portfolio["benchmark_metrics"]["sharpe"] + 0.10
        ),
        "max_drawdown": portfolio["metrics"]["max_drawdown"] >= -0.35,
        "positive_excess_folds": portfolio["positive_excess_folds"] >= 2,
        "best_year_independence": portfolio["cagr_excluding_best_year"] > 0,
        "cost_retention": portfolio["gross_to_net_cagr_retention"] >= 0.80,
        "turnover": portfolio["annual_turnover"] <= 4.0,
        "execution": (
            portfolio["execution_failure_rate"] <= 0.10
            and portfolio["missing_valuation_rate"] <= 0.02
        ),
    }
    if all(event_checks.values()) and all(portfolio_checks.values()):
        verdict = "GO"
    elif all(event_checks.values()) and portfolio["metrics"]["cagr"] > 0:
        verdict = "MARGINAL"
    else:
        verdict = "NO-GO"
    return {"verdict": verdict, "event_checks": event_checks, "portfolio_checks": portfolio_checks}


def render_markdown(payload: dict) -> str:
    event = payload["events"]
    portfolio = payload["portfolio"]
    return "\n".join(
        [
            "# A股业绩预告漂移结果",
            "",
            f"- verdict: **{payload['decision']['verdict']}**",
            f"- usable first positive events: {payload['data']['first_positive_events']}",
            "",
            "| Event | Count | Mean active 20d | Win rate | Mean active 60d |",
            "| --- | ---: | ---: | ---: | ---: |",
            f"| combined | {event['combined20']['count']} | {event['combined20']['mean']:.2%} | "
            f"{event['combined20']['win_rate']:.2%} | {event['combined60']['mean']:.2%} |",
            f"| preincrease | {event['preincrease20']['count']} | {event['preincrease20']['mean']:.2%} | "
            f"{event['preincrease20']['win_rate']:.2%} | {event['preincrease60']['mean']:.2%} |",
            f"| turnaround | {event['turnaround20']['count']} | {event['turnaround20']['mean']:.2%} | "
            f"{event['turnaround20']['win_rate']:.2%} | {event['turnaround60']['mean']:.2%} |",
            "",
            f"- portfolio CAGR: {portfolio['metrics']['cagr']:.2%}",
            f"- benchmark CAGR: {portfolio['benchmark_metrics']['cagr']:.2%}",
            f"- portfolio Sharpe: {portfolio['metrics']['sharpe']:.3f}",
            f"- portfolio max drawdown: {portfolio['metrics']['max_drawdown']:.2%}",
        ]
    )


def run(start: str, end: str, forecast_path: str) -> dict:
    dates, lookup, event_frame, targets, cap_targets, metadata = build_inputs(
        start, end, forecast_path
    )
    blocked_rate = float(event_frame["entry_blocked"].mean()) if len(event_frame) else 0.0
    events = {
        "combined20": event_summary(event_frame, 20),
        "combined60": event_summary(event_frame, 60),
        "preincrease20": event_summary(event_frame[event_frame["type"] == "预增"], 20),
        "preincrease60": event_summary(event_frame[event_frame["type"] == "预增"], 60),
        "turnaround20": event_summary(event_frame[event_frame["type"] == "扭亏"], 20),
        "turnaround60": event_summary(event_frame[event_frame["type"] == "扭亏"], 60),
        "blocked_rate": blocked_rate,
    }
    cap_nav = simulate_index(dates, lookup, cap_targets)
    cap_returns = _returns(cap_nav, INITIAL_NAV)
    config = BasketConfig(name="forecast_drift_monthly", target_count=20)
    net = simulate_basket(dates, lookup, targets, config)
    gross = simulate_basket(
        dates, lookup, targets, replace(config, buy_cost=0.0, sell_cost=0.0)
    )
    portfolio = summarize_basket(net, gross, cap_returns, config, folds=FOLDS)
    decision = decide(events, portfolio)
    return _clean(
        {
            "study": "a-share-management-forecast-drift-v1",
            "data": metadata,
            "events": events,
            "portfolio": portfolio,
            "decision": decision,
            "limitations": [
                "announcement time-of-day is unavailable, so entry is delayed to the following open",
                "management forecast drift is adjacent to but not identical to analyst-consensus PEAD",
                "forecast data are current-vintage and may lack withdrawn historical records",
                "the interval is not virgin OOS",
            ],
        }
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--forecast", default="overall/a-share-forecast-vip.csv")
    parser.add_argument("--start", default="2016-01-01")
    parser.add_argument("--end", default="2026-08-25")
    parser.add_argument("--out-json", default="overall/a-share-pead.json")
    parser.add_argument("--out-md", default="overall/a-share-pead.md")
    args = parser.parse_args(argv)
    payload = run(args.start, args.end, args.forecast)
    Path(args.out_json).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown = render_markdown(payload)
    Path(args.out_md).write_text(markdown + "\n", encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
