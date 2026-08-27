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


def test_price_bar_archive_paths_are_provider_named_and_scoped():
    day = dt.date(2026, 7, 15)
    assert MODULE.price_archive_url("mark", day).endswith(
        "/markPriceKlines/KORUUSDT/1h/KORUUSDT-1h-2026-07-15.zip"
    )
    assert MODULE.price_archive_url("index", day).endswith(
        "/indexPriceKlines/KORUUSDT/1h/KORUUSDT-1h-2026-07-15.zip"
    )
    assert MODULE.price_archive_path(Path("data"), "mark", day) == Path(
        "data/binance_usdm/priceBars/mark/1h/daily/KORUUSDT-1h-2026-07-15.zip"
    )
    with pytest.raises(ValueError, match="unsupported price-bar source"):
        MODULE.price_archive_url("last", day)


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


def test_derived_price_validation_requires_exact_matching_1h_grid():
    rows = []
    for offset in range(11):
        open_time = MODULE.REST_START_MS + offset * MODULE.HOUR_MS
        rows.append(
            [
                MODULE.iso_ms(open_time),
                "1.00000000",
                "1.00000000",
                "1.00000000",
                "1.00000000",
                MODULE.iso_ms(open_time + MODULE.HOUR_MS - 1),
                "0.0",
            ]
        )
    summary = MODULE.validate_derived_price_rows(rows, "mark")
    assert summary["row_count"] == 11
    assert summary["timestamps_ms"] == [
        MODULE.REST_START_MS + offset * MODULE.HOUR_MS for offset in range(11)
    ]
    with pytest.raises(MODULE.CaptureError, match="exact 00:00-11:00"):
        MODULE.validate_derived_price_rows(rows[:-1], "mark")
    rows[-1][0] = MODULE.iso_ms(MODULE.HOLDOUT_START_MS)
    with pytest.raises(MODULE.CaptureError, match="holdout|exact bounded"):
        MODULE.validate_derived_price_rows(rows, "mark")


def test_accepted_funding_capture_is_exact_regular_cover_and_excludes_holdout():
    rows, response_bytes, receipt_bytes, receipt, binding = (
        MODULE._accepted_funding_source()
    )
    summary = MODULE.validate_funding_rows(rows, exact_cover=True)
    assert len(rows) == 120
    assert {row["rateType"] for row in rows} == {"Regular"}
    assert summary["regular_rate_type_count"] == 120
    assert summary["special_rate_type_count"] == 0
    assert summary["missing_rate_type_count"] == 0
    assert summary["min_time_ms"] == MODULE.ACCEPTED_FUNDING_FIRST_MS
    assert summary["max_time_ms"] == MODULE.ACCEPTED_FUNDING_LAST_MS
    assert summary["max_time_ms"] < MODULE.HOLDOUT_START_MS
    assert receipt["request"] == {
        "end_time_milliseconds": MODULE.REST_END_MS,
        "limit": 1000,
        "start_time_milliseconds": MODULE.AUTHORITY_START_MS,
        "symbol": "KORUUSDT",
    }
    assert MODULE.sha256_bytes(response_bytes) == binding["response_sha256"]
    assert MODULE.sha256_bytes(receipt_bytes) == binding["receipt_sha256"]


def test_offline_funding_mirror_is_byte_equal_and_rejects_type_or_time_tamper(
    tmp_path,
):
    rows, files, _ = MODULE.mirror_accepted_funding_capture(tmp_path)
    source_dir = MODULE.ROOT / MODULE.ACCEPTED_FUNDING_REPO_DIR
    for item in files:
        assert item["path"].read_bytes() == (source_dir / item["path"].name).read_bytes()
        assert item["status"] == MODULE.ACCEPTED_FUNDING_STATUS

    missing = [dict(row) for row in rows]
    missing[0].pop("rateType")
    with pytest.raises(MODULE.CaptureError, match="exact 120-row Regular cover"):
        MODULE.validate_funding_rows(missing, exact_cover=True)
    special = [dict(row) for row in rows]
    special[0]["rateType"] = "Special"
    with pytest.raises(MODULE.CaptureError, match="exact 120-row Regular cover"):
        MODULE.validate_funding_rows(special, exact_cover=True)
    holdout = [dict(rows[0], fundingTime=MODULE.HOLDOUT_START_MS)]
    with pytest.raises(MODULE.CaptureError, match="authority interval"):
        MODULE.validate_funding_rows(holdout)


