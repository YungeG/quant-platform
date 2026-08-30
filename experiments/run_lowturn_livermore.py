"""Run the frozen low-turnover selection plus Livermore management study."""

from __future__ import annotations

import argparse
import gc
import json
import math
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

QUANT_REPO = Path("/home/ygguo/agent-projs/quant-claude")
if str(QUANT_REPO) not in sys.path:
    sys.path.insert(0, str(QUANT_REPO))

import numpy as np
import pandas as pd

from experiments.lowturn_livermore import Bar, Candidate, StrategyConfig, simulate
from factormine.config import Config
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel
from factormine.preprocess.pipeline import preprocess_factor
from factormine.research.combination import repair_point_in_time_size


FOLDS = (
    ("2016-2019", "2016-01-01", "2019-12-31"),
    ("2020-2022", "2020-01-01", "2022-12-31"),
    ("2023-2026", "2023-01-01", "2026-12-31"),
)


def _turnover_factor(panel: pd.DataFrame) -> pd.Series:
    ordered = panel.sort_values(["Symbol", "TradingDay"])
    daily = ordered["Amount"] / ordered["CircMV"].where(ordered["CircMV"] > 0)
    values = daily.groupby(ordered["Symbol"], sort=False).transform(
        lambda series: series.rolling(20, min_periods=20).mean()
    )
    index = pd.MultiIndex.from_arrays(
        [ordered["TradingDay"], ordered["Symbol"]], names=["TradingDay", "Symbol"]
    )
    return pd.Series(values.to_numpy(), index=index, name="turnover20")


def build_inputs(start: str, end: str) -> tuple:
    cfg = Config()
    connection = connect(cfg, read_only=True)
    try:
        built = load_or_build_panel(cfg, start, end, con=connection)
    finally:
        connection.close()
    panel = repair_point_in_time_size(built.df)
    panel["TradingDay"] = pd.to_datetime(panel["TradingDay"])
    factor = _turnover_factor(panel)
    panel = panel.merge(
        factor.rename("_factor"),
        left_on=["TradingDay", "Symbol"],
        right_index=True,
        how="left",
        validate="one_to_one",
    )
    ordered = panel.sort_values(["Symbol", "TradingDay"])
    panel.loc[ordered.index, "_daily_return"] = ordered.groupby("Symbol", sort=False)[
        "adj_close"
    ].pct_change(fill_method=None)
    panel.loc[ordered.index, "_prior20_high"] = ordered.groupby("Symbol", sort=False)[
        "adj_close"
    ].transform(lambda series: series.shift(1).rolling(20, min_periods=20).max())
    panel.loc[ordered.index, "_ma60"] = ordered.groupby("Symbol", sort=False)[
        "adj_close"
    ].transform(lambda series: series.rolling(60, min_periods=60).mean())

    size_pct = panel.groupby("TradingDay")["log_size"].rank(pct=True, method="first")
    adv_pct = panel.groupby("TradingDay")["adv20"].rank(pct=True, method="first")
    panel["practical"] = (
        (~panel["suspended"].fillna(True))
        & (panel["age"] >= 252)
        & (panel["Close"] >= 5.0)
        & (panel["Volume"] > 0)
        & panel["_factor"].notna()
        & panel["log_size"].notna()
        & (size_pct > 0.50)
        & (adv_pct > 0.50)
    )
    original_selectable = panel["selectable"].copy()
    panel["selectable"] = panel["practical"]
    panel["_score"] = -preprocess_factor(panel, "_factor").reindex(panel.index)
    panel["selectable"] = original_selectable
    panel["_benchmark_eligible"] = (
        panel.sort_values(["Symbol", "TradingDay"])
        .groupby("Symbol", sort=False)["practical"]
        .shift(1)
        .reindex(panel.index)
        .fillna(False)
        .astype(bool)
    )
    benchmark = (
        panel[panel["_benchmark_eligible"]]
        .groupby("TradingDay")["_daily_return"]
        .mean()
        .fillna(0.0)
    )

    sessions = sorted(panel["TradingDay"].drop_duplicates())
    decision_dates = set(sessions[::5])
    candidates: dict[str, list[Candidate]] = {}
    candidate_symbols: set[str] = set()
    decisions = panel[panel["TradingDay"].isin(decision_dates) & panel["practical"]].copy()
    for day, group in decisions.groupby("TradingDay"):
        ranked = group.dropna(subset=["_score"]).sort_values(
            ["_score", "Symbol"], ascending=[False, True]
        ).head(20)
        confirmed = ranked[
            (ranked["adj_close"] > ranked["_prior20_high"])
            & (ranked["adj_close"] > ranked["_ma60"])
        ]
        rows = [
            Candidate(symbol=str(symbol), score=float(score))
            for symbol, score in zip(confirmed["Symbol"], confirmed["_score"], strict=True)
        ]
        if rows:
            key = pd.Timestamp(day).date().isoformat()
            candidates[key] = rows
            candidate_symbols.update(candidate.symbol for candidate in rows)

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
    market = panel[panel["Symbol"].isin(candidate_symbols)][columns].copy()
    market = market.set_index(["TradingDay", "Symbol"]).sort_index()
    dates = [pd.Timestamp(day).date().isoformat() for day in sessions]
    benchmark_map = {
        pd.Timestamp(day).date().isoformat(): float(value)
        for day, value in benchmark.items()
        if np.isfinite(value)
    }
    metadata = {
        "panel_version": built.version_hash,
        "rows": int(len(panel)),
        "start": dates[0],
        "end": dates[-1],
        "candidate_signal_days": len(candidates),
        "candidate_symbols": len(candidate_symbols),
        "average_candidates_per_signal_day": (
            float(np.mean([len(rows) for rows in candidates.values()])) if candidates else 0.0
        ),
    }
    del panel, ordered, decisions, factor
    gc.collect()

    def lookup(date: str, symbol: str) -> Bar | None:
        key = (pd.Timestamp(date), symbol)
        try:
            row = market.loc[key]
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

    return dates, lookup, candidates, benchmark_map, metadata


