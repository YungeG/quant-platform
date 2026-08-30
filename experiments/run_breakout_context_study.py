"""Build and evaluate proxy-sourced context features for breakout-retest events."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from experiments.context_features import analyst_eps_revision, holm_adjust
from experiments.run_lowturn_livermore import _clean


DB_PATH = "/srv/bcache-8t/ygguo/duckdb/quant-a50/quant_a50.duckdb"
FOLDS = (
    ("2016-2019", "2016-01-01", "2019-12-31"),
    ("2020-2022", "2020-01-01", "2022-12-31"),
    ("2023-2026", "2023-01-01", "2026-12-31"),
)
FEATURES = {
    "chip_winner_rate": -1,
    "moneyflow_ths_net_rate": 1,
    "recent_limit_count5": -1,
    "hot_money_intensity5": -1,
    "analyst_eps_revision30": 1,
}


def _read(path: Path, **kwargs) -> pd.DataFrame:
    return pd.read_csv(path, **kwargs) if path.exists() and path.stat().st_size > 1 else pd.DataFrame()


def _local_context(events: pd.DataFrame) -> tuple[pd.DataFrame, list[pd.Timestamp]]:
    request = events[["event_id", "symbol", "signal_date"]].copy()
    connection = duckdb.connect(DB_PATH, read_only=True)
    try:
        connection.register("event_request", request)
        context = connection.execute(
            """
            select e.event_id, m.Close as signal_close, f.CircMV as signal_circ_mv
            from event_request e
            left join MarketData m on m.Symbol=e.symbol and m.TradingDay=cast(e.signal_date as date)
            left join FundamentalData f on f.Symbol=e.symbol and f.TradingDay=cast(e.signal_date as date)
            """
        ).df()
        sessions = connection.execute(
            """
            select distinct TradingDay from (
                select TradingDay from MarketData
                union all
                select TradingDay from DelistedMarketData
            ) order by TradingDay
            """
        ).df()["TradingDay"].tolist()
    finally:
        connection.close()
    return context, [pd.Timestamp(day) for day in sessions]


def build_ledger(events_path: str, raw_dir: str) -> pd.DataFrame:
    events = pd.read_csv(
        events_path,
        dtype={"symbol": str},
        parse_dates=["breakout_date", "signal_date", "entry_date"],
    )
    events["symbol"] = events["symbol"].str.zfill(6)
    executed = events[events["execution_reason"] == "executed"].copy()
    context, sessions = _local_context(executed)
    executed = executed.merge(context, on="event_id", how="left")
    session_position = {day: index for index, day in enumerate(sessions)}
    valid_dates = {}
    for row in executed.itertuples(index=False):
        position = session_position.get(pd.Timestamp(row.signal_date))
        valid_dates[row.event_id] = set(sessions[max(0, position - 4) : position + 1]) if position is not None else set()

    raw = Path(raw_dir)
    cyq = _read(raw / "cyq_perf.csv", dtype={"trade_date": str})
    if len(cyq):
        cyq = cyq.drop_duplicates("event_id", keep="last")
        executed = executed.merge(
            cyq[["event_id", "weight_avg", "winner_rate"]].rename(
                columns={"weight_avg": "chip_weight_avg", "winner_rate": "chip_winner_rate"}
            ),
            on="event_id",
            how="left",
        )
        executed["chip_close_to_cost"] = executed["signal_close"] / executed["chip_weight_avg"] - 1.0
    else:
        executed[["chip_weight_avg", "chip_winner_rate", "chip_close_to_cost"]] = np.nan

    ths = _read(raw / "moneyflow_ths.csv")
    if len(ths):
        rate_columns = ["buy_lg_amount_rate", "buy_md_amount_rate", "buy_sm_amount_rate"]
        ths["moneyflow_ths_net_rate"] = ths[rate_columns].sum(axis=1, min_count=len(rate_columns))
        executed = executed.merge(
            ths[["event_id", "moneyflow_ths_net_rate", "net_amount", "net_d5_amount"]].rename(
                columns={"net_amount": "moneyflow_ths_net_amount", "net_d5_amount": "moneyflow_ths_net_d5"}
            ).drop_duplicates("event_id", keep="last"),
            on="event_id",
            how="left",
        )
    else:
        executed[["moneyflow_ths_net_rate", "moneyflow_ths_net_amount", "moneyflow_ths_net_d5"]] = np.nan

    dc = _read(raw / "moneyflow_dc.csv")
    if len(dc):
        executed = executed.merge(
            dc[["event_id", "net_amount_rate"]].rename(columns={"net_amount_rate": "moneyflow_dc_net_rate"}).drop_duplicates("event_id", keep="last"),
            on="event_id",
            how="left",
        )
    else:
        executed["moneyflow_dc_net_rate"] = np.nan

    limit_rows = _read(raw / "limit_list_d.csv", dtype={"trade_date": str})
    limit_counts = {}
    if len(limit_rows):
        limit_rows["trade_date"] = pd.to_datetime(limit_rows["trade_date"])
        for event_id, group in limit_rows.groupby("event_id"):
            limit_counts[event_id] = int(
                group[
                    group["trade_date"].isin(valid_dates.get(event_id, set()))
                    & group["limit"].isin(["U", "Z"])
                ].shape[0]
            )
    executed["recent_limit_count5"] = [
        limit_counts.get(row.event_id, 0) if row.signal_date >= pd.Timestamp("2020-01-01") else np.nan
        for row in executed.itertuples(index=False)
    ]

    hot = _read(raw / "hm_detail.csv", dtype={"trade_date": str})
    hot_sums = {}
    if len(hot):
        hot["trade_date"] = pd.to_datetime(hot["trade_date"])
        for event_id, group in hot.groupby("event_id"):
            selected = group[group["trade_date"].isin(valid_dates.get(event_id, set()))]
            hot_sums[event_id] = float(selected["net_amount"].sum())
    hot_amount = [
        hot_sums.get(row.event_id, 0.0) if row.signal_date >= pd.Timestamp("2022-08-01") else np.nan
        for row in executed.itertuples(index=False)
    ]
    executed["hot_money_net_amount5"] = hot_amount
    executed["hot_money_intensity5"] = (
        np.abs(executed["hot_money_net_amount5"]) / (executed["signal_circ_mv"] * 10_000.0)
    )

    reports = _read(raw / "report_rc.csv", dtype={"report_date": str, "quarter": str})
    report_groups = {event_id: group for event_id, group in reports.groupby("event_id")} if len(reports) else {}
    revisions = [
        analyst_eps_revision(report_groups.get(row.event_id, pd.DataFrame()), pd.Timestamp(row.signal_date))
        for row in executed.itertuples(index=False)
    ]
    executed["analyst_target_quarter"] = [row["quarter"] for row in revisions]
    executed["analyst_current_count"] = [row["current_count"] for row in revisions]
    executed["analyst_prior_count"] = [row["prior_count"] for row in revisions]
    executed["analyst_current_eps"] = [row["current_eps"] for row in revisions]
    executed["analyst_prior_eps"] = [row["prior_eps"] for row in revisions]
    executed["analyst_eps_revision30"] = [row["revision"] for row in revisions]
    return executed


def _bootstrap_rho(x: np.ndarray, y: np.ndarray, seed: int = 20260827) -> list[float]:
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(2000):
        index = rng.integers(0, len(x), len(x))
        sampled_x = x[index]
        sampled_y = y[index]
        if np.unique(sampled_x).size < 2 or np.unique(sampled_y).size < 2:
            values.append(0.0)
            continue
        rho = spearmanr(sampled_x, sampled_y).statistic
        values.append(float(rho) if np.isfinite(rho) else 0.0)
    return [float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))] if values else [0.0, 0.0]


def feature_stats(events: pd.DataFrame, feature: str) -> dict:
    clean = events[[feature, "active20", "signal_date"]].dropna()
    if len(clean) >= 3 and clean[feature].nunique() > 1:
        test = spearmanr(clean[feature], clean["active20"])
        rho, p_value = float(test.statistic), float(test.pvalue)
        confidence = _bootstrap_rho(clean[feature].to_numpy(float), clean["active20"].to_numpy(float))
    else:
        rho, p_value, confidence = 0.0, 1.0, [0.0, 0.0]
    folds = {}
    for name, start, end in FOLDS:
        fold = clean[clean["signal_date"].between(start, end)]
        fold_rho = (
            float(spearmanr(fold[feature], fold["active20"]).statistic)
            if len(fold) >= 3 and fold[feature].nunique() > 1
            else 0.0
        )
        folds[name] = {"count": len(fold), "rho": fold_rho}
    success = clean[clean["active20"] > 0][feature]
    failure = clean[clean["active20"] <= 0][feature]
    return {
        "count": len(clean),
        "rho": rho,
        "p_value": p_value,
        "bootstrap_95": confidence,
        "folds": folds,
        "successful_median": float(success.median()) if len(success) else 0.0,
        "failed_median": float(failure.median()) if len(failure) else 0.0,
    }


def decide(events: pd.DataFrame) -> dict:
    stats = {feature: feature_stats(events, feature) for feature in FEATURES}
    adjusted = holm_adjust({feature: row["p_value"] for feature, row in stats.items()})
    statuses = {}
    for feature, expected in FEATURES.items():
        row = stats[feature]
        direction = expected * row["rho"] > 0
        fold_counts = [fold["count"] for fold in row["folds"].values()]
        fold_direction = sum(expected * fold["rho"] > 0 for fold in row["folds"].values())
        ci_direction = expected * row["bootstrap_95"][0 if expected > 0 else 1] > 0
        checks = {
            "count": row["count"] >= 80,
            "fold_counts": sum(count >= 15 for count in fold_counts) >= 2,
            "direction": direction,
            "bootstrap": ci_direction,
            "fold_direction": fold_direction >= 2,
            "holm": adjusted[feature] < 0.05,
        }
        if all(checks.values()):
            status = "SHADOW-CANDIDATE"
        elif direction:
            status = "MARGINAL"
        else:
            status = "NO-GO"
        statuses[feature] = {"status": status, "expected_sign": expected, "holm_p": adjusted[feature], "checks": checks}
    overall = "SHADOW-CANDIDATE" if any(row["status"] == "SHADOW-CANDIDATE" for row in statuses.values()) else (
        "MARGINAL" if any(row["status"] == "MARGINAL" for row in statuses.values()) else "NO-GO"
    )
    return {"verdict": overall, "features": stats, "decisions": statuses}


def render_markdown(payload: dict) -> str:
    lines = [
        "# 突破回踩上下文特征结果", "",
        f"- verdict: **{payload['decision']['verdict']}**", "",
        "| Feature | N | Rho | Bootstrap 95% | Holm p | Decision |",
        "| --- | ---: | ---: | --- | ---: | --- |",
    ]
    for feature, row in payload["decision"]["features"].items():
        decision = payload["decision"]["decisions"][feature]
        lines.append(
            f"| {feature} | {row['count']} | {row['rho']:.3f} | "
            f"[{row['bootstrap_95'][0]:.3f}, {row['bootstrap_95'][1]:.3f}] | "
            f"{decision['holm_p']:.4f} | {decision['status']} |"
        )
    return "\n".join(lines)


def run(events: str, raw_dir: str, ledger: str) -> dict:
    frame = build_ledger(events, raw_dir)
    frame.to_csv(ledger, index=False, date_format="%Y-%m-%d")
    decision = decide(frame)
    return _clean(
        {
            "study": "a-share-breakout-context-features-v1",
            "data": {"events": len(frame), "active20_complete": int(frame["active20"].notna().sum())},
            "decision": decision,
            "ledger": ledger,
            "limitations": [
                "moneyflow_ths history is sparse before 2025",
                "limit-list history starts in 2020 and hot-money history in 2022-08",
                "report_rc is proxy-observed and needs a source-contract audit before decision-grade use",
                "this is a feature-screening study, not a portfolio backtest",
            ],
        }
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", default="overall/a-share-breakout-retest-v2-events.csv")
    parser.add_argument("--raw-dir", default="overall/a-share-breakout-context-raw")
    parser.add_argument("--ledger", default="overall/a-share-breakout-context-events.csv")
    parser.add_argument("--out-json", default="overall/a-share-breakout-context.json")
    parser.add_argument("--out-md", default="overall/a-share-breakout-context.md")
    args = parser.parse_args(argv)
    payload = run(args.events, args.raw_dir, args.ledger)
    Path(args.out_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = render_markdown(payload)
    Path(args.out_md).write_text(markdown + "\n", encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
