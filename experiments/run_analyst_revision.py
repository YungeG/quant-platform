"""Backtest a monthly A-share analyst EPS revision strategy."""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from experiments.context_features import eps_revision_to_price
from experiments.quarterly_portfolio import Bar, BasketConfig, simulate_basket
from experiments.run_largecap_lowvol import summarize_basket
from experiments.run_lowturn_livermore import _clean
from factormine.config import Config
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel
from factormine.research.combination import repair_point_in_time_size


FOLDS = (
    ("2017-2019", "2017-01-01", "2019-12-31"),
    ("2020-2022", "2020-01-01", "2022-12-31"),
    ("2023-2026", "2023-01-01", "2026-12-31"),
)


def load_reports(raw_dir: str) -> pd.DataFrame:
    connection = duckdb.connect()
    try:
        reports = connection.execute(
            """
            select ts_code, report_date, org_name, quarter, eps, create_time
            from read_csv_auto(?, union_by_name=true, header=true)
            where eps is not null and regexp_matches(cast(quarter as varchar), '^[0-9]{4}Q4$')
            """,
            [str(Path(raw_dir) / "report_rc_*.csv")],
        ).df()
    finally:
        connection.close()
    reports["Symbol"] = reports["ts_code"].astype(str).str[:6]
    reports["report_date"] = pd.to_datetime(reports["report_date"].astype(str))
    reports["quarter_year"] = reports["quarter"].astype(str).str[:4].astype(int)
    reports = reports.dropna(subset=["org_name", "eps"]).drop_duplicates(
        ["Symbol", "report_date", "org_name", "quarter", "eps", "create_time"],
        keep="last",
    )
    return reports.sort_values(["report_date", "Symbol", "quarter", "org_name"])


def month_ends(sessions: list[pd.Timestamp]) -> list[pd.Timestamp]:
    series = pd.Series(sessions)
    return series.groupby(series.dt.to_period("M")).max().tolist()


def consensus_revisions(reports: pd.DataFrame, day: pd.Timestamp) -> pd.DataFrame:
    current_start = day - pd.Timedelta(days=180)
    prior_cutoff = day - pd.Timedelta(days=60)
    prior_start = prior_cutoff - pd.Timedelta(days=180)
    window = reports[
        reports["report_date"].between(prior_start, day)
        & (reports["quarter_year"] >= day.year)
    ].copy()
    if window.empty:
        return pd.DataFrame(columns=["Symbol", "quarter", "revision", "current_count", "prior_count"])

    def latest(start: pd.Timestamp, cutoff: pd.Timestamp, prefix: str) -> pd.DataFrame:
        selected = window[window["report_date"].between(start, cutoff)].sort_values(
            ["Symbol", "quarter", "org_name", "report_date", "create_time"]
        )
        return selected.drop_duplicates(
            ["Symbol", "quarter", "org_name"], keep="last"
        )[["Symbol", "quarter", "org_name", "eps"]].rename(
            columns={"eps": f"{prefix}_org_eps"}
        )

    current_latest = latest(current_start, day, "current")
    prior_latest = latest(prior_start, prior_cutoff, "prior")
    current = (
        current_latest.groupby(["Symbol", "quarter"])["current_org_eps"]
        .agg([("current_count", "count"), ("current_eps", "median")])
        .reset_index()
    )
    prior = (
        prior_latest.groupby(["Symbol", "quarter"])["prior_org_eps"]
        .agg([("prior_count", "count"), ("prior_eps", "median")])
        .reset_index()
    )
    paired = current_latest.merge(
        prior_latest, on=["Symbol", "quarter", "org_name"], how="inner"
    )
    paired["direction"] = np.sign(
        paired["current_org_eps"] - paired["prior_org_eps"]
    )
    breadth = (
        paired.groupby(["Symbol", "quarter"])["direction"]
        .agg([("paired_count", "count"), ("breadth", "mean")])
        .reset_index()
    )
    merged = current.merge(prior, on=["Symbol", "quarter"], how="inner").merge(
        breadth, on=["Symbol", "quarter"], how="left"
    )
    merged = merged[
        (merged["current_count"] >= 3)
        & (merged["prior_count"] >= 3)
    ].copy()
    merged.loc[merged["paired_count"].fillna(0) < 3, "breadth"] = np.nan
    if merged.empty:
        return pd.DataFrame(
            columns=["Symbol", "quarter", "revision", "breadth", "paired_count", "current_count", "prior_count"]
        )
    merged["revision"] = np.where(
        merged["prior_eps"] != 0,
        merged["current_eps"] / merged["prior_eps"] - 1.0,
        np.nan,
    )
    merged["quarter_year"] = merged["quarter"].astype(str).str[:4].astype(int)
    return merged.sort_values(["Symbol", "quarter_year"]).drop_duplicates("Symbol", keep="first")


