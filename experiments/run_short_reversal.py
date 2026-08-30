"""Run the frozen liquid large/mid-cap short-term reversal study."""

from __future__ import annotations

import argparse
import gc
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.lowturn_livermore import Bar
from experiments.quarterly_portfolio import BasketConfig, simulate_basket
from experiments.run_largecap_lowvol import simulate_index, summarize_basket
from experiments.run_lowturn_livermore import _clean, _metrics, _returns
from factormine.config import Config
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel
from factormine.preprocess.neutralize import neutralize
from factormine.preprocess.standardize import zscore
from factormine.preprocess.winsorize import winsorize_mad
from factormine.research.combination import repair_point_in_time_size


FOLDS = (
    ("2016-2019", "2016-01-01", "2019-12-31"),
    ("2020-2022", "2020-01-01", "2022-12-31"),
    ("2023-2026", "2023-01-01", "2026-12-31"),
)
INITIAL_NAV = 400_000.0


def build_inputs(start: str, end: str) -> tuple:
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
    panel["_ret20"] = grouped["adj_close"].transform(
        lambda series: series / series.shift(20) - 1.0
    )
    one_price_down = (
        (panel["Open"] == panel["High"])
        & (panel["High"] == panel["Low"])
        & (panel["Low"] == panel["Close"])
        & (panel["PctChange"] <= -4.5)
    )
    panel["_down_limit_5"] = one_price_down.groupby(panel["Symbol"], sort=False).transform(
        lambda series: series.rolling(5, min_periods=1).max().astype(bool)
    )
    adv_pct = panel.groupby("TradingDay")["adv20"].rank(pct=True, method="first")
    panel["practical"] = (
        (~panel["suspended"].fillna(True))
        & (panel["age"] >= 252)
        & (panel["Close"] >= 5.0)
        & (panel["Volume"] > 0)
        & panel["CircMV"].notna()
        & panel["_ret20"].notna()
        & (panel["_ret20"] >= -0.30)
        & (~panel["_down_limit_5"])
        & (adv_pct > 0.50)
    )

    sessions = sorted(
        panel.loc[panel["TradingDay"] >= pd.Timestamp(start), "TradingDay"].drop_duplicates()
    )
    decision_dates = sessions[::20]
    targets = {"reversal_30": {}, "reversal_50": {}}
    cap_targets = {}
    equal_targets = {}
    all_symbols: set[str] = set()
    decisions = panel[panel["TradingDay"].isin(decision_dates) & panel["practical"]].copy()
    for day, group in decisions.groupby("TradingDay"):
        top500 = group.nlargest(500, "CircMV").copy()
        if len(top500) < 400:
            continue
        factor = winsorize_mad(top500["_ret20"], 5.0)
        factor = neutralize(factor, top500["industry"], top500["log_size"])
        top500["_score"] = -zscore(factor)
        ranked = top500.dropna(subset=["_score"]).sort_values(
            ["_score", "Symbol"], ascending=[False, True]
        )
        key = pd.Timestamp(day).date().isoformat()
        targets["reversal_30"][key] = ranked["Symbol"].astype(str).head(30).tolist()
        targets["reversal_50"][key] = ranked["Symbol"].astype(str).head(50).tolist()
        valid_cap = top500[top500["CircMV"] > 0]
        cap_sum = float(valid_cap["CircMV"].sum())
        cap_targets[key] = {
            str(symbol): float(value / cap_sum)
            for symbol, value in zip(valid_cap["Symbol"], valid_cap["CircMV"], strict=True)
        }
        equal_targets[key] = {str(symbol): 1.0 / len(top500) for symbol in top500["Symbol"]}
        all_symbols.update(top500["Symbol"].astype(str))

    columns = [
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
    market = panel[
        panel["Symbol"].isin(all_symbols) & panel["TradingDay"].isin(sessions)
    ][columns].copy()
    market = market.set_index(["TradingDay", "Symbol"]).sort_index()
    dates = [pd.Timestamp(day).date().isoformat() for day in sessions]
    metadata = {
        "panel_version": built.version_hash,
        "rows": int(len(panel)),
        "start": dates[0],
        "end": dates[-1],
        "rebalance_count": len(cap_targets),
        "symbols": len(all_symbols),
    }
    del panel, decisions
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

    return dates, lookup, targets, cap_targets, equal_targets, metadata


def decide(main: dict) -> dict:
    benchmark = main["benchmark_metrics"]
    checks = {
        "cagr_margin": main["excess_cagr"] >= 0.01,
        "sharpe_margin": main["metrics"]["sharpe"] >= benchmark["sharpe"] + 0.10,
        "max_drawdown": main["metrics"]["max_drawdown"] >= -0.35,
        "positive_excess_folds": main["positive_excess_folds"] >= 2,
        "best_year_independence": main["cagr_excluding_best_year"] > 0,
        "cost_retention": main["gross_to_net_cagr_retention"] >= 0.80,
        "turnover": main["annual_turnover"] <= 4.0,
        "execution": (
            main["average_positions"] >= 25
            and main["execution_failure_rate"] <= 0.10
            and main["missing_valuation_rate"] <= 0.02
        ),
    }
    if all(checks.values()):
        verdict = "GO"
    elif main["metrics"]["cagr"] > 0 and main["excess_cagr"] > 0:
        verdict = "MARGINAL"
    else:
        verdict = "NO-GO"
    return {"verdict": verdict, "checks": checks}


def render_markdown(payload: dict) -> str:
    lines = [
        "# A股流动性约束短期反转结果",
        "",
        f"- verdict: **{payload['decision']['verdict']}**",
        "",
        "| Variant | CAGR | Sharpe | Max drawdown | Excess CAGR | Turnover |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name in ("reversal_30", "reversal_50"):
        row = payload["variants"][name]
        metrics = row["metrics"]
        lines.append(
            f"| {name} | {metrics['cagr']:.2%} | {metrics['sharpe']:.3f} | "
            f"{metrics['max_drawdown']:.2%} | {row['excess_cagr']:.2%} | "
            f"{row['annual_turnover']:.2f} |"
        )
    for name, metrics in payload["benchmarks"].items():
        lines.append(
            f"| {name} | {metrics['cagr']:.2%} | {metrics['sharpe']:.3f} | "
            f"{metrics['max_drawdown']:.2%} | 0.00% | 0.00 |"
        )
    return "\n".join(lines)


def run(start: str, end: str) -> dict:
    dates, lookup, targets, cap_targets, equal_targets, metadata = build_inputs(start, end)
    cap_nav = simulate_index(dates, lookup, cap_targets)
    equal_nav = simulate_index(dates, lookup, equal_targets)
    cap_returns = _returns(cap_nav, INITIAL_NAV)
    equal_returns = _returns(equal_nav, INITIAL_NAV)
    variants = {}
    for name, count in (("reversal_30", 30), ("reversal_50", 50)):
        config = BasketConfig(name=name, target_count=count)
        net = simulate_basket(dates, lookup, targets[name], config)
        gross = simulate_basket(
            dates, lookup, targets[name], replace(config, buy_cost=0.0, sell_cost=0.0)
        )
        variants[name] = summarize_basket(
            net, gross, cap_returns, config, folds=FOLDS
        )
    decision = decide(variants["reversal_30"])
    return _clean(
        {
            "study": "a-share-short-reversal-v1",
            "data": metadata,
            "variants": variants,
            "benchmarks": {
                "top500_cap": _metrics(cap_returns),
                "top500_equal": _metrics(equal_returns),
            },
            "decision": decision,
            "limitations": [
                "historical ST authority is unavailable",
                "the interval is not virgin OOS",
                "residual return neutralization uses current-vintage industry history",
            ],
        }
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2016-01-01")
    parser.add_argument("--end", default="2026-08-25")
    parser.add_argument("--out-json", default="overall/a-share-short-reversal.json")
    parser.add_argument("--out-md", default="overall/a-share-short-reversal.md")
    args = parser.parse_args(argv)
    payload = run(args.start, args.end)
    Path(args.out_json).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown = render_markdown(payload)
    Path(args.out_md).write_text(markdown + "\n", encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
