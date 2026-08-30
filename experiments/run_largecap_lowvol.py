"""Run the frozen quarterly large-cap low-volatility study."""

from __future__ import annotations

import argparse
import gc
import json
import math
import sys
from dataclasses import replace
from pathlib import Path

QUANT_REPO = Path("/home/ygguo/agent-projs/quant-claude")
if str(QUANT_REPO) not in sys.path:
    sys.path.insert(0, str(QUANT_REPO))

import numpy as np
import pandas as pd

from experiments.lowturn_livermore import Bar
from experiments.quarterly_portfolio import (
    BasketConfig,
    select_industry_balanced,
    simulate_basket,
)
from experiments.run_lowturn_livermore import _clean, _metrics, _returns
from factormine.config import Config
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel
from factormine.research.combination import repair_point_in_time_size


FOLDS = (
    ("2018-2020", "2018-01-01", "2020-12-31"),
    ("2021-2023", "2021-01-01", "2023-12-31"),
    ("2024-2026", "2024-01-01", "2026-12-31"),
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
    panel["_daily_return"] = grouped["adj_close"].pct_change(fill_method=None)
    panel["_vol252"] = grouped["_daily_return"].transform(
        lambda series: series.rolling(252, min_periods=200).std()
    )
    adv_pct = panel.groupby("TradingDay")["adv20"].rank(pct=True, method="first")
    panel["practical"] = (
        (~panel["suspended"].fillna(True))
        & (panel["age"] >= 252)
        & (panel["Close"] >= 5.0)
        & (panel["Volume"] > 0)
        & panel["CircMV"].notna()
        & panel["_vol252"].notna()
        & (adv_pct > 0.50)
    )

    sessions = sorted(
        panel.loc[panel["TradingDay"] >= pd.Timestamp(start), "TradingDay"].drop_duplicates()
    )
    decision_dates = sessions[::63]
    targets = {"balanced_30": {}, "naive_30": {}, "balanced_50": {}}
    cap_targets: dict[str, dict[str, float]] = {}
    equal_targets: dict[str, dict[str, float]] = {}
    all_symbols: set[str] = set()
    decisions = panel[panel["TradingDay"].isin(decision_dates) & panel["practical"]].copy()
    for day, group in decisions.groupby("TradingDay"):
        top300 = group.nlargest(300, "CircMV").copy()
        if len(top300) < 250:
            continue
        top300["_industry_pct"] = top300.groupby("industry")["_vol252"].rank(
            pct=True, method="first", ascending=True
        )
        rows = [
            (str(symbol), str(industry), float(volatility), float(percentile))
            for symbol, industry, volatility, percentile in zip(
                top300["Symbol"],
                top300["industry"],
                top300["_vol252"],
                top300["_industry_pct"],
                strict=True,
            )
        ]
        key = pd.Timestamp(day).date().isoformat()
        targets["balanced_30"][key] = select_industry_balanced(rows, 30, 4)
        targets["balanced_50"][key] = select_industry_balanced(rows, 50, 6)
        targets["naive_30"][key] = (
            top300.sort_values(["_vol252", "Symbol"])["Symbol"].astype(str).head(30).tolist()
        )
        valid_cap = top300[top300["CircMV"] > 0]
        cap_sum = float(valid_cap["CircMV"].sum())
        cap_targets[key] = {
            str(symbol): float(value / cap_sum)
            for symbol, value in zip(valid_cap["Symbol"], valid_cap["CircMV"], strict=True)
        }
        equal_targets[key] = {str(symbol): 1.0 / len(top300) for symbol in top300["Symbol"]}
        all_symbols.update(top300["Symbol"].astype(str))

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


def simulate_index(
    dates: list[str],
    lookup,
    targets: dict[str, dict[str, float]],
) -> pd.Series:
    signal_to_execution = {
        dates[index + 1]: weights
        for index, date in enumerate(dates[:-1])
        if (weights := targets.get(date)) is not None
    }
    cash = INITIAL_NAV
    shares: dict[str, float] = {}
    last_close: dict[str, float] = {}
    navs = []
    for date in dates:
        if date in signal_to_execution:
            nav_open = cash + sum(
                quantity
                * (
                    lookup(date, symbol).adj_open
                    if lookup(date, symbol) is not None
                    else last_close.get(symbol, 0.0)
                )
                for symbol, quantity in shares.items()
            )
            cash = nav_open
            shares = {}
            for symbol, weight in signal_to_execution[date].items():
                bar = lookup(date, symbol)
                if bar is None or bar.volume <= 0:
                    continue
                notional = nav_open * weight
                shares[symbol] = notional / bar.adj_open
                last_close[symbol] = bar.adj_open
                cash -= notional
        value = cash
        for symbol, quantity in shares.items():
            bar = lookup(date, symbol)
            if bar is not None:
                last_close[symbol] = bar.adj_close
            value += quantity * last_close[symbol]
        navs.append(value)
    return pd.Series(navs, index=pd.to_datetime(dates), dtype=float)


def summarize_basket(
    result,
    gross_result,
    benchmark_returns: pd.Series,
    config: BasketConfig,
    folds=FOLDS,
) -> dict:
    index = pd.to_datetime(result.dates)
    nav = pd.Series(result.nav, index=index, dtype=float)
    gross_nav = pd.Series(gross_result.nav, index=index, dtype=float)
    returns = _returns(nav, config.initial_nav)
    gross_returns = _returns(gross_nav, config.initial_nav)
    metrics = _metrics(returns)
    gross_metrics = _metrics(gross_returns)
    benchmark_metrics = _metrics(benchmark_returns)
    fold_results = {}
    positive_excess_folds = 0
    for name, start, end in folds:
        fold = _metrics(returns.loc[start:end])
        benchmark_fold = _metrics(benchmark_returns.loc[start:end])
        fold["benchmark_cagr"] = benchmark_fold["cagr"]
        fold["excess_cagr"] = fold["cagr"] - benchmark_fold["cagr"]
        if fold["excess_cagr"] > 0:
            positive_excess_folds += 1
        fold_results[name] = fold
    yearly = {
        str(year): float((1.0 + group).prod() - 1.0)
        for year, group in returns.groupby(returns.index.year)
    }
    best_year = max(yearly, key=yearly.get) if yearly else None
    remaining = [value for year, value in yearly.items() if year != best_year]
    cagr_without_best = (
        float(np.prod([1.0 + value for value in remaining]) ** (1.0 / len(remaining)) - 1.0)
        if remaining
        else 0.0
    )
    buys = [trade for trade in result.trades if trade["side"] == "BUY"]
    sells = [trade for trade in result.trades if trade["side"] == "SELL"]
    years = len(result.dates) / 252.0
    average_nav = float(nav.mean())
    annual_turnover = (
        0.5 * sum(trade["notional"] for trade in result.trades) / average_nav / years
        if years > 0 and average_nav > 0
        else 0.0
    )
    failures = result.blocked_buys + result.lot_failures
    attempts = len(buys) + failures
    retention = metrics["cagr"] / gross_metrics["cagr"] if gross_metrics["cagr"] > 0 else 0.0
    return {
        "metrics": metrics,
        "gross_metrics": gross_metrics,
        "benchmark_metrics": benchmark_metrics,
        "excess_cagr": metrics["cagr"] - benchmark_metrics["cagr"],
        "gross_to_net_cagr_retention": retention,
        "folds": fold_results,
        "positive_excess_folds": positive_excess_folds,
        "yearly_returns": yearly,
        "best_year": best_year,
        "best_year_return": yearly.get(best_year, 0.0) if best_year else 0.0,
        "cagr_excluding_best_year": cagr_without_best,
        "annual_turnover": annual_turnover,
        "average_positions": float(np.mean(result.position_count)),
        "minimum_positions": int(np.min(result.position_count)),
        "average_cash_fraction": float(np.mean(result.cash_fraction)),
        "trade_count": len(result.trades),
        "buy_count": len(buys),
        "sell_count": len(sells),
        "fees": float(sum(trade["fee"] for trade in result.trades)),
        "blocked_buys": result.blocked_buys,
        "blocked_sells": result.blocked_sells,
        "lot_failures": result.lot_failures,
        "expired_buys": result.expired_buys,
        "execution_failure_rate": failures / attempts if attempts else 0.0,
        "missing_valuation_rate": (
            result.missing_valuation_days / result.position_days if result.position_days else 0.0
        ),
    }


def decide(main: dict) -> dict:
    benchmark = main["benchmark_metrics"]
    drawdown_improvement = (
        (abs(benchmark["max_drawdown"]) - abs(main["metrics"]["max_drawdown"]))
        / abs(benchmark["max_drawdown"])
        if benchmark["max_drawdown"] < 0
        else 0.0
    )
    checks = {
        "cagr_margin": main["excess_cagr"] >= 0.01,
        "sharpe_margin": main["metrics"]["sharpe"] >= benchmark["sharpe"] + 0.10,
        "drawdown_improvement": drawdown_improvement >= 0.15,
        "positive_excess_folds": main["positive_excess_folds"] >= 2,
        "best_year_independence": main["cagr_excluding_best_year"] >= 0,
        "cost_retention": main["gross_to_net_cagr_retention"] >= 0.90,
        "turnover": main["annual_turnover"] <= 2.0,
        "execution": (
            main["average_positions"] >= 25
            and main["execution_failure_rate"] <= 0.10
            and main["missing_valuation_rate"] <= 0.02
        ),
    }
    if all(checks.values()):
        verdict = "GO"
    elif main["metrics"]["cagr"] > 0 and main["excess_cagr"] > 0 and drawdown_improvement > 0:
        verdict = "MARGINAL"
    else:
        verdict = "NO-GO"
    return {"verdict": verdict, "checks": checks, "drawdown_improvement": drawdown_improvement}


def render_markdown(payload: dict) -> str:
    lines = [
        "# A股大盘低波策略回测结果",
        "",
        f"- verdict: **{payload['decision']['verdict']}**",
        f"- data: {payload['data']['start']}—{payload['data']['end']}",
        f"- rebalances: {payload['data']['rebalance_count']}",
        "",
        "| Variant | CAGR | Sharpe | Max drawdown | Excess CAGR | Avg positions | Turnover |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name in ("balanced_30", "naive_30", "balanced_50"):
        row = payload["variants"][name]
        metrics = row["metrics"]
        lines.append(
            f"| {name} | {metrics['cagr']:.2%} | {metrics['sharpe']:.3f} | "
            f"{metrics['max_drawdown']:.2%} | {row['excess_cagr']:.2%} | "
            f"{row['average_positions']:.1f} | {row['annual_turnover']:.2f} |"
        )
    for name in ("top300_cap", "top300_equal"):
        metrics = payload["benchmarks"][name]
        lines.append(
            f"| {name} | {metrics['cagr']:.2%} | {metrics['sharpe']:.3f} | "
            f"{metrics['max_drawdown']:.2%} | 0.00% | 300 | 0.00 |"
        )
    lines.extend(["", "## Gate", ""])
    for name, passed in payload["decision"]["checks"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} `{name}`")
    return "\n".join(lines)


def run(start: str, end: str) -> dict:
    dates, lookup, targets, cap_targets, equal_targets, metadata = build_inputs(start, end)
    cap_nav = simulate_index(dates, lookup, cap_targets)
    equal_nav = simulate_index(dates, lookup, equal_targets)
    cap_returns = _returns(cap_nav, INITIAL_NAV)
    equal_returns = _returns(equal_nav, INITIAL_NAV)
    configs = {
        "balanced_30": BasketConfig(name="balanced_30", target_count=30),
        "naive_30": BasketConfig(name="naive_30", target_count=30),
        "balanced_50": BasketConfig(name="balanced_50", target_count=50),
    }
    variants = {}
    for name, config in configs.items():
        net = simulate_basket(dates, lookup, targets[name], config)
        gross = simulate_basket(
            dates,
            lookup,
            targets[name],
            replace(config, buy_cost=0.0, sell_cost=0.0),
        )
        variants[name] = summarize_basket(net, gross, cap_returns, config)
    decision = decide(variants["balanced_30"])
    return _clean(
        {
            "study": "a-share-largecap-lowvol-v1",
            "data": metadata,
            "rules": {
                "universe": "top300 float market cap within top-half ADV",
                "signal": "252-session realized volatility",
                "rebalance": "every 63 sessions, next open",
                "main": "30 names, max 4 per SW L1 industry",
            },
            "variants": variants,
            "benchmarks": {
                "top300_cap": _metrics(cap_returns),
                "top300_equal": _metrics(equal_returns),
            },
            "decision": decision,
            "limitations": [
                "historical ST authority is unavailable",
                "stock adjustment is reconstructed from stored percentage changes",
                "unchanged holdings are not forced back to equal weight between quarterly reviews",
                "the interval is not virgin OOS",
            ],
        }
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2018-01-01")
    parser.add_argument("--end", default="2026-08-25")
    parser.add_argument("--out-json", default="overall/a-share-largecap-lowvol.json")
    parser.add_argument("--out-md", default="overall/a-share-largecap-lowvol.md")
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