def _returns(nav: pd.Series, initial_nav: float) -> pd.Series:
    out = nav.pct_change()
    if len(out):
        out.iloc[0] = nav.iloc[0] / initial_nav - 1.0
    return out.fillna(0.0)


def _metrics(returns: pd.Series) -> dict:
    clean = returns.dropna().astype(float)
    if clean.empty:
        return {
            "cagr": 0.0,
            "volatility": 0.0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "calmar": 0.0,
        }
    wealth = (1.0 + clean).cumprod()
    years = len(clean) / 252.0
    cagr = float(wealth.iloc[-1] ** (1.0 / years) - 1.0) if years > 0 else 0.0
    volatility = float(clean.std(ddof=1) * math.sqrt(252.0))
    sharpe = float(clean.mean() / clean.std(ddof=1) * math.sqrt(252.0)) if clean.std(ddof=1) > 0 else 0.0
    max_drawdown = float((wealth / wealth.cummax() - 1.0).min())
    calmar = cagr / abs(max_drawdown) if max_drawdown < 0 else 0.0
    return {
        "cagr": cagr,
        "volatility": volatility,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "calmar": calmar,
    }


def summarize(result, gross_result, config: StrategyConfig) -> dict:
    index = pd.to_datetime(result.dates)
    nav = pd.Series(result.nav, index=index, dtype=float)
    gross_nav = pd.Series(gross_result.nav, index=index, dtype=float)
    returns = _returns(nav, config.initial_nav)
    gross_returns = _returns(gross_nav, config.initial_nav)
    benchmark_returns = pd.Series(result.benchmark_returns, index=index, dtype=float)
    metrics = _metrics(returns)
    gross_metrics = _metrics(gross_returns)
    benchmark_metrics = _metrics(benchmark_returns)
    fold_metrics = {}
    positive_folds = 0
    positive_excess_folds = 0
    for name, start, end in FOLDS:
        fold = _metrics(returns.loc[start:end])
        fold_benchmark = _metrics(benchmark_returns.loc[start:end])
        fold["benchmark_cagr"] = fold_benchmark["cagr"]
        fold["excess_cagr"] = fold["cagr"] - fold_benchmark["cagr"]
        if fold["cagr"] > 0:
            positive_folds += 1
        if fold["excess_cagr"] > 0:
            positive_excess_folds += 1
        fold_metrics[name] = fold
    yearly = {
        str(year): float((1.0 + group).prod() - 1.0)
        for year, group in returns.groupby(returns.index.year)
    }
    reasons = Counter(trade["reason"] for trade in result.trades)
    buys = [trade for trade in result.trades if trade["side"] == "BUY"]
    sells = [trade for trade in result.trades if trade["side"] == "SELL"]
    sell_returns = [float(trade["return_from_average_cost"]) for trade in sells]
    entry_symbols = Counter(trade["symbol"] for trade in buys if trade["reason"] == "entry")
    best_year = max(yearly, key=yearly.get) if yearly else None
    remaining_years = [value for year, value in yearly.items() if year != best_year]
    cagr_without_best_year = (
        float(np.prod([1.0 + value for value in remaining_years]) ** (1.0 / len(remaining_years)) - 1.0)
        if remaining_years
        else 0.0
    )
    buy_attempts = len(buys) + result.blocked_buys + result.gap_skips
    fees = float(sum(trade["fee"] for trade in result.trades))
    holding_days = [trade["holding_days"] for trade in sells]
    retention = metrics["cagr"] / gross_metrics["cagr"] if gross_metrics["cagr"] > 0 else 0.0
    return {
        "metrics": metrics,
        "gross_metrics": gross_metrics,
        "benchmark_metrics": benchmark_metrics,
        "excess_cagr": metrics["cagr"] - benchmark_metrics["cagr"],
        "gross_to_net_cagr_retention": retention,
        "positive_folds": positive_folds,
        "positive_excess_folds": positive_excess_folds,
        "folds": fold_metrics,
        "yearly_returns": yearly,
        "positive_years": sum(value > 0 for value in yearly.values()),
        "total_years": len(yearly),
        "best_year": best_year,
        "best_year_return": yearly.get(best_year, 0.0) if best_year else 0.0,
        "cagr_excluding_best_year": cagr_without_best_year,
        "average_exposure": float(np.mean(result.gross_exposure)),
        "maximum_exposure": float(np.max(result.gross_exposure)),
        "cash_fraction": 1.0 - float(np.mean(result.gross_exposure)),
        "trade_count": len(result.trades),
        "buy_count": len(buys),
        "sell_count": len(sells),
        "entry_count": reasons["entry"],
        "add_count": reasons["add"],
        "hard_stop_count": reasons["hard_stop"],
        "trailing_stop_count": reasons["trailing_stop"],
        "fixed_hold_count": reasons["fixed_hold"],
        "blocked_buys": result.blocked_buys,
        "blocked_sells": result.blocked_sells,
        "expired_buys": result.expired_buys,
        "gap_skips": result.gap_skips,
        "blocked_buy_rate": (
            (result.blocked_buys + result.gap_skips) / buy_attempts if buy_attempts else 0.0
        ),
        "missing_valuation_rate": (
            result.missing_valuation_days / result.position_days if result.position_days else 0.0
        ),
        "fees": fees,
        "trade_win_rate": float(np.mean([value > 0 for value in sell_returns])) if sell_returns else 0.0,
        "average_closed_trade_return": float(np.mean(sell_returns)) if sell_returns else 0.0,
        "median_closed_trade_return": float(np.median(sell_returns)) if sell_returns else 0.0,
        "top_entry_symbols": entry_symbols.most_common(5),
        "average_holding_days": float(np.mean(holding_days)) if holding_days else 0.0,
        "median_holding_days": float(np.median(holding_days)) if holding_days else 0.0,
        "final_positions": len(result.final_positions),
    }


