"""Enrich breakout-retest events with PIT sector context and evaluate the overlay."""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.run_breakout_retest_v2 import event_metrics
from experiments.run_lowturn_livermore import _clean
from experiments.sector_effect import sector_confirmed
from factormine.config import Config
from factormine.data.db import connect
from factormine.data.panel import load_or_build_panel
from factormine.research.combination import repair_point_in_time_size


def build_enriched(events_path: str, start: str, end: str) -> tuple[pd.DataFrame, dict]:
    cfg = Config()
    connection = connect(cfg, read_only=True)
    try:
        built = load_or_build_panel(cfg, "2014-11-27", end, con=connection)
        industry = connection.execute(
            """
            with l1 as (
                select distinct L1Code as TSCode, L1Name as industry
                from IndustryMemberHistoryData
            )
            select d.TradeDate, d.TSCode, l1.industry, d.PctChange
            from IndustryDailyData d join l1 on d.TSCode = l1.TSCode
            where d.TradeDate between ? and ?
            """,
            ["2014-11-27", end],
        ).df()
    finally:
        connection.close()
    panel = repair_point_in_time_size(built.df)
    panel["TradingDay"] = pd.to_datetime(panel["TradingDay"])
    panel = panel.sort_values(["Symbol", "TradingDay"]).reset_index(drop=True)
    grouped = panel.groupby("Symbol", sort=False)
    panel["_ma20"] = grouped["adj_close"].transform(
        lambda series: series.rolling(20, min_periods=20).mean()
    )
    panel["_stock_ret60"] = grouped["adj_close"].transform(
        lambda series: series / series.shift(60) - 1.0
    )
    breadth_rows = panel[
        (panel["age"] >= 60)
        & (~panel["suspended"].fillna(True))
        & panel["_ma20"].notna()
        & panel["industry"].notna()
    ].copy()
    breadth_rows["_above_ma20"] = breadth_rows["adj_close"] > breadth_rows["_ma20"]
    breadth = (
        breadth_rows.groupby(["TradingDay", "industry"])["_above_ma20"]
        .mean()
        .rename("industry_breadth_ma20")
        .reset_index()
    )
    stock_context = panel[
        ["TradingDay", "Symbol", "industry", "_stock_ret60"]
    ].rename(
        columns={
            "TradingDay": "breakout_date",
            "Symbol": "symbol",
            "_stock_ret60": "stock_ret60",
        }
    )

    industry["TradeDate"] = pd.to_datetime(industry["TradeDate"])
    industry = industry.drop_duplicates(["TradeDate", "TSCode"], keep="last")
    industry = industry.sort_values(["TSCode", "TradeDate"])
    industry["index_value"] = industry.groupby("TSCode", sort=False)["PctChange"].transform(
        lambda series: (1.0 + series.fillna(0.0) / 100.0).cumprod()
    )
    industry["industry_ret20"] = industry.groupby("TSCode", sort=False)["index_value"].transform(
        lambda series: series / series.shift(20) - 1.0
    )
    industry["industry_ret60"] = industry.groupby("TSCode", sort=False)["index_value"].transform(
        lambda series: series / series.shift(60) - 1.0
    )
    industry["industry_ma60"] = industry.groupby("TSCode", sort=False)["index_value"].transform(
        lambda series: series.rolling(60, min_periods=60).mean()
    )
    industry["industry_strength_pct"] = industry.groupby("TradeDate")["industry_ret60"].rank(
        pct=True, method="average"
    )
    industry["industry_above_ma60"] = industry["index_value"] > industry["industry_ma60"]
    industry_context = industry[
        [
            "TradeDate",
            "industry",
            "industry_ret20",
            "industry_ret60",
            "industry_strength_pct",
            "industry_above_ma60",
        ]
    ].rename(columns={"TradeDate": "breakout_date"})

    events = pd.read_csv(events_path, parse_dates=["breakout_date", "signal_date"])
    events["symbol"] = events["symbol"].astype(str).str.zfill(6)
    events = events.merge(stock_context, on=["breakout_date", "symbol"], how="left")
    events = events.merge(industry_context, on=["breakout_date", "industry"], how="left")
    events = events.merge(
        breadth.rename(columns={"TradingDay": "breakout_date"}),
        on=["breakout_date", "industry"],
        how="left",
    )
    events["stock_excess_60"] = events["stock_ret60"] - events["industry_ret60"]
    events["sector_confirmed"] = [
        sector_confirmed(
            float(strength) if np.isfinite(strength) else -1.0,
            bool(above) if pd.notna(above) else False,
            float(width) if np.isfinite(width) else -1.0,
            float(excess) if np.isfinite(excess) else -1.0,
        )
        for strength, above, width, excess in zip(
            events["industry_strength_pct"],
            events["industry_above_ma60"],
            events["industry_breadth_ma20"],
            events["stock_excess_60"],
            strict=True,
        )
    ]
    metadata = {
        "panel_version": built.version_hash,
        "events": len(events),
        "sector_confirmed_events": int(events["sector_confirmed"].sum()),
        "feature_complete_rate": float(events["industry_strength_pct"].notna().mean()),
        "start": start,
        "end": end,
    }
    del panel, breadth_rows, breadth, stock_context, industry, industry_context
    gc.collect()
    return events, metadata


