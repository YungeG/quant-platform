"""Frozen actual-quarterly SUE stock/cash study; no analyst inputs."""
from __future__ import annotations

import argparse
import gc
import json
import sys
from pathlib import Path

QUANT_REPO = Path("/home/ygguo/agent-projs/quant-claude")
if str(QUANT_REPO) not in sys.path:
    sys.path.insert(0, str(QUANT_REPO))

import numpy as np
import pandas as pd

from experiments.lowturn_livermore import Bar
from experiments.quarterly_portfolio import BasketConfig, simulate_basket
from experiments.run_largecap_lowvol import summarize_basket
from experiments.run_lowturn_livermore import _clean, _metrics
from factormine.config import Config
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel
from factormine.research.combination import repair_point_in_time_size

FOLDS = (("discovery", "2017-01-01", "2021-12-31"), ("validation", "2022-01-01", "2024-12-31"), ("holdout", "2025-01-01", "2025-12-31"))
TOP_SIZE, TARGET_COUNT, SIGNAL_DAYS, HISTORY, MIN_HISTORY = 500, 20, 120, 8, 6


def quarterly_sue(income: pd.DataFrame) -> pd.DataFrame:
    """Use first-announced cumulative income records to derive PIT single quarters."""
    frame = income.copy()
    frame["ann_date"] = pd.to_datetime(frame["ann_date"].astype(str), format="%Y%m%d", errors="coerce")
    frame["end_date"] = pd.to_datetime(frame["end_date"].astype(str), format="%Y%m%d", errors="coerce")
    frame["profit"] = pd.to_numeric(frame["n_income_attr_p"], errors="coerce")
    frame["update_flag"] = pd.to_numeric(frame.get("update_flag", 0), errors="coerce").fillna(0)
    frame = frame.dropna(subset=["ann_date", "end_date", "profit"]).copy()
    frame["Symbol"] = frame["ts_code"].astype(str).str[:6]
    frame["quarter"] = frame["end_date"].dt.quarter
    frame = frame[frame["quarter"].isin([1, 2, 3, 4])]
    first = frame.groupby(["Symbol", "end_date"])["ann_date"].transform("min")
    frame = frame[frame["ann_date"] == first].sort_values(["Symbol", "end_date", "update_flag"])
    frame = frame.drop_duplicates(["Symbol", "end_date"], keep="last")
    frame = frame.sort_values(["Symbol", "end_date"]).reset_index(drop=True)
    prior_cumulative = frame.groupby("Symbol", sort=False)["profit"].shift(1)
    prior_quarter = frame.groupby("Symbol", sort=False)["quarter"].shift(1)
    frame["single_profit"] = np.where(frame["quarter"] == 1, frame["profit"], np.where(prior_quarter == frame["quarter"] - 1, frame["profit"] - prior_cumulative, np.nan))
    frame["seasonal_change"] = frame["single_profit"] - frame.groupby("Symbol", sort=False)["single_profit"].shift(4)
    history = frame.groupby("Symbol", sort=False)["seasonal_change"]
    frame["prior_count"] = history.transform(lambda s: s.shift(1).rolling(HISTORY, min_periods=MIN_HISTORY).count())
    frame["prior_std"] = history.transform(lambda s: s.shift(1).rolling(HISTORY, min_periods=MIN_HISTORY).std(ddof=1))
    frame["sue"] = frame["seasonal_change"] / frame["prior_std"]
    return frame.loc[(frame["prior_count"] >= MIN_HISTORY) & (frame["prior_std"] > 0), ["Symbol", "end_date", "ann_date", "single_profit", "seasonal_change", "prior_count", "prior_std", "sue"]].sort_values(["ann_date", "Symbol"])


