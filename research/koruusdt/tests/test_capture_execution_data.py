from __future__ import annotations

import datetime as dt
import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "capture_execution_data.py"
SPEC = importlib.util.spec_from_file_location("koruusdt_capture_execution_data", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)  # type: ignore[union-attr]


def test_archive_scope_stops_before_holdout_day():
    dates = list(MODULE.daily_dates())
    assert dates[0] == dt.date(2026, 7, 15)
    assert dates[-1] == dt.date(2026, 8, 23)
    assert dt.date(2026, 8, 24) not in dates
    assert all("2026-08-24" not in MODULE.archive_url(kind, day) for kind in ("aggTrades", "markPriceKlines") for day in dates)


def test_every_rest_url_requires_inclusive_end_before_holdout():
    url = MODULE.bounded_rest_url(
        "aggTrades",
        {"symbol": "KORUUSDT", "startTime": MODULE.REST_START_MS, "endTime": MODULE.REST_END_MS},
    )
    assert f"endTime={MODULE.HOLDOUT_START_MS - 1}" in url
    with pytest.raises(MODULE.CaptureError, match="before holdout"):
        MODULE.bounded_rest_url(
            "aggTrades",
            {"symbol": "KORUUSDT", "startTime": MODULE.REST_START_MS, "endTime": MODULE.HOLDOUT_START_MS},
        )
    with pytest.raises(MODULE.CaptureError, match="must have endTime"):
        MODULE.bounded_rest_url("aggTrades", {"symbol": "KORUUSDT"})


def test_provider_checksum_binds_exact_filename():
    digest = "a" * 64
    assert MODULE.parse_provider_checksum(f"{digest}  file.zip\n".encode(), "file.zip") == "sha256:" + digest
    with pytest.raises(MODULE.CaptureError, match="does not bind"):
        MODULE.parse_provider_checksum(f"{digest}  other.zip\n".encode(), "file.zip")


def test_deterministic_rest_zip_has_standard_member_and_timestamp():
    csv_value = b"agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker\n"
    first = MODULE.deterministic_zip("bounded.csv", csv_value)
    second = MODULE.deterministic_zip("bounded.csv", csv_value)
    assert first == second
    path = Path("bounded.zip")
    import io

    with zipfile.ZipFile(io.BytesIO(first)) as archive:
        assert archive.namelist() == ["bounded.csv"]
        assert archive.getinfo("bounded.csv").date_time == (1980, 1, 1, 0, 0, 0)
        assert archive.read("bounded.csv") == csv_value


def test_rest_mark_validation_requires_exact_660_minute_grid():
    rows = []
    for offset in range(660):
        open_time = MODULE.REST_START_MS + offset * MODULE.MINUTE_MS
        rows.append([open_time, "1", "1", "1", "1", "0", open_time + MODULE.MINUTE_MS - 1, "0", 60, "0", "0", "0"])
    summary = MODULE.validate_rest_mark(rows)
    assert summary["row_count"] == 660
    with pytest.raises(MODULE.CaptureError, match="exact 00:00-11:00"):
        MODULE.validate_rest_mark(rows[:-1])
    rows[-1][0] = MODULE.HOLDOUT_START_MS
    with pytest.raises(MODULE.CaptureError):
        MODULE.validate_rest_mark(rows)


def test_rest_agg_validation_checks_contiguous_aggregate_and_nonoverlapping_raw_ids():
    rows = [
        {"a": 10, "p": "1.0", "q": "2.0", "f": 20, "l": 21, "T": MODULE.REST_START_MS, "m": True},
        {"a": 11, "p": "1.0", "q": "3.0", "f": 22, "l": 25, "T": MODULE.REST_START_MS + 1, "m": False},
    ]
    gaps = []
    assert MODULE.validate_rest_agg(rows, MODULE.REST_START_MS, gaps)["max_raw_trade_id"] == 25
    assert gaps == []
    rows[1]["f"] = 23
    MODULE.validate_rest_agg(rows, MODULE.REST_START_MS, gaps)
    assert gaps[-1]["missing_id_count"] == 1
    rows[1]["f"] = 21
    with pytest.raises(MODULE.CaptureError, match="overlap or regress"):
        MODULE.validate_rest_agg(rows, MODULE.REST_START_MS)


def test_manifest_hash_is_canonical_and_excludes_its_value():
    first = {"b": 2, "a": 1, "manifest_sha256": ""}
    second = {"manifest_sha256": "sha256:ignored", "a": 1, "b": 2}
    assert MODULE.manifest_sha256(first) == MODULE.manifest_sha256(second)
    second["a"] = 3
    assert MODULE.manifest_sha256(first) != MODULE.manifest_sha256(second)


def test_no_retained_koru_aggregate_trade_fixture_is_added():
    fixture_roots = [
        SCRIPT_PATH.parents[2] / "tests" / "fixtures",
        SCRIPT_PATH.parents[2] / "backtest" / "tests" / "fixtures",
    ]
    newly_named = []
    for root in fixture_roots:
        if root.exists():
            newly_named.extend(path for path in root.rglob("*") if "koruusdt-aggtrades-2026" in path.name.lower())
    assert newly_named == []


def test_manifest_file_cover_rejects_extra_missing_duplicate_and_symlink(tmp_path):
    root = tmp_path / "binance_usdm"
    root.mkdir()
    expected = root / "expected.txt"
    expected.write_text("expected", encoding="utf-8")
    manifest = {"files": [{"path": "binance_usdm/expected.txt"}]}
    MODULE.validate_manifest_file_cover(tmp_path, manifest)

    extra = root / "extra.txt"
    extra.write_text("extra", encoding="utf-8")
    with pytest.raises(MODULE.CaptureError, match="file cover mismatch"):
        MODULE.validate_manifest_file_cover(tmp_path, manifest)
    extra.unlink()

    expected.unlink()
    with pytest.raises(MODULE.CaptureError, match="file cover mismatch"):
        MODULE.validate_manifest_file_cover(tmp_path, manifest)
    expected.write_text("expected", encoding="utf-8")

    duplicate = {"files": [*manifest["files"], *manifest["files"]]}
    with pytest.raises(MODULE.CaptureError, match="duplicate file paths"):
        MODULE.validate_manifest_file_cover(tmp_path, duplicate)

    link = root / "link.txt"
    link.symlink_to(expected)
    with pytest.raises(MODULE.CaptureError, match="contains symlink"):
        MODULE.validate_manifest_file_cover(tmp_path, manifest)


def test_checked_manifest_when_present_has_holdout_binding_and_canonical_hash():
    path = SCRIPT_PATH.parent / "data" / MODULE.EXECUTION_MANIFEST_NAME
    if not path.exists():
        pytest.skip("capture has not run yet")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["manifest_sha256"] == MODULE.manifest_sha256(manifest)
    assert manifest["holdout_protection"]["full_2026_08_24_daily_archive_downloaded"] is False
    assert manifest["discovery_interval"]["end_ms_exclusive"] == MODULE.HOLDOUT_START_MS
    assert all("/daily/KORUUSDT" not in item["source_url"] or "2026-08-24" not in item["source_url"] for item in manifest["files"])