def test_price_derivatives_are_exact_deterministic_frozen_csv_subsets(tmp_path):
    rows = {
        source: [
            [
                MODULE.iso_ms(MODULE.REST_START_MS + offset * MODULE.HOUR_MS),
                "1.00000000",
                "2.00000000",
                "0.50000000",
                "1.50000000",
                MODULE.iso_ms(
                    MODULE.REST_START_MS
                    + (offset + 1) * MODULE.HOUR_MS
                    - 1
                ),
                "0.0",
            ]
            for offset in range(11)
        ]
        for source in MODULE.PRICE_BAR_SOURCES
    }
    bindings = {
        source: {"frozen_source_metadata": {"endpoint": f"https://example/{source}"}}
        for source in MODULE.PRICE_BAR_SOURCES
    }
    first = MODULE.write_price_bar_derivatives(tmp_path, rows, bindings)
    hashes = {item["path"]: MODULE.sha256_path(item["path"]) for item in first}
    second = MODULE.write_price_bar_derivatives(tmp_path, rows, bindings)
    assert hashes == {item["path"]: MODULE.sha256_path(item["path"]) for item in second}
    for source in MODULE.PRICE_BAR_SOURCES:
        csv_path = next(
            item["path"]
            for item in first
            if f"/priceBars/{source}/" in item["path"].as_posix()
            and item["path"].suffix == ".csv"
        )
        assert MODULE._load_bound_csv(csv_path, MODULE.FROZEN_PRICE_HEADER) == rows[source]
    assert {item["status"] for item in first} == {MODULE.DERIVED_STATUS}


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


def test_checksum_validation_detects_tamper(tmp_path):
    archive = tmp_path / "provider.zip"
    archive.write_bytes(b"provider bytes")
    digest = MODULE.sha256_path(archive).removeprefix("sha256:")
    checksum = tmp_path / "provider.zip.CHECKSUM"
    checksum.write_text(f"{digest}  provider.zip\n", encoding="utf-8")
    assert MODULE._validate_checksum_file(archive, checksum) == f"sha256:{digest}"
    archive.write_bytes(b"tampered")
    with pytest.raises(MODULE.CaptureError, match="checksum mismatch"):
        MODULE._validate_checksum_file(archive, checksum)


def test_offline_archive_resume_validates_all_existing_without_network(tmp_path, monkeypatch):
    day = dt.date(2026, 7, 15)
    monkeypatch.setattr(MODULE, "daily_dates", lambda: iter((day,)))
    paths = [
        *(MODULE.archive_path(tmp_path, kind, day) for kind in ("aggTrades", "markPriceKlines")),
        *(MODULE.price_archive_path(tmp_path, source, day) for source in MODULE.PRICE_BAR_SOURCES),
    ]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(path.name.encode())
        digest = MODULE.sha256_path(path).removeprefix("sha256:")
        path.with_name(path.name + ".CHECKSUM").write_text(
            f"{digest}  {path.name}\n", encoding="utf-8"
        )
    monkeypatch.setattr(
        MODULE,
        "fetch_bytes",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network used")),
    )
    statuses = MODULE.capture_archives(tmp_path, offline=True)
    assert len(statuses) == 8
    assert set(statuses.values()) == {"already_verified"}


def test_archive_metadata_refresh_heads_exact_retained_allowlist_and_rejects_tamper(
    tmp_path, monkeypatch
):
    day = dt.date(2026, 7, 15)
    monkeypatch.setattr(MODULE, "daily_dates", lambda: iter((day,)))
    specs = MODULE.official_archive_metadata_specs(tmp_path)
    expected = {url: path for path, url in specs}
    for path in expected.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(path.name.encode("utf-8"))

    calls = []

    class Response:
        status = 200

        def __init__(self, url, size):
            self.url = url
            self.headers = {
                "Content-Length": str(size),
                "Last-Modified": "Tue, 25 Aug 2026 12:34:56 GMT",
            }
            if not url.endswith(".CHECKSUM"):
                self.headers["ETag"] = '"provider-etag"'

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def geturl(self):
            return self.url

        def getcode(self):
            return self.status

    def fake_request(url, *, range_start=None, method="GET"):
        assert range_start is None
        assert method == "HEAD"
        assert url in expected
        calls.append(url)
        return Response(url, expected[url].stat().st_size)

    monkeypatch.setattr(MODULE, "_request", fake_request)
    receipt = MODULE.refresh_archive_metadata(tmp_path)
    assert calls == [url for _, url in specs]
    assert len(calls) == 6
    assert all("2026-08-24" not in url for url in calls)
    assert all("/1m/" not in url for url in calls)
    assert receipt["receipt_sha256"] == MODULE.archive_metadata_receipt_sha256(
        receipt
    )
    assert {
        item["etag"] for item in receipt["files"] if not item["url"].endswith(".CHECKSUM")
    } == {'"provider-etag"'}
    assert {
        item["provider_last_modified_utc"] for item in receipt["files"]
    } == {"2026-08-25T12:34:56Z"}
    assert {
        item["provider_last_modified_ns"] for item in receipt["files"]
    } == {1787661296000000000}

    receipt["files"][0]["url"] += "?tampered=1"
    receipt["receipt_sha256"] = MODULE.archive_metadata_receipt_sha256(receipt)
    (tmp_path / MODULE.ARCHIVE_METADATA_RECEIPT_NAME).write_bytes(
        MODULE._canonical_receipt_bytes(receipt)
    )
    with pytest.raises(MODULE.CaptureError, match="URL mismatch"):
        MODULE.validate_archive_metadata_receipt(tmp_path)

    receipt = MODULE.refresh_archive_metadata(tmp_path)
    first_path = tmp_path / receipt["files"][0]["path"]
    first_path.write_bytes(first_path.read_bytes() + b"tamper")
    with pytest.raises(MODULE.CaptureError, match="size mismatch"):
        MODULE.validate_archive_metadata_receipt(tmp_path)


