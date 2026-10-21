"""Bounded P3 input normalization and event-position Views.

Only the fixture harness currently supplies an access policy. Real CLI admission
remains closed until actual packages A/B and qualified inputs are accepted.
Neither a manifest hash, reservation receipt nor a fixture flag is permission.
"""

from __future__ import annotations

import csv
import fcntl
import hashlib
import io
import math
import os
import re
import stat
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from crypto_quant_research import RetrospectiveSourceSlice
from crypto_quant_validation import RetrospectiveReservationReceipt

from experiments import a_share_price_volume_retro_v1 as core

COLUMNS = (
    "instrument_id",
    "session",
    "close",
    "volume",
    "quantity_unit",
    "listed",
    "suspended",
    "comparable",
    "up_limit",
    "down_limit",
)
IDS = ("000001.XSHE", "600001.XSHG")
FIXTURE_ORIGIN = "PROCEDURAL_ADAPTER_FIXTURE_V1_NOT_MARKET_DATA"
FROZEN_CAPTURE_ORIGIN = "LOCAL_DERIVED_RETROSPECTIVE_CAPTURE_V1"


class InputError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require(value, code):
    if not value:
        raise InputError(code)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def wire_hash(raw: bytes) -> str:
    return "sha256:" + digest(raw)


def utc(value: datetime) -> str:
    require(
        type(value) is datetime
        and value.tzinfo is not None
        and value.utcoffset() is not None,
        "TIME_INVALID",
    )
    return (
        value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )


def instant(day: date) -> str:
    return utc(datetime.combine(day, time(), core.SHANGHAI))


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def select_calendar_splits(
    calendar: tuple[tuple[date, bool], ...],
) -> tuple[core.Split, ...]:
    """Calendar only: maximize packable open decision weeks,4:1:2,remainder TRAIN."""
    require(type(calendar) is tuple and bool(calendar), "CALENDAR_INVALID")
    require(
        all(
            type(row) is tuple
            and len(row) == 2
            and type(row[0]) is date
            and type(row[1]) is bool
            for row in calendar
        ),
        "CALENDAR_INVALID",
    )
    dates = tuple(row[0] for row in calendar)
    require(dates == tuple(sorted(set(dates))), "CALENDAR_DUPLICATE_OR_UNSORTED")
    require(
        dates == tuple(dates[0] + timedelta(days=i) for i in range(len(dates))),
        "CALENDAR_GAP",
    )
    opened = tuple(day for day, is_open in calendar if is_open)
    end = dates[-1] + timedelta(days=1)
    weeks = {week_start(day) for day in opened}

    def place(counts):
        cursor = dates[0]
        result = []
        for role, count in zip(core.RETRO_PARTITIONS, counts, strict=True):
            available = [day for day in opened if day >= cursor]
            if len(available) < 71 or count < 1:
                return None
            # Entire65-session warmup precedes the first natural decision week.
            decision_from = week_start(available[64]) + timedelta(days=7)
            last = {}
            for day in available:
                w = week_start(day)
                if w >= decision_from and w + timedelta(days=7) <= end:
                    last[w] = day
            choices = sorted(last)
            if len(choices) < count:
                return None
            final_week = choices[count - 1]
            final_day = last[final_week]
            t = available.index(final_day)
            if t + 5 >= len(available):
                return None
            read_to = available[t + 5] + timedelta(days=1)
            result.append(
                core.Split(
                    role, cursor, read_to, decision_from, final_week + timedelta(days=7)
                )
            )
            cursor = read_to
        return tuple(result)

    for total in range(len(weeks), 6, -1):
        q, remainder = divmod(total, 7)
        found = place((4 * q + remainder, q, 2 * q))
        if found is not None:
            return found
    raise InputError("INPUT_INSUFFICIENT_CALENDAR")


def normalize_number(value) -> dict[str, Any]:
    """Preserve binary64 exactly; never claim string(float) recovers provider text."""
    if value is None or value == "":
        return {"decimal": None, "binary64_hex": None, "basis": "MISSING"}
    require(type(value) is not bool, "NUMERIC_INVALID")
    try:
        if type(value) is float:
            require(math.isfinite(value), "NUMERIC_INVALID")
            return {
                "decimal": str(Decimal.from_float(value)),
                "binary64_hex": value.hex(),
                "basis": "BINARY64_EXACT_NOT_PROVIDER_PRECISION",
            }
        require(type(value) in (str, int, Decimal), "NUMERIC_INVALID")
        number = Decimal(value)
        require(number.is_finite(), "NUMERIC_INVALID")
        return {
            "decimal": str(number),
            "binary64_hex": None,
            "basis": "EXACT_DECLARED_TEXT_OR_INTEGER",
        }
    except (ValueError, ArithmeticError, TypeError) as error:
        raise InputError("NUMERIC_INVALID") from error


