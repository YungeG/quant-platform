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
from pathlib import Path
from typing import Any

SYMBOL = "KORUUSDT"
UTC = dt.timezone.utc
DAY_MS = 86_400_000
MINUTE_MS = 60_000
DISCOVERY_START = dt.datetime(2026, 7, 15, tzinfo=UTC)
ARCHIVE_END_DATE = dt.date(2026, 8, 23)
REST_DATE = dt.date(2026, 8, 24)
HOLDOUT_START = dt.datetime(2026, 8, 24, 11, tzinfo=UTC)
DISCOVERY_START_MS = int(DISCOVERY_START.timestamp() * 1000)
REST_START_MS = int(dt.datetime.combine(REST_DATE, dt.time(), UTC).timestamp() * 1000)
HOLDOUT_START_MS = int(HOLDOUT_START.timestamp() * 1000)
REST_END_MS = HOLDOUT_START_MS - 1
BASE_ARCHIVE_URL = "https://data.binance.vision/data/futures/um/daily"
FAPI_URL = "https://fapi.binance.com/fapi/v1"
DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data"
BASE_MANIFEST_NAME = "manifest.json"
EXECUTION_MANIFEST_NAME = "execution_data_manifest.json"
USER_AGENT = "koruusdt-bounded-discovery-capture/1"
MAX_RETRIES = 5

AGG_HEADER = (
    "agg_trade_id",
    "price",
    "quantity",
    "first_trade_id",
    "last_trade_id",
    "transact_time",
    "is_buyer_maker",
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


def daily_dates() -> Iterator[dt.date]:
    current = DISCOVERY_START.date()
    while current <= ARCHIVE_END_DATE:
        yield current
        current += dt.timedelta(days=1)


def _request(url: str, *, range_start: int | None = None) -> urllib.response.addinfourl:
    headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
    if range_start is not None:
        headers["Range"] = f"bytes={range_start}-"
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60)


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


def capture_archives(data_dir: Path) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for kind in ("aggTrades", "markPriceKlines"):
        for utc_date in daily_dates():
            url = archive_url(kind, utc_date)
            destination = archive_path(data_dir, kind, utc_date)
            checksum_path = destination.with_name(destination.name + ".CHECKSUM")
            checksum_url = url + ".CHECKSUM"
            checksum_bytes = fetch_bytes(checksum_url)
            expected = parse_provider_checksum(checksum_bytes, destination.name)
            atomic_write(checksum_path, checksum_bytes)
            statuses[destination.relative_to(data_dir).as_posix()] = download_resumable_atomic(
                url, destination, expected
            )
            statuses[checksum_path.relative_to(data_dir).as_posix()] = "downloaded_official_checksum"
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


def _clean_rest_directory(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for path in directory.iterdir():
        if path.is_file():
            path.unlink()


def capture_mark_rest(data_dir: Path) -> tuple[list[list[Any]], list[dict[str, Any]]]:
    directory = data_dir / "binance_usdm" / "markPriceKlines" / "rest-bounded" / REST_DATE.isoformat()
    _clean_rest_directory(directory)
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
) -> dict[str, Any]:
    return {
        "path": path.relative_to(data_dir).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_path(path),
        "source_url": source_url,
        "provider_checksum": provider_checksum,
        "status": status,
        "row_count": row_count,
    }