def test_archive_metadata_head_rejects_redirect_size_and_bad_timestamp(monkeypatch):
    class Response:
        status = 200

        def __init__(self, url, headers):
            self.url = url
            self.headers = headers

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def geturl(self):
            return self.url

        def getcode(self):
            return self.status

    requested = "https://data.binance.vision/retained.zip"
    monkeypatch.setattr(
        MODULE,
        "_request",
        lambda *args, **kwargs: Response(
            requested + ".redirected",
            {"Content-Length": "3", "Last-Modified": "Tue, 25 Aug 2026 12:34:56 GMT"},
        ),
    )
    with pytest.raises(MODULE.CaptureError, match="URL mismatch"):
        MODULE.head_archive_metadata(requested, 3)

    monkeypatch.setattr(
        MODULE,
        "_request",
        lambda *args, **kwargs: Response(
            requested,
            {"Content-Length": "4", "Last-Modified": "Tue, 25 Aug 2026 12:34:56 GMT"},
        ),
    )
    with pytest.raises(MODULE.CaptureError, match="retained size"):
        MODULE.head_archive_metadata(requested, 3)

    monkeypatch.setattr(
        MODULE,
        "_request",
        lambda *args, **kwargs: Response(
            requested, {"Content-Length": "3", "Last-Modified": "not-a-date"}
        ),
    )
    with pytest.raises(MODULE.CaptureError, match="invalid Last-Modified"):
        MODULE.head_archive_metadata(requested, 3)


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
    if manifest.get("schema_version", 0) >= 2:
        assert manifest["datasets"]["markPriceKlines_1h"]["required_authority_interval"]["row_count"] == 961
        assert manifest["datasets"]["indexPriceKlines_1h"]["required_authority_interval"]["row_count"] == 961
        funding = manifest["datasets"]["fundingRate"]
        assert funding["selection_end_utc_exclusive"] == MODULE.iso_ms(MODULE.HOLDOUT_START_MS)
        assert funding["status"] == MODULE.ACCEPTED_FUNDING_STATUS
        assert funding["rate_type_counts"] == {"Regular": 120}
        assert funding["special_rate_type_count"] == 0
        assert funding["missing_rate_type_count"] == 0
        assert funding["accepted_source_binding"]["response_sha256"] == MODULE.ACCEPTED_FUNDING_RESPONSE_SHA256
        assert funding["accepted_source_binding"]["receipt_sha256"] == MODULE.ACCEPTED_FUNDING_RECEIPT_SHA256
        assert all(
            item["status"] == MODULE.DERIVED_STATUS
            for item in manifest["files"]
            if "/priceBars/" in item["path"] and "/derived-bounded/" in item["path"]
        )
        assert manifest["datasets"]["markPriceKlines_1m"]["rest_2026_08_24"]["retained_from_commit"] == "a61ef74"
    if manifest.get("schema_version", 0) >= 3:
        receipt, metadata = MODULE.validate_archive_metadata_receipt(
            SCRIPT_PATH.parent / "data"
        )
        assert manifest["official_archive_metadata_receipt"]["receipt_sha256"] == receipt["receipt_sha256"]
        assert manifest["official_archive_metadata_receipt"]["file_count"] == len(metadata)


def test_normal_capture_forces_offline_archive_validation(monkeypatch):
    def stop_after_archive_mode(data_dir, *, offline):
        assert offline is True
        raise RuntimeError("archive mode checked")

    monkeypatch.setattr(MODULE, "capture_archives", stop_after_archive_mode)
    monkeypatch.setattr(
        MODULE,
        "_request",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network used")),
    )
    with pytest.raises(RuntimeError, match="archive mode checked"):
        MODULE.capture(SCRIPT_PATH.parent / "data")


def test_validate_only_path_never_uses_network(monkeypatch):
    monkeypatch.setattr(
        MODULE,
        "_request",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network used")),
    )
    manifest = MODULE.validate_existing(SCRIPT_PATH.parent / "data")
    assert manifest["validation"]["derived_rows_equal_base_manifest_artifacts"] is True
    assert manifest["validation"]["funding_byte_exact_mirror_verified"] is True
    assert manifest["validation"]["funding_120_regular_no_special_or_missing"] is True
