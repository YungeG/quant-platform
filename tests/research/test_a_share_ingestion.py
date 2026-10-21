"""Offline acceptance for local copies. Never access real sources or HTTP."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments.a_share_ingestion import daily, importer, industry, runtime, schema
from experiments.a_share_ingestion.__main__ import main

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "experiments/a_share_ingestion"


def forbid(*args, **kwargs):
    pytest.fail("unapproved dependency/network/data I/O")


@pytest.mark.parametrize(
    "command,extra",
    [
        (
            "daily",
            [
                "--start-date",
                "20240101",
                "--target-date",
                "20240105",
                "--limit",
                "1",
                "--max-requests",
                "2",
            ],
        ),
        (
            "industry",
            [
                "--start-date",
                "20240101",
                "--end-date",
                "20240105",
                "--max-requests",
                "10",
            ],
        ),
        ("init", ["--db", "unused.duckdb"]),
        ("import", ["--db", "unused.duckdb"]),
    ],
)
def test_plan_only_never_imports_dependencies_or_creates_outputs(
    tmp_path, monkeypatch, capsys, command, extra
):
    monkeypatch.setattr(runtime, "dependency", forbid)
    output = tmp_path / "not-created"
    assert main([command, "--data-root", str(output), *extra]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["state"] == "plan_only"
    assert report["source_qualified"] is False
    assert not output.exists()
    assert not Path("unused.duckdb").exists()


@pytest.mark.parametrize("command", ["daily", "industry", "init", "import"])
def test_help_is_offline(command, monkeypatch, capsys):
    monkeypatch.setattr(runtime, "dependency", forbid)
    with pytest.raises(SystemExit) as stop:
        main([command, "--help"])
    assert stop.value.code == 0
    assert "--execute" in capsys.readouterr().out


def test_import_requires_explicit_replacement_before_connect(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr(importer, "open_database", forbid)
    assert (
        main(
            [
                "import",
                "--data-root",
                str(tmp_path),
                "--db",
                str(tmp_path / "x.duckdb"),
                "--execute",
            ]
        )
        == 2
    )
    assert "--replace" in capsys.readouterr().out


def test_own_paths_do_not_use_external_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "read_text", forbid)
    runtime.configure_paths(tmp_path / "owned", tmp_path / "own.duckdb")
    assert runtime.provider_path("market_data_dir") == tmp_path / "owned/market_data"
    assert runtime.provider_path("duckdb_path") == tmp_path / "own.duckdb"
    with pytest.raises(runtime.PipelineError):
        runtime.provider_path("foreign")


def test_token_is_env_only_and_missing_token_precedes_sdk_import(monkeypatch):
    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)
    monkeypatch.setattr(runtime, "dependency", forbid)
    with pytest.raises(runtime.PipelineError, match="TUSHARE_TOKEN"):
        runtime.init_tushare(1)


@pytest.mark.skipif(
    importlib.util.find_spec("tushare") is None, reason="local SDK required"
)
def test_real_sdk_initialization_is_offline_and_does_not_write_home(
    tmp_path, monkeypatch
):
    requests = runtime.dependency("requests")
    monkeypatch.setattr(requests, "post", forbid)
    monkeypatch.setattr(requests.sessions.Session, "request", forbid)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("TUSHARE_TOKEN", "synthetic-offline-token-not-real")
    api = runtime.init_tushare(1)
    assert api.attempts == 0
    assert callable(api.api.daily)
    assert list(tmp_path.iterdir()) == []


def test_sdk_token_constructor_does_not_persist_home_credentials(monkeypatch):
    calls = []
    api = SimpleNamespace(daily=lambda **kwargs: [])
    sdk = SimpleNamespace(
        pro_api=lambda **kwargs: calls.append(kwargs) or api, set_token=forbid
    )
    monkeypatch.setenv("TUSHARE_TOKEN", "synthetic-not-a-real-token")
    monkeypatch.setattr(runtime, "dependency", lambda name: sdk)
    assert runtime.init_tushare(1).daily(ts_code="600000.SH") == []
    assert calls == [{"token": "synthetic-not-a-real-token"}]


def test_api_budget_is_shared_and_failed_calls_are_not_refunded():
    def fail(**kwargs):
        raise ValueError("synthetic")

    api = runtime.BoundedAPI(SimpleNamespace(daily=fail, stock_basic=list), 1)
    with pytest.raises(ValueError):
        api.daily()
    assert api.attempts == 1
    with pytest.raises(runtime.PipelineError, match="exhausted"):
        api.stock_basic()
    assert api.attempts == 1


@pytest.mark.parametrize("invalid", [True, 0, -1])
def test_bad_request_budget_rejected(invalid):
    with pytest.raises(runtime.PipelineError):
        runtime.BoundedAPI(SimpleNamespace(), invalid)


@pytest.mark.parametrize("invalid", ["../x", "600000/", "1234567", "token", ""])
def test_csv_symbol_cannot_escape_directory(invalid):
    with pytest.raises(runtime.PipelineError):
        runtime.validate_symbol(invalid)


def test_original_member_modes_and_half_month_windows():
    assert industry.normalize_member_is_new_modes("Y;N,Y") == ["Y", "N"]
    with pytest.raises(ValueError):
        industry.normalize_member_is_new_modes("Z")
    assert industry.month_windows("20240110", "20240202") == [
        ("20240110", "20240115"),
        ("20240116", "20240131"),
        ("20240201", "20240202"),
    ]
    assert industry.month_windows("20240229", "20240229") == [("20240229", "20240229")]
    with pytest.raises(ValueError):
        industry.month_windows("20240202", "20240101")


def test_daily_progress_path_is_project_local_and_defined(tmp_path):
    root = tmp_path / "owned"
    daily.configure(root)
    daily.write_run_state({"synthetic": True})
    assert json.loads((root / "download_progress_tushare.json").read_text()) == {
        "synthetic": True
    }
    assert daily.CSV_CACHE_DIR == root / "market_data"


def test_date_tokens_and_local_clock_have_explicit_semantics():
    assert runtime.date_text("2024-02-29") == "20240229"
    assert runtime.date_text("20240229") == "20240229"
    assert runtime.local_now().tzinfo is not None
    for value in ("20240230", "2024-W01-1", "today"):
        with pytest.raises(argparse.ArgumentTypeError):
            runtime.date_text(value)


def test_reversed_daily_plan_refused_before_dependency_or_directory_io(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr(runtime, "dependency", forbid)
    output = tmp_path / "never-created"
    assert (
        main(
            [
                "daily",
                "--data-root",
                str(output),
                "--start-date",
                "20240202",
                "--target-date",
                "20240101",
                "--limit",
                "1",
                "--max-requests",
                "2",
            ]
        )
        == 2
    )
    assert "must not exceed" in capsys.readouterr().out
    assert not output.exists()


def test_import_nonpositive_limit_rejected_before_connect(tmp_path, monkeypatch):
    monkeypatch.setattr(importer, "open_database", forbid)
    with pytest.raises(SystemExit) as stop:
        importer.main([*import_args(tmp_path), "--limit", "0"])
    assert stop.value.code == 2


def test_owned_database_settings_do_not_use_external_environment(tmp_path, monkeypatch):
    calls = []
    driver = SimpleNamespace(
        __version__="1.5.4",
        connect=lambda *args, **kwargs: calls.append((args, kwargs)) or "fake",
    )
    monkeypatch.setattr(runtime, "dependency", lambda name: driver)
    assert runtime.open_database(tmp_path / "own.duckdb") == "fake"
    assert calls[0][0] == (str(tmp_path / "own.duckdb"),)
    assert calls[0][1]["config"]["threads"] == "4"
    assert calls[0][1]["config"]["memory_limit"] == "2GiB"
    assert calls[0][1]["config"]["enable_external_access"] == "false"


def test_industry_rate_retry_cannot_exceed_shared_logical_cap(monkeypatch):
    calls = []
    sleeps = []

    def fail(**kwargs):
        calls.append(True)
        raise ValueError("频率超限 synthetic")

    api = runtime.BoundedAPI(SimpleNamespace(daily=fail), 1)
    monkeypatch.setattr(industry.time, "sleep", sleeps.append)
    with pytest.raises(runtime.PipelineError, match="exhausted"):
        industry.query_with_backoff(api.daily, sleep_seconds=0)
    assert calls == [True]
    assert sleeps == [60.0]
    assert api.attempts == 1


def test_atomic_csv_preserves_previous_file_on_failure(tmp_path):
    destination = tmp_path / "600000.csv"
    destination.write_text("old-synthetic-content")

    class BrokenFrame:
        def to_csv(self, path, index):
            path.write_text("partial-synthetic-content")
            raise OSError("synthetic disk failure")

    with pytest.raises(OSError):
        runtime.atomic_csv(BrokenFrame(), destination)
    assert destination.read_text() == "old-synthetic-content"
    assert list(tmp_path.iterdir()) == [destination]


def test_atomic_csv_success(tmp_path):
    class Frame:
        def to_csv(self, path, index):
            assert index is False
            path.write_text("synthetic-complete")

    destination = tmp_path / "out.csv"
    runtime.atomic_csv(Frame(), destination)
    assert destination.read_text() == "synthetic-complete"
    assert list(tmp_path.iterdir()) == [destination]


@pytest.mark.skipif(
    importlib.util.find_spec("pandas") is None, reason="local pandas required"
)
def test_source_csv_preserves_nullable_date_tokens_and_leading_zero_ids(tmp_path):
    path = tmp_path / "synthetic-members.csv"
    path.write_text("symbol,out_date\n000001,20191231\n000002,\n")
    frame = importer.read_source_csv(path)
    assert frame.iloc[0]["symbol"] == "000001"
    assert frame.iloc[1]["symbol"] == "000002"
    assert frame.iloc[0]["out_date"] == "20191231"
    assert runtime.dependency("pandas").isna(frame.iloc[1]["out_date"])


@pytest.mark.skipif(
    importlib.util.find_spec("duckdb") is None, reason="local DuckDB required"
)
def test_fresh_initialization_covers_industry_and_is_idempotent(tmp_path):
    db = tmp_path / "synthetic-init.duckdb"
    args = ["--data-root", str(tmp_path), "--db", str(db), "--execute"]
    assert schema.main(args) == 0
    driver = runtime.dependency("duckdb")
    con = driver.connect(str(db))
    try:
        tables = {row[0] for row in con.execute("SHOW TABLES").fetchall()}
        assert {
            "MarketData",
            "IndustryMemberHistoryData",
            "IndustryTaxonomyData",
            "IndustryDailyData",
        } <= tables
        con.execute(
            "INSERT INTO MarketData (TradingDay, Symbol) VALUES ('2024-01-02', '000001')"
        )
    finally:
        con.close()
    assert schema.main(args) == 0
    con = driver.connect(str(db), read_only=True)
    try:
        assert con.execute("SELECT COUNT(*) FROM MarketData").fetchone() == (1,)
    finally:
        con.close()


class Connection:
    def __init__(self, fail_begin=False):
        self.statements = []
        self.closed = False
        self.fail_begin = fail_begin

    def execute(self, statement):
        self.statements.append(statement)
        if statement == "BEGIN TRANSACTION" and self.fail_begin:
            raise ValueError("synthetic begin failure")
        return self

    def close(self):
        self.closed = True


def import_args(tmp_path):
    return [
        "--data-root",
        str(tmp_path),
        "--db",
        str(tmp_path / "test.duckdb"),
        "--execute",
        "--replace",
    ]


def test_transaction_rolls_back_and_closes_on_import_failure(tmp_path, monkeypatch):
    connection = Connection()
    monkeypatch.setattr(importer, "open_database", lambda path: connection)

    def fail(*args, **kwargs):
        raise ValueError("synthetic row failure")

    monkeypatch.setattr(importer, "import_market", fail)
    with pytest.raises(ValueError):
        importer.main(import_args(tmp_path))
    assert connection.statements[0] == "BEGIN TRANSACTION"
    assert connection.statements[-1] == "ROLLBACK"
    assert "COMMIT" not in connection.statements
    assert connection.closed


def test_transaction_commits_and_closes_once(tmp_path, monkeypatch):
    connection = Connection()
    monkeypatch.setattr(importer, "open_database", lambda path: connection)
    monkeypatch.setattr(importer, "import_market", lambda *args, **kwargs: None)
    assert importer.main(import_args(tmp_path)) == 0
    assert connection.statements[-1] == "COMMIT"
    assert "ROLLBACK" not in connection.statements
    assert connection.closed


def test_failed_begin_does_not_issue_spurious_rollback(tmp_path, monkeypatch):
    connection = Connection(fail_begin=True)
    monkeypatch.setattr(importer, "open_database", lambda path: connection)
    with pytest.raises(ValueError):
        importer.main(import_args(tmp_path))
    assert connection.statements == ["BEGIN TRANSACTION"]
    assert connection.closed


def test_empty_market_source_rolls_back_without_pandas_or_live_data(
    tmp_path, monkeypatch
):
    connection = Connection()
    monkeypatch.setattr(runtime, "dependency", forbid)
    monkeypatch.setattr(importer, "open_database", lambda path: connection)
    with pytest.raises(runtime.PipelineError, match="no usable rows"):
        importer.main(import_args(tmp_path))
    assert "DELETE FROM MarketData" in connection.statements
    assert connection.statements[-1] == "ROLLBACK"
    assert connection.closed


def test_copied_source_marker_schema_and_unit_mapping_preserved():
    tree = ast.parse((PACKAGE / "importer.py").read_text())
    assignments = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if (
                    isinstance(key, ast.Constant)
                    and key.value == "Source"
                    and isinstance(value, ast.Constant)
                ):
                    assignments.append(value.value)
    assert len(assignments) == 1
    assert (
        hashlib.sha256(assignments[0].encode()).hexdigest()
        == "81fb5999a6f3e1cc03bbf8196dd7a4ba6ba9b25cda02c1b4e147b70a29bfe6bd"
    )
    daily_tree = ast.parse((PACKAGE / "daily.py").read_text())
    daily_function = next(
        node
        for node in daily_tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "fetch_daily_data"
    )
    factors = [
        node.right.value
        for node in ast.walk(daily_function)
        if isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Mult)
        and isinstance(node.right, ast.Constant)
    ]
    assert factors == [100, 1000]
    assert "Source VARCHAR" in schema.DDL[0]
    assert "UpdateAt TIMESTAMP" in schema.DDL[0]


def test_no_external_project_imports_or_runtime_paths():
    for path in PACKAGE.glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("operations")
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert "/home/ygguo/agent-projs/quant-claude" not in node.value
                assert "/srv/bcache-8t/" not in node.value


def test_fresh_process_imports_are_side_effect_free_without_dependencies(tmp_path):
    environment = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE="1")
    environment.pop("TUSHARE_TOKEN", None)
    code = "import sys; from experiments.a_share_ingestion import daily,industry,importer,schema; assert not any(x in sys.modules for x in ('pandas','duckdb','tushare')); print('offline-import-ok')"
    result = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "offline-import-ok"
    assert list(tmp_path.iterdir()) == []


@pytest.mark.skipif(
    importlib.util.find_spec("pandas") is None,
    reason="local pandas not installed; transform execution unverified",
)
def test_real_pandas_daily_unit_mapping():
    pd = runtime.dependency("pandas")
    api = SimpleNamespace(
        daily=lambda **kwargs: pd.DataFrame(
            [
                {
                    "ts_code": "600000.SH",
                    "trade_date": "20240102",
                    "open": 10,
                    "high": 11,
                    "low": 9,
                    "close": 10.5,
                    "vol": 12.5,
                    "amount": 2.5,
                    "pct_chg": 1.2,
                }
            ]
        )
    )
    frame = daily.fetch_daily_data(api, "600000.SH", "20240101", "20240105")
    assert frame.iloc[0]["volume"] == 1250
    assert frame.iloc[0]["amount"] == 2500


@pytest.mark.skipif(
    any(importlib.util.find_spec(name) is None for name in ("pandas", "duckdb")),
    reason="local pandas/DuckDB not installed; engine roundtrip unverified",
)
def test_real_engine_roundtrip_and_rollback(tmp_path):
    market = tmp_path / "market_data"
    market.mkdir()
    csv_path = market / "600000.csv"
    csv_path.write_text(
        "date,open,high,low,close,volume,amount,pct_change\n2024-01-02,10,11,9,10.5,1250,2500,1.2\n"
    )
    assert importer.main(import_args(tmp_path)) == 0
    driver = runtime.dependency("duckdb")
    con = driver.connect(str(tmp_path / "test.duckdb"), read_only=True)
    assert con.execute("SELECT Symbol, Volume, Amount FROM MarketData").fetchall() == [
        ("600000", 1250.0, 2500.0)
    ]
    con.close()
    csv_path.unlink()
    with pytest.raises(runtime.PipelineError):
        importer.main(import_args(tmp_path))
    con = driver.connect(str(tmp_path / "test.duckdb"), read_only=True)
    assert con.execute("SELECT COUNT(*) FROM MarketData").fetchone() == (1,)
    con.close()


@pytest.mark.skipif(
    any(importlib.util.find_spec(name) is None for name in ("pandas", "duckdb")),
    reason="local libraries required for the synthetic daily pipeline",
)
def test_synthetic_daily_collection_csv_and_engine_pipeline(tmp_path, monkeypatch):
    pd = runtime.dependency("pandas")
    calls = []

    def stock_basic(**kwargs):
        calls.append(("stock_basic", kwargs))
        return pd.DataFrame(
            [
                {
                    "ts_code": "600000.SH",
                    "symbol": "600000",
                    "name": "SYNTHETIC",
                    "market": "主板",
                    "list_date": "20000101",
                }
            ]
        )

    def fetch_daily(**kwargs):
        calls.append(("daily", kwargs))
        return pd.DataFrame(
            [
                {
                    "ts_code": "600000.SH",
                    "trade_date": "20240102",
                    "open": 10,
                    "high": 11,
                    "low": 9,
                    "close": 10.5,
                    "vol": 12.5,
                    "amount": 2.5,
                    "pct_chg": 1.2,
                },
                {
                    "ts_code": "600000.SH",
                    "trade_date": "20240103",
                    "open": 11,
                    "high": 12,
                    "low": 10,
                    "close": 11.5,
                    "vol": 15,
                    "amount": 3,
                    "pct_chg": 2.1,
                },
            ]
        )

    api = runtime.BoundedAPI(
        SimpleNamespace(stock_basic=stock_basic, daily=fetch_daily), 2
    )
    monkeypatch.setattr(daily, "init_tushare", lambda budget: api)
    monkeypatch.setattr(daily.time, "sleep", lambda seconds: None)
    output = tmp_path / "daily-owned"
    assert (
        main(
            [
                "daily",
                "--data-root",
                str(output),
                "--start-date",
                "20240101",
                "--target-date",
                "20240105",
                "--limit",
                "1",
                "--max-requests",
                "2",
                "--execute",
            ]
        )
        == 0
    )
    assert api.attempts == 2
    assert [name for name, _ in calls] == ["stock_basic", "daily"]
    progress = json.loads((output / "download_progress_tushare.json").read_text())
    assert progress["success_count"] == 1 and progress["total"] == 1
    assert (output / "market_data/600000.csv").is_file()
    db = tmp_path / "synthetic-daily.duckdb"
    assert (
        main(
            [
                "import",
                "--data-root",
                str(output),
                "--db",
                str(db),
                "--table",
                "market",
                "--execute",
                "--replace",
            ]
        )
        == 0
    )
    driver = runtime.dependency("duckdb")
    con = driver.connect(str(db), read_only=True)
    try:
        assert con.execute(
            "SELECT Symbol, Volume, Amount FROM MarketData ORDER BY TradingDay"
        ).fetchall() == [("600000", 1250.0, 2500.0), ("600000", 1500.0, 3000.0)]
        assert con.execute(
            "SELECT COUNT(*) FROM MarketData WHERE UpdateAt IS NOT NULL"
        ).fetchone() == (2,)
    finally:
        con.close()


@pytest.mark.skipif(
    any(importlib.util.find_spec(name) is None for name in ("pandas", "duckdb")),
    reason="local libraries required for the synthetic industry pipeline",
)
def test_synthetic_industry_collection_csv_manifest_and_engine_pipeline(
    tmp_path, monkeypatch
):
    pd = runtime.dependency("pandas")
    calls = []

    def classify(**kwargs):
        calls.append("index_classify")
        return pd.DataFrame(
            [
                {
                    "index_code": "850101",
                    "industry_name": "SYNTHETIC",
                    "parent_code": "850100",
                    "level": "L3",
                    "industry_code": "850101",
                    "is_pub": 1,
                    "src": "SW2021",
                }
            ]
        )

    def members(**kwargs):
        calls.append("index_member_all")
        mode = kwargs["is_new"]
        return pd.DataFrame(
            [
                {
                    "l1_code": "801150.SI",
                    "l1_name": "SYNTHETIC",
                    "l2_code": "850100.SI",
                    "l2_name": "SYNTHETIC",
                    "l3_code": "850101.SI",
                    "l3_name": "SYNTHETIC",
                    "ts_code": "600000.SH",
                    "name": "SYNTHETIC",
                    "in_date": "20200101" if mode == "Y" else "20100101",
                    "out_date": None if mode == "Y" else "20191231",
                    "is_new": mode,
                }
            ]
        )

    def industry_daily(**kwargs):
        calls.append("sw_daily")
        return pd.DataFrame(
            [
                {
                    "ts_code": "801150.SI",
                    "trade_date": "20240102",
                    "name": "SYNTHETIC",
                    "open": 10,
                    "low": 9,
                    "high": 11,
                    "close": 10.5,
                    "change": 0.5,
                    "pct_change": 1.2,
                    "vol": 12.5,
                    "amount": 2.5,
                    "pe": 10,
                    "pb": 1,
                    "float_mv": 100,
                }
            ]
        )

    api = runtime.BoundedAPI(
        SimpleNamespace(
            index_classify=classify, index_member_all=members, sw_daily=industry_daily
        ),
        4,
    )
    monkeypatch.setattr(industry, "init_tushare", lambda budget: api)
    output = tmp_path / "industry-owned"
    assert (
        main(
            [
                "industry",
                "--data-root",
                str(output),
                "--start-date",
                "20240101",
                "--end-date",
                "20240105",
                "--max-requests",
                "4",
                "--sleep-seconds",
                "0",
                "--execute",
                "--json",
            ]
        )
        == 0
    )
    assert calls == [
        "index_classify",
        "index_member_all",
        "index_member_all",
        "sw_daily",
    ]
    assert api.attempts == 4
    manifest = json.loads((output / "industry/manifest.json").read_text())
    assert manifest["rows"]["member_current"] == 1
    assert manifest["rows"]["member_historical"] == 1
    assert manifest["rows"]["daily"] == 1
    db = tmp_path / "synthetic-industry.duckdb"
    assert (
        main(
            [
                "import",
                "--data-root",
                str(output),
                "--db",
                str(db),
                "--table",
                "industry",
                "--execute",
                "--replace",
            ]
        )
        == 0
    )
    driver = runtime.dependency("duckdb")
    con = driver.connect(str(db), read_only=True)
    try:
        assert con.execute("SELECT COUNT(*) FROM IndustryTaxonomyData").fetchone() == (
            1,
        )
        assert con.execute(
            "SELECT COUNT(*) FROM IndustryMemberHistoryData"
        ).fetchone() == (2,)
        assert con.execute("SELECT COUNT(*) FROM IndustryDailyData").fetchone() == (1,)
        assert con.execute(
            "SELECT IsNew FROM IndustryMemberHistoryData ORDER BY IsNew"
        ).fetchall() == [("N",), ("Y",)]
        assert con.execute(
            "SELECT COUNT(*) FROM IndustryMemberHistoryData WHERE OutDate IS NULL"
        ).fetchone() == (1,)
        assert (
            str(
                con.execute(
                    "SELECT OutDate FROM IndustryMemberHistoryData WHERE IsNew = 'N'"
                ).fetchone()[0]
            )
            == "2019-12-31"
        )
    finally:
        con.close()