def decide(full: dict, no_pyramid: dict, fixed: dict) -> dict:
    full_metrics = full["metrics"]
    no_metrics = no_pyramid["metrics"]
    fixed_metrics = fixed["metrics"]
    fixed_increment = (
        full_metrics["sharpe"] >= fixed_metrics["sharpe"] + 0.10
        or (
            abs(full_metrics["max_drawdown"]) <= abs(fixed_metrics["max_drawdown"]) * 0.80
            and full_metrics["cagr"] >= fixed_metrics["cagr"] - 0.03
        )
    )
    pyramid_increment = (
        (full_metrics["cagr"] > no_metrics["cagr"] or full_metrics["sharpe"] > no_metrics["sharpe"])
        and full_metrics["max_drawdown"] >= no_metrics["max_drawdown"] - 0.05
    )
    checks = {
        "positive_and_sharpe": full_metrics["cagr"] > 0 and full_metrics["sharpe"] >= 0.60,
        "drawdown_20pct_improvement": full_metrics["max_drawdown"] >= -0.392,
        "positive_folds": full["positive_folds"] >= 2,
        "beats_fixed_management": fixed_increment,
        "pyramiding_increment": pyramid_increment,
        "cost_retention": full["gross_to_net_cagr_retention"] >= 0.70,
        "execution_coverage": full["blocked_buy_rate"] <= 0.10 and full["missing_valuation_rate"] <= 0.02,
    }
    if all(checks.values()):
        verdict = "GO"
    elif (
        full_metrics["cagr"] > 0
        and full_metrics["sharpe"] > 0
        and full_metrics["max_drawdown"] >= -0.440
    ):
        verdict = "MARGINAL"
    else:
        verdict = "NO-GO"
    return {"verdict": verdict, "checks": checks}