def build_inputs(start: str, end: str, reports: pd.DataFrame, factor: str) -> tuple:
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
    panel["_fwd20"] = grouped["adj_open"].shift(-21) / grouped["adj_open"].shift(-1) - 1.0
    adv_pct = panel.groupby("TradingDay")["adv20"].rank(pct=True, method="first")
    panel["practical"] = (
        (~panel["is_st"].fillna(True))
        & (~panel["suspended"].fillna(True))
        & (panel["age"] >= 252)
        & (panel["Close"] >= 5.0)
        & (panel["Volume"] > 0)
        & panel["CircMV"].notna()
        & (adv_pct > 0.50)
    )
    sessions = sorted(panel.loc[panel["TradingDay"] >= pd.Timestamp(start), "TradingDay"].drop_duplicates())
    decisions = month_ends(sessions)
    targets: dict[str, list[str]] = {}
    signal_rows = []
    all_symbols: set[str] = set()
    for day in decisions:
        universe = panel[(panel["TradingDay"] == day) & panel["practical"]].nlargest(500, "CircMV")
        if len(universe) < 300:
            continue
        revision = consensus_revisions(reports, day)
        candidates = universe.merge(revision, on="Symbol", how="inner")
        if factor == "revision_to_price":
            candidates["revision_to_price"] = [
                eps_revision_to_price(current, prior, price)
                for current, prior, price in zip(
                    candidates["current_eps"], candidates["prior_eps"], candidates["Close"], strict=True
                )
            ]
        benchmark = float(universe["_fwd20"].mean())
        candidates["active20"] = candidates["_fwd20"] - benchmark
        for row in candidates.itertuples(index=False):
            signal_rows.append(
                {
                    "signal_date": day,
                    "symbol": row.Symbol,
                    "quarter": row.quarter,
                    "signal_value": getattr(row, factor),
                    "revision": row.revision,
                    "revision_to_price": getattr(row, "revision_to_price", np.nan),
                    "current_eps": row.current_eps,
                    "prior_eps": row.prior_eps,
                    "breadth": row.breadth,
                    "paired_count": row.paired_count,
                    "current_count": row.current_count,
                    "prior_count": row.prior_count,
                    "active20": row.active20,
                }
            )
        selected = candidates[candidates[factor] > 0].sort_values(
            [factor, "paired_count", "Symbol"], ascending=[False, False, True]
        ).head(30)
        key = day.date().isoformat()
        targets[key] = selected["Symbol"].astype(str).tolist()
        all_symbols.update(targets[key])

    columns = [
        "TradingDay", "Symbol", "adj_open", "adj_close", "Open", "High", "Low", "Close", "Volume", "PctChange"
    ]
    market = panel[
        panel["Symbol"].isin(all_symbols) & panel["TradingDay"].isin(sessions)
    ][columns].set_index(["TradingDay", "Symbol"]).sort_index()
    dates = [day.date().isoformat() for day in sessions]

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

    metadata = {
        "panel_version": built.version_hash,
        "report_rows": len(reports),
        "decision_count": len(targets),
        "selected_symbols": len(all_symbols),
    }
    del panel
    gc.collect()
    return dates, lookup, targets, pd.DataFrame(signal_rows), metadata


def ic_summary(signals: pd.DataFrame) -> dict:
    monthly = []
    for day, group in signals.dropna(subset=["revision", "active20"]).groupby("signal_date"):
        if len(group) < 10 or group["signal_value"].nunique() < 2:
            continue
        monthly.append({"signal_date": day, "ic": float(spearmanr(group["signal_value"], group["active20"]).statistic), "count": len(group)})
    frame = pd.DataFrame(monthly)
    if frame.empty:
        return {"count": 0, "mean": 0.0, "median": 0.0, "win_rate": 0.0, "t_stat": 0.0, "folds": {}}
    mean = float(frame["ic"].mean())
    std = float(frame["ic"].std(ddof=1))
    folds = {}
    for name, start, end in FOLDS:
        fold = frame[frame["signal_date"].between(start, end)]
        folds[name] = {"count": len(fold), "mean_ic": float(fold["ic"].mean()) if len(fold) else 0.0}
    return {
        "count": len(frame),
        "mean": mean,
        "median": float(frame["ic"].median()),
        "win_rate": float((frame["ic"] > 0).mean()),
        "t_stat": mean / (std / np.sqrt(len(frame))) if std > 0 else 0.0,
        "average_coverage": float(frame["count"].mean()),
        "folds": folds,
    }


def benchmark_returns(path: str, dates: list[str]) -> pd.Series:
    data = pd.read_csv(path, parse_dates=["trade_date"])
    equity = data[data["asset"] == "equity"].drop_duplicates("trade_date").set_index("trade_date")["adj_close"].sort_index()
    index = pd.to_datetime(dates)
    return equity.reindex(index).ffill().pct_change(fill_method=None).fillna(0.0)


