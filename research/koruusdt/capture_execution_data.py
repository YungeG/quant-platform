#!/usr/bin/env python3
"""Capture and validate bounded KORUUSDT discovery execution data.

Only the half-open interval [2026-07-15T00:00Z, 2026-08-24T11:00Z) is
addressed. Every REST request carries an inclusive endTime no later than the
last millisecond before the holdout boundary.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections.abc import Iterable, Iterator
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

SYMBOL = "KORUUSDT"
UTC = dt.timezone.utc
DAY_MS = 86_400_000
MINUTE_MS = 60_000
HOUR_MS = 3_600_000
DISCOVERY_START = dt.datetime(2026, 7, 15, tzinfo=UTC)
AUTHORITY_START = dt.datetime(2026, 7, 15, 10, tzinfo=UTC)
ARCHIVE_END_DATE = dt.date(2026, 8, 23)
REST_DATE = dt.date(2026, 8, 24)
HOLDOUT_START = dt.datetime(2026, 8, 24, 11, tzinfo=UTC)
DISCOVERY_START_MS = int(DISCOVERY_START.timestamp() * 1000)
AUTHORITY_START_MS = int(AUTHORITY_START.timestamp() * 1000)
REST_START_MS = int(dt.datetime.combine(REST_DATE, dt.time(), UTC).timestamp() * 1000)
HOLDOUT_START_MS = int(HOLDOUT_START.timestamp() * 1000)
REST_END_MS = HOLDOUT_START_MS - 1
RETAINED_AGG_COVERAGE_START_MS = 1_787_553_260_640
BASE_ARCHIVE_URL = "https://data.binance.vision/data/futures/um/daily"
FAPI_URL = "https://fapi.binance.com/fapi/v1"
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data"
BASE_MANIFEST_NAME = "manifest.json"
EXECUTION_MANIFEST_NAME = "execution_data_manifest.json"
ARCHIVE_METADATA_RECEIPT_NAME = "binance_usdm/official_archive_metadata_receipt.json"
USER_AGENT = "koruusdt-bounded-discovery-capture/1"
MAX_RETRIES = 5
DERIVED_STATUS = "base_manifest_derived_raw_observations"
ACCEPTED_FUNDING_STATUS = "accepted_source_capture_mirror"
ACCEPTED_FUNDING_REPO_DIR = Path(
    "backtest/tests/fixtures/market_data/providers/binance_usdm/"
    "koru-funding-history-v1"
)
ACCEPTED_FUNDING_RESPONSE_SHA256 = (
    "sha256:ace9f779682989befac94ffd1c835e7a6e97b2b8103e6ad347ec8dc38fa6c960"
)
ACCEPTED_FUNDING_RECEIPT_SHA256 = (
    "sha256:74ea246da8d5b6aaf84ffce983cdb1f01a69533707683816dccc838f06b9d053"
)
ACCEPTED_FUNDING_FIRST_MS = 1_784_131_200_001
ACCEPTED_FUNDING_LAST_MS = 1_787_558_400_001
ACCEPTED_FUNDING_ROW_COUNT = 120
A61_MARK_RETAINED_SHA256 = {
    "KORUUSDT-1m-2026-08-24.discovery-bounded.csv": "sha256:f348bbef9dcd614eb6498501e116d8b83c06527c094f24fc67333551ef694da2",
    "KORUUSDT-1m-2026-08-24.discovery-bounded.page-0001.json": "sha256:ea41a6aa90b93ea28e840c46d72e80b87da4f16b4c0afd8144c0444709e8388d",
    "KORUUSDT-1m-2026-08-24.discovery-bounded.zip": "sha256:6274c0416b615f849ee544ea9c2a75dc97fc099be7ffa82bb3262ae48e3392e1",
    "KORUUSDT-1m-2026-08-24.discovery-bounded.zip.CHECKSUM": "sha256:94fc2760b78a0a374904c901b7d7ce47fcf30d23c3018d4fe3490c85492fb5bf",
}

AGG_HEADER = (
    "agg_trade_id",
    "price",
    "quantity",
    "first_trade_id",
    "last_trade_id",
    "transact_time",
    "is_buyer_maker",
)
PRICE_BAR_SOURCES = {
    "mark": "markPriceKlines",
    "index": "indexPriceKlines",
}

FROZEN_PRICE_HEADER = (
    "open_time_utc",
    "open",
    "high",
    "low",
    "close",
    "close_time_utc",
    "volume",
)
MARK_HEADER = (
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "count",
    "taker_buy_volume",
    "taker_buy_quote_volume",
    "ignore",
)
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


class CaptureError(RuntimeError):
    pass


class RestRestriction(CaptureError):
    pass


def iso_ms(value_ms: int) -> str:
    value = dt.datetime.fromtimestamp(value_ms / 1000, UTC)
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def manifest_sha256(manifest: dict[str, Any]) -> str:
    payload = dict(manifest)
    payload["manifest_sha256"] = ""
    return sha256_bytes(canonical_json_bytes(payload))


def atomic_write(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("wb") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def archive_url(kind: str, utc_date: dt.date) -> str:
    date_text = utc_date.isoformat()
    if kind == "aggTrades":
        filename = f"{SYMBOL}-aggTrades-{date_text}.zip"
        return f"{BASE_ARCHIVE_URL}/aggTrades/{SYMBOL}/{filename}"
    if kind == "markPriceKlines":
        filename = f"{SYMBOL}-1m-{date_text}.zip"
        return f"{BASE_ARCHIVE_URL}/markPriceKlines/{SYMBOL}/1m/{filename}"
    raise ValueError(f"unsupported archive kind: {kind}")


def archive_path(data_dir: Path, kind: str, utc_date: dt.date) -> Path:
    return data_dir / "binance_usdm" / kind / "daily" / Path(archive_url(kind, utc_date)).name


def price_archive_url(source: str, utc_date: dt.date) -> str:
    endpoint = PRICE_BAR_SOURCES.get(source)
    if endpoint is None:
        raise ValueError(f"unsupported price-bar source: {source}")
    filename = f"{SYMBOL}-1h-{utc_date.isoformat()}.zip"
    return f"{BASE_ARCHIVE_URL}/{endpoint}/{SYMBOL}/1h/{filename}"


def price_archive_path(data_dir: Path, source: str, utc_date: dt.date) -> Path:
    return (
        data_dir
        / "binance_usdm"
        / "priceBars"
        / source
        / "1h"
        / "daily"
        / Path(price_archive_url(source, utc_date)).name
    )


def daily_dates() -> Iterator[dt.date]:
    current = DISCOVERY_START.date()
    while current <= ARCHIVE_END_DATE:
        yield current
        current += dt.timedelta(days=1)


def official_archive_metadata_specs(data_dir: Path) -> list[tuple[Path, str]]:
    specs: list[tuple[Path, str]] = []
    for utc_date in daily_dates():
        archives = [
            (
                archive_path(data_dir, "aggTrades", utc_date),
                archive_url("aggTrades", utc_date),
            ),
            *(
                (
                    price_archive_path(data_dir, source, utc_date),
                    price_archive_url(source, utc_date),
                )
                for source in PRICE_BAR_SOURCES
            ),
        ]
        for path, url in archives:
            specs.extend(
                (
                    (path, url),
                    (path.with_name(path.name + ".CHECKSUM"), url + ".CHECKSUM"),
                )
            )
    return sorted(specs, key=lambda item: item[0].relative_to(data_dir).as_posix())


def archive_metadata_receipt_sha256(receipt: dict[str, Any]) -> str:
    payload = dict(receipt)
    payload["receipt_sha256"] = ""
    return sha256_bytes(canonical_json_bytes(payload))


def parse_last_modified(value: str) -> tuple[str, int]:
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise CaptureError(f"invalid Last-Modified header: {value!r}") from error
    if parsed.tzinfo is None:
        raise CaptureError("Last-Modified header has no timezone")
    parsed = parsed.astimezone(UTC)
    canonical = parsed.isoformat(timespec="seconds").replace("+00:00", "Z")
    nanoseconds = int(parsed.timestamp()) * 1_000_000_000 + parsed.microsecond * 1000
    return canonical, nanoseconds


def _request(
    url: str, *, range_start: int | None = None, method: str = "GET"
) -> urllib.response.addinfourl:
    headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
    if range_start is not None:
        headers["Range"] = f"bytes={range_start}-"
    request = urllib.request.Request(url, headers=headers, method=method)
    return urllib.request.urlopen(request, timeout=60)


def head_archive_metadata(url: str, expected_size: int) -> dict[str, Any]:
    for attempt in range(MAX_RETRIES):
        try:
            with _request(url, method="HEAD") as response:
                response_url = response.geturl()
                status = getattr(response, "status", response.getcode())
                content_length = response.headers.get("Content-Length")
                last_modified = response.headers.get("Last-Modified")
                etag = response.headers.get("ETag")
            if status != 200:
                raise CaptureError(f"HEAD {url} returned HTTP {status}")
            if response_url != url:
                raise CaptureError(f"HEAD URL mismatch: requested={url} response={response_url}")
            try:
                size = int(content_length) if content_length is not None else -1
            except ValueError as error:
                raise CaptureError(f"HEAD {url} returned invalid Content-Length") from error
            if size != expected_size:
                raise CaptureError(
                    f"HEAD {url} Content-Length {size} does not equal retained size {expected_size}"
                )
            if last_modified is None:
                raise CaptureError(f"HEAD {url} omitted Last-Modified")
            provider_utc, provider_ns = parse_last_modified(last_modified)
            if etag is not None and not etag:
                raise CaptureError(f"HEAD {url} returned an empty ETag")
            return {
                "url": url,
                "content_length_bytes": size,
                "etag": etag,
                "provider_last_modified_utc": provider_utc,
                "provider_last_modified_ns": provider_ns,
            }
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == MAX_RETRIES - 1:
                raise CaptureError(f"HEAD {url} failed with HTTP {error.code}") from error
        except (OSError, TimeoutError) as error:
            if attempt == MAX_RETRIES - 1:
                raise CaptureError(f"HEAD {url} failed: {error}") from error
        time.sleep(2**attempt)
    raise AssertionError("unreachable")


def _canonical_receipt_bytes(receipt: dict[str, Any]) -> bytes:
    return canonical_json_bytes(receipt) + b"\n"


def validate_archive_metadata_receipt(
    data_dir: Path,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    path = data_dir / ARCHIVE_METADATA_RECEIPT_NAME
    raw = path.read_bytes()
    receipt = json.loads(raw)
    if not isinstance(receipt, dict) or raw != _canonical_receipt_bytes(receipt):
        raise CaptureError("official archive metadata receipt is not canonical JSON")
    if receipt.get("receipt_sha256") != archive_metadata_receipt_sha256(receipt):
        raise CaptureError("official archive metadata receipt canonical hash mismatch")
    if (
        receipt.get("type") != "binance_usdm_official_archive_metadata_receipt"
        or receipt.get("schema_version") != 1
        or receipt.get("instrument") != SYMBOL
        or receipt.get("request_method") != "HEAD"
        or receipt.get("retained_date_start") != DISCOVERY_START.date().isoformat()
        or receipt.get("retained_date_end") != ARCHIVE_END_DATE.isoformat()
    ):
        raise CaptureError("official archive metadata receipt identity mismatch")

    specs = official_archive_metadata_specs(data_dir)
    expected = {
        path.relative_to(data_dir).as_posix(): (path, url) for path, url in specs
    }
    files = receipt.get("files")
    if not isinstance(files, list) or len(files) != len(expected):
        raise CaptureError("official archive metadata receipt does not have exact file cover")
    by_path: dict[str, dict[str, Any]] = {}
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise CaptureError("official archive metadata receipt file schema mismatch")
        relative = item["path"]
        if relative in by_path or relative not in expected:
            raise CaptureError("official archive metadata receipt has extra or duplicate path")
        retained_path, expected_url = expected[relative]
        if item.get("url") != expected_url:
            raise CaptureError(f"official archive metadata receipt URL mismatch: {relative}")
        if (
            not retained_path.is_file()
            or item.get("content_length_bytes") != retained_path.stat().st_size
        ):
            raise CaptureError(f"official archive metadata receipt size mismatch: {relative}")
        try:
            parsed = dt.datetime.strptime(
                item.get("provider_last_modified_utc", ""), "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=UTC)
        except (TypeError, ValueError) as error:
            raise CaptureError(
                f"official archive metadata receipt timestamp mismatch: {relative}"
            ) from error
        if item.get("provider_last_modified_ns") != int(parsed.timestamp()) * 1_000_000_000:
            raise CaptureError(
                f"official archive metadata receipt nanoseconds mismatch: {relative}"
            )
        if item.get("etag") is not None and not isinstance(item.get("etag"), str):
            raise CaptureError(f"official archive metadata receipt ETag mismatch: {relative}")
        by_path[relative] = item
    if set(by_path) != set(expected):
        raise CaptureError("official archive metadata receipt does not have exact path cover")
    return receipt, by_path


def refresh_archive_metadata(data_dir: Path) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for path, url in official_archive_metadata_specs(data_dir):
        if not path.is_file() or path.is_symlink():
            raise CaptureError(f"retained official archive file is missing or unsafe: {path}")
        metadata = head_archive_metadata(url, path.stat().st_size)
        if metadata.get("url") != url:
            raise CaptureError(f"HEAD metadata URL mismatch: {url}")
        files.append({"path": path.relative_to(data_dir).as_posix(), **metadata})
    receipt: dict[str, Any] = {
        "type": "binance_usdm_official_archive_metadata_receipt",
        "schema_version": 1,
        "instrument": SYMBOL,
        "request_method": "HEAD",
        "retained_date_start": DISCOVERY_START.date().isoformat(),
        "retained_date_end": ARCHIVE_END_DATE.isoformat(),
        "files": files,
        "receipt_sha256": "",
    }
    receipt["receipt_sha256"] = archive_metadata_receipt_sha256(receipt)
    atomic_write(data_dir / ARCHIVE_METADATA_RECEIPT_NAME, _canonical_receipt_bytes(receipt))
    return validate_archive_metadata_receipt(data_dir)[0]


def fetch_bytes(url: str) -> bytes:
    for attempt in range(MAX_RETRIES):
        try:
            with _request(url) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == MAX_RETRIES - 1:
                raise CaptureError(f"GET {url} failed with HTTP {error.code}") from error
        except (OSError, TimeoutError) as error:
            if attempt == MAX_RETRIES - 1:
                raise CaptureError(f"GET {url} failed: {error}") from error
        time.sleep(2**attempt)
    raise AssertionError("unreachable")


def parse_provider_checksum(value: bytes, filename: str) -> str:
    try:
        fields = value.decode("utf-8").strip().split()
    except UnicodeDecodeError as error:
        raise CaptureError("provider checksum is not UTF-8") from error
    if len(fields) != 2 or fields[1].lstrip("*") != filename or not SHA256_RE.fullmatch(fields[0]):
        raise CaptureError(f"provider checksum does not bind {filename}")
    return "sha256:" + fields[0]


def download_resumable_atomic(url: str, destination: Path, expected_sha256: str) -> str:
    if destination.exists() and sha256_path(destination) == expected_sha256:
        return "already_verified"
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    for attempt in range(MAX_RETRIES):
        start = partial.stat().st_size if partial.exists() else 0
        try:
            with _request(url, range_start=start if start else None) as response:
                status = getattr(response, "status", response.getcode())
                append = start > 0 and status == 206
                mode = "ab" if append else "wb"
                with partial.open(mode) as handle:
                    for block in iter(lambda: response.read(1024 * 1024), b""):
                        handle.write(block)
                    handle.flush()
                    os.fsync(handle.fileno())
            if sha256_path(partial) != expected_sha256:
                partial.unlink(missing_ok=True)
                raise CaptureError(f"SHA256 mismatch for {url}")
            os.replace(partial, destination)
            return "downloaded_verified"
        except urllib.error.HTTPError as error:
            if error.code == 416 and partial.exists():
                partial.unlink()
            elif error.code not in (429, 500, 502, 503, 504):
                raise CaptureError(f"GET {url} failed with HTTP {error.code}") from error
            if attempt == MAX_RETRIES - 1:
                raise CaptureError(f"GET {url} exhausted retries") from error
        except (OSError, TimeoutError) as error:
            if attempt == MAX_RETRIES - 1:
                raise CaptureError(f"GET {url} failed: {error}") from error
        time.sleep(2**attempt)
    raise AssertionError("unreachable")


def _capture_archive(
    data_dir: Path, url: str, destination: Path, statuses: dict[str, str]
) -> None:
    checksum_path = destination.with_name(destination.name + ".CHECKSUM")
    if checksum_path.exists():
        checksum_bytes = checksum_path.read_bytes()
        checksum_status = "already_verified"
    else:
        checksum_bytes = fetch_bytes(url + ".CHECKSUM")
        atomic_write(checksum_path, checksum_bytes)
        checksum_status = "downloaded_official_checksum"
    expected = parse_provider_checksum(checksum_bytes, destination.name)
    statuses[destination.relative_to(data_dir).as_posix()] = download_resumable_atomic(
        url, destination, expected
    )
    statuses[checksum_path.relative_to(data_dir).as_posix()] = checksum_status


def capture_archives(data_dir: Path, *, offline: bool) -> dict[str, str]:
    specs = []
    for utc_date in daily_dates():
        specs.extend(
            (
                (archive_url(kind, utc_date), archive_path(data_dir, kind, utc_date))
                for kind in ("aggTrades", "markPriceKlines")
            )
        )
        specs.extend(
            (price_archive_url(source, utc_date), price_archive_path(data_dir, source, utc_date))
            for source in PRICE_BAR_SOURCES
        )

    statuses: dict[str, str] = {}
    missing: list[tuple[str, Path]] = []
    for url, destination in specs:
        checksum_path = destination.with_name(destination.name + ".CHECKSUM")
        if destination.exists() and not checksum_path.exists():
            raise CaptureError(f"cannot validate existing archive without checksum: {destination}")
        if destination.exists():
            _validate_checksum_file(destination, checksum_path)
            statuses[destination.relative_to(data_dir).as_posix()] = "already_verified"
            statuses[checksum_path.relative_to(data_dir).as_posix()] = "already_verified"
        else:
            if checksum_path.exists():
                parse_provider_checksum(checksum_path.read_bytes(), destination.name)
            missing.append((url, destination))

    if missing and offline:
        raise CaptureError(f"offline capture is missing official archive: {missing[0][1]}")
    for url, destination in missing:
        _capture_archive(data_dir, url, destination, statuses)
    return statuses


def bounded_rest_url(endpoint: str, parameters: dict[str, int | str]) -> str:
    end_time = parameters.get("endTime")
    if type(end_time) is not int or end_time > REST_END_MS:
        raise CaptureError("every REST request must have endTime before holdout start")
    return f"{FAPI_URL}/{endpoint}?{urllib.parse.urlencode(parameters)}"


def fetch_rest_page(endpoint: str, parameters: dict[str, int | str]) -> tuple[list[Any], bytes, str]:
    url = bounded_rest_url(endpoint, parameters)
    for attempt in range(MAX_RETRIES):
        try:
            with _request(url) as response:
                raw = response.read()
        except urllib.error.HTTPError as error:
            raw = error.read()
            if error.code == 400:
                try:
                    payload = json.loads(raw)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    payload = None
                if isinstance(payload, dict) and payload.get("code") == -4166:
                    raise RestRestriction(str(payload.get("msg", "REST history restriction"))) from None
            if error.code not in (429, 500, 502, 503, 504) or attempt == MAX_RETRIES - 1:
                raise CaptureError(f"GET {url} failed with HTTP {error.code}: {raw[:300]!r}") from error
            time.sleep(2**attempt)
            continue
        except (OSError, TimeoutError) as error:
            if attempt == MAX_RETRIES - 1:
                raise CaptureError(f"GET {url} failed: {error}") from error
            time.sleep(2**attempt)
            continue
        try:
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise CaptureError(f"GET {url} returned invalid JSON") from error
        if not isinstance(payload, list):
            raise CaptureError(f"GET {url} did not return a JSON array")
        return payload, canonical_json_bytes(payload), url
    raise AssertionError("unreachable")


def fetch_raw_rest_page(
    endpoint: str, parameters: dict[str, int | str]
) -> tuple[list[Any], bytes, str]:
    """Fetch a bounded page while retaining the provider's exact JSON lexemes."""
    url = bounded_rest_url(endpoint, parameters)
    for attempt in range(MAX_RETRIES):
        try:
            with _request(url) as response:
                raw = response.read()
        except urllib.error.HTTPError as error:
            body = error.read()
            if error.code not in (429, 500, 502, 503, 504) or attempt == MAX_RETRIES - 1:
                raise CaptureError(
                    f"GET {url} failed with HTTP {error.code}: {body[:300]!r}"
                ) from error
        except (OSError, TimeoutError) as error:
            if attempt == MAX_RETRIES - 1:
                raise CaptureError(f"GET {url} failed: {error}") from error
        else:
            try:
                payload = json.loads(raw)
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise CaptureError(f"GET {url} returned invalid JSON") from error
            if not isinstance(payload, list):
                raise CaptureError(f"GET {url} did not return a JSON array")
            return payload, raw, url
        time.sleep(2**attempt)
    raise AssertionError("unreachable")