def number(atom):
    require(
        isinstance(atom, Mapping) and set(atom) == {"decimal", "binary64_hex", "basis"},
        "NUMERIC_IDENTITY_INVALID",
    )
    if atom["decimal"] is None:
        require(
            atom["binary64_hex"] is None and atom["basis"] == "MISSING",
            "NUMERIC_IDENTITY_INVALID",
        )
        return None
    require(
        type(atom["decimal"]) is str
        and (atom["binary64_hex"] is None or type(atom["binary64_hex"]) is str),
        "NUMERIC_IDENTITY_INVALID",
    )
    try:
        value = Decimal(atom["decimal"])
    except (ValueError, ArithmeticError, TypeError) as error:
        raise InputError("NUMERIC_INVALID") from error
    require(value.is_finite(), "NUMERIC_INVALID")
    if atom["binary64_hex"] is not None:
        try:
            original = float.fromhex(atom["binary64_hex"])
        except (ValueError, TypeError) as error:
            raise InputError("NUMERIC_IDENTITY_INVALID") from error
        require(
            math.isfinite(original)
            and Decimal.from_float(original) == value
            and original.hex() == atom["binary64_hex"]
            and atom["basis"] == "BINARY64_EXACT_NOT_PROVIDER_PRECISION",
            "NUMERIC_IDENTITY_INVALID",
        )
    else:
        require(
            atom["basis"] == "EXACT_DECLARED_TEXT_OR_INTEGER",
            "NUMERIC_IDENTITY_INVALID",
        )
    return value


def state(value):
    if value is None or value == "":
        return None
    if type(value) is bool:
        return value
    require(value in ("true", "false"), "STATE_INVALID")
    return value == "true"


def _date(value):
    require(type(value) is str, "DATE_INVALID")
    try:
        result = date.fromisoformat(value)
    except ValueError as error:
        raise InputError("DATE_INVALID") from error
    require(result.isoformat() == value, "DATE_INVALID")
    return result


def normalize_row(row: Mapping[str, Any]):
    require(set(row) == set(COLUMNS), "SCHEMA_INVALID")
    identifier = row["instrument_id"]
    require(
        type(identifier) is str
        and (
            identifier == "801150.SI"
            or re.fullmatch(r"[0-9]{6}\.(?:XSHG|XSHE)", identifier) is not None
        ),
        "IDENTITY_INVALID",
    )
    # This validates syntax only; ordinary-stock/industry qualification is separate.
    day = _date(row["session"])
    require(
        row["quantity_unit"] is None or type(row["quantity_unit"]) is str,
        "VOLUME_UNIT_INVALID",
    )
    result = {
        "instrument_id": identifier,
        "session": day.isoformat(),
        "quantity_unit": row["quantity_unit"] or None,
    }
    for key in ("close", "volume", "up_limit", "down_limit"):
        result[key] = normalize_number(row[key])
    for key in ("listed", "suspended", "comparable"):
        result[key] = state(row[key])
    # Core enforces value/state rules, including positive prices and nonnegative volume.
    return result


def no_links(path: Path):
    require(not any(p.is_symlink() for p in (path, *path.parents)), "SYMLINK_REJECTED")