def build_manifest(
    data_dir: Path,
    archive_statuses: dict[str, str],
    mark_rows: list[list[Any]],
    mark_page_files: list[dict[str, Any]],
    agg_rows: list[dict[str, Any]],
    agg_page_files: list[dict[str, Any]],
    coverage_start_ms: int,
    derivative_files: list[dict[str, Any]],
) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    daily_agg: list[dict[str, Any]] = []
    daily_mark: list[dict[str, Any]] = []
    previous_ids: tuple[int, int, int, int] | None = None
    raw_id_gaps: list[dict[str, Any]] = []
    first_agg: dict[str, Any] | None = None
    last_agg: dict[str, Any] | None = None
    for utc_date in daily_dates():
        agg_path = archive_path(data_dir, "aggTrades", utc_date)
        agg_summary, previous_ids = validate_agg_archive(
            agg_path, utc_date, previous_ids, raw_id_gaps
        )
        agg_summary["utc_date"] = utc_date.isoformat()
        agg_summary["min_time_utc"] = iso_ms(agg_summary["min_time_ms"])
        agg_summary["max_time_utc"] = iso_ms(agg_summary["max_time_ms"])
        daily_agg.append(agg_summary)
        first_agg = first_agg or agg_summary
        last_agg = agg_summary
        mark_path = archive_path(data_dir, "markPriceKlines", utc_date)
        mark_summary = validate_mark_archive(mark_path, utc_date)
        mark_summary["utc_date"] = utc_date.isoformat()
        mark_summary["min_time_utc"] = iso_ms(mark_summary["min_time_ms"])
        mark_summary["max_time_utc"] = iso_ms(mark_summary["max_time_ms"])
        daily_mark.append(mark_summary)
        for kind, path, summary in (
            ("aggTrades", agg_path, agg_summary),
            ("markPriceKlines", mark_path, mark_summary),
        ):
            url = archive_url(kind, utc_date)
            checksum_path = path.with_name(path.name + ".CHECKSUM")
            provider_checksum = parse_provider_checksum(checksum_path.read_bytes(), path.name)
            if sha256_path(path) != provider_checksum:
                raise CaptureError(f"provider checksum mismatch after capture: {path}")
            files.append(
                _file_entry(
                    data_dir,
                    path,
                    source_url=url,
                    provider_checksum=provider_checksum,
                    status=archive_statuses.get(path.relative_to(data_dir).as_posix(), "verified"),
                    row_count=summary["row_count"],
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
                )
            )
    rest_mark_summary = validate_rest_mark(mark_rows)
    rest_mark_summary["min_time_utc"] = iso_ms(rest_mark_summary["min_time_ms"])
    rest_mark_summary["max_time_utc"] = iso_ms(rest_mark_summary["max_time_ms"])
    rest_agg_summary = validate_rest_agg(agg_rows, coverage_start_ms, raw_id_gaps)
    if rest_agg_summary["row_count"]:
        rest_agg_summary["min_time_utc"] = iso_ms(rest_agg_summary["min_time_ms"])
        rest_agg_summary["max_time_utc"] = iso_ms(rest_agg_summary["max_time_ms"])
    for item in mark_page_files + agg_page_files:
        files.append(
            _file_entry(
                data_dir,
                item["path"],
                source_url=item["source_url"],
                provider_checksum=None,
                status="canonical_rest_response",
                row_count=item["row_count"],
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
    missing_intervals = []
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
    manifest: dict[str, Any] = {
        "type": "koruusdt_execution_data_manifest",
        "schema_version": 1,
        "instrument": SYMBOL,
        "generated_at_utc": iso_ms(int(time.time() * 1000)),
        "base_manifest": {
            "path": BASE_MANIFEST_NAME,
            "sha256": sha256_path(data_dir / BASE_MANIFEST_NAME),
        },
        "discovery_interval": {
            "semantics": "half-open",
            "start_utc_inclusive": iso_ms(DISCOVERY_START_MS),
            "end_utc_exclusive": iso_ms(HOLDOUT_START_MS),
            "start_ms": DISCOVERY_START_MS,
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
                item["size_bytes"] for item in files if item["status"] == "canonical_rest_response"
            ),
            "rest_derived_artifacts": sum(
                item["size_bytes"]
                for item in files
                if item["status"] in ("rest_derived_standard_schema", "locally_generated_checksum")
            ),
            "all_manifest_bound_files": sum(item["size_bytes"] for item in files),
        },
        "datasets": {
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
                | {"provenance": "REST-derived; not an official archive"},
                "daily": daily_mark,
            },
        },
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
            "standard_binance_schemas": True,
            "no_row_at_or_after_holdout": True,
            "aggregate_trade_ids_contiguous_within_and_across_available_coverage": True,
            "raw_trade_id_intervals_strictly_increasing_non_overlapping": True,
            "raw_trade_id_gaps_recorded_as_source_evidence": True,
            "mark_price_complete_1m_grid": True,
        },
        "manifest_sha256": "",
    }
    manifest["manifest_sha256"] = manifest_sha256(manifest)
    return manifest