def _clean_rest_directory(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for path in directory.iterdir():
        if path.is_file():
            path.unlink()


def _load_base_manifest(data_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    path = data_dir / BASE_MANIFEST_NAME
    manifest = json.loads(path.read_bytes())
    if manifest.get("manifest_sha256") != manifest_sha256(manifest):
        raise CaptureError("base manifest canonical hash mismatch")
    artifacts = {
        item["path"]: item
        for item in manifest.get("artifacts", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    return manifest, artifacts


def _base_source(manifest: dict[str, Any], source_id: str) -> dict[str, Any]:
    matches = [
        source
        for source in manifest.get("sources", [])
        if isinstance(source, dict) and source.get("source_id") == source_id
    ]
    if len(matches) != 1:
        raise CaptureError(f"base manifest source is not unique: {source_id}")
    return matches[0]


def _frozen_rows(
    data_dir: Path,
    artifacts: dict[str, Any],
    name: str,
    header: tuple[str, ...],
    time_column: str,
    start_ms: int,
    end_ms: int,
) -> list[list[str]]:
    path = data_dir / name
    artifact = artifacts.get(name)
    if not isinstance(artifact, dict) or artifact.get("sha256") != sha256_path(path):
        raise CaptureError(f"base manifest artifact hash mismatch: {name}")
    selected: list[list[str]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        actual_header = tuple(next(reader, ()))
        if actual_header != header:
            raise CaptureError(f"frozen CSV header mismatch: {name}")
        column = actual_header.index(time_column)
        for row in reader:
            if len(row) != len(header):
                raise CaptureError(f"frozen CSV row width mismatch: {name}")
            if time_column.endswith("_utc"):
                timestamp = int(
                    dt.datetime.fromisoformat(row[column].replace("Z", "+00:00")).timestamp()
                    * 1000
                )
            else:
                timestamp = int(row[column])
            if start_ms <= timestamp < end_ms:
                selected.append(row)
    if not selected:
        raise CaptureError(f"no bounded frozen rows selected: {name}")
    return selected


def _derivation_binding(
    data_dir: Path,
    base_manifest: dict[str, Any],
    artifacts: dict[str, Any],
    input_name: str,
    source_id: str,
) -> dict[str, Any]:
    return {
        "status": DERIVED_STATUS,
        "input": {
            "path": input_name,
            "sha256": artifacts[input_name]["sha256"],
        },
        "base_manifest": {
            "path": BASE_MANIFEST_NAME,
            "file_sha256": sha256_path(data_dir / BASE_MANIFEST_NAME),
            "manifest_sha256": base_manifest["manifest_sha256"],
        },
        "frozen_source_metadata": _base_source(base_manifest, source_id),
    }


def load_frozen_price_rows(
    data_dir: Path,
    base_manifest: dict[str, Any],
    artifacts: dict[str, Any],
    source: str,
) -> tuple[list[list[str]], dict[str, Any]]:
    name = f"binance_{source}_raw.csv"
    rows = _frozen_rows(
        data_dir,
        artifacts,
        name,
        FROZEN_PRICE_HEADER,
        "open_time_utc",
        REST_START_MS,
        HOLDOUT_START_MS,
    )
    binding = _derivation_binding(
        data_dir,
        base_manifest,
        artifacts,
        name,
        f"binance_futures_{source}_price_kline",
    )
    return rows, binding


def validate_funding_rows(
    rows: list[dict[str, Any]], *, exact_cover: bool = False
) -> dict[str, Any]:
    previous_time: int | None = None
    regular_count = 0
    special_count = 0
    missing_rate_type_count = 0
    for row in rows:
        if (
            not isinstance(row, dict)
            or row.get("symbol") != SYMBOL
            or type(row.get("fundingTime")) is not int
            or not isinstance(row.get("fundingRate"), str)
            or not isinstance(row.get("markPrice"), str)
        ):
            raise CaptureError("fundingRate accepted response schema mismatch")
        funding_time = row["fundingTime"]
        if not AUTHORITY_START_MS <= funding_time < HOLDOUT_START_MS:
            raise CaptureError("fundingRate row escaped exact authority interval")
        if previous_time is not None and funding_time <= previous_time:
            raise CaptureError("fundingRate observations are not ordered and unique")
        rate_type = row.get("rateType")
        if rate_type is None:
            missing_rate_type_count += 1
        elif rate_type == "Regular":
            regular_count += 1
        else:
            special_count += 1
        previous_time = funding_time
    if not rows:
        raise CaptureError("fundingRate accepted response has no observations")
    summary = {
        "row_count": len(rows),
        "min_time_ms": rows[0]["fundingTime"],
        "max_time_ms": rows[-1]["fundingTime"],
        "rate_type_counts": {"Regular": regular_count},
        "regular_rate_type_count": regular_count,
        "special_rate_type_count": special_count,
        "missing_rate_type_count": missing_rate_type_count,
    }
    if exact_cover and summary != {
        "row_count": ACCEPTED_FUNDING_ROW_COUNT,
        "min_time_ms": ACCEPTED_FUNDING_FIRST_MS,
        "max_time_ms": ACCEPTED_FUNDING_LAST_MS,
        "rate_type_counts": {"Regular": ACCEPTED_FUNDING_ROW_COUNT},
        "regular_rate_type_count": ACCEPTED_FUNDING_ROW_COUNT,
        "special_rate_type_count": 0,
        "missing_rate_type_count": 0,
    }:
        raise CaptureError("accepted funding response does not have exact 120-row Regular cover")
    return summary


def _accepted_funding_source() -> tuple[
    list[dict[str, Any]], bytes, bytes, dict[str, Any], dict[str, Any]
]:
    source_dir = ROOT / ACCEPTED_FUNDING_REPO_DIR
    response_path = source_dir / "funding-history.json"
    receipt_path = source_dir / "acquisition-receipt.json"
    response_bytes = response_path.read_bytes()
    receipt_bytes = receipt_path.read_bytes()
    if sha256_bytes(response_bytes) != ACCEPTED_FUNDING_RESPONSE_SHA256:
        raise CaptureError("accepted funding response source hash mismatch")
    if sha256_bytes(receipt_bytes) != ACCEPTED_FUNDING_RECEIPT_SHA256:
        raise CaptureError("accepted funding receipt source hash mismatch")
    rows = json.loads(response_bytes)
    receipt = json.loads(receipt_bytes)
    if not isinstance(rows, list) or not isinstance(receipt, dict):
        raise CaptureError("accepted funding capture JSON schema mismatch")
    summary = validate_funding_rows(rows, exact_cover=True)
    expected_request = {
        "end_time_milliseconds": REST_END_MS,
        "limit": 1000,
        "start_time_milliseconds": AUTHORITY_START_MS,
        "symbol": SYMBOL,
    }
    if (
        receipt.get("status") != 200
        or receipt.get("request") != expected_request
        or receipt.get("record_count") != ACCEPTED_FUNDING_ROW_COUNT
        or receipt.get("byte_count") != len(response_bytes)
        or receipt.get("response_sha256") != ACCEPTED_FUNDING_RESPONSE_SHA256
    ):
        raise CaptureError("accepted funding receipt does not bind exact authority cover")
    binding = {
        "status": ACCEPTED_FUNDING_STATUS,
        "original_repo_path": ACCEPTED_FUNDING_REPO_DIR.as_posix(),
        "response_sha256": ACCEPTED_FUNDING_RESPONSE_SHA256,
        "receipt_sha256": ACCEPTED_FUNDING_RECEIPT_SHA256,
        "request_start_utc_inclusive": iso_ms(AUTHORITY_START_MS),
        "request_end_utc_inclusive": iso_ms(REST_END_MS),
        "row_count": summary["row_count"],
        "min_time_ms": summary["min_time_ms"],
        "min_time_utc": iso_ms(summary["min_time_ms"]),
        "max_time_ms": summary["max_time_ms"],
        "max_time_utc": iso_ms(summary["max_time_ms"]),
        "rate_type_counts": summary["rate_type_counts"],
        "special_rate_type_count": summary["special_rate_type_count"],
        "missing_rate_type_count": summary["missing_rate_type_count"],
    }
    return rows, response_bytes, receipt_bytes, receipt, binding


def mirror_accepted_funding_capture(
    data_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows, response_bytes, receipt_bytes, _, binding = _accepted_funding_source()
    directory = data_dir / "binance_usdm" / "fundingHistory" / "accepted-capture"
    response_path = directory / "funding-history.json"
    receipt_path = directory / "acquisition-receipt.json"
    atomic_write(response_path, response_bytes)
    atomic_write(receipt_path, receipt_bytes)

    obsolete = (
        data_dir
        / "binance_usdm/fundingHistory/derived-bounded/"
        f"{SYMBOL}-fundingRate-20260715T100000Z-20260824T105959Z.json"
    )
    if obsolete.exists():
        obsolete.unlink()
        obsolete.parent.rmdir()

    source_prefix = f"repo:{ACCEPTED_FUNDING_REPO_DIR.as_posix()}"
    return rows, [
        {
            "path": response_path,
            "source_url": f"{source_prefix}/funding-history.json",
            "row_count": len(rows),
            "status": ACCEPTED_FUNDING_STATUS,
            "accepted_source_binding": binding,
        },
        {
            "path": receipt_path,
            "source_url": f"{source_prefix}/acquisition-receipt.json",
            "row_count": None,
            "status": ACCEPTED_FUNDING_STATUS,
            "accepted_source_binding": binding,
        },
    ], binding


def capture_mark_rest(data_dir: Path) -> tuple[list[list[Any]], list[dict[str, Any]]]:
    directory = data_dir / "binance_usdm" / "markPriceKlines" / "rest-bounded" / REST_DATE.isoformat()
    payload, raw, url = fetch_rest_page(
        "markPriceKlines",
        {
            "symbol": SYMBOL,
            "interval": "1m",
            "startTime": REST_START_MS,
            "endTime": REST_END_MS,
            "limit": 1500,
        },
    )
    path = directory / f"{SYMBOL}-1m-{REST_DATE.isoformat()}.discovery-bounded.page-0001.json"
    _clean_rest_directory(directory)
    atomic_write(path, raw)
    return payload, [{"path": path, "source_url": url, "row_count": len(payload)}]


def _agg_probe(start_ms: int, end_ms: int) -> bool:
    try:
        fetch_rest_page(
            "aggTrades",
            {"symbol": SYMBOL, "startTime": start_ms, "endTime": end_ms, "limit": 1},
        )
    except RestRestriction:
        return False
    return True


def earliest_accessible_start(start_ms: int, end_ms: int) -> int | None:
    if not _agg_probe(end_ms, end_ms):
        return None
    low = start_ms
    high = end_ms
    while low < high:
        middle = (low + high) // 2
        if _agg_probe(middle, end_ms):
            high = middle
        else:
            low = middle + 1
    return low


def _capture_agg_window(
    directory: Path, window_start_ms: int, window_end_ms: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []
    from_id: int | None = None
    page_number = 1
    try:
        while True:
            parameters: dict[str, int | str] = {
                "symbol": SYMBOL,
                "startTime": window_start_ms,
                "endTime": window_end_ms,
                "limit": 1000,
            }
            if from_id is not None:
                parameters["fromId"] = from_id
            payload, raw, url = fetch_rest_page("aggTrades", parameters)
            if any(not isinstance(row, dict) for row in payload):
                raise CaptureError("aggTrades REST page contains a non-object row")
            typed_payload = list(payload)
            for row in typed_payload:
                timestamp = row.get("T")
                if type(timestamp) is not int or not window_start_ms <= timestamp <= window_end_ms:
                    raise CaptureError("aggTrades REST row escaped its bounded request")
            label_start = dt.datetime.fromtimestamp(window_start_ms / 1000, UTC).strftime("%Y%m%dT%H%M%S")
            label_end = dt.datetime.fromtimestamp(window_end_ms / 1000, UTC).strftime("%Y%m%dT%H%M%S")
            path = directory / f"{SYMBOL}-aggTrades-{label_start}Z-{label_end}Z-page-{page_number:04d}.json"
            atomic_write(path, raw)
            files.append({"path": path, "source_url": url, "row_count": len(typed_payload)})
            rows.extend(typed_payload)
            if len(typed_payload) < 1000:
                break
            last_id = typed_payload[-1].get("a")
            if type(last_id) is not int or (from_id is not None and last_id < from_id):
                raise CaptureError("aggTrades REST page did not advance aggregate IDs")
            from_id = last_id + 1
            page_number += 1
    except Exception:
        for item in files:
            item["path"].unlink(missing_ok=True)
        raise
    return rows, files


def capture_agg_rest(
    data_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    directory = data_dir / "binance_usdm" / "aggTrades" / "rest-bounded" / REST_DATE.isoformat()
    _clean_rest_directory(directory)
    all_rows: list[dict[str, Any]] = []
    all_files: list[dict[str, Any]] = []
    coverage_start = HOLDOUT_START_MS
    for hour in range(10, -1, -1):
        window_start = REST_START_MS + hour * 3_600_000
        window_end = min(window_start + 3_600_000 - 1, REST_END_MS)
        try:
            rows, files = _capture_agg_window(directory, window_start, window_end)
        except RestRestriction:
            accessible_start = earliest_accessible_start(window_start, window_end)
            if accessible_start is not None:
                # The provider cutoff advances during capture; retry just inside it.
                while accessible_start <= window_end:
                    try:
                        rows, files = _capture_agg_window(directory, accessible_start, window_end)
                        break
                    except RestRestriction:
                        accessible_start += 1000
                else:
                    rows, files = [], []
                if files:
                    all_rows.extend(rows)
                    all_files.extend(files)
                    coverage_start = accessible_start
            break
        all_rows.extend(rows)
        all_files.extend(files)
        coverage_start = window_start
    all_rows.sort(key=lambda row: (row["a"], row["T"]))
    all_files.sort(key=lambda item: item["path"].name)
    return all_rows, all_files, coverage_start


def _csv_bytes(header: tuple[str, ...], rows: Iterable[Iterable[object]]) -> bytes:
    text = io.StringIO(newline="")
    writer = csv.writer(text, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return text.getvalue().encode("utf-8")


def deterministic_zip(csv_name: str, csv_value: bytes) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        info = zipfile.ZipInfo(csv_name, (1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        archive.writestr(info, csv_value, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return output.getvalue()


def write_rest_derivatives(
    data_dir: Path,
    mark_rows: list[list[Any]],
    agg_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    definitions = (
        (
            "markPriceKlines",
            f"{SYMBOL}-1m-{REST_DATE.isoformat()}.discovery-bounded.csv",
            MARK_HEADER,
            mark_rows,
            f"{FAPI_URL}/markPriceKlines",
        ),
        (
            "aggTrades",
            f"{SYMBOL}-aggTrades-{REST_DATE.isoformat()}.discovery-bounded.csv",
            AGG_HEADER,
            (
                (
                    row["a"], row["p"], row["q"], row["f"], row["l"], row["T"],
                    str(row["m"]).lower(),
                )
                for row in agg_rows
            ),
            f"{FAPI_URL}/aggTrades",
        ),
    )
    for kind, csv_name, header, rows, source_url in definitions:
        directory = data_dir / "binance_usdm" / kind / "rest-bounded" / REST_DATE.isoformat()
        csv_value = _csv_bytes(header, rows)
        csv_path = directory / csv_name
        zip_path = directory / (csv_name.removesuffix(".csv") + ".zip")
        checksum_path = zip_path.with_name(zip_path.name + ".CHECKSUM")
        zip_value = deterministic_zip(csv_name, csv_value)
        checksum_value = f"{hashlib.sha256(zip_value).hexdigest()}  {zip_path.name}\n".encode()
        atomic_write(csv_path, csv_value)
        atomic_write(zip_path, zip_value)
        atomic_write(checksum_path, checksum_value)
        for path, status in (
            (csv_path, "rest_derived_standard_schema"),
            (zip_path, "rest_derived_standard_schema"),
            (checksum_path, "locally_generated_checksum"),
        ):
            outputs.append(
                {
                    "path": path,
                    "source_url": source_url,
                    "row_count": len(mark_rows) if kind == "markPriceKlines" else len(agg_rows),
                    "status": status,
                }
            )
    return outputs


def write_price_bar_derivatives(
    data_dir: Path,
    captures: dict[str, list[list[str]]],
    bindings: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    for source, rows in captures.items():
        directory = (
            data_dir
            / "binance_usdm"
            / "priceBars"
            / source
            / "1h"
            / "derived-bounded"
            / REST_DATE.isoformat()
        )
        csv_name = f"{SYMBOL}-1h-{REST_DATE.isoformat()}.discovery-bounded.csv"
        csv_value = _csv_bytes(FROZEN_PRICE_HEADER, rows)
        csv_path = directory / csv_name
        zip_path = directory / (csv_name.removesuffix(".csv") + ".zip")
        checksum_path = zip_path.with_name(zip_path.name + ".CHECKSUM")
        zip_value = deterministic_zip(csv_name, csv_value)
        checksum_value = (
            f"{hashlib.sha256(zip_value).hexdigest()}  {zip_path.name}\n".encode()
        )
        atomic_write(csv_path, csv_value)
        atomic_write(zip_path, zip_value)
        atomic_write(checksum_path, checksum_value)
        for path in (csv_path, zip_path, checksum_path):
            outputs.append(
                {
                    "path": path,
                    "source_url": bindings[source]["frozen_source_metadata"]["endpoint"],
                    "row_count": len(rows),
                    "status": DERIVED_STATUS,
                    "derivation_binding": bindings[source],
                }
            )
    return outputs


def _zip_csv_rows(path: Path) -> Iterator[list[str]]:
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if not name.endswith("/")]
        if len(members) != 1 or not members[0].endswith(".csv"):
            raise CaptureError(f"{path} must contain exactly one CSV")
        with archive.open(members[0]) as raw:
            with io.TextIOWrapper(raw, encoding="utf-8", newline="") as text:
                yield from csv.reader(text)


def _validate_agg_row(row: list[str], path: Path) -> tuple[int, int, int, int]:
    if len(row) != 7:
        raise CaptureError(f"{path} aggTrades row does not have 7 columns")
    try:
        aggregate_id, first_id, last_id, timestamp = map(int, (row[0], row[3], row[4], row[5]))
        float(row[1])
        float(row[2])
    except ValueError as error:
        raise CaptureError(f"{path} aggTrades row has invalid numeric fields") from error
    if row[6] not in ("true", "false") or first_id > last_id:
        raise CaptureError(f"{path} aggTrades row violates standard schema")
    if timestamp >= HOLDOUT_START_MS:
        raise CaptureError(f"{path} contains a holdout aggregate trade")
    return aggregate_id, first_id, last_id, timestamp


def _record_raw_id_gap(
    gaps: list[dict[str, Any]] | None,
    previous: tuple[int, int, int, int],
    current: tuple[int, int, int, int],
    classification: str,
) -> None:
    if gaps is None or current[1] <= previous[2] + 1:
        return
    gaps.append(
        {
            "dataset": "aggTrades",
            "kind": "raw_trade_id",
            "classification": classification,
            "start_inclusive": previous[2] + 1,
            "end_exclusive": current[1],
            "missing_id_count": current[1] - previous[2] - 1,
            "previous_aggregate_trade_id": previous[0],
            "next_aggregate_trade_id": current[0],
            "previous_time_ms": previous[3],
            "next_time_ms": current[3],
        }
    )


def validate_agg_archive(
    path: Path,
    utc_date: dt.date,
    previous: tuple[int, int, int, int] | None,
    raw_gaps: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], tuple[int, int, int, int]]:
    day_start = int(dt.datetime.combine(utc_date, dt.time(), UTC).timestamp() * 1000)
    day_end = day_start + DAY_MS
    count = 0
    first: tuple[int, int, int, int] | None = None
    last: tuple[int, int, int, int] | None = None
    for row_number, row in enumerate(_zip_csv_rows(path), 1):
        if row_number == 1 and tuple(row) == AGG_HEADER:
            continue
        current = _validate_agg_row(row, path)
        if not day_start <= current[3] < day_end:
            raise CaptureError(f"{path} aggregate trade is outside its UTC date")
        if last is not None:
            if current[0] != last[0] + 1:
                raise CaptureError(f"{path} aggregate trade IDs are not contiguous")
            if current[1] <= last[2]:
                raise CaptureError(f"{path} raw trade ID intervals overlap or regress")
            _record_raw_id_gap(
                raw_gaps,
                last,
                current,
                "provider_gap_between_contiguous_aggregate_trade_ids",
            )
        if first is None:
            first = current
        last = current
        count += 1
    if first is None or last is None:
        raise CaptureError(f"{path} contains no aggregate trades")
    if previous is not None:
        if first[0] != previous[0] + 1:
            raise CaptureError(f"{path} aggregate trade IDs are not contiguous across dates")
        if first[1] <= previous[2]:
            raise CaptureError(f"{path} raw trade ID intervals overlap or regress across dates")
        _record_raw_id_gap(
            raw_gaps,
            previous,
            first,
            "provider_gap_across_contiguous_daily_archives",
        )
    return (
        {
            "row_count": count,
            "min_aggregate_trade_id": first[0],
            "max_aggregate_trade_id": last[0],
            "min_raw_trade_id": first[1],
            "max_raw_trade_id": last[2],
            "min_time_ms": first[3],
            "max_time_ms": last[3],
        },
        last,
    )


def validate_mark_archive(path: Path, utc_date: dt.date) -> dict[str, Any]:
    day_start = int(dt.datetime.combine(utc_date, dt.time(), UTC).timestamp() * 1000)
    expected = day_start
    count = 0
    first_time: int | None = None
    last_time: int | None = None
    for row_number, row in enumerate(_zip_csv_rows(path), 1):
        if row_number == 1:
            if tuple(row) != MARK_HEADER:
                raise CaptureError(f"{path} markPriceKlines header mismatch")
            continue
        if len(row) != 12:
            raise CaptureError(f"{path} markPriceKlines row does not have 12 columns")
        try:
            open_time = int(row[0])
            close_time = int(row[6])
            int(row[8])
            for index in (1, 2, 3, 4, 5, 7, 9, 10, 11):
                float(row[index])
        except ValueError as error:
            raise CaptureError(f"{path} markPriceKlines numeric schema mismatch") from error
        if open_time != expected or close_time != open_time + MINUTE_MS - 1:
            raise CaptureError(f"{path} does not have a complete 1m grid")
        if open_time >= HOLDOUT_START_MS:
            raise CaptureError(f"{path} contains a holdout mark-price bar")
        first_time = open_time if first_time is None else first_time
        last_time = open_time
        expected += MINUTE_MS
        count += 1
    if count != 1440 or expected != day_start + DAY_MS:
        raise CaptureError(f"{path} does not contain exactly 1440 one-minute bars")
    return {"row_count": count, "min_time_ms": first_time, "max_time_ms": last_time}


def validate_price_bar_archive(
    path: Path, utc_date: dt.date, source: str
) -> dict[str, Any]:
    day_start = int(dt.datetime.combine(utc_date, dt.time(), UTC).timestamp() * 1000)
    expected = day_start
    count = 0
    first_time: int | None = None
    last_time: int | None = None
    for row_number, row in enumerate(_zip_csv_rows(path), 1):
        if row_number == 1:
            if tuple(row) != MARK_HEADER:
                raise CaptureError(f"{path} {source} 1h header mismatch")
            continue
        if len(row) != 12:
            raise CaptureError(f"{path} {source} 1h row does not have 12 columns")
        try:
            open_time = int(row[0])
            close_time = int(row[6])
            int(row[8])
            for index in (1, 2, 3, 4, 5, 7, 9, 10, 11):
                float(row[index])
        except ValueError as error:
            raise CaptureError(f"{path} {source} 1h numeric schema mismatch") from error
        if open_time != expected or close_time != open_time + HOUR_MS - 1:
            raise CaptureError(f"{path} does not have a complete 1h grid")
        if open_time >= HOLDOUT_START_MS:
            raise CaptureError(f"{path} contains a holdout {source} bar")
        first_time = open_time if first_time is None else first_time
        last_time = open_time
        expected += HOUR_MS
        count += 1
    if count != 24 or expected != day_start + DAY_MS:
        raise CaptureError(f"{path} does not contain exactly 24 one-hour bars")
    return {"row_count": count, "min_time_ms": first_time, "max_time_ms": last_time}


def validate_derived_price_rows(
    rows: list[list[str]], source: str
) -> dict[str, Any]:
    expected = REST_START_MS
    timestamps: list[int] = []
    for row in rows:
        if not isinstance(row, list) or len(row) != len(FROZEN_PRICE_HEADER):
            raise CaptureError(f"derived {source} 1h schema mismatch")
        try:
            open_time = int(
                dt.datetime.fromisoformat(row[0].replace("Z", "+00:00")).timestamp()
                * 1000
            )
            close_time = int(
                dt.datetime.fromisoformat(row[5].replace("Z", "+00:00")).timestamp()
                * 1000
            )
            for value in row[1:5] + row[6:]:
                float(value)
        except ValueError as error:
            raise CaptureError(f"derived {source} 1h schema mismatch") from error
        if open_time != expected or close_time != open_time + HOUR_MS - 1:
            raise CaptureError(f"derived {source} does not have the exact bounded 1h grid")
        if open_time >= HOLDOUT_START_MS:
            raise CaptureError(f"derived {source} contains a holdout bar")
        timestamps.append(open_time)
        expected += HOUR_MS
    if expected != HOLDOUT_START_MS or len(rows) != 11:
        raise CaptureError(f"derived {source} does not cover exact 00:00-11:00")
    return {
        "row_count": len(rows),
        "min_time_ms": timestamps[0],
        "max_time_ms": timestamps[-1],
        "timestamps_ms": timestamps,
    }


def validate_rest_mark(rows: list[list[Any]]) -> dict[str, Any]:
    expected = REST_START_MS
    for row in rows:
        if not isinstance(row, list) or len(row) != 12 or type(row[0]) is not int or type(row[6]) is not int:
            raise CaptureError("REST markPriceKlines schema mismatch")
        if row[0] != expected or row[6] != row[0] + MINUTE_MS - 1:
            raise CaptureError("REST markPriceKlines does not have the complete bounded 1m grid")
        if row[0] >= HOLDOUT_START_MS:
            raise CaptureError("REST markPriceKlines contains a holdout bar")
        expected += MINUTE_MS
    if expected != HOLDOUT_START_MS or len(rows) != 660:
        raise CaptureError("REST markPriceKlines does not cover exact 00:00-11:00")
    return {
        "row_count": len(rows),
        "min_time_ms": rows[0][0],
        "max_time_ms": rows[-1][0],
    }


def validate_rest_agg(
    rows: list[dict[str, Any]],
    coverage_start_ms: int,
    raw_gaps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    previous: tuple[int, int, int, int] | None = None
    for row in rows:
        required = {"a": int, "p": str, "q": str, "f": int, "l": int, "T": int, "m": bool}
        if any(type(row.get(key)) is not expected_type for key, expected_type in required.items()):
            raise CaptureError("REST aggTrades schema mismatch")
        if not coverage_start_ms <= row["T"] < HOLDOUT_START_MS or row["f"] > row["l"]:
            raise CaptureError("REST aggTrades row escaped bounded coverage")
        current = (row["a"], row["f"], row["l"], row["T"])
        if previous is not None:
            if current[0] != previous[0] + 1:
                raise CaptureError("REST aggTrades aggregate IDs are not contiguous")
            if current[1] <= previous[2]:
                raise CaptureError("REST aggTrades raw trade ID intervals overlap or regress")
            _record_raw_id_gap(
                raw_gaps,
                previous,
                current,
                "provider_gap_between_contiguous_rest_aggregate_trade_ids",
            )
        previous = current
    if not rows:
        return {"row_count": 0}
    return {
        "row_count": len(rows),
        "min_aggregate_trade_id": rows[0]["a"],
        "max_aggregate_trade_id": rows[-1]["a"],
        "min_raw_trade_id": rows[0]["f"],
        "max_raw_trade_id": rows[-1]["l"],
        "min_time_ms": rows[0]["T"],
        "max_time_ms": rows[-1]["T"],
    }


def _file_entry(
    data_dir: Path,
    path: Path,
    *,
    source_url: str,
    provider_checksum: str | None,
    status: str,
    row_count: int | None,
    derivation_binding: dict[str, Any] | None = None,
    accepted_source_binding: dict[str, Any] | None = None,
    archive_metadata: dict[str, Any] | None = None,
    metadata_receipt_sha256: str | None = None,
) -> dict[str, Any]:
    result = {
        "path": path.relative_to(data_dir).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_path(path),
        "source_url": source_url,
        "provider_checksum": provider_checksum,
        "status": status,
        "row_count": row_count,
    }
    if derivation_binding is not None:
        result["derivation_binding"] = derivation_binding
    if accepted_source_binding is not None:
        result["accepted_source_binding"] = accepted_source_binding
    if archive_metadata is not None:
        result |= {
            "provider_last_modified_utc": archive_metadata[
                "provider_last_modified_utc"
            ],
            "provider_last_modified_ns": archive_metadata[
                "provider_last_modified_ns"
            ],
            "etag": archive_metadata["etag"],
            "official_archive_metadata_receipt_sha256": metadata_receipt_sha256,
        }
    return result


def build_manifest(
    data_dir: Path,
    archive_statuses: dict[str, str],
    mark_rows: list[list[Any]],
    mark_page_files: list[dict[str, Any]],
    agg_rows: list[dict[str, Any]],
    agg_page_files: list[dict[str, Any]],
    coverage_start_ms: int,
    price_rows: dict[str, list[list[str]]],
    price_page_files: dict[str, list[dict[str, Any]]],
    funding_rows: list[dict[str, Any]],
    funding_page_files: list[dict[str, Any]],
    derivative_files: list[dict[str, Any]],
    archive_metadata_receipt: dict[str, Any] | None = None,
    archive_metadata_by_path: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    daily_agg: list[dict[str, Any]] = []
    daily_mark: list[dict[str, Any]] = []
    daily_prices: dict[str, list[dict[str, Any]]] = {
        source: [] for source in PRICE_BAR_SOURCES
    }
    previous_ids: tuple[int, int, int, int] | None = None
    raw_id_gaps: list[dict[str, Any]] = []
    first_agg: dict[str, Any] | None = None
    last_agg: dict[str, Any] | None = None
    metadata_by_path = archive_metadata_by_path or {}
    metadata_receipt_sha256 = (
        archive_metadata_receipt["receipt_sha256"]
        if archive_metadata_receipt is not None
        else None
    )
    bound_metadata_paths: set[str] = set()

    def add_official_archive(
        path: Path, url: str, row_count: int
    ) -> None:
        checksum_path = path.with_name(path.name + ".CHECKSUM")
        provider_checksum = parse_provider_checksum(
            checksum_path.read_bytes(), path.name
        )
        if sha256_path(path) != provider_checksum:
            raise CaptureError(f"provider checksum mismatch after capture: {path}")
        relative = path.relative_to(data_dir).as_posix()
        checksum_relative = checksum_path.relative_to(data_dir).as_posix()
        archive_metadata = metadata_by_path.get(relative)
        checksum_metadata = metadata_by_path.get(checksum_relative)
        if archive_metadata is not None:
            bound_metadata_paths.add(relative)
        if checksum_metadata is not None:
            bound_metadata_paths.add(checksum_relative)
        files.append(
            _file_entry(
                data_dir,
                path,
                source_url=url,
                provider_checksum=provider_checksum,
                status=archive_statuses.get(relative, "verified"),
                row_count=row_count,
                archive_metadata=archive_metadata,
                metadata_receipt_sha256=metadata_receipt_sha256,
            )
        )
        files.append(
            _file_entry(
                data_dir,
                checksum_path,
                source_url=url + ".CHECKSUM",
                provider_checksum=None,
                status="official_provider_checksum",
                row_count=None,
                archive_metadata=checksum_metadata,
                metadata_receipt_sha256=metadata_receipt_sha256,
            )
        )

    for utc_date in daily_dates():
        agg_path = archive_path(data_dir, "aggTrades", utc_date)
        agg_summary, previous_ids = validate_agg_archive(
            agg_path, utc_date, previous_ids, raw_id_gaps
        )
        agg_summary |= {
            "utc_date": utc_date.isoformat(),
            "min_time_utc": iso_ms(agg_summary["min_time_ms"]),
            "max_time_utc": iso_ms(agg_summary["max_time_ms"]),
        }
        daily_agg.append(agg_summary)
        first_agg = first_agg or agg_summary
        last_agg = agg_summary
        add_official_archive(
            agg_path, archive_url("aggTrades", utc_date), agg_summary["row_count"]
        )

        mark_path = archive_path(data_dir, "markPriceKlines", utc_date)
        mark_summary = validate_mark_archive(mark_path, utc_date)
        mark_summary |= {
            "utc_date": utc_date.isoformat(),
            "min_time_utc": iso_ms(mark_summary["min_time_ms"]),
            "max_time_utc": iso_ms(mark_summary["max_time_ms"]),
        }
        daily_mark.append(mark_summary)
        add_official_archive(
            mark_path,
            archive_url("markPriceKlines", utc_date),
            mark_summary["row_count"],
        )

        for source in PRICE_BAR_SOURCES:
            path = price_archive_path(data_dir, source, utc_date)
            summary = validate_price_bar_archive(path, utc_date, source)
            summary |= {
                "utc_date": utc_date.isoformat(),
                "min_time_utc": iso_ms(summary["min_time_ms"]),
                "max_time_utc": iso_ms(summary["max_time_ms"]),
            }
            daily_prices[source].append(summary)
            add_official_archive(
                path, price_archive_url(source, utc_date), summary["row_count"]
            )

    if bound_metadata_paths != set(metadata_by_path):
        raise CaptureError("official archive metadata was not bound to exact manifest paths")
    if archive_metadata_receipt is not None:
        receipt_path = data_dir / ARCHIVE_METADATA_RECEIPT_NAME
        files.append(
            _file_entry(
                data_dir,
                receipt_path,
                source_url=BASE_ARCHIVE_URL,
                provider_checksum=None,
                status="official_archive_metadata_receipt",
                row_count=None,
            )
        )

    rest_mark_summary = validate_rest_mark(mark_rows)
    rest_mark_summary |= {
        "min_time_utc": iso_ms(rest_mark_summary["min_time_ms"]),
        "max_time_utc": iso_ms(rest_mark_summary["max_time_ms"]),
    }
    rest_agg_summary = validate_rest_agg(agg_rows, coverage_start_ms, raw_id_gaps)
    if rest_agg_summary["row_count"]:
        rest_agg_summary |= {
            "min_time_utc": iso_ms(rest_agg_summary["min_time_ms"]),
            "max_time_utc": iso_ms(rest_agg_summary["max_time_ms"]),
        }

    derived_price_summaries = {
        source: validate_derived_price_rows(rows, source)
        for source, rows in price_rows.items()
    }
    if (
        derived_price_summaries["mark"]["timestamps_ms"]
        != derived_price_summaries["index"]["timestamps_ms"]
    ):
        raise CaptureError("derived mark/index 1h timestamps differ")
    for summary in derived_price_summaries.values():
        summary |= {
            "min_time_utc": iso_ms(summary["min_time_ms"]),
            "max_time_utc": iso_ms(summary["max_time_ms"]),
        }
        del summary["timestamps_ms"]

    funding_summary = validate_funding_rows(funding_rows, exact_cover=True)
    funding_binding = funding_page_files[0]["accepted_source_binding"]
    funding_summary |= {
        "min_time_utc": iso_ms(funding_summary["min_time_ms"]),
        "max_time_utc": iso_ms(funding_summary["max_time_ms"]),
        "selection_start_utc_inclusive": iso_ms(AUTHORITY_START_MS),
        "selection_end_utc_exclusive": iso_ms(HOLDOUT_START_MS),
        "selection_semantics": "accepted Binance response to an exact half-open authority-window request; funding observations are event rows",
        "status": ACCEPTED_FUNDING_STATUS,
        "provenance": "byte-exact mirror of the accepted Backtest funding response and acquisition receipt",
        "no_network_request_performed": True,
        "rateType_preserved_without_inference": True,
        "original_repo_path": funding_binding["original_repo_path"],
        "response_sha256": funding_binding["response_sha256"],
        "receipt_sha256": funding_binding["receipt_sha256"],
        "bounded_artifacts": [
            {
                "path": item["path"].relative_to(data_dir).as_posix(),
                "row_count": item["row_count"],
                "status": item["status"],
            }
            for item in funding_page_files
        ],
        "accepted_source_binding": funding_binding,
    }

    for item in mark_page_files + agg_page_files:
        files.append(
            _file_entry(
                data_dir,
                item["path"],
                source_url=item["source_url"],
                provider_checksum=None,
                status=item["status"],
                row_count=item["row_count"],
            )
        )
    for source in PRICE_BAR_SOURCES:
        for item in price_page_files[source]:
            files.append(
                _file_entry(
                    data_dir,
                    item["path"],
                    source_url=item["source_url"],
                    provider_checksum=None,
                    status=item["status"],
                    row_count=item["row_count"],
                    derivation_binding=item["derivation_binding"],
                )
            )
    for item in funding_page_files:
        files.append(
            _file_entry(
                data_dir,
                item["path"],
                source_url=item["source_url"],
                provider_checksum=None,
                status=item["status"],
                row_count=item["row_count"],
                accepted_source_binding=item["accepted_source_binding"],
            )
        )
    for item in derivative_files:
        files.append(
            _file_entry(
                data_dir,
                item["path"],
                source_url=item["source_url"],
                provider_checksum=None,
                status=item["status"],
                row_count=item["row_count"],
            )
        )

    assert first_agg is not None and last_agg is not None
    agg_total = sum(item["row_count"] for item in daily_agg) + rest_agg_summary["row_count"]
    mark_total = sum(item["row_count"] for item in daily_mark) + rest_mark_summary["row_count"]
    price_totals = {
        source: sum(item["row_count"] for item in daily_prices[source])
        + derived_price_summaries[source]["row_count"]
        for source in PRICE_BAR_SOURCES
    }
    required_price_rows = (HOLDOUT_START_MS - AUTHORITY_START_MS) // HOUR_MS

    missing_intervals: list[dict[str, Any]] = []
    gaps = raw_id_gaps
    if coverage_start_ms > REST_START_MS:
        missing_intervals.append(
            {
                "dataset": "aggTrades",
                "start_utc_inclusive": iso_ms(REST_START_MS),
                "end_utc_exclusive": iso_ms(coverage_start_ms),
                "reason": "Binance public aggTrades REST rejected older requests with code -4166; no archive or alternate feed was used for 2026-08-24",
            }
        )
    if rest_agg_summary["row_count"]:
        missing_aggregate_start = last_agg["max_aggregate_trade_id"] + 1
        missing_aggregate_end = rest_agg_summary["min_aggregate_trade_id"]
        missing_raw_start = last_agg["max_raw_trade_id"] + 1
        missing_raw_end = rest_agg_summary["min_raw_trade_id"]
        if missing_aggregate_start < missing_aggregate_end:
            gaps.append(
                {
                    "dataset": "aggTrades",
                    "kind": "aggregate_trade_id",
                    "classification": "unavailable_due_to_rest_history_restriction",
                    "start_inclusive": missing_aggregate_start,
                    "end_exclusive": missing_aggregate_end,
                    "missing_id_count": missing_aggregate_end - missing_aggregate_start,
                    "associated_missing_interval": missing_intervals[0] if missing_intervals else None,
                }
            )
        if missing_raw_start < missing_raw_end:
            gaps.append(
                {
                    "dataset": "aggTrades",
                    "kind": "raw_trade_id",
                    "classification": "unavailable_due_to_rest_history_restriction",
                    "start_inclusive": missing_raw_start,
                    "end_exclusive": missing_raw_end,
                    "missing_id_count": missing_raw_end - missing_raw_start,
                    "associated_missing_interval": missing_intervals[0] if missing_intervals else None,
                }
            )

    datasets: dict[str, Any] = {
        "aggTrades": {
            "source": "official Binance USD-M daily archives through 2026-08-23 plus bounded Binance REST-derived rows for 2026-08-24",
            "row_count": agg_total,
            "observed": {
                "min_time_ms": first_agg["min_time_ms"],
                "min_time_utc": iso_ms(first_agg["min_time_ms"]),
                "max_time_ms": rest_agg_summary.get("max_time_ms", last_agg["max_time_ms"]),
                "max_time_utc": iso_ms(rest_agg_summary.get("max_time_ms", last_agg["max_time_ms"])),
                "min_aggregate_trade_id": first_agg["min_aggregate_trade_id"],
                "max_aggregate_trade_id": rest_agg_summary.get("max_aggregate_trade_id", last_agg["max_aggregate_trade_id"]),
                "min_raw_trade_id": first_agg["min_raw_trade_id"],
                "max_raw_trade_id": rest_agg_summary.get("max_raw_trade_id", last_agg["max_raw_trade_id"]),
            },
            "rest_2026_08_24": rest_agg_summary
            | {
                "covered_start_utc_inclusive": iso_ms(coverage_start_ms),
                "covered_end_utc_exclusive": iso_ms(HOLDOUT_START_MS),
                "provenance": "REST-derived; not an official archive",
            },
            "daily": daily_agg,
        },
        "markPriceKlines_1m": {
            "source": "official Binance USD-M daily archives through 2026-08-23 plus exact bounded Binance REST-derived rows for 2026-08-24",
            "row_count": mark_total,
            "observed": {
                "min_time_ms": daily_mark[0]["min_time_ms"],
                "min_time_utc": iso_ms(daily_mark[0]["min_time_ms"]),
                "max_time_ms": rest_mark_summary["max_time_ms"],
                "max_time_utc": iso_ms(rest_mark_summary["max_time_ms"]),
            },
            "complete_grid": True,
            "rest_2026_08_24": rest_mark_summary
            | {
                "provenance": "retained canonical bounded REST response and derivatives from commit a61ef74; not refetched",
                "retained_from_commit": "a61ef74",
            },
            "daily": daily_mark,
        },
        "fundingRate": funding_summary,
    }
    for source, endpoint in PRICE_BAR_SOURCES.items():
        summaries = daily_prices[source]
        rest_summary = derived_price_summaries[source]
        datasets[f"{endpoint}_1h"] = {
            "source": f"official Binance USD-M {endpoint} 1h daily archives through 2026-08-23 plus exact bounded rows derived from the base-manifest-pinned binance_{source}_raw.csv for 2026-08-24",
            "row_count": price_totals[source],
            "retained_archive_interval": {
                "start_utc_inclusive": iso_ms(DISCOVERY_START_MS),
                "end_utc_exclusive": iso_ms(HOLDOUT_START_MS),
                "row_count": price_totals[source],
            },
            "required_authority_interval": {
                "semantics": "half-open completed 1h grid",
                "start_utc_inclusive": iso_ms(AUTHORITY_START_MS),
                "end_utc_exclusive": iso_ms(HOLDOUT_START_MS),
                "row_count": required_price_rows,
                "complete_grid": True,
            },
            "observed": {
                "min_time_ms": summaries[0]["min_time_ms"],
                "min_time_utc": iso_ms(summaries[0]["min_time_ms"]),
                "max_time_ms": rest_summary["max_time_ms"],
                "max_time_utc": iso_ms(rest_summary["max_time_ms"]),
            },
            "derived_2026_08_24": rest_summary
            | {
                "status": DERIVED_STATUS,
                "provenance": "exact frozen base CSV observations; not an official archive or REST response",
                "derivation_binding": price_page_files[source][0]["derivation_binding"],
            },
            "daily": summaries,
        }

    manifest: dict[str, Any] = {
        "type": "koruusdt_execution_data_manifest",
        "schema_version": 3 if archive_metadata_receipt is not None else 2,
        "instrument": SYMBOL,
        "generated_at_utc": json.loads((data_dir / BASE_MANIFEST_NAME).read_bytes())["generated_at_utc"],
        "generated_at_basis": "frozen base manifest generated_at_utc used as a deterministic offline regeneration marker",
        "base_manifest": {
            "path": BASE_MANIFEST_NAME,
            "sha256": sha256_path(data_dir / BASE_MANIFEST_NAME),
        },
        **(
            {
                "official_archive_metadata_receipt": {
                    "path": ARCHIVE_METADATA_RECEIPT_NAME,
                    "file_sha256": sha256_path(
                        data_dir / ARCHIVE_METADATA_RECEIPT_NAME
                    ),
                    "receipt_sha256": archive_metadata_receipt[
                        "receipt_sha256"
                    ],
                    "file_count": len(archive_metadata_by_path or {}),
                }
            }
            if archive_metadata_receipt is not None
            else {}
        ),
        "discovery_interval": {
            "semantics": "half-open",
            "start_utc_inclusive": iso_ms(DISCOVERY_START_MS),
            "end_utc_exclusive": iso_ms(HOLDOUT_START_MS),
            "start_ms": DISCOVERY_START_MS,
            "end_ms_exclusive": HOLDOUT_START_MS,
        },
        "backtest_authority_interval": {
            "semantics": "half-open",
            "start_utc_inclusive": iso_ms(AUTHORITY_START_MS),
            "end_utc_exclusive": iso_ms(HOLDOUT_START_MS),
            "start_ms": AUTHORITY_START_MS,
            "end_ms_exclusive": HOLDOUT_START_MS,
        },
        "holdout_protection": {
            "start_utc_inclusive": iso_ms(HOLDOUT_START_MS),
            "policy": "No request, retained row, or archive may address this instant or later",
            "rest_end_time_inclusive": REST_END_MS,
            "full_2026_08_24_daily_archive_downloaded": False,
        },
        "size_summary_bytes": {
            "official_archives": sum(
                item["size_bytes"]
                for item in files
                if item["path"].endswith(".zip") and "/daily/" in item["path"]
            ),
            "official_checksums": sum(
                item["size_bytes"]
                for item in files
                if item["path"].endswith(".zip.CHECKSUM") and "/daily/" in item["path"]
            ),
            "canonical_rest_responses": sum(
                item["size_bytes"]
                for item in files
                if item["status"].endswith("canonical_rest_response")
            ),
            "rest_derived_artifacts": sum(
                item["size_bytes"]
                for item in files
                if item["status"].endswith("rest_derived_standard_schema")
                or item["status"].endswith("locally_generated_checksum")
                or item["status"] == DERIVED_STATUS
            ),
            "accepted_source_capture_mirrors": sum(
                item["size_bytes"]
                for item in files
                if item["status"] == ACCEPTED_FUNDING_STATUS
            ),
            "all_manifest_bound_files": sum(item["size_bytes"] for item in files),
        },
        "datasets": datasets,
        "missing_intervals": missing_intervals,
        "gap_summary": {
            "gap_count": len(gaps),
            "missing_id_count": sum(item["missing_id_count"] for item in gaps),
            "by_classification": {
                classification: {
                    "gap_count": sum(item["classification"] == classification for item in gaps),
                    "missing_id_count": sum(
                        item["missing_id_count"]
                        for item in gaps
                        if item["classification"] == classification
                    ),
                }
                for classification in sorted({item["classification"] for item in gaps})
            },
        },
        "gaps": gaps,
        "files": sorted(files, key=lambda item: item["path"]),
        "validation": {
            "archives_streamed": True,
            "official_checksums_verified": True,
            "standard_binance_schemas": True,
            "no_row_at_or_after_holdout": True,
            "aggregate_trade_ids_contiguous_within_and_across_available_coverage": True,
            "raw_trade_id_intervals_strictly_increasing_non_overlapping": True,
            "raw_trade_id_gaps_recorded_as_source_evidence": True,
            "mark_price_complete_1m_grid": True,
            "mark_and_index_price_complete_1h_authority_grid": True,
            "mark_and_index_price_timestamps_exact": True,
            "derived_rows_equal_base_manifest_artifacts": True,
            "derived_artifacts_deterministic": True,
            "funding_accepted_source_hashes_verified": True,
            "funding_byte_exact_mirror_verified": True,
            "funding_120_regular_no_special_or_missing": True,
            "funding_ordered_unique_exact_interval_semantics": True,
            "manifest_file_exact_cover": True,
            "official_archive_metadata_receipt_verified": archive_metadata_receipt
            is not None,
        },
        "manifest_sha256": "",
    }
    manifest["manifest_sha256"] = manifest_sha256(manifest)
    return manifest


def _load_json_pages(paths: Iterable[Path]) -> list[Any]:
    rows: list[Any] = []
    found = False
    for path in paths:
        found = True
        payload = json.loads(path.read_bytes())
        if not isinstance(payload, list):
            raise CaptureError(f"{path} is not a JSON array")
        rows.extend(payload)
    if not found:
        raise CaptureError("no bounded REST page found")
    return rows


def _load_bound_csv(path: Path, header: tuple[str, ...]) -> list[list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        if tuple(next(reader, ())) != header:
            raise CaptureError(f"bounded CSV header mismatch: {path}")
        return list(reader)


def _load_retained_manifest(
    data_dir: Path, *, allow_refreshed_metadata_receipt: bool = False
) -> dict[str, Any]:
    path = data_dir / EXECUTION_MANIFEST_NAME
    manifest = json.loads(path.read_bytes())
    if manifest.get("manifest_sha256") != manifest_sha256(manifest):
        raise CaptureError("retained execution manifest canonical hash mismatch")
    if manifest.get("base_manifest", {}).get("sha256") != sha256_path(
        data_dir / BASE_MANIFEST_NAME
    ):
        raise CaptureError("retained execution manifest base binding mismatch")
    for item in manifest.get("files", []):
        if (
            allow_refreshed_metadata_receipt
            and item["path"] == ARCHIVE_METADATA_RECEIPT_NAME
        ):
            continue
        file_path = data_dir / item["path"]
        if not file_path.is_file() or sha256_path(file_path) != item["sha256"]:
            raise CaptureError(f"retained execution file binding mismatch: {file_path}")
    return manifest


def load_retained_rest_capture(
    data_dir: Path, retained_manifest: dict[str, Any]
) -> tuple[
    list[list[Any]],
    list[dict[str, Any]],
    int,
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    entries = {item["path"]: item for item in retained_manifest["files"]}
    mark_directory = (
        data_dir
        / "binance_usdm"
        / "markPriceKlines"
        / "rest-bounded"
        / REST_DATE.isoformat()
    )
    for name, expected in A61_MARK_RETAINED_SHA256.items():
        path = mark_directory / name
        if not path.is_file() or sha256_path(path) != expected:
            raise CaptureError(f"retained a61ef74 mark artifact mismatch: {path}")
    mark_pages = sorted(mark_directory.glob("*.page-*.json"))
    mark_rows = _load_json_pages(mark_pages)

    agg_directory = (
        data_dir
        / "binance_usdm"
        / "aggTrades"
        / "rest-bounded"
        / REST_DATE.isoformat()
    )
    agg_pages = sorted(path for path in agg_directory.glob("*.json") if "page-" in path.name)
    agg_rows: list[dict[str, Any]] = []
    coverage_start = RETAINED_AGG_COVERAGE_START_MS
    for path in agg_pages:
        payload = json.loads(path.read_bytes())
        if not isinstance(payload, list):
            raise CaptureError(f"{path} is not a JSON array")
        agg_rows.extend(payload)
    agg_rows.sort(key=lambda row: (row["a"], row["T"]))

    def metadata(paths: Iterable[Path], *, retained_mark: bool = False) -> list[dict[str, Any]]:
        result = []
        for path in paths:
            relative = path.relative_to(data_dir).as_posix()
            old = entries.get(relative)
            if old is None:
                raise CaptureError(f"retained REST artifact is not manifest-bound: {path}")
            status = old["status"]
            if retained_mark and not status.startswith("retained_from_a61ef74_"):
                status = "retained_from_a61ef74_" + status
            result.append(
                {
                    "path": path,
                    "source_url": old["source_url"],
                    "row_count": old["row_count"],
                    "status": status,
                }
            )
        return result

    mark_page_files = metadata(mark_pages, retained_mark=True)
    agg_page_files = metadata(agg_pages)
    derivative_files = metadata(
        sorted(
            path
            for directory in (mark_directory, agg_directory)
            for path in directory.iterdir()
            if path.is_file() and path.suffix != ".json"
        ),
        retained_mark=False,
    )
    for item in derivative_files:
        if (
            "markPriceKlines" in item["path"].as_posix()
            and not item["status"].startswith("retained_from_a61ef74_")
        ):
            item["status"] = "retained_from_a61ef74_" + item["status"]
    return (
        mark_rows,
        agg_rows,
        coverage_start,
        mark_page_files,
        agg_page_files,
        derivative_files,
    )


def validate_manifest_file_cover(
    data_dir: Path, manifest: dict[str, Any]
) -> None:
    listed = tuple(item["path"] for item in manifest["files"])
    if len(set(listed)) != len(listed):
        raise CaptureError("execution manifest contains duplicate file paths")
    root = data_dir / "binance_usdm"
    symlinks = tuple(path for path in root.rglob("*") if path.is_symlink())
    if symlinks:
        raise CaptureError(f"capture directory contains symlink: {symlinks[0]}")
    actual = {
        path.relative_to(data_dir).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }
    expected = set(listed)
    if actual != expected:
        extra = tuple(sorted(actual - expected))
        missing = tuple(sorted(expected - actual))
        raise CaptureError(
            f"execution manifest file cover mismatch: extra={extra} missing={missing}"
        )


def _validate_checksum_file(path: Path, checksum_path: Path) -> str:
    expected = parse_provider_checksum(checksum_path.read_bytes(), path.name)
    if sha256_path(path) != expected:
        raise CaptureError(f"checksum mismatch: {path}")
    return expected


def validate_existing(data_dir: Path) -> dict[str, Any]:
    manifest_path = data_dir / EXECUTION_MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("manifest_sha256") != manifest_sha256(manifest):
        raise CaptureError("execution manifest canonical hash mismatch")
    if manifest["base_manifest"]["sha256"] != sha256_path(
        data_dir / BASE_MANIFEST_NAME
    ):
        raise CaptureError("base manifest hash binding mismatch")
    archive_metadata_receipt: dict[str, Any] | None = None
    archive_metadata_by_path: dict[str, dict[str, Any]] = {}
    if manifest.get("schema_version", 0) >= 3:
        archive_metadata_receipt, archive_metadata_by_path = (
            validate_archive_metadata_receipt(data_dir)
        )
        binding = manifest.get("official_archive_metadata_receipt")
        if binding != {
            "path": ARCHIVE_METADATA_RECEIPT_NAME,
            "file_sha256": sha256_path(data_dir / ARCHIVE_METADATA_RECEIPT_NAME),
            "receipt_sha256": archive_metadata_receipt["receipt_sha256"],
            "file_count": len(archive_metadata_by_path),
        }:
            raise CaptureError("execution manifest metadata receipt binding mismatch")
    validate_manifest_file_cover(data_dir, manifest)
    for item in manifest["files"]:
        path = data_dir / item["path"]
        if (
            path.stat().st_size != item["size_bytes"]
            or sha256_path(path) != item["sha256"]
        ):
            raise CaptureError(f"manifest file binding mismatch: {path}")
        parsed = urllib.parse.urlparse(item["source_url"])
        parameters = urllib.parse.parse_qs(parsed.query)
        if parameters:
            end_times = parameters.get("endTime")
            if not end_times or int(end_times[0]) > REST_END_MS:
                raise CaptureError(f"manifest REST URL escapes holdout: {item['source_url']}")
        elif "/daily/" in item["path"] and "2026-08-24" in item["source_url"]:
            raise CaptureError("manifest references a holdout-day daily archive")
        metadata = archive_metadata_by_path.get(item["path"])
        metadata_fields = {
            "provider_last_modified_utc",
            "provider_last_modified_ns",
            "etag",
            "official_archive_metadata_receipt_sha256",
        }
        if metadata is not None:
            expected_metadata = {
                "provider_last_modified_utc": metadata[
                    "provider_last_modified_utc"
                ],
                "provider_last_modified_ns": metadata[
                    "provider_last_modified_ns"
                ],
                "etag": metadata["etag"],
                "official_archive_metadata_receipt_sha256": archive_metadata_receipt[
                    "receipt_sha256"
                ],
            }
            if any(item.get(key) != value for key, value in expected_metadata.items()):
                raise CaptureError(
                    f"manifest official archive metadata mismatch: {item['path']}"
                )
        elif metadata_fields.intersection(item):
            raise CaptureError(
                f"manifest has metadata on a non-receipted path: {item['path']}"
            )

    (
        mark_rows,
        agg_rows,
        _,
        _,
        _,
        _,
    ) = load_retained_rest_capture(data_dir, manifest)
    coverage_start = int(
        dt.datetime.fromisoformat(
            manifest["datasets"]["aggTrades"]["rest_2026_08_24"][
                "covered_start_utc_inclusive"
            ].replace("Z", "+00:00")
        ).timestamp()
        * 1000
    )
    rest_mark = validate_rest_mark(mark_rows)
    rest_agg = validate_rest_agg(agg_rows, coverage_start)

    base_manifest, artifacts = _load_base_manifest(data_dir)
    price_rows: dict[str, list[list[str]]] = {}
    expected_price_rows: dict[str, list[list[str]]] = {}
    for source in PRICE_BAR_SOURCES:
        expected_price_rows[source], expected_binding = load_frozen_price_rows(
            data_dir, base_manifest, artifacts, source
        )
        directory = (
            data_dir
            / "binance_usdm"
            / "priceBars"
            / source
            / "1h"
            / "derived-bounded"
            / REST_DATE.isoformat()
        )
        csv_name = f"{SYMBOL}-1h-{REST_DATE.isoformat()}.discovery-bounded.csv"
        csv_path = directory / csv_name
        price_rows[source] = _load_bound_csv(csv_path, FROZEN_PRICE_HEADER)
        if price_rows[source] != expected_price_rows[source]:
            raise CaptureError(f"derived {source} rows differ from frozen base artifact")
        csv_value = _csv_bytes(FROZEN_PRICE_HEADER, expected_price_rows[source])
        zip_path = csv_path.with_suffix(".zip")
        expected_zip = deterministic_zip(csv_name, csv_value)
        checksum_path = zip_path.with_name(zip_path.name + ".CHECKSUM")
        expected_checksum = (
            f"{hashlib.sha256(expected_zip).hexdigest()}  {zip_path.name}\n".encode()
        )
        if (
            csv_path.read_bytes() != csv_value
            or zip_path.read_bytes() != expected_zip
            or checksum_path.read_bytes() != expected_checksum
        ):
            raise CaptureError(f"derived {source} artifacts are not deterministic")
        for item in manifest["files"]:
            if item["path"] in {
                csv_path.relative_to(data_dir).as_posix(),
                zip_path.relative_to(data_dir).as_posix(),
                checksum_path.relative_to(data_dir).as_posix(),
            } and (
                item["status"] != DERIVED_STATUS
                or item.get("derivation_binding") != expected_binding
            ):
                raise CaptureError(f"derived {source} provenance binding mismatch")

    price_summaries = {
        source: validate_derived_price_rows(rows, source)
        for source, rows in price_rows.items()
    }
    if price_summaries["mark"]["timestamps_ms"] != price_summaries["index"]["timestamps_ms"]:
        raise CaptureError("derived mark/index 1h timestamps differ")

    (
        funding_rows,
        accepted_response_bytes,
        accepted_receipt_bytes,
        _,
        accepted_funding_binding,
    ) = _accepted_funding_source()
    funding_entries = [
        item
        for item in manifest["files"]
        if item["status"] == ACCEPTED_FUNDING_STATUS
        and "fundingHistory/accepted-capture/" in item["path"]
    ]
    if len(funding_entries) != 2:
        raise CaptureError("accepted funding response and receipt are not exactly manifest-bound")
    expected_mirrors = {
        "funding-history.json": accepted_response_bytes,
        "acquisition-receipt.json": accepted_receipt_bytes,
    }
    for entry in funding_entries:
        path = data_dir / entry["path"]
        if (
            path.read_bytes() != expected_mirrors.get(path.name)
            or entry.get("accepted_source_binding") != accepted_funding_binding
        ):
            raise CaptureError("accepted funding mirror or provenance binding mismatch")
    funding_summary = validate_funding_rows(funding_rows, exact_cover=True)

    previous = None
    daily_agg_rows = 0
    daily_mark_rows = 0
    daily_price_rows = {source: 0 for source in PRICE_BAR_SOURCES}
    for utc_date in daily_dates():
        agg_path = archive_path(data_dir, "aggTrades", utc_date)
        _validate_checksum_file(
            agg_path, agg_path.with_name(agg_path.name + ".CHECKSUM")
        )
        agg_summary, previous = validate_agg_archive(
            agg_path, utc_date, previous
        )
        daily_agg_rows += agg_summary["row_count"]

        mark_path = archive_path(data_dir, "markPriceKlines", utc_date)
        _validate_checksum_file(
            mark_path, mark_path.with_name(mark_path.name + ".CHECKSUM")
        )
        daily_mark_rows += validate_mark_archive(mark_path, utc_date)["row_count"]

        for source in PRICE_BAR_SOURCES:
            path = price_archive_path(data_dir, source, utc_date)
            _validate_checksum_file(path, path.with_name(path.name + ".CHECKSUM"))
            daily_price_rows[source] += validate_price_bar_archive(
                path, utc_date, source
            )["row_count"]

    expected_rows = {
        "aggTrades": daily_agg_rows + rest_agg["row_count"],
        "markPriceKlines_1m": daily_mark_rows + rest_mark["row_count"],
        "markPriceKlines_1h": daily_price_rows["mark"]
        + price_summaries["mark"]["row_count"],
        "indexPriceKlines_1h": daily_price_rows["index"]
        + price_summaries["index"]["row_count"],
        "fundingRate": funding_summary["row_count"],
    }
    for name, row_count in expected_rows.items():
        if manifest["datasets"][name]["row_count"] != row_count:
            raise CaptureError(f"manifest dataset row count mismatch: {name}")
    for name in ("markPriceKlines_1h", "indexPriceKlines_1h"):
        authority = manifest["datasets"][name]["required_authority_interval"]
        if authority != {
            "semantics": "half-open completed 1h grid",
            "start_utc_inclusive": iso_ms(AUTHORITY_START_MS),
            "end_utc_exclusive": iso_ms(HOLDOUT_START_MS),
            "row_count": (HOLDOUT_START_MS - AUTHORITY_START_MS) // HOUR_MS,
            "complete_grid": True,
        }:
            raise CaptureError(f"manifest authority coverage mismatch: {name}")
    funding_dataset = manifest["datasets"]["fundingRate"]
    if (
        funding_dataset["selection_start_utc_inclusive"]
        != iso_ms(AUTHORITY_START_MS)
        or funding_dataset["selection_end_utc_exclusive"]
        != iso_ms(HOLDOUT_START_MS)
        or funding_dataset["status"] != ACCEPTED_FUNDING_STATUS
        or funding_dataset["accepted_source_binding"] != accepted_funding_binding
        or funding_dataset["regular_rate_type_count"] != ACCEPTED_FUNDING_ROW_COUNT
        or funding_dataset["special_rate_type_count"] != 0
        or funding_dataset["missing_rate_type_count"] != 0
    ):
        raise CaptureError("manifest accepted funding coverage mismatch")
    return manifest


def capture(
    data_dir: Path, *, allow_refreshed_metadata_receipt: bool = False
) -> dict[str, Any]:
    if not (data_dir / BASE_MANIFEST_NAME).is_file():
        raise CaptureError(
            f"base manifest is required at {data_dir / BASE_MANIFEST_NAME}"
        )
    base_manifest, artifacts = _load_base_manifest(data_dir)
    retained_manifest = _load_retained_manifest(
        data_dir,
        allow_refreshed_metadata_receipt=allow_refreshed_metadata_receipt,
    )
    archive_statuses = capture_archives(data_dir, offline=True)
    receipt_path = data_dir / ARCHIVE_METADATA_RECEIPT_NAME
    archive_metadata_receipt: dict[str, Any] | None = None
    archive_metadata_by_path: dict[str, dict[str, Any]] = {}
    if receipt_path.is_file():
        archive_metadata_receipt, archive_metadata_by_path = (
            validate_archive_metadata_receipt(data_dir)
        )
    (
        mark_rows,
        agg_rows,
        coverage_start,
        mark_page_files,
        agg_page_files,
        derivative_files,
    ) = load_retained_rest_capture(data_dir, retained_manifest)

    validate_rest_mark(mark_rows)
    validate_rest_agg(agg_rows, coverage_start)
    price_rows: dict[str, list[list[str]]] = {}
    price_bindings: dict[str, dict[str, Any]] = {}
    for source in PRICE_BAR_SOURCES:
        price_rows[source], price_bindings[source] = load_frozen_price_rows(
            data_dir, base_manifest, artifacts, source
        )
    price_summaries = {
        source: validate_derived_price_rows(rows, source)
        for source, rows in price_rows.items()
    }
    if price_summaries["mark"]["timestamps_ms"] != price_summaries["index"]["timestamps_ms"]:
        raise CaptureError("derived mark/index 1h timestamps differ")

    price_page_files = {
        source: [] for source in PRICE_BAR_SOURCES
    }
    for item in write_price_bar_derivatives(data_dir, price_rows, price_bindings):
        source = "mark" if "/priceBars/mark/" in item["path"].as_posix() else "index"
        price_page_files[source].append(item)
    funding_rows, funding_page_files, _ = mirror_accepted_funding_capture(data_dir)
    validate_funding_rows(funding_rows, exact_cover=True)

    manifest = build_manifest(
        data_dir,
        archive_statuses,
        mark_rows,
        mark_page_files,
        agg_rows,
        agg_page_files,
        coverage_start,
        price_rows,
        price_page_files,
        funding_rows,
        funding_page_files,
        derivative_files,
        archive_metadata_receipt,
        archive_metadata_by_path,
    )
    atomic_write(
        data_dir / EXECUTION_MANIFEST_NAME,
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode(
            "utf-8"
        )
        + b"\n",
    )
    validate_existing(data_dir)
    return manifest


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    result.add_argument("--validate-only", action="store_true")
    result.add_argument(
        "--offline",
        action="store_true",
        help="explicitly document the default network-free capture mode",
    )
    result.add_argument(
        "--refresh-archive-metadata",
        action="store_true",
        help="HEAD only retained pre-holdout Binance Vision ZIP/CHECKSUM URLs",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.refresh_archive_metadata and (args.validate_only or args.offline):
        raise SystemExit(
            "capture failed: --refresh-archive-metadata cannot be combined with --validate-only or --offline"
        )
    try:
        if args.refresh_archive_metadata:
            receipt_path = args.data_dir / ARCHIVE_METADATA_RECEIPT_NAME
            manifest_path = args.data_dir / EXECUTION_MANIFEST_NAME
            previous_receipt = receipt_path.read_bytes() if receipt_path.exists() else None
            previous_manifest = manifest_path.read_bytes()
            try:
                refresh_archive_metadata(args.data_dir)
                manifest = capture(
                    args.data_dir, allow_refreshed_metadata_receipt=True
                )
            except Exception:
                if previous_receipt is None:
                    receipt_path.unlink(missing_ok=True)
                else:
                    atomic_write(receipt_path, previous_receipt)
                atomic_write(manifest_path, previous_manifest)
                raise
        elif args.validate_only:
            manifest = validate_existing(args.data_dir)
        else:
            manifest = capture(args.data_dir)
    except (CaptureError, OSError, ValueError, zipfile.BadZipFile, json.JSONDecodeError) as error:
        raise SystemExit(f"capture failed: {error}") from None
    print(
        json.dumps(
            {
                "manifest_sha256": manifest["manifest_sha256"],
                "aggTrades_rows": manifest["datasets"]["aggTrades"]["row_count"],
                "markPriceKlines_1m_rows": manifest["datasets"][
                    "markPriceKlines_1m"
                ]["row_count"],
                "markPriceKlines_1h_rows": manifest["datasets"][
                    "markPriceKlines_1h"
                ]["row_count"],
                "indexPriceKlines_1h_rows": manifest["datasets"][
                    "indexPriceKlines_1h"
                ]["row_count"],
                "fundingRate_rows": manifest["datasets"]["fundingRate"][
                    "row_count"
                ],
                "backtest_authority_interval": manifest[
                    "backtest_authority_interval"
                ],
                "missing_intervals": manifest["missing_intervals"],
                "gap_summary": manifest["gap_summary"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