class ArtifactBudget:
    """Hard caps for this writer/reader only, not a filesystem quota or DB scan cap."""

    def __init__(
        self,
        root: Path,
        *,
        read_bytes=32 * 1024**2,
        write_bytes=16 * 1024**2,
        max_rows=10000,
    ):
        self.root = Path(root).absolute()
        no_links(self.root)
        self.read_limit = read_bytes
        self.write_limit = write_bytes
        self.max_rows = max_rows
        require(
            all(type(v) is int and v > 0 for v in (read_bytes, write_bytes, max_rows)),
            "BUDGET_INVALID",
        )
        self.read_debit = 0
        self.write_debit = 0
        self.read_calls = 0
        self.files = {}

    def path(self, name):
        require(type(name) is str and name and Path(name).name == name, "PATH_INVALID")
        target = self.root / name
        no_links(target)
        return target

    def write(self, name, raw: bytes):
        require(type(raw) is bytes, "SCHEMA_INVALID")
        require(self.write_debit + len(raw) <= self.write_limit, "OUTPUT_CAP")
        self.write_debit += len(
            raw
        )  # Failed publication does not refund its reservation.
        target = self.path(name)
        with target.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        self.files[name] = self.descriptor(name)
        return self.files[name]

    def append_event(self, name, event):
        raw = core.canonical_bytes(event) + b"\n"
        require(self.write_debit + len(raw) <= self.write_limit, "OUTPUT_CAP")
        self.write_debit += len(raw)
        target = self.path(name)
        expected = self.files.get(name)
        if expected is not None:
            require(self.descriptor(name) == expected, "JOURNAL_IDENTITY_CONFLICT")
        else:
            require(not target.exists(), "OUTPUT_CONFLICT")
        fd = os.open(
            target,
            os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW | os.O_NONBLOCK,
            0o600,
        )
        try:
            require(stat.S_ISREG(os.fstat(fd).st_mode), "NOT_REGULAR_FILE")
            offset = 0
            while offset < len(raw):
                offset += os.write(fd, raw[offset:])
            os.fsync(fd)
        finally:
            os.close(fd)
        self.files[name] = self.descriptor(name)

    def descriptor(self, name):
        path = self.path(name)
        info = path.stat(follow_symlinks=False)
        require(stat.S_ISREG(info.st_mode), "NOT_REGULAR_FILE")
        # Owned generated artifacts, not an authorization to hash arbitrary sources.
        with path.open("rb") as stream:
            raw = stream.read(self.write_limit + 1)
        require(len(raw) <= self.write_limit, "OUTPUT_CAP")
        return {
            "name": name,
            "sha256": digest(raw),
            "bytes": len(raw),
            "device": info.st_dev,
            "inode": info.st_ino,
            "mtime_ns": info.st_mtime_ns,
        }

    def read(self, descriptor, authorize: Callable[[], None]):
        authorize()  # Every admission failure precedes even input stat/open.
        require(
            set(descriptor)
            == {"name", "sha256", "bytes", "device", "inode", "mtime_ns"},
            "INPUT_IDENTITY_INVALID",
        )
        path = self.path(descriptor["name"])
        info = path.stat(follow_symlinks=False)
        require(
            stat.S_ISREG(info.st_mode)
            and (info.st_size, info.st_dev, info.st_ino, info.st_mtime_ns)
            == (
                descriptor["bytes"],
                descriptor["device"],
                descriptor["inode"],
                descriptor["mtime_ns"],
            ),
            "INPUT_IDENTITY_MISMATCH",
        )
        debit = info.st_size + 1
        require(self.read_debit + debit <= self.read_limit, "INPUT_CAP")
        self.read_debit += debit
        self.read_calls += 1
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            actual = os.fstat(fd)
            require(
                stat.S_ISREG(actual.st_mode)
                and (actual.st_dev, actual.st_ino, actual.st_size, actual.st_mtime_ns)
                == (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns),
                "INPUT_IDENTITY_MISMATCH",
            )
            chunks = []
            left = debit
            while left:
                chunk = os.read(fd, min(65536, left))
                if not chunk:
                    break
                chunks.append(chunk)
                left -= len(chunk)
            raw = b"".join(chunks)
            require(
                len(raw) == descriptor["bytes"] and digest(raw) == descriptor["sha256"],
                "INPUT_CONTENT_CONFLICT",
            )
            return raw
        finally:
            os.close(fd)


def read_csv_rows(budget: ArtifactBudget, descriptor, authorize):
    raw = budget.read(descriptor, authorize)
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8")))
        require(tuple(reader.fieldnames or ()) == COLUMNS, "SCHEMA_INVALID")
        result = []
        seen = set()
        for row in reader:
            require(len(result) < budget.max_rows, "ROW_CAP")
            value = normalize_row(row)
            key = (value["instrument_id"], value["session"])
            require(key not in seen, "DUPLICATE_STOCK_DAY")
            seen.add(key)
            result.append(value)
        return tuple(result)
    except (UnicodeError, csv.Error) as error:
        raise InputError("CSV_INVALID") from error


def open_database(path: Path, *, read_only: bool):
    import duckdb

    require(duckdb.__version__ == "1.5.4", "DUCKDB_VERSION_UNSUPPORTED")
    connection = duckdb.connect(
        str(path),
        read_only=read_only,
        config={
            "threads": 4,
            "memory_limit": "2GiB",
            "enable_external_access": False,
            "autoinstall_known_extensions": False,
            "autoload_known_extensions": False,
            "max_temp_directory_size": "0B",
        },
    )
    try:
        settings = connection.execute(
            "SELECT current_setting('threads'), current_setting('memory_limit'), current_setting('enable_external_access'), current_setting('max_temp_directory_size')"
        ).fetchone()
        require(
            settings is not None
            and settings[0] == 4
            and settings[1] == "2.0 GiB"
            and settings[2] is False
            and settings[3] == "0 bytes",
            "DUCKDB_SETTINGS_INVALID",
        )
        return connection
    except BaseException:
        connection.close()
        raise