def load_rest_capture(data_dir: Path) -> tuple[list[list[Any]], list[dict[str, Any]], int]:
    mark_directory = data_dir / "binance_usdm" / "markPriceKlines" / "rest-bounded" / REST_DATE.isoformat()
    mark_pages = sorted(mark_directory.glob("*.page-*.json"))
    if not mark_pages:
        raise CaptureError("no bounded markPriceKlines REST page found")
    mark_rows: list[list[Any]] = []
    for path in mark_pages:
        payload = json.loads(path.read_bytes())
        if not isinstance(payload, list):
            raise CaptureError(f"{path} is not a JSON array")
        mark_rows.extend(payload)
    agg_directory = data_dir / "binance_usdm" / "aggTrades" / "rest-bounded" / REST_DATE.isoformat()
    agg_pages = sorted(agg_directory.glob("*.json"))
    agg_pages = [path for path in agg_pages if "page-" in path.name]
    agg_rows: list[dict[str, Any]] = []
    coverage_start = HOLDOUT_START_MS
    for path in agg_pages:
        match = re.search(r"-(\d{8}T\d{6})Z-", path.name)
        if match:
            start = int(dt.datetime.strptime(match.group(1), "%Y%m%dT%H%M%S").replace(tzinfo=UTC).timestamp() * 1000)
            coverage_start = min(coverage_start, start)
        payload = json.loads(path.read_bytes())
        if not isinstance(payload, list):
            raise CaptureError(f"{path} is not a JSON array")
        agg_rows.extend(payload)
    agg_rows.sort(key=lambda row: (row["a"], row["T"]))
    return mark_rows, agg_rows, coverage_start


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


def validate_existing(data_dir: Path) -> dict[str, Any]:
    manifest_path = data_dir / EXECUTION_MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("manifest_sha256") != manifest_sha256(manifest):
        raise CaptureError("execution manifest canonical hash mismatch")
    if manifest["base_manifest"]["sha256"] != sha256_path(data_dir / BASE_MANIFEST_NAME):
        raise CaptureError("base manifest hash binding mismatch")
    validate_manifest_file_cover(data_dir, manifest)
    for item in manifest["files"]:
        path = data_dir / item["path"]
        if path.stat().st_size != item["size_bytes"] or sha256_path(path) != item["sha256"]:
            raise CaptureError(f"manifest file binding mismatch: {path}")
    mark_rows, agg_rows, _ = load_rest_capture(data_dir)
    coverage_start = int(
        dt.datetime.fromisoformat(
            manifest["datasets"]["aggTrades"]["rest_2026_08_24"][
                "covered_start_utc_inclusive"
            ].replace("Z", "+00:00")
        ).timestamp()
        * 1000
    )
    validate_rest_mark(mark_rows)
    validate_rest_agg(agg_rows, coverage_start)
    previous = None
    for utc_date in daily_dates():
        _, previous = validate_agg_archive(archive_path(data_dir, "aggTrades", utc_date), utc_date, previous)
        validate_mark_archive(archive_path(data_dir, "markPriceKlines", utc_date), utc_date)
    return manifest


def capture(data_dir: Path) -> dict[str, Any]:
    if not (data_dir / BASE_MANIFEST_NAME).is_file():
        raise CaptureError(f"base manifest is required at {data_dir / BASE_MANIFEST_NAME}")
    archive_statuses = capture_archives(data_dir)
    mark_rows, mark_page_files = capture_mark_rest(data_dir)
    agg_rows, agg_page_files, coverage_start = capture_agg_rest(data_dir)
    validate_rest_mark(mark_rows)
    validate_rest_agg(agg_rows, coverage_start)
    derivative_files = write_rest_derivatives(data_dir, mark_rows, agg_rows)
    manifest = build_manifest(
        data_dir,
        archive_statuses,
        mark_rows,
        mark_page_files,
        agg_rows,
        agg_page_files,
        coverage_start,
        derivative_files,
    )
    atomic_write(
        data_dir / EXECUTION_MANIFEST_NAME,
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n",
    )
    validate_existing(data_dir)
    return manifest


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    result.add_argument("--validate-only", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        manifest = validate_existing(args.data_dir) if args.validate_only else capture(args.data_dir)
    except (CaptureError, OSError, ValueError, zipfile.BadZipFile, json.JSONDecodeError) as error:
        raise SystemExit(f"capture failed: {error}") from None
    print(json.dumps({
        "manifest_sha256": manifest["manifest_sha256"],
        "aggTrades_rows": manifest["datasets"]["aggTrades"]["row_count"],
        "markPriceKlines_1m_rows": manifest["datasets"]["markPriceKlines_1m"]["row_count"],
        "missing_intervals": manifest["missing_intervals"],
        "gap_summary": manifest["gap_summary"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