def build_inputs(start: str, end: str, income_path: str) -> tuple:
    sue = quarterly_sue(pd.read_csv(income_path, dtype={"ts_code": str, "ann_date": str, "end_date": str}))
    cfg = Config(); connection = connect(cfg, read_only=True)
    try:
        built = load_or_build_panel(cfg, "2014-01-01", end, con=connection)
    finally:
        connection.close()
    panel = repair_point_in_time_size(built.df)
    panel["TradingDay"] = pd.to_datetime(panel["TradingDay"])
    panel = panel.sort_values(["TradingDay", "Symbol"]).reset_index(drop=True)
    adv_rank = panel.groupby("TradingDay")["adv20"].rank(pct=True, method="first")
    panel["practical"] = (~panel["is_st"].fillna(True) & ~panel["suspended"].fillna(True) & (panel["age"] >= 252) & (panel["Close"] >= 5) & (panel["Volume"] > 0) & panel["CircMV"].notna() & (adv_rank > .50))
    sessions = sorted(panel.loc[panel.TradingDay.between(start, end), "TradingDay"].unique())
    panel = panel[panel.TradingDay.isin(sessions)].copy()
    universe = panel[panel.practical].copy()
    universe["size_rank"] = universe.groupby("TradingDay")["CircMV"].rank(method="first", ascending=False)
    universe = universe[universe.size_rank <= TOP_SIZE]
    universe_sets = {day: set(group.Symbol.astype(str)) for day, group in universe.groupby("TradingDay")}
    panel = panel.sort_values(["Symbol", "TradingDay"])
    panel["_daily_return"] = panel.groupby("Symbol", sort=False)["adj_close"].pct_change(fill_method=None)
    benchmark_returns = universe.join(panel.set_index(["TradingDay", "Symbol"])["_daily_return"], on=["TradingDay", "Symbol"]).groupby("TradingDay")["_daily_return"].mean().reindex(sessions).fillna(0.0)
    events = sue[(sue.ann_date <= max(sessions)) & (sue.ann_date >= min(sessions) - pd.Timedelta(days=SIGNAL_DAYS))].copy()
    targets: dict[str, list[str]] = {}; event_rows = []
    for day in sessions:
        available = events[(events.ann_date <= day) & (events.ann_date > day - pd.Timedelta(days=SIGNAL_DAYS)) & (events.sue > 0)].sort_values(["Symbol", "ann_date", "end_date"]).drop_duplicates("Symbol", keep="last")
        allowed = universe_sets.get(day, set())
        selected = available[available.Symbol.isin(allowed)].nlargest(TARGET_COUNT, "sue")
        key = day.date().isoformat(); targets[key] = selected.Symbol.astype(str).tolist()
        if not selected.empty:
            event_rows.append(selected.assign(signal_day=day, target_rank=range(1, len(selected) + 1)))
    all_symbols = set(symbol for symbols in targets.values() for symbol in symbols)
    market = panel[panel.Symbol.isin(all_symbols)].set_index(["TradingDay", "Symbol"]).sort_index()
    dates = [day.date().isoformat() for day in sessions]
    def lookup(date: str, symbol: str) -> Bar | None:
        try: row = market.loc[(pd.Timestamp(date), symbol)]
        except KeyError: return None
        return Bar(float(row.adj_open), float(row.adj_close), float(row.Open), float(row.High), float(row.Low), float(row.Close), float(row.Volume), float(row.PctChange))
    ledger = pd.concat(event_rows, ignore_index=True) if event_rows else pd.DataFrame()
    metadata = {"panel_version": built.version_hash, "statement_sue_rows": len(sue), "target_days": len(targets), "start": dates[0], "end": dates[-1], "st_source": "DuckDB PIT is_st"}
    del panel, universe; gc.collect()
    return dates, lookup, targets, benchmark_returns, ledger, metadata


def decide(portfolio: dict) -> dict:
    folds = portfolio["folds"]
    checks = {"validation_excess_cagr": folds["validation"]["excess_cagr"] > 0, "validation_sharpe": folds["validation"]["sharpe"] >= folds["validation"]["benchmark_sharpe"], "validation_drawdown": folds["validation"]["max_drawdown"] >= -.50, "holdout_excess_cagr": folds["holdout"]["excess_cagr"] > 0, "holdout_sharpe": folds["holdout"]["sharpe"] >= folds["holdout"]["benchmark_sharpe"], "holdout_drawdown": folds["holdout"]["max_drawdown"] >= -.50, "cost_retention": portfolio["gross_to_net_cagr_retention"] >= .80, "positive_folds": portfolio["positive_excess_folds"] >= 2}
    return {"verdict": "GO" if all(checks.values()) else "NO-GO", "checks": checks}