def render_markdown(payload: dict) -> str:
    lines = [
        "# 低换手 × Livermore 回测结果",
        "",
        f"- verdict: **{payload['decision']['verdict']}**",
        f"- data: {payload['data']['start']}—{payload['data']['end']}",
        f"- candidate signal days: {payload['data']['candidate_signal_days']}",
        "",
        "| Variant | CAGR | Sharpe | Max drawdown | Excess CAGR | Avg exposure | Trades |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key in ("livermore", "no_pyramid", "fixed_20", "benchmark"):
        row = payload["variants"][key]
        metrics = row["metrics"]
        lines.append(
            f"| {key} | {metrics['cagr']:.2%} | {metrics['sharpe']:.3f} | "
            f"{metrics['max_drawdown']:.2%} | {row.get('excess_cagr', 0.0):.2%} | "
            f"{row.get('average_exposure', 1.0):.2%} | {row.get('trade_count', 0)} |"
        )
    lines.extend(["", "## Gate", ""])
    for name, passed in payload["decision"]["checks"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} `{name}`")
    return "\n".join(lines)


def _clean(value):
    if isinstance(value, dict):
        return {key: _clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def run(start: str, end: str) -> dict:
    dates, lookup, candidates, benchmark, metadata = build_inputs(start, end)
    configs = {
        "livermore": StrategyConfig(name="livermore"),
        "no_pyramid": StrategyConfig(
            name="no_pyramid", initial_fraction=0.25, pyramid=False, max_units=1
        ),
        "fixed_20": StrategyConfig(
            name="fixed_20",
            initial_fraction=0.25,
            pyramid=False,
            max_units=1,
            stop_enabled=False,
            fixed_hold_days=20,
        ),
    }
    variants = {}
    for name, config in configs.items():
        net = simulate(dates, lookup, candidates, benchmark, config)
        gross = simulate(
            dates,
            lookup,
            candidates,
            benchmark,
            replace(config, buy_cost=0.0, sell_cost=0.0),
        )
        variants[name] = summarize(net, gross, config)
    benchmark_returns = pd.Series(
        [benchmark.get(date, 0.0) for date in dates], index=pd.to_datetime(dates), dtype=float
    )
    variants["benchmark"] = {
        "metrics": _metrics(benchmark_returns),
        "excess_cagr": 0.0,
        "average_exposure": 1.0,
        "trade_count": 0,
    }
    decision = decide(variants["livermore"], variants["no_pyramid"], variants["fixed_20"])
    prior_path = Path("overall/a-share-low-turnover-replication.json")
    prior = json.loads(prior_path.read_text(encoding="utf-8")) if prior_path.exists() else None
    return _clean(
        {
            "study": "a-share-lowturn-livermore-v1",
            "data": metadata,
            "rules": {
                "selection": "low-turnover top20 then prior-20d-high breakout and above MA60",
                "max_positions": 4,
                "units": 3,
                "add_thresholds": [0.05, 0.10],
                "hard_stop": 0.08,
                "trailing_stop": 0.12,
                "buy_cost": 0.0013,
                "sell_cost": 0.0018,
            },
            "variants": variants,
            "decision": decision,
            "prior_lowturn_top20": prior,
            "limitations": [
                "historical ST name/status authority is unavailable",
                "PctChange-reconstructed adjusted prices replace a formal corporate-action event stream",
                "adjusted-unit accounting models total-return continuity; raw-share corporate-action lots are diagnostic only",
                "the historical interval was used by prior related research and is not virgin OOS",
            ],
        }
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2016-01-01")
    parser.add_argument("--end", default="2026-08-25")
    parser.add_argument("--out-json", default="overall/a-share-lowturn-livermore.json")
    parser.add_argument("--out-md", default="overall/a-share-lowturn-livermore.md")
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