def read_duckdb_rows(budget: ArtifactBudget, descriptor, authorize):
    # Read only verified bytes. Neither a pathname reopen nor pre/post hashes
    # prevent ABA substitution; a kernel-sealed private memfd does.
    raw = budget.read(descriptor, authorize)
    require(
        hasattr(os, "memfd_create") and hasattr(fcntl, "F_ADD_SEALS"),
        "PINNED_DATABASE_UNSUPPORTED",
    )
    fd = os.memfd_create("retro-frozen-duckdb", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    connection = None
    try:
        offset = 0
        while offset < len(raw):
            offset += os.write(fd, raw[offset:])
        fcntl.fcntl(
            fd,
            fcntl.F_ADD_SEALS,
            fcntl.F_SEAL_WRITE
            | fcntl.F_SEAL_GROW
            | fcntl.F_SEAL_SHRINK
            | fcntl.F_SEAL_SEAL,
        )
        connection = open_database(Path("/proc/self/fd") / str(fd), read_only=True)
        connection.execute("BEGIN TRANSACTION")
        cursor = connection.execute(
            "SELECT "
            + ",".join(COLUMNS)
            + " FROM bars ORDER BY instrument_id,session LIMIT ?",
            [budget.max_rows + 1],
        )
        result = []
        seen = set()
        for values in cursor.fetchall():
            require(len(result) < budget.max_rows, "ROW_CAP")
            value = normalize_row(dict(zip(COLUMNS, values, strict=True)))
            key = (value["instrument_id"], value["session"])
            require(key not in seen, "DUPLICATE_STOCK_DAY")
            seen.add(key)
            result.append(value)
        connection.execute("COMMIT")
        return tuple(result)
    finally:
        try:
            if connection is not None:
                connection.close()
        finally:
            os.close(fd)


def fixture_calendar(weeks=110):
    start = date(2000, 1, 3)
    return tuple(
        (start + timedelta(days=i), (start + timedelta(days=i)).weekday() < 5)
        for i in range(weeks * 7)
    )


def fixture_source_rows(days):
    opened = [day for day, is_open in days if is_open]
    for i, day in enumerate(opened):
        for stock, identifier in enumerate((*IDS, "801150.SI")):
            if stock == 2:
                close = Decimal(1000) + Decimal(".1") * i
                volume = None
            else:
                changes = tuple(
                    Decimal(".4") if (j // 5 + stock * 2) % 4 < 2 else Decimal("-.1")
                    for j in range(20)
                )
                n = i + 1
                close = (
                    Decimal(100)
                    + (n // 20) * sum(changes, Decimal(0))
                    + sum(changes[: n % 20], Decimal(0))
                )
                volume = Decimal((50, 200, 100, 100)[(i // 5 + stock * 2) % 4])
            yield {
                "instrument_id": identifier,
                "session": day.isoformat(),
                "close": str(close),
                "volume": None if volume is None else str(volume),
                "quantity_unit": None if stock == 2 else "synthetic_share",
                "listed": None if stock == 2 else True,
                "suspended": None if stock == 2 else False,
                "comparable": True,
                "up_limit": None if stock == 2 else str(close * Decimal("1.1")),
                "down_limit": None if stock == 2 else str(close * Decimal(".9")),
            }


def write_fixture_source(budget, days, kind):
    require(kind in ("csv", "duckdb"), "FORMAT_UNSUPPORTED")
    rows = tuple(fixture_source_rows(days))
    require(len(rows) <= budget.max_rows, "ROW_CAP")
    if kind == "csv":
        text = io.StringIO()
        fieldnames: list[str] = list(COLUMNS)
        writer = csv.DictWriter(text, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    k: ("" if v is None else str(v).lower() if type(v) is bool else v)
                    for k, v in row.items()
                }
            )
        return budget.write("source.csv", text.getvalue().encode())
    target = budget.path("source.duckdb")
    require(not target.exists(), "OUTPUT_CONFLICT")
    connection = open_database(target, read_only=False)
    try:
        connection.execute(
            "CREATE TABLE bars(instrument_id VARCHAR,session VARCHAR,close DOUBLE,volume DOUBLE,quantity_unit VARCHAR,listed BOOLEAN,suspended BOOLEAN,comparable BOOLEAN,up_limit DOUBLE,down_limit DOUBLE)"
        )
        connection.executemany(
            "INSERT INTO bars VALUES (?,?,?,?,?,?,?,?,?,?)",
            [[row[k] for k in COLUMNS] for row in rows],
        )
    finally:
        connection.close()
    descriptor = budget.descriptor("source.duckdb")
    require(
        budget.write_debit + descriptor["bytes"] <= budget.write_limit, "OUTPUT_CAP"
    )
    budget.write_debit += descriptor["bytes"]
    budget.files["source.duckdb"] = descriptor
    return descriptor


@dataclass(frozen=True)
class ReadAdmission:
    """Host composition-root dependency, never deserialized from a source/approval flag.

    authorize must enforce actual runtime permission as well as the public
    reservation. The current CLI wires only its internally generated fixtures.
    """

    phase: str
    receipt: RetrospectiveReservationReceipt
    source_slice: Any
    authorize: Callable[[], None]
    catalog_assertion: (
        Callable[
            [Path, RetrospectiveSourceSlice, RetrospectiveReservationReceipt], None
        ]
        | None
    ) = None
    catalog_governance: Mapping[str, Any] | None = None


CATALOG_SQL = (
    "SELECT table_name,column_name,data_type,column_index,is_nullable "
    "FROM duckdb_columns() WHERE schema_name='main' AND "
    "regexp_replace(lower(column_name),'_','','g') IN "
    "('caldate','calendardate','tradingday','tradedate','isopen','exchange',"
    "'tscode','symbol','listdate','delistdate','listed','isactive','suspended',"
    "'suspendtype','suspendtiming','uplimit','downlimit','adjfactor','comparable',"
    "'quantityunit','source','updateat') ORDER BY table_name,column_index LIMIT 257"
)
CATALOG_RESULT_BYTES = 256 * 1024
CATALOG_AUDIT_BYTES = 384 * 1024
CATALOG_CLOSE_BYTES = 128 * 1024
CATALOG_WRITER_BYTES = CATALOG_RESULT_BYTES + CATALOG_AUDIT_BYTES + CATALOG_CLOSE_BYTES


def catalog_scope_hash(source_path: Path) -> str:
    """Declaration hash only. No path stat, source bytes, permission or provider revision."""
    path = Path(source_path)
    require(
        path.is_absolute()
        and str(path) == os.path.abspath(path)
        and "\x00" not in str(path)
        and len(str(path)) <= 4096,
        "CATALOG_PATH_INVALID",
    )
    require(len(path.parents) <= 6, "CATALOG_PATH_DEPTH")
    return wire_hash(
        core.canonical_bytes(
            {
                "kind": "retrospective-catalog-only-v2",
                "path": str(path),
                "sql": CATALOG_SQL,
                "read_only": True,
                "source_rows": False,
                "row_cap": 256,
                "text_character_cap": 128,
                "execute_attempt_cap": 5,
                "result_bytes": CATALOG_RESULT_BYTES,
                "audit_bytes": CATALOG_AUDIT_BYTES,
                "close_reserve_bytes": CATALOG_CLOSE_BYTES,
                "governance_original_content_bytes": 256 * 1024,
                "governance_private_peak_bytes": 640 * 1024,
                "governance_account_bytes": 128 * 1024,
                "governance_private_clock_calls": 8,
                "governance_sdk_calls_upper_reserved": 128,
                "governance_content_read_upper_bytes": 256 * 1024**2,
                "governance_content_write_upper_bytes": 64 * 1024**2,
                "governance_program_profile": "PINNED_EXACT_SDK_TWO_DECL_ONE_SAMPLE_V1",
                "host_authority": "LIVE_AF_UNIX_PARENT_CALLBACK_NOT_DATA_GRANT",
                "host_request_cap": 128,
                "host_request_bytes": 256,
                "host_response_bytes": 32,
                "worker_packet_bytes": 16 * 1024,
                "native_source_bytes": "UNKNOWN_NOT_A_PHYSICAL_IO_CAP",
            }
        )
    )


def validate_catalog_admission(source_path: Path, admission: ReadAdmission) -> None:
    # Only a trusted composition root may supply this callback. A receipt alone
    # and an externally supplied approval flag are never runtime permission.
    admission.authorize()
    require(admission.phase == "INPUT_QUALIFICATION", "CATALOG_PHASE_CONFLICT")
    s, r = admission.source_slice, admission.receipt
    require(admission.catalog_assertion is not None, "CATALOG_ROOT_BINDING_MISSING")
    require(
        type(s) is RetrospectiveSourceSlice
        and type(r) is RetrospectiveReservationReceipt,
        "CATALOG_ADMISSION_INVALID",
    )
    require(
        s.source_scope_hash == catalog_scope_hash(source_path)
        and s.input_manifest_hash is None
        and r.study_ref is None
        and r.purpose == r.record.purpose == "discovery"
        and r.read_task_ref.artifact_type == "retrospective_input_read_task"
        and r.record.dataset_revision == s.capture_revision
        and r.record.interval_start == s.interval_start
        and r.record.interval_end == s.interval_end,
        "CATALOG_SCOPE_CONFLICT",
    )
    if admission.catalog_assertion is None:
        raise InputError("CATALOG_ROOT_BINDING_MISSING")
    admission.catalog_assertion(source_path, s, r)


def catalog_resource_evidence():
    from experiments.a_share_price_volume_retro_resources_v1 import (
        worker_resource_evidence,
    )

    value = worker_resource_evidence()
    require(
        value["memory_max"] == 6 * 1024**3
        and os.environ.get("OPENBLAS_NUM_THREADS") == "1",
        "RESOURCE_NOT_ENFORCED",
    )
    value.pop("allocated_bytes", None)
    value["scope"] = "kernel setting at catalog worker entry, not workload peak"
    return value


def inspect_lake_catalog(
    source_path: Path, budget: ArtifactBudget, admission: ReadAdmission
):
    """Guarded fixed metadata operation. Not wired to a real CLI or human grant.

    All runtime authority must come from the trusted ReadAdmission callback;
    public owner/reservation validation belongs there, as for SnapshotReader.
    No source table rows, whole DB copy, arbitrary SQL, retry or follow-up.
    """
    source_path = Path(source_path)
    validate_catalog_admission(source_path, admission)
    resource = catalog_resource_evidence()
    require(
        budget.write_limit - budget.write_debit >= CATALOG_WRITER_BYTES,
        "CATALOG_OUTPUT_CAP",
    )
    names = (
        "catalog-attempt.reserve.json",
        "catalog-events.jsonl",
        "catalog-columns.json",
        "catalog-close.json",
    )
    require(
        not any(budget.path(name).exists() for name in names),
        "CATALOG_ATTEMPT_ALREADY_RESERVED",
    )
    # Debit the entire close allowance before any source operation; never refund.
    budget.write_debit += CATALOG_CLOSE_BYTES
    audit_used = 0
    counts = {
        "source_open_attempts": 0,
        "connection_attempts": 0,
        "sql_attempts": 0,
        "ancestor_stats": 0,
        "source_stats": 0,
        "wal_stats": 0,
        "fd_stats": 0,
    }
    conn = None
    fd = None
    begun = False
    connection_closed = True
    fd_closed = True
    failure = None
    cause = None
    interruption: BaseException | None = None
    rows = []
    identity = None

    def audit(name, value, *, append=False):
        nonlocal audit_used
        raw = core.canonical_bytes(value) + (b"\n" if append else b"")
        require(audit_used + len(raw) <= CATALOG_AUDIT_BYTES, "CATALOG_AUDIT_CAP")
        audit_used += len(raw)
        if append:
            budget.append_event(name, value)
        else:
            budget.write(name, raw)

    def event(stage):
        audit(
            "catalog-events.jsonl",
            {"stage": stage, "counts": dict(counts)},
            append=True,
        )

    def guard():
        validate_catalog_admission(source_path, admission)

    def remember_interrupt(error: BaseException):
        nonlocal interruption
        if not isinstance(error, Exception) and interruption is None:
            interruption = error

    def checked_stat(path, kind):
        guard()
        counts[kind] += 1
        event(kind.upper() + "_ATTEMPT")
        try:
            return os.lstat(path)
        except FileNotFoundError:
            if kind == "wal_stats":
                return None
            raise

    def signature(info):
        return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)

    def sql(statement, stage):
        if statement != "ROLLBACK":
            guard()  # Revoke before each new read/commit; cleanup remains permitted.
        if conn is None:
            raise InputError("CATALOG_CONNECTION_MISSING")
        require(counts["sql_attempts"] < 5, "CATALOG_SQL_CAP")
        counts["sql_attempts"] += 1
        event(stage + "_ATTEMPT")
        return conn.execute(statement)

    try:
        audit(
            "catalog-attempt.reserve.json",
            {
                "source_scope_hash": admission.source_slice.source_scope_hash,
                "capture_revision": admission.source_slice.capture_revision,
                "source": str(source_path),
                "close_bytes_reserved": CATALOG_CLOSE_BYTES,
                "governance_verification": admission.catalog_governance,
                "resource": resource,
                "physical_source_bytes": None,
            },
        )
        for parent in reversed(source_path.parents):
            info = checked_stat(parent, "ancestor_stats")
            require(
                info is not None
                and stat.S_ISDIR(info.st_mode)
                and not stat.S_ISLNK(info.st_mode),
                "CATALOG_SOURCE_LINK",
            )
        first = checked_stat(source_path, "source_stats")
        if first is None:
            raise InputError("CATALOG_SOURCE_NONREGULAR")
        require(stat.S_ISREG(first.st_mode), "CATALOG_SOURCE_NONREGULAR")
        wal = Path(str(source_path) + ".wal")
        require(checked_stat(wal, "wal_stats") is None, "CATALOG_WAL_PRESENT")
        guard()
        counts["source_open_attempts"] += 1
        event("SOURCE_OPEN_ATTEMPT")
        fd = os.open(source_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        fd_closed = False
        counts["fd_stats"] += 1
        actual = os.fstat(fd)
        require(
            stat.S_ISREG(actual.st_mode) and signature(actual) == signature(first),
            "CATALOG_SOURCE_CHANGED",
        )
        identity = {
            "device": actual.st_dev,
            "inode": actual.st_ino,
            "bytes": actual.st_size,
            "mtime_ns": actual.st_mtime_ns,
        }
        guard()
        counts["connection_attempts"] += 1
        counts["sql_attempts"] += (
            1  # open_database's settings readback, reserved pre-connect.
        )
        connection_closed = False
        event("READ_ONLY_CONNECT_AND_SETTINGS_ATTEMPT")
        conn = open_database(Path("/proc/self/fd") / str(fd), read_only=True)
        require(checked_stat(wal, "wal_stats") is None, "CATALOG_WAL_PRESENT")
        begun = True  # An uncertain BEGIN is not silently treated as no transaction.
        sql("BEGIN TRANSACTION", "BEGIN")
        cursor = sql(CATALOG_SQL, "CATALOG")
        for row in cursor.fetchall():
            require(len(rows) < 256, "CATALOG_ROW_CAP")
            require(
                len(row) == 5
                and all(type(v) is str and len(v) <= 128 for v in row[:3])
                and type(row[3]) is int
                and row[3] > 0
                and type(row[4]) is bool,
                "CATALOG_RESULT_SCHEMA",
            )
            rows.append(tuple(row))
        require(
            len(core.canonical_bytes(rows)) <= CATALOG_RESULT_BYTES,
            "CATALOG_RESULT_CAP",
        )
        counts["fd_stats"] += 1
        final = os.fstat(fd)
        named = checked_stat(source_path, "source_stats")
        require(
            named is not None
            and stat.S_ISREG(named.st_mode)
            and signature(final) == signature(first) == signature(named),
            "CATALOG_SOURCE_CHANGED",
        )
        sql("COMMIT", "COMMIT")
        begun = False
    except BaseException as error:  # noqa: BLE001 -- retain interrupt/close facts before propagation.
        remember_interrupt(error)
        failure = (
            error.code if isinstance(error, InputError) else "CATALOG_IO_OR_SQL_FAILED"
        )
        cause = error
    finally:
        if begun and conn is not None:
            try:
                sql("ROLLBACK", "ROLLBACK")
            except BaseException as error:  # noqa: BLE001 -- interrupted rollback still permits fd cleanup.
                remember_interrupt(error)
                failure, cause = "CATALOG_ROLLBACK_UNVERIFIED", error
        if conn is not None:
            try:
                conn.close()
                connection_closed = True
            except BaseException as error:  # noqa: BLE001 -- interrupted close still permits fd cleanup.
                remember_interrupt(error)
                failure, cause = "CATALOG_CLEANUP_UNVERIFIED", error
        if fd is not None:
            try:
                os.close(fd)
                fd_closed = True
            except BaseException as error:  # noqa: BLE001 -- preserve stop signal while recording unknown fd state.
                remember_interrupt(error)
                failure, cause = "CATALOG_CLEANUP_UNVERIFIED", error

    result = {
        "state": "CATALOG_OBSERVED_NOT_SOURCE_QUALIFIED",
        "source_qualified": False,
        "governance_verification": admission.catalog_governance,
        "columns": tuple(rows),
        "source_identity": identity,
        "counts": dict(counts),
        "physical_source_io_bytes": None,
        "resource": resource,
    }
    if failure is None:
        try:
            raw = core.canonical_bytes(result)
            require(len(raw) <= CATALOG_RESULT_BYTES, "CATALOG_RESULT_CAP")
            budget.write("catalog-columns.json", raw)
        except BaseException as error:  # noqa: BLE001 -- output interrupts still need reserved close.
            remember_interrupt(error)
            failure = (
                error.code if isinstance(error, InputError) else "CATALOG_OUTPUT_FAILED"
            )
            cause = error
    close = {
        "state": "COMPLETE" if failure is None else "FAILED",
        "error_code": failure,
        "interruption_type": None
        if interruption is None
        else type(interruption).__name__,
        **counts,
        "connection_closed": connection_closed,
        "fd_closed": fd_closed,
        "close_bytes_reserved": CATALOG_CLOSE_BYTES,
        "audit_bytes_debited": audit_used,
        "writer_bytes_debited": budget.write_debit,
        "physical_source_io_bytes": None,
        "source_qualified": False,
    }
    try:
        raw = core.canonical_bytes(close)
        require(len(raw) <= CATALOG_CLOSE_BYTES, "CATALOG_CLOSE_CAP")
        with budget.path("catalog-close.json").open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        budget.files["catalog-close.json"] = budget.descriptor("catalog-close.json")
    except BaseException as error:  # Preserve a prior stop on close-write failure.
        remember_interrupt(error)
        if interruption is not None:
            raise interruption from error
        raise InputError("CATALOG_CLOSE_FAILED") from error
    if interruption is not None:
        raise interruption
    if failure is not None:
        raise InputError(failure) from cause
    return result


class SnapshotReader:
    def __init__(self, budget, manifest, plan):
        self.budget = budget
        self.manifest = manifest
        self.plan = plan
        self.open_calls = 0

    def _admit(self, admission, split, outcome):
        admission.authorize()
        expected = split.partition + ("_OUTCOME" if outcome else "_FEATURE")
        if split.partition == "TRAIN" and outcome:
            expected = "TRAIN_FIT"
        require(admission.phase == expected, "READ_PHASE_CONFLICT")
        s = admission.source_slice
        r = admission.receipt
        bound_manifest = {
            key: value
            for key, value in self.manifest.items()
            if key != "input_manifest_hash"
        }
        require(
            wire_hash(core.canonical_bytes(bound_manifest))
            == self.manifest["input_manifest_hash"],
            "INPUT_MANIFEST_BINDING_CONFLICT",
        )
        require(
            dict(self.plan.source_hashes).get("derived_snapshot")
            == self.manifest["snapshot"]["sha256"],
            "INPUT_MANIFEST_BINDING_CONFLICT",
        )
        require(
            r.record.dataset_revision
            == self.plan.dataset_revision
            == s.capture_revision
            and s.input_manifest_hash == self.manifest["input_manifest_hash"]
            and s.source_scope_hash == self.manifest["source_scope_hash"]
            and r.record.interval_start == s.interval_start == instant(split.read_from)
            and r.record.interval_end == s.interval_end == instant(split.read_to),
            "READ_SCOPE_CONFLICT",
        )
        require(
            self.manifest["origin"] in (FIXTURE_ORIGIN, FROZEN_CAPTURE_ORIGIN),
            "SOURCE_ORIGIN_UNSUPPORTED",
        )
        require(
            type(self.plan.fixture_only) is bool
            and self.plan.fixture_only == (self.manifest["origin"] == FIXTURE_ORIGIN),
            "SOURCE_ORIGIN_CONFLICT",
        )

    def _load(self, admission, split, outcome):
        import json

        self._admit(admission, split, outcome)
        raw = self.budget.read(
            self.manifest["snapshot"], lambda: self._admit(admission, split, outcome)
        )
        self.open_calls += 1
        value = json.loads(raw)
        require(
            core.canonical_bytes(value) == raw
            and value["origin"] == self.manifest["origin"],
            "SNAPSHOT_SCHEMA_INVALID",
        )
        require(
            value["capture_revision"] == self.plan.dataset_revision
            and value["source_scope_hash"] == self.manifest["source_scope_hash"]
            and value["captured_at"] == self.manifest["captured_at"]
            and value["observed_at"]
            == self.manifest["observed_at"]
            == utc(self.plan.snapshot_observed_at)
            and core.canonical_bytes(value["calendar"])
            == core.canonical_bytes(
                [[row.day.isoformat(), row.is_open] for row in self.plan.calendar]
            ),
            "SNAPSHOT_IDENTITY_CONFLICT",
        )
        classes = self.plan.cohort_classifications
        require(
            tuple(row["instrument_id"] for row in value["cohort"]) == self.plan.cohort
            and len(value["cohort"]) == len(classes),
            "COHORT_IDENTITY_CONFLICT",
        )
        for row, classification in zip(value["cohort"], classes, strict=True):
            require(
                core.canonical_bytes(
                    (
                        row["instrument_id"],
                        row["venue"],
                        row["industry_code"],
                        row["ordinary_a_share"],
                        row["selected"],
                    )
                )
                == core.canonical_bytes(
                    (
                        classification.instrument_id,
                        classification.venue,
                        classification.industry_code,
                        classification.ordinary_a_share,
                        classification.selected,
                    )
                ),
                "COHORT_IDENTITY_CONFLICT",
            )
        index = {}
        for row in value["rows"]:
            identifier = row["instrument_id"]
            day = _date(row["session"])
            key = (identifier, day)
            require(key not in index, "DUPLICATE_STOCK_DAY")
            index[key] = row
        return index

    def _bar(self, index, identifier, day, *, price_only) -> core.DailyBar | None:
        row = index.get((identifier, day))
        if row is None:
            return None
        p = core.SnapshotProvenance(
            self.plan.dataset_revision,
            "derived_snapshot",
            self.manifest["snapshot"]["sha256"],
            datetime.combine(day, time(15), core.SHANGHAI),
            datetime.fromisoformat(self.manifest["captured_at"]),
            self.plan.snapshot_observed_at,
            None,
        )
        return core.DailyBar(
            day,
            number(row["close"]),
            p,
            None if price_only else number(row["volume"]),
            None if price_only else row["quantity_unit"],
            row["listed"],
            row["suspended"],
            row["comparable"],
            None if price_only else number(row["up_limit"]),
            None if price_only else number(row["down_limit"]),
        )

    def views(self, admission, split, *, outcome=False):
        index = self._load(admission, split, outcome)
        sessions = tuple(
            row.day
            for row in self.plan.calendar
            if row.is_open and split.read_from <= row.day < split.read_to
        )
        last = {
            week_start(day): day
            for day in sessions
            if split.decision_from <= day < split.decision_to
        }
        classes = {row.instrument_id: row for row in self.plan.cohort_classifications}
        result = []
        for day in sorted(last.values()):
            t = sessions.index(day)
            needed = sessions[
                max(0, t - 64) : min(len(sessions), t + 6 if outcome else t + 1)
            ]
            for identifier in self.plan.cohort:
                key = core.RetrospectiveSampleKey(
                    identifier,
                    day,
                    datetime.combine(day, time(23, 59, 59), core.SHANGHAI),
                    self.plan.dataset_revision,
                )
                stock = tuple(
                    bar
                    for d in needed
                    if (bar := self._bar(index, identifier, d, price_only=outcome))
                    is not None
                )
                if outcome:
                    result.append(core.OutcomeView(key, split.partition, stock))
                else:
                    industry_rows: list[core.DailyBar] = []
                    for d in needed:
                        industry_bar = self._bar(index, "801150.SI", d, price_only=True)
                        if industry_bar is not None:
                            industry_rows.append(industry_bar)
                    industry = tuple(industry_rows)
                    result.append(
                        core.FeatureView(
                            key, split.partition, classes[identifier], stock, industry
                        )
                    )
        return tuple(sorted(result, key=lambda row: row.key))
