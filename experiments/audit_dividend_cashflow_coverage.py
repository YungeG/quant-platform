"""Audit PIT annual operating-cash-flow coverage for dividend lifecycle rows."""
from __future__ import annotations

import argparse
import bisect
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

INTERIM = ("中期", "半年度", "季度", "特别分红")


def fiscal_year(title: str) -> int | None:
    match = re.search(r"(20\d{2})年", title or "")
    return int(match.group(1)) if match else None


def is_annual(title: str) -> bool:
    return "年度" in (title or "") and not any(token in title for token in INTERIM)


def run(dividends_path: str, cashflow_path: str, out_json: str, out_md: str) -> dict:
    dividend_rows = [
        row for row in csv.DictReader(Path(dividends_path).open(encoding="utf-8"))
        if row["status"] == "COMPLETE" and row["security_code"].startswith(("0", "3", "6"))
    ]
    annual_dividends = [
        row for row in dividend_rows
        if row.get("fiscal_period_type") == "ANNUAL" or (not row.get("fiscal_period_type") and is_annual(row["title"]))
    ]
    cashflow = pd.read_csv(cashflow_path, dtype={"ts_code": str, "ann_date": str, "end_date": str})
    cashflow["ann_date"] = pd.to_datetime(cashflow.ann_date, errors="coerce")
    cashflow["end_date"] = pd.to_datetime(cashflow.end_date, errors="coerce")
    cashflow["n_cashflow_act"] = pd.to_numeric(cashflow.n_cashflow_act, errors="coerce")
    cashflow = cashflow.dropna(subset=["ts_code", "ann_date", "end_date"])
    cashflow = cashflow[(cashflow.end_date.dt.month == 12) & (cashflow.end_date.dt.day == 31)]
    history: dict[tuple[str, int], list[tuple[pd.Timestamp, float | None]]] = defaultdict(list)
    for row in cashflow.sort_values(["ts_code", "end_date", "ann_date", "update_flag"]).itertuples(index=False):
        value = float(row.n_cashflow_act) if pd.notna(row.n_cashflow_act) else None
        history[(row.ts_code[:6], row.end_date.year)].append((pd.Timestamp(row.ann_date), value))
    missing_year = []
    missing_cashflow = []
    covered = []
    for row in annual_dividends:
        year = int(row["fiscal_year"]) if row.get("fiscal_year") else fiscal_year(row["title"])
        if year is None:
            missing_year.append(row["announcement_id"])
            continue
        revisions = history.get((row["security_code"], year), [])
        dates = [item[0] for item in revisions]
        position = bisect.bisect_right(dates, pd.Timestamp(row["publish_date"])) - 1
        if position < 0 or revisions[position][1] is None:
            missing_cashflow.append({"announcement_id": row["announcement_id"], "security_code": row["security_code"], "fiscal_year": year})
            continue
        covered.append({
            "announcement_id": row["announcement_id"],
            "security_code": row["security_code"],
            "fiscal_year": year,
            "cashflow_ann_date": str(revisions[position][0].date()),
            "n_cashflow_act": revisions[position][1],
        })
    unique_pairs = {(row["security_code"], row["fiscal_year"]) for row in covered}
    payload = {
        "audit_id": "a-share-dividend-cashflow-coverage-v1",
        "dividend_rows_sh_sz_complete": len(dividend_rows),
        "annual_dividend_rows_by_title": len(annual_dividends),
        "annual_rows_with_pit_cashflow": len(covered),
        "annual_unique_symbol_years_with_pit_cashflow": len(unique_pairs),
        "annual_rows_missing_title_year": len(missing_year),
        "annual_rows_missing_pit_cashflow": len(missing_cashflow),
        "coverage_rate": len(covered) / len(annual_dividends) if annual_dividends else 0.0,
        "cashflow_annual_source_rows": len(cashflow),
        "cashflow_symbol_year_pairs": len(history),
        "cashflow_earliest_announcement": str(cashflow.ann_date.min().date()) if len(cashflow) else None,
        "cashflow_latest_announcement": str(cashflow.ann_date.max().date()) if len(cashflow) else None,
        "missing_title_year_ids": missing_year[:100],
        "missing_pit_cashflow": missing_cashflow[:100],
        "limitations": [
            "annual/interim classification uses official PDF text; UNKNOWN period rows are excluded from annual coverage",
            "cash-flow source is a captured vendor CSV and still needs immutable source/terminal completeness authority",
            "dividend payout denominator and proposal/cancellation lineage are not yet bound",
        ],
        "backtest_ready": False,
        "trade_authorized": False,
    }
    Path(out_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(out_md).write_text(
        "# A股分红现金流覆盖审计V1\n\n"
        f"- annual dividend rows: {len(annual_dividends)}\n"
        f"- PIT cash-flow covered: {len(covered)} ({payload['coverage_rate']:.2%})\n"
        f"- missing PIT cash-flow: {len(missing_cashflow)}\n"
        "- verdict: **SOURCE-BOUNDED / NO BACKTEST**\n",
        encoding="utf-8",
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dividends", default="overall/a-share-cninfo-dividend-2022-2025-normalized.csv")
    parser.add_argument("--cashflow", default="/home/ygguo/agent-projs/ai-crypt/platform-a-share-research/overall/a-share-quarterly-statements-raw/cashflow_vip.csv")
    parser.add_argument("--out-json", default="overall/a-share-dividend-cashflow-coverage-v1.json")
    parser.add_argument("--out-md", default="overall/a-share-dividend-cashflow-coverage-v1.md")
    args = parser.parse_args(argv)
    print(json.dumps(run(args.dividends, args.cashflow, args.out_json, args.out_md), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
