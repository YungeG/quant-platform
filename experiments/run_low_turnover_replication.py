"""Independent practical replication of the A-share low-turnover factor."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

QUANT_REPO = Path("/home/ygguo/agent-projs/quant-claude")
if str(QUANT_REPO) not in sys.path:
    sys.path.insert(0, str(QUANT_REPO))

import numpy as np
import pandas as pd

from factormine.config import Config
from factormine.data.calendar import TradingCalendar
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel
from factormine.eval.returns import forward_return_columns
from factormine.factors.mined_price_volume_combo import compute_factor
from factormine.preprocess.pipeline import preprocess_factor
from factormine.research.combination import repair_point_in_time_size


ANCHOR = 5
TOP_N = 20
COST_PER_SIDE = 0.0012
SMALL_SIZE_EXCLUSION = 0.30
PLACEBO_SEEDS = tuple(range(20))
FOLDS = (
    ("2016-2019", "2016-01-01", "2019-12-31"),
    ("2020-2022", "2020-01-01", "2022-12-31"),
    ("2023-2026", "2023-01-01", "2026-12-31"),
)


def _prepare(panel: pd.DataFrame) -> pd.DataFrame:
    data = repair_point_in_time_size(panel)
    factor = compute_factor(data)
    data = data.merge(
        factor.rename("_factor"),
        left_on=["TradingDay", "Symbol"],
        right_index=True,
        how="left",
        validate="one_to_one",
    )
    size_pct = data.groupby("TradingDay")["log_size"].rank(pct=True, method="first")
    data["practical"] = (
        data["selectable"].fillna(False)
        & data["_factor"].notna()
        & data["log_size"].notna()
        & (size_pct > SMALL_SIZE_EXCLUSION)
    )
    neutral = data.copy()
    neutral["selectable"] = neutral["practical"]
    data["_score"] = -preprocess_factor(neutral, "_factor").reindex(data.index)
    return data


def _arm_records(data: pd.DataFrame, seed: int | None = None) -> pd.DataFrame:
    sessions = sorted(pd.to_datetime(data["TradingDay"].unique()))
    rebalance = set(sessions[::ANCHOR])
    rng = np.random.default_rng(seed) if seed is not None else None
    previous: set[str] = set()
    rows = []
    for day, group in data[data["TradingDay"].isin(rebalance)].groupby("TradingDay"):
        eligible = group[group["practical"] & group["_score"].notna()].copy()
        if len(eligible) < TOP_N:
            continue
        if rng is None:
            eligible = eligible.sort_values(["_score", "Symbol"], ascending=[False, True])
        else:
            eligible["_random"] = rng.random(len(eligible))
            eligible = eligible.sort_values(["_random", "Symbol"], ascending=[False, True])
        selected = eligible.head(TOP_N)
        valid = selected["fwd5"].notna()
        executed = set(selected.loc[valid, "Symbol"].astype(str))
        missing_rate = 1.0 - float(valid.mean())
        gross_absolute = float(selected["fwd5"].fillna(0.0).sum() / TOP_N)
        benchmark = float(eligible["fwd5"].dropna().mean())
        turnover = 1.0 if not previous else 1.0 - len(executed & previous) / TOP_N
        cost = turnover * COST_PER_SIDE * 2.0
        rows.append(
            {
                "date": pd.Timestamp(day),
                "gross_absolute": gross_absolute,
                "net_absolute": gross_absolute - cost,
                "benchmark": benchmark,
                "gross_active": gross_absolute - benchmark,
                "net_active": gross_absolute - benchmark - cost,
                "turnover": turnover,
                "missing_rate": missing_rate,
                "executed_names": len(executed),
            }
        )
        previous = executed
    return pd.DataFrame(rows).set_index("date").sort_index()


def _stream_metrics(returns: pd.Series) -> dict:
    clean = returns.dropna().astype(float)
    if clean.empty:
        return {"mean": 0.0, "cagr": 0.0, "sharpe": 0.0, "max_drawdown": 0.0}
    standard_deviation = clean.std(ddof=1)
    sharpe = (
        float(clean.mean() / standard_deviation * math.sqrt(252.0 / ANCHOR))
        if standard_deviation > 0
        else 0.0
    )
    wealth = (1.0 + clean).cumprod()
    cagr = float(wealth.iloc[-1] ** (252.0 / (ANCHOR * len(clean))) - 1.0)
    max_drawdown = float((wealth / wealth.cummax() - 1.0).min())
    return {
        "mean": float(clean.mean()),
        "cagr": cagr,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
    }


def _summarize(records: pd.DataFrame) -> dict:
    active = _stream_metrics(records["net_active"])
    absolute = _stream_metrics(records["net_absolute"])
    gross_active = _stream_metrics(records["gross_active"])
    gross_absolute = _stream_metrics(records["gross_absolute"])
    benchmark = _stream_metrics(records["benchmark"])
    fold_results = {}
    positive_folds = 0
    for name, start, end in FOLDS:
        fold = records.loc[start:end]
        metrics = _stream_metrics(fold["net_active"])
        if metrics["mean"] > 0:
            positive_folds += 1
        fold_results[name] = {"n_periods": len(fold), "active": metrics}
    return {
        "n_periods": len(records),
        "active": active,
        "absolute": absolute,
        "gross_active": gross_active,
        "gross_absolute": gross_absolute,
        "benchmark": benchmark,
        "average_cost_drag": float((records["gross_absolute"] - records["net_absolute"]).mean()),
        "annual_turnover": float(records["turnover"].mean() * 252.0 / ANCHOR),
        "selected_missing_rate": float(records["missing_rate"].mean()),
        "average_executed_names": float(records["executed_names"].mean()),
        "positive_folds": positive_folds,
        "folds": fold_results,
    }


def _verdict(real: dict, placebo_sharpes: list[float]) -> dict:
    placebo_median = statistics.median(placebo_sharpes)
    checks = {
        "active_edge_positive": real["active"]["mean"] > 0,
        "active_sharpe": real["active"]["sharpe"] >= 0.50,
        "positive_folds": real["positive_folds"] >= 2,
        "placebo_margin": real["active"]["sharpe"] >= placebo_median + 0.20,
        "turnover": real["annual_turnover"] <= 16.0,
        "missing_rate": real["selected_missing_rate"] <= 0.02,
        "absolute_cagr": real["absolute"]["cagr"] > 0,
    }
    if all(checks.values()):
        verdict = "GO"
    elif checks["active_edge_positive"] and checks["absolute_cagr"]:
        verdict = "MARGINAL"
    else:
        verdict = "NO-GO"
    return {
        "verdict": verdict,
        "checks": checks,
        "placebo_median_sharpe": placebo_median,
        "placebo_positive_count": sum(value > 0 for value in placebo_sharpes),
    }


def _latest_lot_feasibility(data: pd.DataFrame, nav: float = 400_000.0) -> dict:
    latest_day = data["TradingDay"].max()
    group = data[(data["TradingDay"] == latest_day) & data["practical"] & data["_score"].notna()]
    selected = group.sort_values(["_score", "Symbol"], ascending=[False, True]).head(TOP_N)
    target_notional = nav / TOP_N
    shares = (target_notional / selected["Close"] // 100 * 100).fillna(0).astype(int)
    return {
        "date": pd.Timestamp(latest_day).date().isoformat(),
        "selected": len(selected),
        "lot_feasible": int((shares >= 100).sum()),
        "minimum_target_shares": int(shares.min()) if len(shares) else 0,
    }


def render_markdown(payload: dict) -> str:
    real = payload["real"]
    verdict = payload["verdict"]
    lines = [
        "# A股横截面低换手因子复核结果",
        "",
        f"- verdict: **{verdict['verdict']}**",
        f"- periods: {real['n_periods']}",
        f"- net active edge / 5 sessions: {real['active']['mean']:.3%}",
        f"- net active Sharpe: {real['active']['sharpe']:.3f}",
        f"- absolute CAGR: {real['absolute']['cagr']:.2%}",
        f"- annual turnover: {real['annual_turnover']:.2f}",
        f"- selected return missing rate: {real['selected_missing_rate']:.2%}",
        f"- placebo median Sharpe: {verdict['placebo_median_sharpe']:.3f}",
        "",
        "| Fold | Periods | Active edge | Active Sharpe |",
        "| --- | ---: | ---: | ---: |",
    ]
    for name, fold in real["folds"].items():
        lines.append(
            f"| {name} | {fold['n_periods']} | {fold['active']['mean']:.3%} | {fold['active']['sharpe']:.3f} |"
        )
    lines.extend(["", "## Gate", ""])
    for name, passed in verdict["checks"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} `{name}`")
    return "\n".join(lines)


def run_study(start: str, end: str, panel_cache: str = "") -> dict:
    cfg = Config()
    connection = connect(cfg, read_only=True)
    try:
        calendar = TradingCalendar.from_duckdb(connection)
        if panel_cache:
            panel = pd.read_parquet(panel_cache)
            version_hash = Path(panel_cache).stem.removeprefix("panel_")
        else:
            built = load_or_build_panel(cfg, start, end, con=connection)
            panel = built.df
            version_hash = built.version_hash
    finally:
        connection.close()
    panel = forward_return_columns(panel, calendar, [ANCHOR])
    data = _prepare(panel)
    real_records = _arm_records(data)
    real = _summarize(real_records)
    placebo_sharpes = []
    for seed in PLACEBO_SEEDS:
        placebo = _summarize(_arm_records(data, seed=seed))
        placebo_sharpes.append(placebo["active"]["sharpe"])
    verdict = _verdict(real, placebo_sharpes)
    post_report = _summarize(real_records.loc["2026-07-22":])
    post_status = (
        "OBSERVATIONAL"
        if post_report["n_periods"] >= 20 and post_report["selected_missing_rate"] <= 0.02
        else "HOLDOUT_INCOMPLETE"
    )
    return {
        "study": "a-share-cross-sectional-low-turnover-replication-v1",
        "data_version": version_hash,
        "start": start,
        "end": end,
        "parameters": {
            "window": 20,
            "top_n": TOP_N,
            "anchor": ANCHOR,
            "cost_per_side": COST_PER_SIDE,
            "small_size_exclusion": SMALL_SIZE_EXCLUSION,
            "placebo_seeds": list(PLACEBO_SEEDS),
        },
        "real": real,
        "placebo_sharpes": placebo_sharpes,
        "verdict": verdict,
        "post_2026_07_21_observation": {"status": post_status, **post_report},
        "latest_lot_feasibility": _latest_lot_feasibility(data),
        "limitations": [
            "rolling replication, not a virgin untouched holdout",
            "current-name/ST proxy is not complete point-in-time status authority",
            "missing scheduled forward return is treated as cash rather than delayed execution",
            "portfolio uses equal-weight research returns, not order-level lot execution",
        ],
    }


def self_check() -> None:
    positive = pd.Series([0.01, -0.005, 0.008, 0.002])
    metrics = _stream_metrics(positive)
    if metrics["cagr"] <= 0:
        raise RuntimeError("self-check expected positive CAGR")
    real = {
        "active": {"mean": 0.001, "sharpe": 0.8},
        "absolute": {"cagr": 0.1},
        "positive_folds": 3,
        "annual_turnover": 10.0,
        "selected_missing_rate": 0.0,
    }
    if _verdict(real, [0.1] * 20)["verdict"] != "GO":
        raise RuntimeError("self-check expected GO verdict")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2016-01-01")
    parser.add_argument("--end", default="2026-08-25")
    parser.add_argument("--panel-cache", default="")
    parser.add_argument("--out-json", default="overall/a-share-low-turnover-replication.json")
    parser.add_argument("--out-md", default="overall/a-share-low-turnover-replication.md")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args(argv)
    if args.self_check:
        self_check()
        print("self-check passed")
        return 0
    payload = run_study(args.start, args.end, args.panel_cache)
    Path(args.out_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = render_markdown(payload)
    Path(args.out_md).write_text(markdown + "\n", encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
