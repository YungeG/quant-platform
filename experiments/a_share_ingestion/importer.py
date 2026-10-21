"""Local CSV importer. Explicit replacement and a single transaction protect existing tables."""

from __future__ import annotations

import argparse
from pathlib import Path

from .runtime import (
    PipelineError,
    add_io_arguments,
    execution_guard,
    open_database,
    pd,
    positive_int,
    provider_path,
    validate_symbol,
)
from .schema import (
    ensure_industry_tables,
    ensure_legacy_industry_member_table,
    initialize_schema,
)


def read_source_csv(path: Path):
    # Nullable YYYYMMDD and leading-zero IDs must not pass through float inference.
    # Numeric columns are converted explicitly by each table's mapping below.
    return pd.read_csv(path, dtype=str)


def get_paths() -> dict:
    return {
        "market_data_dir": provider_path("market_data_dir"),
        "fundamentals_dir": provider_path("fundamentals_dir"),
        "static_dir": provider_path("static_dir"),
        "extended_dir": provider_path("extended_dir"),
        "duckdb_path": provider_path("duckdb_path"),
    }


def industry_evidence_dir() -> Path:
    return provider_path("industry_evidence_dir")


def import_static(con, static_dir: Path):
    path = static_dir / "stock_basic.csv"
    if not path.exists():
        print("skip StaticData, stock_basic.csv missing")
        return
    df = read_source_csv(path)
    if df.empty:
        print("skip StaticData, empty file")
        return
    out = pd.DataFrame(
        {
            "Symbol": df["symbol"].astype(str).str.zfill(6),
            "TSCode": df["ts_code"],
            "Name": df.get("name"),
            "Area": df.get("area"),
            "Industry": df.get("industry"),
            "Market": df.get("market"),
            "ListDate": pd.to_datetime(
                df.get("list_date").astype(str), format="%Y%m%d", errors="coerce"
            ).dt.strftime("%Y-%m-%d"),
            "IsActive": True,
            "UpdateAt": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )
    con.execute("DELETE FROM StaticData")
    con.register("tmp_static", out)
    con.execute("""
        INSERT INTO StaticData
        SELECT
            Symbol,
            TSCode,
            Name,
            Area,
            Industry,
            Market,
            CAST(ListDate AS DATE),
            IsActive,
            CAST(UpdateAt AS TIMESTAMP)
        FROM tmp_static
    """)
    print("imported StaticData", len(out))


def import_fundamentals(con, fundamentals_dir: Path, limit: int | None = None):
    files = sorted(
        p
        for p in fundamentals_dir.glob("daily_basic_*.csv")
        if p.name != "daily_basic_latest.csv"
    )
    if limit:
        files = files[-limit:]
    con.execute("DELETE FROM FundamentalData")
    total = 0
    for path in files:
        df = read_source_csv(path)
        if df.empty:
            continue
        out = pd.DataFrame(
            {
                "TradingDay": pd.to_datetime(
                    df["trade_date"].astype(str), format="%Y%m%d", errors="coerce"
                ).dt.strftime("%Y-%m-%d"),
                "Symbol": df["symbol"].astype(str).str.zfill(6),
                "TSCode": df["ts_code"],
                "Close": pd.to_numeric(df.get("close"), errors="coerce"),
                "TurnoverRate": pd.to_numeric(df.get("turnover_rate"), errors="coerce"),
                "TurnoverRateF": pd.to_numeric(
                    df.get("turnover_rate_f"), errors="coerce"
                ),
                "VolumeRatio": pd.to_numeric(df.get("volume_ratio"), errors="coerce"),
                "PE": pd.to_numeric(df.get("pe"), errors="coerce"),
                "PETTM": pd.to_numeric(df.get("pe_ttm"), errors="coerce"),
                "PB": pd.to_numeric(df.get("pb"), errors="coerce"),
                "PS": pd.to_numeric(df.get("ps"), errors="coerce"),
                "PSTTM": pd.to_numeric(df.get("ps_ttm"), errors="coerce"),
                "DVRatio": pd.to_numeric(df.get("dv_ratio"), errors="coerce"),
                "DVTTM": pd.to_numeric(df.get("dv_ttm"), errors="coerce")
                if "dv_ttm" in df.columns
                else None,
                "TotalShare": pd.to_numeric(df.get("total_share"), errors="coerce"),
                "FloatShare": pd.to_numeric(df.get("float_share"), errors="coerce"),
                "FreeShare": pd.to_numeric(df.get("free_share"), errors="coerce"),
                "TotalMV": pd.to_numeric(df.get("total_mv"), errors="coerce"),
                "CircMV": pd.to_numeric(df.get("circ_mv"), errors="coerce"),
                "UpdateAt": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        con.register("tmp_fund", out)
        con.execute("""
            INSERT INTO FundamentalData
            SELECT
                CAST(TradingDay AS DATE),
                Symbol,
                TSCode,
                Close,
                TurnoverRate,
                TurnoverRateF,
                VolumeRatio,
                PE,
                PETTM,
                PB,
                PS,
                PSTTM,
                DVRatio,
                DVTTM,
                TotalShare,
                FloatShare,
                FreeShare,
                TotalMV,
                CircMV,
                CAST(UpdateAt AS TIMESTAMP)
            FROM tmp_fund
        """)
        total += len(out)
    if total == 0:
        raise PipelineError(
            "fundamental import has no usable rows; replacement must roll back"
        )
    print("imported FundamentalData rows", total)


def import_financials(con, fundamentals_dir: Path):
    income_path = fundamentals_dir / "income.csv"
    fina_path = fundamentals_dir / "fina_indicator.csv"

    if income_path.exists():
        df = read_source_csv(income_path)
        if df.empty:
            raise PipelineError("income input is empty; replacement must roll back")
        # Tushare 利润表净利润字段是 n_income(净利润),n_income_attr_p 为归母;旧脚本误用 net_profit(不存在)→ 全 NaN
        np_col = next(
            (
                c
                for c in ("n_income", "net_profit", "n_income_attr_p")
                if c in df.columns
            ),
            None,
        )
        out = pd.DataFrame(
            {
                "Symbol": df["ts_code"].astype(str).str.split(".").str[0].str.zfill(6),
                "TSCode": df["ts_code"],
                "AnnDate": pd.to_datetime(
                    df["ann_date"].astype(str), format="%Y%m%d", errors="coerce"
                ).dt.strftime("%Y-%m-%d"),
                "EndDate": pd.to_datetime(
                    df["end_date"].astype(str), format="%Y%m%d", errors="coerce"
                ).dt.strftime("%Y-%m-%d"),
                "TotalRevenue": pd.to_numeric(df.get("total_revenue"), errors="coerce"),
                "OperateProfit": pd.to_numeric(
                    df.get("operate_profit"), errors="coerce"
                ),
                "NetProfit": pd.to_numeric(df[np_col], errors="coerce")
                if np_col
                else None,
                "UpdateAt": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        con.execute("DELETE FROM IncomeData")
        con.register("tmp_income", out)
        con.execute("""
            INSERT INTO IncomeData
            SELECT
                CAST(Symbol AS VARCHAR),
                CAST(TSCode AS VARCHAR),
                CAST(AnnDate AS DATE),
                CAST(EndDate AS DATE),
                TotalRevenue,
                OperateProfit,
                NetProfit,
                CAST(UpdateAt AS TIMESTAMP)
            FROM tmp_income
        """)
        print("imported IncomeData rows", len(out))
    else:
        print("skip IncomeData, income.csv missing")

    if fina_path.exists():
        df = read_source_csv(fina_path)
        if df.empty:
            raise PipelineError(
                "financial indicator input is empty; replacement must roll back"
            )
        margin_col = (
            "grossprofit_margin"
            if "grossprofit_margin" in df.columns
            else "gross_margin"
        )
        out = pd.DataFrame(
            {
                "Symbol": df["ts_code"].astype(str).str.split(".").str[0].str.zfill(6),
                "TSCode": df["ts_code"],
                "AnnDate": pd.to_datetime(
                    df["ann_date"].astype(str), format="%Y%m%d", errors="coerce"
                ).dt.strftime("%Y-%m-%d"),
                "EndDate": pd.to_datetime(
                    df["end_date"].astype(str), format="%Y%m%d", errors="coerce"
                ).dt.strftime("%Y-%m-%d"),
                "ROE": pd.to_numeric(df.get("roe"), errors="coerce"),
                "ROA": pd.to_numeric(df.get("roa"), errors="coerce"),
                "GrossMargin": pd.to_numeric(df.get(margin_col), errors="coerce"),
                "UpdateAt": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        con.execute("DELETE FROM FinancialIndicatorData")
        con.register("tmp_fina", out)
        con.execute("""
            INSERT INTO FinancialIndicatorData
            SELECT
                CAST(Symbol AS VARCHAR),
                CAST(TSCode AS VARCHAR),
                CAST(AnnDate AS DATE),
                CAST(EndDate AS DATE),
                ROE,
                ROA,
                GrossMargin,
                CAST(UpdateAt AS TIMESTAMP)
            FROM tmp_fina
        """)
        print("imported FinancialIndicatorData rows", len(out), "using", margin_col)
    else:
        print("skip FinancialIndicatorData, fina_indicator.csv missing")


def import_industry_members(con, fundamentals_dir: Path):
    path = fundamentals_dir / "industry_members.csv"
    if not path.exists():
        print("skip IndustryMemberData, industry_members.csv missing")
        return
    df = read_source_csv(path)
    if df.empty:
        print("skip IndustryMemberData, empty file")
        return
    ensure_legacy_industry_member_table(con)
    out = pd.DataFrame(
        {
            "IndexCode": df.get("index_code"),
            "IndexName": df.get("index_name"),
            "Symbol": df.get("con_code").astype(str).str.split(".").str[0].str.zfill(6),
            "TSCode": df.get("con_code"),
            "InDate": pd.to_datetime(
                df.get("in_date").astype(str), format="%Y%m%d", errors="coerce"
            ).dt.strftime("%Y-%m-%d"),
            "OutDate": pd.to_datetime(
                df.get("out_date").astype(str), format="%Y%m%d", errors="coerce"
            ).dt.strftime("%Y-%m-%d"),
            "IsNew": df.get("is_new"),
            "UpdateAt": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )
    con.execute("DELETE FROM IndustryMemberData")
    con.register("tmp_industry", out)
    con.execute("""
        INSERT INTO IndustryMemberData
        SELECT
            CAST(IndexCode AS VARCHAR),
            CAST(IndexName AS VARCHAR),
            CAST(Symbol AS VARCHAR),
            CAST(TSCode AS VARCHAR),
            CAST(InDate AS DATE),
            CAST(OutDate AS DATE),
            CAST(IsNew AS VARCHAR),
            CAST(UpdateAt AS TIMESTAMP)
        FROM tmp_industry
    """)
    print("imported IndustryMemberData rows", len(out))


def import_industry_tushare_evidence(con, industry_dir: Path):
    ensure_industry_tables(con)

    taxonomy_path = industry_dir / "index_classify_all.csv"
    member_path = industry_dir / "index_member_all.csv"
    daily_path = industry_dir / "sw_daily.csv"

    if taxonomy_path.exists():
        df = read_source_csv(taxonomy_path)
        if not df.empty:
            out = pd.DataFrame(
                {
                    "IndexCode": df["index_code"].astype(str),
                    "IndustryName": df["industry_name"].astype(str),
                    "ParentCode": df["parent_code"].astype(str),
                    "Level": df["level"].astype(str),
                    "IndustryCode": df["industry_code"].astype(str),
                    "IsPub": pd.to_numeric(df.get("is_pub"), errors="coerce")
                    .fillna(0)
                    .astype(int),
                    "Src": df.get("src"),
                    "UpdateAt": pd.to_datetime(
                        df.get("fetched_at"), errors="coerce"
                    ).fillna(pd.Timestamp.now()),
                }
            )
            con.execute("DELETE FROM IndustryTaxonomyData")
            con.register("tmp_industry_taxonomy", out)
            con.execute(
                """
                INSERT INTO IndustryTaxonomyData
                SELECT
                    CAST(IndexCode AS VARCHAR),
                    CAST(IndustryName AS VARCHAR),
                    CAST(ParentCode AS VARCHAR),
                    CAST(Level AS VARCHAR),
                    CAST(IndustryCode AS VARCHAR),
                    CAST(IsPub AS INTEGER),
                    CAST(Src AS VARCHAR),
                    CAST(UpdateAt AS TIMESTAMP)
                FROM tmp_industry_taxonomy
                """
            )
            print("imported IndustryTaxonomyData rows", len(out))
        else:
            print("skip IndustryTaxonomyData, empty file")
    else:
        print("skip IndustryTaxonomyData, index_classify_all.csv missing")

    if member_path.exists():
        df = read_source_csv(member_path)
        if not df.empty:
            out = pd.DataFrame(
                {
                    "L1Code": df["l1_code"].astype(str),
                    "L1Name": df["l1_name"].astype(str),
                    "L2Code": df["l2_code"].astype(str),
                    "L2Name": df["l2_name"].astype(str),
                    "L3Code": df["l3_code"].astype(str),
                    "L3Name": df["l3_name"].astype(str),
                    "Symbol": df["ts_code"]
                    .astype(str)
                    .str.split(".")
                    .str[0]
                    .str.zfill(6),
                    "TSCode": df["ts_code"].astype(str),
                    "InDate": pd.to_datetime(
                        df.get("in_date").astype(str), format="%Y%m%d", errors="coerce"
                    ),
                    "OutDate": pd.to_datetime(
                        df.get("out_date").astype(str), format="%Y%m%d", errors="coerce"
                    ),
                    "IsNew": df.get("is_new").astype(str),
                    "UpdateAt": pd.to_datetime(
                        df.get("fetched_at"), errors="coerce"
                    ).fillna(pd.Timestamp.now()),
                }
            )
            con.execute("DELETE FROM IndustryMemberHistoryData")
            con.register("tmp_industry_member_history", out)
            con.execute(
                """
                INSERT INTO IndustryMemberHistoryData
                SELECT
                    CAST(L1Code AS VARCHAR),
                    CAST(L1Name AS VARCHAR),
                    CAST(L2Code AS VARCHAR),
                    CAST(L2Name AS VARCHAR),
                    CAST(L3Code AS VARCHAR),
                    CAST(L3Name AS VARCHAR),
                    CAST(Symbol AS VARCHAR),
                    CAST(TSCode AS VARCHAR),
                    CAST(InDate AS DATE),
                    CAST(OutDate AS DATE),
                    CAST(IsNew AS VARCHAR),
                    CAST(UpdateAt AS TIMESTAMP)
                FROM tmp_industry_member_history
                """
            )
            print("imported IndustryMemberHistoryData rows", len(out))
        else:
            print("skip IndustryMemberHistoryData, empty file")
    else:
        print("skip IndustryMemberHistoryData, index_member_all.csv missing")

    if daily_path.exists():
        df = read_source_csv(daily_path)
        if not df.empty:
            out = pd.DataFrame(
                {
                    "TSCode": df["ts_code"].astype(str),
                    "TradeDate": pd.to_datetime(df["trade_date"], errors="coerce"),
                    "Name": df["name"].astype(str),
                    "Open": pd.to_numeric(df.get("open"), errors="coerce"),
                    "Low": pd.to_numeric(df.get("low"), errors="coerce"),
                    "High": pd.to_numeric(df.get("high"), errors="coerce"),
                    "Close": pd.to_numeric(df.get("close"), errors="coerce"),
                    "Change": pd.to_numeric(df.get("change"), errors="coerce"),
                    "PctChange": pd.to_numeric(df.get("pct_change"), errors="coerce"),
                    "Volume": pd.to_numeric(df.get("vol"), errors="coerce"),
                    "Amount": pd.to_numeric(df.get("amount"), errors="coerce"),
                    "PE": pd.to_numeric(df.get("pe"), errors="coerce"),
                    "PB": pd.to_numeric(df.get("pb"), errors="coerce"),
                    "FloatMV": pd.to_numeric(df.get("float_mv"), errors="coerce"),
                    "WindowStart": pd.to_datetime(
                        df.get("window_start").astype(str),
                        format="%Y%m%d",
                        errors="coerce",
                    ),
                    "WindowEnd": pd.to_datetime(
                        df.get("window_end").astype(str),
                        format="%Y%m%d",
                        errors="coerce",
                    ),
                    "UpdateAt": pd.to_datetime(
                        df.get("fetched_at"), errors="coerce"
                    ).fillna(pd.Timestamp.now()),
                }
            )
            con.execute("DELETE FROM IndustryDailyData")
            con.register("tmp_industry_daily", out)
            con.execute(
                """
                INSERT INTO IndustryDailyData
                SELECT
                    CAST(TSCode AS VARCHAR),
                    CAST(TradeDate AS DATE),
                    CAST(Name AS VARCHAR),
                    Open,
                    Low,
                    High,
                    Close,
                    Change,
                    PctChange,
                    Volume,
                    Amount,
                    PE,
                    PB,
                    FloatMV,
                    CAST(WindowStart AS DATE),
                    CAST(WindowEnd AS DATE),
                    CAST(UpdateAt AS TIMESTAMP)
                FROM tmp_industry_daily
                """
            )
            print("imported IndustryDailyData rows", len(out))
        else:
            print("skip IndustryDailyData, empty file")
    else:
        print("skip IndustryDailyData, sw_daily.csv missing")


def import_market(con, market_data_dir: Path, limit: int | None = None):
    files = sorted(market_data_dir.glob("*.csv"))
    if limit:
        files = files[:limit]
    else:
        con.execute("DELETE FROM MarketData")
    total = 0
    for idx, path in enumerate(files, start=1):
        df = read_source_csv(path)
        if df.empty:
            continue
        symbol = validate_symbol(path.stem.zfill(6))
        out = pd.DataFrame(
            {
                "TradingDay": pd.to_datetime(df["date"], errors="coerce").dt.strftime(
                    "%Y-%m-%d"
                ),
                "Symbol": symbol,
                "TSCode": None,
                "Open": pd.to_numeric(df.get("open"), errors="coerce"),
                "High": pd.to_numeric(df.get("high"), errors="coerce"),
                "Low": pd.to_numeric(df.get("low"), errors="coerce"),
                "Close": pd.to_numeric(df.get("close"), errors="coerce"),
                "Volume": pd.to_numeric(df.get("volume"), errors="coerce"),
                "Amount": pd.to_numeric(df.get("amount"), errors="coerce"),
                "PctChange": pd.to_numeric(df.get("pct_change"), errors="coerce"),
                "Source": "tushare_compatible_csv",
                "UpdateAt": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        if limit:
            con.execute("DELETE FROM MarketData WHERE Symbol = ?", [symbol])
        con.register("tmp_market", out)
        con.execute("""
            INSERT INTO MarketData
            SELECT
                CAST(TradingDay AS DATE),
                Symbol,
                TSCode,
                Open,
                High,
                Low,
                Close,
                Volume,
                Amount,
                PctChange,
                Source,
                CAST(UpdateAt AS TIMESTAMP)
            FROM tmp_market
        """)
        total += len(out)
        if idx % 100 == 0:
            print("processed market csv", idx)
    if total == 0:
        raise PipelineError(
            "market import has no usable rows; replacement must roll back"
        )
    print("imported MarketData rows", total)


def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Import quant-a50 CSV data into DuckDB"
    )
    add_io_arguments(parser, database=True, replace=True)
    parser.add_argument(
        "--table",
        choices=["market", "fundamental", "financial", "industry", "static", "all"],
        default="market",
    )
    parser.add_argument(
        "--limit", type=positive_int, default=None, help="limit files for testing"
    )
    parser.add_argument(
        "--industry-evidence-dir",
        default=None,
        help="industry evidence directory produced by operations/bin/fetch-industry-data",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None):
    args = parse_args(argv)
    if not execution_guard(args, "import"):
        return 0
    paths = get_paths()
    con = open_database(paths["duckdb_path"])
    transaction_started = False
    try:
        con.execute("BEGIN TRANSACTION")
        transaction_started = True
        initialize_schema(con)
        if args.table in ("static", "all"):
            import_static(con, paths["static_dir"])
        if args.table in ("fundamental", "all"):
            import_fundamentals(con, paths["fundamentals_dir"], limit=args.limit)
        if args.table in ("financial", "all"):
            import_financials(con, paths["fundamentals_dir"])
        if args.table in ("industry", "all"):
            import_industry_members(con, paths["fundamentals_dir"])
            import_industry_tushare_evidence(
                con,
                Path(args.industry_evidence_dir)
                if args.industry_evidence_dir
                else industry_evidence_dir(),
            )
        if args.table in ("market", "all"):
            import_market(con, paths["market_data_dir"], limit=args.limit)
        con.execute("COMMIT")
    except BaseException:
        if transaction_started:
            con.execute("ROLLBACK")
        raise
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    main()