def decide(events: pd.DataFrame) -> tuple[dict, dict]:
    executed = events[events["execution_reason"] == "executed"]
    confirmed = executed[executed["sector_confirmed"]]
    all_metrics = event_metrics(executed, 20)
    confirmed_metrics = event_metrics(confirmed, 20)
    mean_uplift = confirmed_metrics["mean"] - all_metrics["mean"]
    win_uplift = confirmed_metrics["win_rate"] - all_metrics["win_rate"]
    checks = {
        "count": confirmed_metrics["count"] >= 80,
        "mean": confirmed_metrics["mean"] >= 0.01,
        "median": confirmed_metrics["median"] > 0,
        "win_rate": confirmed_metrics["win_rate"] > 0.52,
        "positive_folds": sum(
            fold["mean"] > 0 for fold in confirmed_metrics["folds"].values()
        )
        >= 2,
        "bootstrap": confirmed_metrics["bootstrap_95"][0] > 0,
        "uplift": mean_uplift >= 0.01 or win_uplift >= 0.05,
    }
    if all(checks.values()):
        verdict = "GO"
    elif mean_uplift > 0:
        verdict = "MARGINAL"
    else:
        verdict = "NO-GO"
    failure_table = (
        events.groupby(["sector_confirmed", "terminal_reason"])
        .size()
        .unstack(fill_value=0)
        .to_dict(orient="index")
    )
    return {
        "verdict": verdict,
        "checks": checks,
        "all_executed20": all_metrics,
        "sector_confirmed20": confirmed_metrics,
        "mean_uplift": mean_uplift,
        "win_rate_uplift": win_uplift,
    }, {str(key): value for key, value in failure_table.items()}


def render_markdown(payload: dict) -> str:
    all_row = payload["decision"]["all_executed20"]
    sector = payload["decision"]["sector_confirmed20"]
    return "\n".join(
        [
            "# 突破回踩板块效应结果",
            "",
            f"- verdict: **{payload['decision']['verdict']}**",
            f"- sector-confirmed executed events: {sector['count']}",
            "",
            "| Sample | Mean active20 | Median | Win rate | Bootstrap 95% |",
            "| --- | ---: | ---: | ---: | --- |",
            f"| all | {all_row['mean']:.2%} | {all_row['median']:.2%} | {all_row['win_rate']:.2%} | "
            f"[{all_row['bootstrap_95'][0]:.2%}, {all_row['bootstrap_95'][1]:.2%}] |",
            f"| sector confirmed | {sector['mean']:.2%} | {sector['median']:.2%} | {sector['win_rate']:.2%} | "
            f"[{sector['bootstrap_95'][0]:.2%}, {sector['bootstrap_95'][1]:.2%}] |",
        ]
    )


def run(events_path: str, output_ledger: str, start: str, end: str) -> dict:
    events, metadata = build_enriched(events_path, start, end)
    events.to_csv(output_ledger, index=False, date_format="%Y-%m-%d")
    decision, failure_table = decide(events)
    return _clean(
        {
            "study": "a-share-breakout-retest-sector-effect-v1",
            "data": metadata,
            "decision": decision,
            "failure_table": failure_table,
            "ledger": output_ledger,
            "limitations": [
                "industry indices and membership use current-vintage stored history",
                "sector thresholds are frozen but the sample is not virgin OOS",
                "daily industry breadth cannot observe intraday sector leadership changes",
            ],
        }
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", default="overall/a-share-breakout-retest-v2-events.csv")
    parser.add_argument("--ledger", default="overall/a-share-breakout-retest-v2-sector-events.csv")
    parser.add_argument("--start", default="2016-01-01")
    parser.add_argument("--end", default="2026-08-25")
    parser.add_argument("--out-json", default="overall/a-share-breakout-retest-sector.json")
    parser.add_argument("--out-md", default="overall/a-share-breakout-retest-sector.md")
    args = parser.parse_args(argv)
    payload = run(args.events, args.ledger, args.start, args.end)
    Path(args.out_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = render_markdown(payload)
    Path(args.out_md).write_text(markdown + "\n", encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
