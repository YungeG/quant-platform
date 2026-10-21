"""Local copy of the inspected base schema; database path is always explicit."""

from __future__ import annotations

import argparse

from .runtime import add_io_arguments, execution_guard, open_database

DDL = [
    """
    CREATE TABLE IF NOT EXISTS MarketData (
        TradingDay DATE,
        Symbol VARCHAR,
        TSCode VARCHAR,
        Open DOUBLE,
        High DOUBLE,
        Low DOUBLE,
        Close DOUBLE,
        Volume DOUBLE,
        Amount DOUBLE,
        PctChange DOUBLE,
        Source VARCHAR,
        UpdateAt TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS FundamentalData (
        TradingDay DATE,
        Symbol VARCHAR,
        TSCode VARCHAR,
        Close DOUBLE,
        TurnoverRate DOUBLE,
        TurnoverRateF DOUBLE,
        VolumeRatio DOUBLE,
        PE DOUBLE,
        PETTM DOUBLE,
        PB DOUBLE,
        PS DOUBLE,
        PSTTM DOUBLE,
        DVRatio DOUBLE,
        DVTTM DOUBLE,
        TotalShare DOUBLE,
        FloatShare DOUBLE,
        FreeShare DOUBLE,
        TotalMV DOUBLE,
        CircMV DOUBLE,
        UpdateAt TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS StaticData (
        Symbol VARCHAR,
        TSCode VARCHAR,
        Name VARCHAR,
        Area VARCHAR,
        Industry VARCHAR,
        Market VARCHAR,
        ListDate DATE,
        IsActive BOOLEAN,
        UpdateAt TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS FinancialIndicatorData (
        Symbol VARCHAR,
        TSCode VARCHAR,
        AnnDate DATE,
        EndDate DATE,
        ROE DOUBLE,
        ROA DOUBLE,
        GrossMargin DOUBLE,
        UpdateAt TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS IncomeData (
        Symbol VARCHAR,
        TSCode VARCHAR,
        AnnDate DATE,
        EndDate DATE,
        TotalRevenue DOUBLE,
        OperateProfit DOUBLE,
        NetProfit DOUBLE,
        UpdateAt TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS IndustryMemberData (
        IndexCode VARCHAR,
        IndexName VARCHAR,
        Symbol VARCHAR,
        TSCode VARCHAR,
        InDate DATE,
        OutDate DATE,
        IsNew VARCHAR,
        UpdateAt TIMESTAMP
    );
    """,
]


def ensure_industry_tables(con):
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS IndustryTaxonomyData (
            IndexCode VARCHAR,
            IndustryName VARCHAR,
            ParentCode VARCHAR,
            Level VARCHAR,
            IndustryCode VARCHAR,
            IsPub INTEGER,
            Src VARCHAR,
            UpdateAt TIMESTAMP
        )
        """
    )


def ensure_legacy_industry_member_table(con):
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS IndustryMemberData (
            IndexCode VARCHAR,
            IndexName VARCHAR,
            Symbol VARCHAR,
            TSCode VARCHAR,
            InDate DATE,
            OutDate DATE,
            IsNew VARCHAR,
            UpdateAt TIMESTAMP
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS IndustryMemberHistoryData (
            L1Code VARCHAR,
            L1Name VARCHAR,
            L2Code VARCHAR,
            L2Name VARCHAR,
            L3Code VARCHAR,
            L3Name VARCHAR,
            Symbol VARCHAR,
            TSCode VARCHAR,
            InDate DATE,
            OutDate DATE,
            IsNew VARCHAR,
            UpdateAt TIMESTAMP
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS IndustryDailyData (
            TSCode VARCHAR,
            TradeDate DATE,
            Name VARCHAR,
            Open DOUBLE,
            Low DOUBLE,
            High DOUBLE,
            Close DOUBLE,
            Change DOUBLE,
            PctChange DOUBLE,
            Volume DOUBLE,
            Amount DOUBLE,
            PE DOUBLE,
            PB DOUBLE,
            FloatMV DOUBLE,
            WindowStart DATE,
            WindowEnd DATE,
            UpdateAt TIMESTAMP
        )
        """
    )


def initialize_schema(connection):
    for statement in DDL:
        connection.execute(statement)
    ensure_industry_tables(connection)
    ensure_legacy_industry_member_table(connection)


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Initialize project-local ingestion tables"
    )
    add_io_arguments(parser, database=True)
    args = parser.parse_args(argv)
    if not execution_guard(args, "init"):
        return 0
    args.db.parent.mkdir(parents=True, exist_ok=True)
    connection = open_database(args.db)
    transaction_started = False
    try:
        connection.execute("BEGIN TRANSACTION")
        transaction_started = True
        initialize_schema(connection)
        connection.execute("COMMIT")
    except BaseException:
        if transaction_started:
            connection.execute("ROLLBACK")
        raise
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    main()