def run(start: str, end: str, income: str, members_path: str, etf_path: str, ledger_path: str) -> dict:
    dates, lookup, targets, benchmark, ledger, metadata = build_inputs(start, end, income)
    members = pd.read_csv(members_path, dtype={"ts_code": str})
    member_symbols = set(members["ts_code"].astype(str).str[:6])
    etf = pd.read_csv(etf_path, dtype={"trade_date": str})
    etf["trade_date"] = pd.to_datetime(etf["trade_date"])
    etf["adj_close"] = pd.to_numeric(etf["adj_close"], errors="coerce")
    etf_returns = etf.set_index("trade_date")["adj_close"].sort_index().pct_change(fill_method=None).reindex(pd.to_datetime(dates)).fillna(0.0)
    metadata.update({"sw2021_member_rows": len(members), "signal_sw2021_coverage": float(ledger.Symbol.isin(member_symbols).mean()) if not ledger.empty else 0.0, "etf_rows": len(etf)})
    config = BasketConfig(name="quarterly_sue_top20", target_count=TARGET_COUNT, initial_nav=400_000, buy_cost=.0013, sell_cost=.0018)
    net = simulate_basket(dates, lookup, targets, config)
    gross = simulate_basket(dates, lookup, targets, BasketConfig(name="quarterly_sue_top20_gross", target_count=TARGET_COUNT, initial_nav=400_000, buy_cost=0, sell_cost=0))
    portfolio = summarize_basket(net, gross, benchmark, config, folds=FOLDS)
    for name, start_date, end_date in FOLDS:
        portfolio["folds"][name]["benchmark_sharpe"] = _metrics(benchmark.loc[start_date:end_date])["sharpe"]
    ledger.to_csv(ledger_path, index=False, date_format="%Y-%m-%d")
    return _clean({"study": "a-share-actual-quarterly-sue-v1", "data": metadata, "portfolio": portfolio, "etf_descriptive_metrics": _metrics(etf_returns), "decision": decide(portfolio), "limitations": ["Day-level ann_date requires conservative next-open execution.", "PIT ST is the corrected DuckDB is_st field; announcement timestamps are unavailable.", "ETF is descriptive; Top-500 equal-weight is the specified execution benchmark."], "ledger": ledger_path})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--income", default="/home/ygguo/agent-projs/ai-crypt/platform-a-share-research/overall/a-share-quarterly-statements-raw/income_vip.csv"); parser.add_argument("--members", default="/home/ygguo/agent-projs/ai-crypt/platform-a-share-research/overall/a-share-sw2021-members.csv"); parser.add_argument("--etf", default="/home/ygguo/agent-projs/ai-crypt/platform-a-share-research/overall/a-share-equity-etf-daily-current.csv"); parser.add_argument("--start", default="2017-01-03"); parser.add_argument("--end", default="2025-12-31"); parser.add_argument("--ledger", default="overall/a-share-quarterly-sue-signals.csv"); parser.add_argument("--out-json", default="overall/a-share-quarterly-sue-result.json"); parser.add_argument("--out-md", default="overall/a-share-quarterly-sue-result.md"); args = parser.parse_args(argv)
    payload = run(args.start, args.end, args.income, args.members, args.etf, args.ledger)
    Path(args.out_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    p = payload["portfolio"]["metrics"]; d = payload["decision"]
    text = f"# A股实际季度SUE结果\n\n- verdict: **{d['verdict']}**\n- CAGR / Sharpe / MDD: {p['cagr']:.2%} / {p['sharpe']:.3f} / {p['max_drawdown']:.2%}\n- benchmark CAGR: {payload['portfolio']['benchmark_metrics']['cagr']:.2%}\n- 2025 excess CAGR: {payload['portfolio']['folds']['holdout']['excess_cagr']:.2%}\n"
    Path(args.out_md).write_text(text, encoding="utf-8"); print(text); return 0

if __name__ == "__main__": raise SystemExit(main())
