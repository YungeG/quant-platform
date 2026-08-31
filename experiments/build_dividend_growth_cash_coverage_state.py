"""Build the frozen dividend-growth and cash-coverage state without returns."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import duckdb
import pandas as pd

YEARS = (2022, 2023, 2024)
MIN_COVERAGE = 1.20


def evaluate(groups: pd.DataFrame, cashflow: pd.DataFrame) -> pd.DataFrame:
    merged = groups.merge(cashflow, on=["security_code", "fiscal_year"], how="left", validate="one_to_one")
    merged["coverage"] = merged.n_cashflow_act / merged.cash_payout
    rows = []
    for security_code, frame in merged.groupby("security_code"):
        by_year = frame.set_index("fiscal_year")
        if not all(year in by_year.index for year in YEARS):
            continue
        dividends = [float(by_year.loc[year, "cash_per_share"]) for year in YEARS]
        coverages = [float(by_year.loc[year, "coverage"]) for year in YEARS]
        rows.append({
            "security_code": security_code,
            **{f"cash_per_share_{year}": dividends[index] for index, year in enumerate(YEARS)},
            **{f"coverage_{year}": coverages[index] for index, year in enumerate(YEARS)},
            "strict_dividend_growth": dividends[0] < dividends[1] < dividends[2],
            "cash_coverage_pass": all(value >= MIN_COVERAGE for value in coverages),
            "eligible": dividends[0] < dividends[1] < dividends[2] and all(value >= MIN_COVERAGE for value in coverages),
        })
    return pd.DataFrame(rows)


def run(dividends_path: str, cashflow_path: str, db_path: str, as_of: str, out_csv: str, out_json: str) -> dict:
    rows = [
        row for row in csv.DictReader(Path(dividends_path).open(encoding="utf-8"))
        if row["status"] == "COMPLETE"
        and row["security_code"].startswith(("0", "3", "6"))
        and row["fiscal_period_type"] == "ANNUAL"
        and row["fiscal_year"] in {str(year) for year in YEARS}
        and row["publish_date"] <= as_of
    ]
    dividends = pd.DataFrame(rows)
    dividends["record_date"] = pd.to_datetime(dividends.record_date)
    dividends["cash_per_share"] = pd.to_numeric(dividends.cash_per_share)
    dividends["fiscal_year"] = pd.to_numeric(dividends.fiscal_year).astype(int)
    dividends["row_id"] = range(len(dividends))
    connection = duckdb.connect(db_path, read_only=True)
    try:
        connection.register("dividend_rows", dividends[["row_id", "security_code", "record_date"]])
        shares = connection.execute("""
            select d.row_id, f.TotalShare as total_share
            from dividend_rows d
            asof left join FundamentalData f
              on d.security_code = f.Symbol and d.record_date >= f.TradingDay
        """).fetchdf()
    finally:
        connection.close()
    dividends = dividends.merge(shares, on="row_id", how="left", validate="one_to_one")
    dividends["cash_payout"] = dividends.cash_per_share * dividends.total_share
    grouped = dividends.groupby(["security_code", "fiscal_year"], as_index=False).agg(
        cash_per_share=("cash_per_share", "sum"),
        cash_payout=("cash_payout", "sum"),
        announcement_count=("announcement_id", "nunique"),
        missing_share=("total_share", lambda values: int(values.isna().sum())),
    )
    cashflow = pd.read_csv(cashflow_path, dtype={"ts_code": str, "ann_date": str, "end_date": str})
    cashflow["ann_date"] = pd.to_datetime(cashflow.ann_date, errors="coerce")
    cashflow["end_date"] = pd.to_datetime(cashflow.end_date, errors="coerce")
    cashflow["n_cashflow_act"] = pd.to_numeric(cashflow.n_cashflow_act, errors="coerce")
    cashflow = cashflow[
        cashflow.ts_code.str.endswith((".SH", ".SZ"))
        & cashflow.end_date.dt.year.isin(YEARS)
        & (cashflow.end_date.dt.month == 12)
        & (cashflow.end_date.dt.day == 31)
        & (cashflow.ann_date <= pd.Timestamp(as_of))
    ].sort_values(["ts_code", "end_date", "ann_date", "update_flag"])
    cashflow = cashflow.drop_duplicates(["ts_code", "end_date"], keep="last")
    cashflow = cashflow.assign(
        security_code=cashflow.ts_code.str[:6],
        fiscal_year=cashflow.end_date.dt.year,
    )[["security_code", "fiscal_year", "n_cashflow_act"]]
    state = evaluate(grouped, cashflow)
    missing_share_rows = int(grouped.missing_share.sum())
    missing_cashflow_pairs = int(grouped.merge(cashflow, on=["security_code", "fiscal_year"], how="left").n_cashflow_act.isna().sum())
    output = Path(out_csv)
    output.parent.mkdir(parents=True, exist_ok=True)
    state.to_csv(output, index=False)
    payload = {
        "study": "a-share-dividend-growth-cash-coverage-state-v1",
        "as_of": as_of,
        "fiscal_years": list(YEARS),
        "rule": {"strict_dividend_growth": True, "minimum_cash_coverage_each_year": MIN_COVERAGE},
        "annual_implementation_rows": len(dividends),
        "symbol_year_groups": len(grouped),
        "symbols_with_three_years": len(state),
        "eligible_symbols": int(state.eligible.sum()) if len(state) else 0,
        "missing_share_rows": missing_share_rows,
        "missing_cashflow_pairs": missing_cashflow_pairs,
        "status": "SOURCE_BLOCKED" if missing_share_rows or missing_cashflow_pairs else "STATE_BUILT_NO_BACKTEST",
        "limitations": [
            "cash payout uses PIT TotalShare at record date multiplied by announced cash per share",
            "one payment date is supplemented by captured Eastmoney vendor data",
            "no listing/ST/liquidity portfolio filter or return evaluation is performed",
            "no public multi-instrument A-share Backtest preparation operation exists",
        ],
        "backtest_ready": False,
        "trade_authorized": False,
    }
    Path(out_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dividends", default="overall/a-share-cninfo-dividend-2022-2025-normalized.csv")
    parser.add_argument("--cashflow", default="/home/ygguo/agent-projs/ai-crypt/platform-a-share-research/overall/a-share-quarterly-statements-raw/cashflow_vip.csv")
    parser.add_argument("--db", default="/srv/bcache-8t/ygguo/duckdb/quant-a50/quant_a50.duckdb")
    parser.add_argument("--as-of", default="2025-12-31")
    parser.add_argument("--out-csv", default="overall/a-share-dividend-growth-cash-coverage-state-v1.csv")
    parser.add_argument("--out-json", default="overall/a-share-dividend-growth-cash-coverage-state-v1.json")
    args = parser.parse_args(argv)
    print(json.dumps(run(args.dividends, args.cashflow, args.db, args.as_of, args.out_csv, args.out_json), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