def decide(ic: dict, portfolio: dict) -> dict:
    signal_checks = {
        "mean_ic": ic["mean"] >= 0.02,
        "t_stat": ic["t_stat"] >= 2.0,
        "positive_folds": sum(fold["mean_ic"] > 0 for fold in ic["folds"].values()) >= 2,
    }
    portfolio_checks = {
        "cagr": portfolio["metrics"]["cagr"] >= 0.10,
        "excess": portfolio["excess_cagr"] >= 0.02,
        "sharpe": portfolio["metrics"]["sharpe"] >= 0.80,
        "drawdown": portfolio["metrics"]["max_drawdown"] >= -0.30,
        "folds": portfolio["positive_excess_folds"] == 3,
        "turnover": portfolio["annual_turnover"] <= 10.0,
        "lots": portfolio["lot_failures"] == 0,
        "cost_retention": portfolio["gross_to_net_cagr_retention"] >= 0.90,
    }
    if all(signal_checks.values()) and all(portfolio_checks.values()):
        verdict = "GO"
    elif ic["mean"] > 0 and portfolio["excess_cagr"] > 0:
        verdict = "MARGINAL"
    else:
        verdict = "NO-GO"
    return {"verdict": verdict, "signal_checks": signal_checks, "portfolio_checks": portfolio_checks}


def json_clean(value):
    if isinstance(value, dict):
        return {key: json_clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_clean(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    return _clean(value)


def render_markdown(payload: dict) -> str:
    ic = payload["ic"]
    p = payload["portfolio"]
    return "\n".join(
        [
            "# A股分析师一致预期修正结果", "",
            f"- verdict: **{payload['decision']['verdict']}**", "",
            f"- mean IC: {ic['mean']:.4f}; t-stat: {ic['t_stat']:.2f}; months: {ic['count']}",
            f"- CAGR: {p['metrics']['cagr']:.2%}; benchmark: {p['benchmark_metrics']['cagr']:.2%}",
            f"- Sharpe: {p['metrics']['sharpe']:.3f}; max drawdown: {p['metrics']['max_drawdown']:.2%}",
        ]
    )


def run(
    raw_dir: str,
    start: str,
    end: str,
    benchmark_path: str,
    signals_path: str,
    factor: str,
    nav_path: str | None = None,
) -> dict:
    reports = load_reports(raw_dir)
    dates, lookup, targets, signals, metadata = build_inputs(start, end, reports, factor)
    signals.to_csv(signals_path, index=False, date_format="%Y-%m-%d")
    config = BasketConfig(name="analyst_revision_top30", target_count=30, initial_nav=400_000.0, buy_cost=0.00155, sell_cost=0.00155)
    gross_config = BasketConfig(name="analyst_revision_top30_gross", target_count=30, initial_nav=400_000.0, buy_cost=0.0, sell_cost=0.0)
    result = simulate_basket(dates, lookup, targets, config)
    gross = simulate_basket(dates, lookup, targets, gross_config)
    benchmark = benchmark_returns(benchmark_path, dates)
    portfolio = summarize_basket(result, gross, benchmark, config, folds=FOLDS)
    if nav_path:
        pd.DataFrame(
            {
                "date": result.dates,
                "nav": result.nav,
                "gross_nav": gross.nav,
                "benchmark_return": benchmark.to_numpy(),
            }
        ).to_csv(nav_path, index=False)
    ic = ic_summary(signals)
    decision = decide(ic, portfolio)
    return json_clean(
        {
            "study": f"a-share-analyst-{factor}-v1",
            "data": {**metadata, "factor": factor},
            "ic": ic,
            "portfolio": portfolio,
            "decision": decision,
            "signals": signals_path,
            "nav": nav_path,
            "limitations": [
                "report_rc is source-bounded and lacks provider revision/completeness authority",
                "report_date has day-level timing and execution is delayed to the next open",
                "the interval is not virgin OOS",
            ],
        }
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", default="overall/a-share-report-rc-raw")
    parser.add_argument("--start", default="2017-01-03")
    parser.add_argument("--end", default="2026-08-26")
    parser.add_argument("--benchmark", default="overall/a-share-multi-asset-etf-daily.csv")
    parser.add_argument("--signals", default="overall/a-share-analyst-revision-signals.csv")
    parser.add_argument("--factor", choices=["revision", "breadth", "revision_to_price"], default="revision")
    parser.add_argument("--nav")
    parser.add_argument("--out-json", default="overall/a-share-analyst-revision.json")
    parser.add_argument("--out-md", default="overall/a-share-analyst-revision.md")
    args = parser.parse_args(argv)
    payload = run(
        args.raw_dir,
        args.start,
        args.end,
        args.benchmark,
        args.signals,
        args.factor,
        args.nav,
    )
    Path(args.out_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = render_markdown(payload)
    Path(args.out_md).write_text(markdown + "\n", encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
