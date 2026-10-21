"""C0 fixed raw-material producer. Code capability is NEVER a source grant.

No model, bars, Study or source qualification is produced. Fake inputs are a
separate scope kind. Real use requires the exact live trusted Root admission.
"""

from __future__ import annotations

import gzip
import hashlib
import inspect
import io
import json
import os
import re
import stat
import tempfile
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, fields, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.request import ProxyHandler, build_opener

from crypto_quant_domain import ArtifactEnvelope, canonical_bytes, canonical_sha256
from crypto_quant_foundation import LocalFoundation
from crypto_quant_research import (
    PublishedRetrospectiveArtifact,
    RetrospectiveReadTask,
    RetrospectiveStudyProtocol,
    publish_retrospective_protocol,
    publish_retrospective_read_task,
)
from crypto_quant_validation import (
    RetrospectiveReservationReceipt,
    SampleConsumptionLedger,
    reserve_retrospective_read,
)

from experiments import a_share_price_volume_retro_inputs_v1 as inputs
from experiments.a_share_price_volume_retro_resources_v1 import RetroResourceLimits

from .proxy import NoRedirect, ProxyAPI, ProxyCapture, read_proxy_token

PROGRAM = "d009-existing-members-tushare-raw-v1"
FAKE = "SYNTHETIC_CAPTURE_FIXTURE"
REAL = "CURRENT_SNAPSHOT_RAW_CAPTURE"
ENDPOINT = "https://fast.xiaodefa.cn/"
MEMBER_FIELDS = ("l1_code", "ts_code", "in_date", "out_date", "is_new")
SOURCE_FIELDS = {
    "stock_basic": "ts_code,symbol,name,market,list_date,delist_date,exchange,curr_type",
    "trade_cal": "exchange,cal_date,is_open,pretrade_date",
    "daily": "ts_code,trade_date,close,vol,pre_close",
    "stk_limit": "trade_date,ts_code,pre_close,up_limit,down_limit",
    "sw_daily": "ts_code,trade_date,close",
}
ROW_CAPS = {"stock_basic": 6000, "daily": 6000, "stk_limit": 5800, "sw_daily": 4000}
LOG = "research.artifacts.v1"
SAMPLE = "validation.sample-consumption.v1"
GOV_SOURCE = 256 * 1024
GOV_PRIVATE = 640 * 1024
GOV_ACCOUNT = 128 * 1024
GOV_PREFIX = 280 * 1024
GOV_READ = 256 * 1024**2
GOV_WRITE = 64 * 1024**2
PROJECT = Path(__file__).absolute().parents[2]
_SEAL = object()


class CaptureError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def require(value, code):
    if not value:
        raise CaptureError(code)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def stamp() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _path(value: str) -> Path:
    require(
        type(value) is str and 0 < len(value) <= 4096 and "\x00" not in value,
        "CAPTURE_PATH",
    )
    p = Path(value)
    require(p.is_absolute() and str(p) == os.path.abspath(p), "CAPTURE_PATH")
    return p


def _day(value: Any, *, compact=False) -> date:
    pattern = r"[0-9]{8}" if compact else r"[0-9]{4}-[0-9]{2}-[0-9]{2}"
    require(type(value) is str and re.fullmatch(pattern, value), "CAPTURE_DATE")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise CaptureError("CAPTURE_DATE") from None


def _days(start: date, end: date):
    for i in range((end - start).days):
        yield start + timedelta(days=i)


def _signature(info):
    return (
        info.st_dev,
        info.st_ino,
        info.st_size,
        info.st_mtime_ns,
        info.st_mode,
        info.st_uid,
        info.st_nlink,
    )


def _read_regular(path: Path, cap: int) -> tuple[bytes, tuple]:
    inputs.no_links(path)
    before = path.stat(follow_symlinks=False)
    require(
        stat.S_ISREG(before.st_mode)
        and before.st_uid == os.getuid()
        and before.st_nlink == 1
        and before.st_size <= cap,
        "CAPTURE_FILE_POLICY",
    )
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    original = None
    try:
        require(_signature(os.fstat(fd)) == _signature(before), "CAPTURE_FILE_CHANGED")
        chunks = []
        left = cap + 1
        while left:
            part = os.read(fd, min(65536, left))
            if not part:
                break
            chunks.append(part)
            left -= len(part)
        raw = b"".join(chunks)
        require(
            len(raw) == before.st_size
            and len(raw) <= cap
            and _signature(os.fstat(fd)) == _signature(before)
            and _signature(path.stat(follow_symlinks=False)) == _signature(before),
            "CAPTURE_FILE_CHANGED",
        )
        return raw, _signature(before)
    except BaseException as error:
        original = error
        raise
    finally:
        try:
            os.close(fd)
        except BaseException as cleanup:
            if original is not None:
                raise original from cleanup
            raise


def _sync_directory(path: Path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    original = None
    try:
        os.fsync(fd)
    except BaseException as error:
        original = error
        raise
    finally:
        try:
            os.close(fd)
        except BaseException as cleanup:
            if original is not None:
                raise original from cleanup
            raise


def _make_directory(path: Path, *, exist_ok=False):
    inputs.no_links(path)
    missing = []
    current = path
    while not current.exists():
        require(len(missing) < 64, "CAPTURE_PATH_DEPTH")
        missing.append(current)
        current = current.parent
    require(current.is_dir() and (missing or exist_ok), "CAPTURE_DIRECTORY_EXISTS")
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
        _sync_directory(directory)
        _sync_directory(directory.parent)


def _write_regular(path: Path, raw: bytes, *, append_size: int | None = None):
    inputs.no_links(path)
    flags = os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK
    flags |= os.O_EXCL if append_size is None else os.O_APPEND
    fd = os.open(path, flags, 0o600)
    original = None
    try:
        info = os.fstat(fd)
        require(
            stat.S_ISREG(info.st_mode)
            and info.st_uid == os.getuid()
            and info.st_nlink == 1,
            "CAPTURE_OUTPUT_POLICY",
        )
        if append_size is not None:
            require(info.st_size == append_size, "CAPTURE_JOURNAL_CHANGED")
        offset = 0
        while offset < len(raw):
            written = os.write(fd, raw[offset:])
            require(written > 0, "CAPTURE_WRITE_FAILED")
            offset += written
        os.fsync(fd)
    except BaseException as error:
        original = error
        raise
    finally:
        try:
            os.close(fd)
        except BaseException as cleanup:
            if original is not None:
                raise original from cleanup
            raise
        try:
            _sync_directory(path.parent)
        except BaseException as cleanup:
            if original is not None:
                raise original from cleanup
            raise


def _unique(pairs):
    result = {}
    for k, v in pairs:
        require(k not in result, "CAPTURE_DUPLICATE_JSON_KEY")
        result[k] = v
    return result


def _nonfinite(_):
    raise CaptureError("CAPTURE_NONFINITE")


def _json(raw) -> Any:
    try:
        return json.loads(
            raw,
            parse_float=Decimal,
            object_pairs_hook=_unique,
            parse_constant=_nonfinite,
        )
    except (UnicodeError, ValueError, TypeError) as error:
        if isinstance(error, CaptureError):
            raise
        raise CaptureError("CAPTURE_JSON") from None


@dataclass(frozen=True, slots=True)
class MemberFile:
    role: str
    path: str
    sha256: str
    bytes: int

    def __post_init__(self):
        require(self.role in ("receipt", "Y", "N"), "CAPTURE_MEMBER_ROLE")
        _path(self.path)
        require(
            type(self.sha256) is str and re.fullmatch(r"[0-9a-f]{64}", self.sha256),
            "CAPTURE_MEMBER_HASH",
        )
        require(
            type(self.bytes) is int and 0 < self.bytes <= GOV_SOURCE,
            "CAPTURE_MEMBER_CAP",
        )


@dataclass(frozen=True, slots=True)
class CaptureLimits:
    max_requests: int
    response_bytes: int
    timeout_seconds: int
    wire_bytes: int
    decoded_bytes: int
    read_bytes: int
    write_bytes: int
    raw_bytes: int
    audit_bytes: int
    close_bytes: int
    temporary_bytes: int
    max_rows: int
    max_cell_chars: int
    minimum_interval_ms: int

    def __post_init__(self):
        require(
            all(type(v) is int and v > 0 for v in asdict(self).values()),
            "CAPTURE_LIMITS",
        )
        require(
            self.max_requests <= 2000
            and self.response_bytes <= 16 * 1024**2
            and self.timeout_seconds <= 60
            and self.max_cell_chars <= 4096
            and 500 <= self.minimum_interval_ms <= 60000
            and self.audit_bytes >= 16384
            and self.close_bytes >= 16384
            and self.write_bytes >= self.close_bytes + self.audit_bytes,
            "CAPTURE_LIMITS",
        )


@dataclass(frozen=True, slots=True)
class CaptureSpec:
    mode: str
    output: str
    credential_file: str
    member_files: tuple[MemberFile, ...]
    start: str
    end: str
    bulk: bool
    limits: CaptureLimits
    resources: RetroResourceLimits
    fixture_root: str | None
    prior_observation_hash: str
    endpoint: str = ENDPOINT
    program: str = PROGRAM

    def __post_init__(self):
        require(
            self.mode in (FAKE, REAL)
            and self.endpoint == ENDPOINT
            and self.program == PROGRAM
            and type(self.bulk) is bool,
            "CAPTURE_SPEC",
        )
        output = _path(self.output)
        credential = _path(self.credential_file)
        require(
            type(self.member_files) is tuple
            and all(type(m) is MemberFile for m in self.member_files)
            and tuple(m.role for m in self.member_files) == ("receipt", "Y", "N")
            and len({m.path for m in self.member_files}) == 3,
            "CAPTURE_MEMBER_SPEC",
        )
        require(type(self.limits) is CaptureLimits, "CAPTURE_LIMITS")
        require(
            type(self.resources) is RetroResourceLimits
            and self.resources.memory_bytes == 6 * 1024**3
            and self.resources.max_attempts == 1,
            "CAPTURE_RESOURCE_LIMITS",
        )
        require(
            0 < (_day(self.end) - _day(self.start)).days <= 6000
            and _day(self.start) <= date(2024, 10, 1)
            and _day(self.end) >= date(2024, 11, 1),
            "CAPTURE_DATE_SPAN",
        )
        require(
            type(self.prior_observation_hash) is str
            and re.fullmatch(r"sha256:[0-9a-f]{64}", self.prior_observation_hash),
            "CAPTURE_PRIOR_HASH",
        )
        sources = [credential, *(Path(m.path) for m in self.member_files)]
        require(
            all(
                p != output and output not in p.parents and p not in output.parents
                for p in sources
            ),
            "CAPTURE_ROOT_OVERLAP",
        )
        if self.mode == FAKE:
            root = _path(self.fixture_root) if self.fixture_root is not None else None
            require(
                root is not None
                and all(root in p.parents for p in sources)
                and root in output.parents,
                "CAPTURE_FIXTURE_SCOPE",
            )
        else:
            require(self.fixture_root is None, "CAPTURE_FIXTURE_SCOPE")

    @property
    def payload(self):
        return asdict(self)

    @classmethod
    def from_payload(cls, payload):
        require(
            type(payload) is dict and set(payload) == {f.name for f in fields(cls)},
            "CAPTURE_SPEC_FIELDS",
        )
        value = dict(payload)
        require(
            type(value["member_files"]) in (list, tuple)
            and type(value["limits"]) is dict
            and type(value["resources"]) is dict,
            "CAPTURE_SPEC_FIELDS",
        )
        try:
            value["member_files"] = tuple(
                MemberFile(**m) for m in value["member_files"]
            )
            value["limits"] = CaptureLimits(**value["limits"])
            value["resources"] = RetroResourceLimits(**value["resources"])
            return cls(**value)
        except (TypeError, KeyError):
            raise CaptureError("CAPTURE_SPEC_FIELDS") from None


def capture_scope_hash(spec: CaptureSpec) -> str:
    require(type(spec) is CaptureSpec, "CAPTURE_SPEC")
    return canonical_sha256(
        (
            "d009-source-capture-scope-v1",
            spec.payload,
            SOURCE_FIELDS,
            ROW_CAPS,
            {
                "sdk_calls": 128,
                "sdk_read": GOV_READ,
                "sdk_write": GOV_WRITE,
                "governance_content": 1024**2,
                "host_checks": 16384,
            },
        )
    )


def capture_adapter_hash() -> str:
    paths = (
        "experiments/a_share_ingestion/proxy.py",
        "experiments/a_share_ingestion/retro_capture_v1.py",
        "experiments/run_a_share_price_volume_retro_real_v1.py",
        "experiments/a_share_price_volume_retro_inputs_v1.py",
        "experiments/a_share_price_volume_retro_resources_v1.py",
    )
    return canonical_sha256(
        (
            "source-capture-adapter-v1",
            tuple(
                (p, "sha256:" + digest(_read_regular(PROJECT / p, 256 * 1024)[0]))
                for p in paths
            ),
        )
    )


class CaptureBudget:
    """One nonresumable account. Failure and EOF sentinels are never refunded."""

    def __init__(self, root: Path, spec: CaptureSpec, authorize: Callable[[], None]):
        authorize()
        require(type(spec) is CaptureSpec, "CAPTURE_SPEC")
        self.spec, self.authorize = spec, authorize
        self.root = Path(root).absolute()
        require(self.root == Path(spec.output) / "data", "CAPTURE_ROOT_BINDING")
        inputs.no_links(self.root)
        require(not self.root.exists(), "CAPTURE_ACCOUNT_EXISTS")
        _make_directory(self.root)
        self.used: dict[str, int] = dict.fromkeys(
            ("requests", "wire", "decoded", "read", "write", "raw", "audit", "rows"), 0
        )
        self.used["write"] = spec.limits.close_bytes
        self.closed = self.poisoned = self.close_verified = False
        self.journal_bytes = 0
        self.files: list[dict[str, Any]] = []
        self._audit_write(
            "reserve.json",
            canonical_bytes(
                {
                    "scope_hash": capture_scope_hash(spec),
                    "limits": asdict(spec.limits),
                    "close_reserved": spec.limits.close_bytes,
                    "no_refund": True,
                }
            ),
        )

    def summary(self):
        return {
            **self.used,
            "closed": self.closed,
            "poisoned": self.poisoned,
            "close_verified": self.close_verified,
            "close_reserved": self.spec.limits.close_bytes,
        }

    def _audit_write(self, name, raw, *, append=False):
        limit = self.spec.limits
        require(
            self.used["audit"] + len(raw) <= limit.audit_bytes
            and self.used["write"] + len(raw) <= limit.write_bytes,
            "CAPTURE_AUDIT_CAP",
        )
        self.used["audit"] += len(raw)
        self.used["write"] += len(raw)
        try:
            _write_regular(
                self.root / name,
                raw,
                append_size=self.journal_bytes if append else None,
            )
        except BaseException:
            self.poisoned = True
            raise
        if append:
            self.journal_bytes += len(raw)

    def reserve(self, event, **debits):
        self.authorize()
        require(not self.closed and not self.poisoned, "CAPTURE_BUDGET_CLOSED")
        require(
            type(event) is str
            and re.fullmatch(r"[A-Z_]{1,64}", event)
            and set(debits) <= set(self.used)
            and all(type(v) is int and v >= 0 for v in debits.values()),
            "CAPTURE_DEBIT",
        )
        limits = self.spec.limits
        ceiling = {
            "requests": limits.max_requests,
            "wire": limits.wire_bytes,
            "decoded": limits.decoded_bytes,
            "read": limits.read_bytes,
            "write": limits.write_bytes,
            "raw": limits.raw_bytes,
            "audit": limits.audit_bytes,
            "rows": limits.max_rows,
        }
        allowed = all(self.used[k] + v <= ceiling[k] for k, v in debits.items())
        if allowed:
            for k, v in debits.items():
                self.used[k] += v
        raw = (
            canonical_bytes(
                {
                    "event": event,
                    "allowed": allowed,
                    "debits": debits,
                    "reserved": dict(self.used),
                }
            )
            + b"\n"
        )
        try:
            self._audit_write("debits.jsonl", raw, append=True)
        except BaseException:
            self.poisoned = True
            raise
        if not allowed:
            self.poisoned = True
            raise CaptureError("CAPTURE_BUDGET_EXHAUSTED")

    def write_raw(self, name: str, raw: bytes):
        require(
            type(raw) is bytes and Path(name).name == name and name.endswith(".bin"),
            "CAPTURE_OUTPUT_NAME",
        )
        require(len(raw) <= self.spec.limits.temporary_bytes, "CAPTURE_TEMP_CAP")
        self.reserve("RAW_WRITE", raw=len(raw), write=len(raw))
        try:
            _write_regular(self.root / name, raw)
        except BaseException:
            self.poisoned = True
            raise
        descriptor = {"name": name, "bytes": len(raw), "sha256": digest(raw)}
        self.files.append(descriptor)
        return descriptor

    def write_audit(self, name: str, raw: bytes):
        self.authorize()
        require(not self.closed and not self.poisoned, "CAPTURE_BUDGET_CLOSED")
        require(
            type(name) is str and re.fullmatch(r"[a-z0-9-]+\.json", name),
            "CAPTURE_OUTPUT_NAME",
        )
        self._audit_write(name, raw)
        return {"name": name, "bytes": len(raw), "sha256": digest(raw)}

    def write_manifest(self, raw: bytes):
        self.write_audit("manifest.json", raw)

    def close(
        self, state, *, manifest_hash=None, error_code=None, transport_attempts=0
    ):
        require(not self.closed, "CAPTURE_BUDGET_CLOSED")
        self.close_verified = False
        self.closed = True
        raw = canonical_bytes(
            {
                "state": state,
                "manifest_hash": manifest_hash,
                "error_code": error_code,
                "transport_attempts": transport_attempts,
                "real_HTTP_attempts": transport_attempts
                if self.spec.mode == REAL
                else 0,
                "budget": {
                    k: v for k, v in self.summary().items() if k != "close_verified"
                },
            }
        )
        try:
            require(len(raw) <= self.spec.limits.close_bytes, "CAPTURE_CLOSE_CAP")
            _write_regular(self.root / "close.json", raw)
            self.close_verified = True
            return True
        except Exception:  # noqa: BLE001 -- no close failure may be called verified; stops propagate.
            self.poisoned = True
            return False


class _GovernanceBudget:
    """Pinned ISSUE/VERIFY only, disjoint from the catalog validator."""

    def __init__(self, spec, policy):
        policy()
        self.spec, self.policy = spec, policy
        self.root = Path(spec.output) / "governance-account"
        self.gov = Path(spec.output) / "governance"
        inputs.no_links(self.root)
        require(not self.root.exists(), "CAPTURE_GOV_ACCOUNT_EXISTS")
        _make_directory(self.root)
        self.read = self.calls = self.journal = 0
        self.write = GOV_ACCOUNT
        self.programs: set[str] = set()
        self.closed = self.poisoned = False
        self._record(
            "reserve.json",
            canonical_bytes(
                {
                    "scope": capture_scope_hash(spec),
                    "read_limit": GOV_READ,
                    "write_limit": GOV_WRITE,
                    "account_content_reserve": GOV_ACCOUNT,
                    "no_refund": True,
                }
            ),
        )

    def _record(self, name, raw, *, append=False):
        require(
            len(raw) <= 16384 if not append else self.journal + len(raw) <= 96 * 1024,
            "CAPTURE_GOV_ACCOUNT_CAP",
        )
        try:
            _write_regular(
                self.root / name, raw, append_size=self.journal if append else None
            )
        except BaseException:
            self.poisoned = True
            raise
        if append:
            self.journal += len(raw)

    def reserve(self, event, *, read=0, write=0, sdk_calls=0):
        self.policy()
        require(not self.closed and not self.poisoned, "CAPTURE_GOV_ACCOUNT_CLOSED")
        require(
            all(type(v) is int and v >= 0 for v in (read, write, sdk_calls)),
            "CAPTURE_GOV_DEBIT",
        )
        allowed = (
            self.read + read <= GOV_READ
            and self.write + write <= GOV_WRITE
            and self.calls + sdk_calls <= 128
        )
        if allowed:
            self.read += read
            self.write += write
            self.calls += sdk_calls
        self._record(
            "debits.jsonl",
            canonical_bytes(
                {
                    "event": event,
                    "allowed": allowed,
                    "reserved": (self.read, self.write, self.calls),
                }
            )
            + b"\n",
            append=True,
        )
        if not allowed:
            self.poisoned = True
            raise CaptureError("CAPTURE_GOV_BUDGET")

    def program(self, name):
        require(
            name in ("ISSUE", "VERIFY") and name not in self.programs,
            "CAPTURE_GOV_PROGRAM_REUSE",
        )
        self.programs.add(name)
        # Only reuse pins, NOT any catalog path/slice validator or issuer.
        from experiments.run_a_share_price_volume_retro_real_v1 import (
            CATALOG_GOVERNANCE_CODE_PINS,
        )

        origins = (
            (LocalFoundation, "foundation/src/crypto_quant_foundation/storage.py"),
            (
                RetrospectiveStudyProtocol,
                "research-platform/src/crypto_quant_research/retrospective_study.py",
            ),
            (
                reserve_retrospective_read,
                "strategy-validation/src/crypto_quant_validation/retrospective_reservation.py",
            ),
            (
                SampleConsumptionLedger,
                "strategy-validation/src/crypto_quant_validation/ledger.py",
            ),
        )
        for symbol, relative in origins:
            require(
                Path(inspect.getfile(symbol)).absolute() == PROJECT / relative,
                "CAPTURE_GOV_CODE_PIN",
            )
        for relative, pin in CATALOG_GOVERNANCE_CODE_PINS.items():
            self.reserve("CODE_PIN", read=65537)
            require(
                digest(_read_regular(PROJECT / relative, 65536)[0]) == pin,
                "CAPTURE_GOV_CODE_PIN",
            )
        self.reserve(
            name, read=64 * 4 * GOV_PREFIX, write=64 * GOV_PREFIX, sdk_calls=64
        )

    def summary(self):
        return {
            "read_upper_debit": self.read,
            "write_upper_debit": self.write,
            "sdk_calls_reserved": self.calls,
            "programs": sorted(self.programs),
            "basis": "PINNED_PROGRAM_UPPER_NOT_MEASURED_IO",
            "closed": self.closed,
        }

    def close(self, state):
        self.closed = True
        self._record("close.json", canonical_bytes({"state": state, **self.summary()}))


def _copy_governance(source: Path, target: Path, io_budget: _GovernanceBudget):
    inputs.no_links(source)
    require(source.is_dir(), "CAPTURE_GOV_MISSING")
    pending = [(source, target)]
    used = nodes = 0
    proof_files = []
    original_directories = [source]
    while pending:
        parent, destination = pending.pop()
        with os.scandir(parent) as entries:
            for entry in entries:
                nodes += 1
                require(nodes <= 128, "CAPTURE_GOV_NODE_CAP")
                info = entry.stat(follow_symlinks=False)
                path = Path(entry.path)
                require(
                    info.st_uid == os.getuid() and not stat.S_ISLNK(info.st_mode),
                    "CAPTURE_GOV_FILE",
                )
                relative = path.relative_to(source)
                require(
                    relative.parts[0]
                    in ("artifacts", "registries", ".staging", ".foundation.clock"),
                    "CAPTURE_GOV_LAYOUT",
                )
                if stat.S_ISDIR(info.st_mode):
                    out = destination / entry.name
                    _make_directory(out)
                    original_directories.append(path)
                    pending.append((path, out))
                else:
                    require(
                        stat.S_ISREG(info.st_mode) and relative.parts[0] != ".staging",
                        "CAPTURE_GOV_PARTIAL",
                    )
                    if relative.parts[0] == "registries":
                        require(
                            len(relative.parts) == 2
                            and entry.name in (LOG + ".jsonl", SAMPLE + ".jsonl"),
                            "CAPTURE_GOV_LAYOUT",
                        )
                    require(
                        used + info.st_size <= GOV_SOURCE, "CAPTURE_GOV_CONTENT_CAP"
                    )
                    io_budget.reserve("COPY", read=info.st_size + 1, write=info.st_size)
                    raw = _read_regular(path, info.st_size)[0]
                    used += len(raw)
                    _write_regular(destination / entry.name, raw)
                    proof_files.append(
                        {
                            "name": str(relative),
                            "bytes": len(raw),
                            "sha256": digest(raw),
                        }
                    )
    for directory in sorted(
        original_directories, key=lambda p: len(p.parts), reverse=True
    ):
        _sync_directory(directory)
    _sync_directory(source.parent)
    return {
        "nodes": nodes,
        "source_content_bytes": used,
        "original_files": proof_files,
        "private_peak_upper": 573440,
        "private_reserved": GOV_PRIVATE,
    }


@dataclass(frozen=True, slots=True)
class CaptureAdmission:
    scope_hash: str
    protocol_publication: PublishedRetrospectiveArtifact
    task_publication: PublishedRetrospectiveArtifact
    reservation: RetrospectiveReservationReceipt
    policy: Callable[[], None]
    governance: dict[str, Any]
    seal: object
    _assertion: Callable[[CaptureSpec, Any], None]

    def check(self, spec):
        require(
            type(self) is CaptureAdmission and self.seal is _SEAL,
            "CAPTURE_ADMISSION_CONFLICT",
        )
        self._assertion(spec, self)


def protocol_from_payload(payload: dict[str, Any]):
    require(
        type(payload) is dict and type(payload.get("source_intervals")) is list,
        "CAPTURE_PROTOCOL",
    )
    try:
        protocol = RetrospectiveStudyProtocol(
            payload["study_key"],
            payload["research_design_hash"],
            payload["core_code_hash"],
            payload["adapter_code_hash"],
            payload["source_scope_hash"],
            payload["prior_observation_hash"],
            tuple(tuple(row) for row in payload["source_intervals"]),
        )
    except (KeyError, TypeError, ValueError):
        raise CaptureError("CAPTURE_PROTOCOL") from None
    require(
        canonical_bytes(protocol.payload) == canonical_bytes(payload),
        "CAPTURE_PROTOCOL",
    )
    return protocol


def _protocol_check(spec, protocol):
    require(
        type(spec) is CaptureSpec and type(protocol) is RetrospectiveStudyProtocol,
        "CAPTURE_PROTOCOL",
    )
    require(
        protocol.source_scope_hash == capture_scope_hash(spec)
        and len(protocol.source_intervals) == 1
        and protocol.prior_observation_hash == spec.prior_observation_hash
        and protocol.adapter_code_hash == capture_adapter_hash()
        and protocol.core_code_hash
        == "sha256:"
        + digest(
            _read_regular(
                PROJECT / "experiments/a_share_price_volume_retro_v1.py", 128 * 1024
            )[0]
        )
        and len(protocol.study_key.encode()) <= 128,
        "CAPTURE_PROTOCOL",
    )
    selected = protocol.source_slices[0]
    require(
        selected.interval_start == spec.start + "T00:00:00.000000Z"
        and selected.interval_end == spec.end + "T00:00:00.000000Z"
        and len(selected.scope_key.encode()) <= 128,
        "CAPTURE_PROTOCOL",
    )
    if spec.mode == FAKE:
        require(
            protocol.study_key == "SYNTHETIC-C0-CAPTURE-ONLY",
            "CAPTURE_FIXTURE_PROTOCOL",
        )
    else:
        require(
            not protocol.study_key.startswith("SYNTHETIC"), "CAPTURE_FIXTURE_PROTOCOL"
        )
    require(
        len(
            canonical_bytes(
                ArtifactEnvelope.create(
                    "retrospective_study_protocol", 1, protocol.payload
                )
            )
        )
        <= 16384,
        "CAPTURE_GOV_BODY_CAP",
    )


def verify_capture_admission(
    spec,
    protocol_publication,
    task_publication,
    reservation,
    *,
    io_budget,
    runtime_authorize=None,
):
    if runtime_authorize is None:
        raise CaptureError("REAL_INPUT_NOT_ADMITTED")
    runtime_authorize()
    require(
        type(io_budget) is _GovernanceBudget
        and io_budget.spec == spec
        and io_budget.policy is runtime_authorize,
        "CAPTURE_GOV_ACCOUNT_CONFLICT",
    )
    require(
        type(protocol_publication) is PublishedRetrospectiveArtifact
        and type(task_publication) is PublishedRetrospectiveArtifact
        and type(reservation) is RetrospectiveReservationReceipt,
        "CAPTURE_PUBLIC_PROOF",
    )
    io_budget.program("VERIFY")
    clock_calls = 0

    def clock():
        nonlocal clock_calls
        require(clock_calls < 8, "CAPTURE_GOV_CLOCK_CAP")
        clock_calls += 1
        return stamp()

    with tempfile.TemporaryDirectory(prefix="capture-proof-") as temporary:
        private = Path(temporary)
        evidence = _copy_governance(io_budget.gov, private, io_budget)
        f = LocalFoundation(private, clock=clock)
        pp = f.read(ref=protocol_publication.ref)
        tp = f.read(ref=task_publication.ref)
        require(
            len(pp.source_bytes) <= 16384 and len(tp.source_bytes) <= 16384,
            "CAPTURE_GOV_BODY_CAP",
        )
        task = tp.envelope.payload
        protocol_payload = pp.envelope.payload
        require(
            pp.envelope.artifact_type == "retrospective_study_protocol"
            and tp.envelope.artifact_type == "retrospective_input_read_task"
            and task["phase"] == "INPUT_QUALIFICATION"
            and canonical_bytes(task["context_ref"])
            == canonical_bytes(protocol_publication.ref)
            and protocol_payload["source_scope_hash"] == capture_scope_hash(spec)
            and len(protocol_payload["source_intervals"]) == 1,
            "CAPTURE_PUBLIC_PROOF",
        )
        verified_protocol = RetrospectiveStudyProtocol(
            protocol_payload["study_key"],
            protocol_payload["research_design_hash"],
            protocol_payload["core_code_hash"],
            protocol_payload["adapter_code_hash"],
            protocol_payload["source_scope_hash"],
            protocol_payload["prior_observation_hash"],
            tuple(tuple(row) for row in protocol_payload["source_intervals"]),
        )
        _protocol_check(spec, verified_protocol)
        require(
            canonical_bytes(verified_protocol.payload)
            == canonical_bytes(protocol_payload)
            and canonical_bytes(task["source_slice"])
            == canonical_bytes(verified_protocol.source_slices[0].payload),
            "CAPTURE_PUBLIC_PROOF",
        )
        require(
            reservation.protocol_ref == protocol_publication.ref
            and reservation.read_task_ref == task_publication.ref
            and reservation.protocol_publication_entry_ref
            == protocol_publication.entry_ref
            and reservation.producer_publication_entry_ref == task_publication.entry_ref
            and reservation.study_ref is None,
            "CAPTURE_PUBLIC_PROOF",
        )
        before = f.entries(SAMPLE)
        require(
            len(before) == 1 and len(f.entries(LOG)) == 2, "CAPTURE_GOV_PREFIX_SHAPE"
        )
        original = f.entries(SAMPLE, reservation.reservation_entry_ref)[-1]
        expected = ArtifactEnvelope.create(
            "sample_consumption_append",
            1,
            {
                "record": asdict(reservation.record),
                "producer_ref": task_publication.ref,
            },
        )
        require(original.payload == canonical_bytes(expected), "CAPTURE_APPEND_MISSING")
        actual = reserve_retrospective_read(
            f,
            SampleConsumptionLedger(f),
            protocol_publication.publication,
            task_publication.publication,
            reservation.record.consumed_at,
        )
        require(
            actual == reservation and f.entries(SAMPLE) == before,
            "CAPTURE_APPEND_CHANGED",
        )
        total = sum(p.stat().st_size for p in private.rglob("*") if p.is_file())
        require(
            total <= GOV_SOURCE + 8 * 1024 + 16384
            and 2 * (GOV_SOURCE + 8 * 1024 + 16384) <= GOV_PRIVATE,
            "CAPTURE_GOV_PRIVATE_CAP",
        )
        evidence.update(
            {"private_final_bytes": total, "private_clock_calls": clock_calls}
        )
    io_budget.close("VERIFIED_NOT_SOURCE_QUALIFIED")
    evidence["io_account"] = io_budget.summary()
    expected_scope = capture_scope_hash(spec)

    def assertion(candidate, current):
        runtime_authorize()  # Captured authority cannot be replaced via a DTO field.
        require(
            candidate == spec
            and current.scope_hash == expected_scope
            and current.policy is runtime_authorize
            and current.protocol_publication == protocol_publication
            and current.task_publication == task_publication
            and current.reservation == reservation,
            "CAPTURE_ADMISSION_CONFLICT",
        )

    return CaptureAdmission(
        expected_scope,
        protocol_publication,
        task_publication,
        reservation,
        runtime_authorize,
        evidence,
        _SEAL,
        assertion,
    )


def issue_capture_admission(
    spec: CaptureSpec, protocol: RetrospectiveStudyProtocol, *, runtime_authorize=None
) -> CaptureAdmission:
    if runtime_authorize is None:
        raise CaptureError("REAL_INPUT_NOT_ADMITTED")
    runtime_authorize()
    resource = capture_resource_evidence() if spec.mode == REAL else None
    _protocol_check(spec, protocol)
    root = Path(spec.output)
    inputs.no_links(root)
    _make_directory(root, exist_ok=True)
    gov = root / "governance"
    inputs.no_links(gov)
    require(not gov.exists(), "CAPTURE_GOV_NAMESPACE_EXISTS")
    io_budget = _GovernanceBudget(spec, runtime_authorize)
    calls = 0

    def clock():
        nonlocal calls
        require(calls < 16, "CAPTURE_GOV_CLOCK_CAP")
        calls += 1
        return stamp()

    try:
        io_budget.program("ISSUE")
        _make_directory(gov)
        f = LocalFoundation(gov, clock=clock)
        pp = publish_retrospective_protocol(protocol, f)
        task = RetrospectiveReadTask(
            pp.ref, "INPUT_QUALIFICATION", protocol.source_slices[0]
        )
        require(
            len(
                canonical_bytes(
                    ArtifactEnvelope.create(task.artifact_type, 1, task.payload)
                )
            )
            <= 16384,
            "CAPTURE_GOV_BODY_CAP",
        )
        tp = publish_retrospective_read_task(task, f)
        receipt = reserve_retrospective_read(
            f, SampleConsumptionLedger(f), pp.publication, tp.publication, stamp()
        )
        admission = verify_capture_admission(
            spec,
            pp,
            tp,
            receipt,
            io_budget=io_budget,
            runtime_authorize=runtime_authorize,
        )
        if resource is not None:
            admission.governance["resource_entry"] = resource
        return admission
    except BaseException as original:
        if not io_budget.closed:
            try:
                io_budget.close("FAILED_OR_INTERRUPTED")
            except BaseException as cleanup:
                raise original from cleanup
        raise


def _member_union(spec, budget):
    payloads = {}
    identities = {}
    for member in spec.member_files:
        budget.reserve("MEMBER_READ", read=member.bytes + 1)
        raw, identity = _read_regular(Path(member.path), member.bytes)
        require(
            len(raw) == member.bytes and digest(raw) == member.sha256,
            "CAPTURE_MEMBER_CHANGED",
        )
        budget.write_raw("member-" + member.role + ".bin", raw)
        payloads[member.role] = _json(raw)
        identities[member.role] = identity
    return _members_from_payloads(spec, payloads), identities


def _members_from_payloads(spec: CaptureSpec, payloads: dict[str, Any]):
    receipt: dict[str, Any] = payloads["receipt"]
    require(
        type(receipt) is dict
        and receipt.get("status") == "captured_diagnostic_only"
        and type(receipt.get("requests")) is list
        and len(receipt["requests"]) == 2,
        "CAPTURE_MEMBER_RECEIPT",
    )
    entries = {}
    for entry in receipt["requests"]:
        require(
            type(entry) is dict and type(entry.get("request")) is dict,
            "CAPTURE_MEMBER_RECEIPT",
        )
        flag = entry["request"].get("params", {}).get("is_new")
        require(flag in ("Y", "N") and flag not in entries, "CAPTURE_MEMBER_RECEIPT")
        require(
            entry["request"]
            == {
                "api_name": "index_member_all",
                "params": {"l1_code": "801150.SI", "is_new": flag},
                "fields": ",".join(MEMBER_FIELDS),
            }
            and entry.get("status") == "captured",
            "CAPTURE_MEMBER_RECEIPT",
        )
        entries[flag] = entry
    ids = set()
    total = 0
    for member in spec.member_files[1:]:
        response: dict[str, Any] = payloads[member.role]
        entry: dict[str, Any] = entries[member.role]
        require(
            type(response) is dict
            and type(response.get("code")) is int
            and response["code"] == 0
            and type(response.get("data")) is dict,
            "CAPTURE_MEMBER_BODY",
        )
        data: dict[str, Any] = response["data"]
        require(
            data.get("fields") == list(MEMBER_FIELDS)
            and type(data.get("items")) is list,
            "CAPTURE_MEMBER_BODY",
        )
        require(
            entry.get("response_sha256") == member.sha256
            and type(entry.get("response_bytes")) is int
            and entry["response_bytes"] == member.bytes
            and type(entry.get("rows")) is int
            and entry["rows"] == len(data["items"]),
            "CAPTURE_MEMBER_RECEIPT",
        )
        for row in data["items"]:
            total += 1
            require(total <= 642, "CAPTURE_MEMBER_ROWS")
            require(
                type(row) is list
                and len(row) == 5
                and row[0] == "801150.SI"
                and type(row[1]) is str
                and re.fullmatch(r"[0-9]{6}\.(SH|SZ|BJ)", row[1])
                and row[4] in ("Y", "N"),
                "CAPTURE_MEMBER_BODY",
            )
            entered = _day(row[2], compact=True)
            if row[3] not in (None, ""):
                require(
                    _day(row[3], compact=True) >= entered, "CAPTURE_MEMBER_INTERVAL"
                )
            ids.add(row[1])  # All relations; never the old effective-date/Oct18 filter.
    require(ids, "CAPTURE_EMPTY_COHORT")
    return tuple(sorted(ids))


def _number(v, *, positive=False):
    if v is None:
        return
    require(type(v) in (int, Decimal), "CAPTURE_NUMBER")
    require(v >= 0 and (not positive or v > 0), "CAPTURE_NUMBER")


def _refusal_evidence(spec, admission):
    """Exercise the same pure spec/admission seams, never a source operation."""
    try:
        CaptureSpec.from_payload({**spec.payload, "approved": True})
    except CaptureError as error:
        require(error.code == "CAPTURE_SPEC_FIELDS", "CAPTURE_REFUSAL_EVIDENCE")
    else:
        raise CaptureError("CAPTURE_REFUSAL_EVIDENCE")
    original = capture_scope_hash(spec)
    wrong = original[:-1] + ("1" if original[-1] == "0" else "0")
    try:
        replace(admission, scope_hash=wrong).check(spec)
    except CaptureError as error:
        if error.code != "CAPTURE_ADMISSION_CONFLICT":
            raise  # Actual revocation/stop is not a successful refusal self-check.
    else:
        raise CaptureError("CAPTURE_REFUSAL_EVIDENCE")
    return {
        "version": 1,
        "scope_hash": original,
        "adapter_code_hash": capture_adapter_hash(),
        "cases": [
            ["EXTRA_SPEC_FIELD", "CAPTURE_SPEC_FIELDS"],
            ["RETARGET_ADMISSION", "CAPTURE_ADMISSION_CONFLICT"],
        ],
    }


def _check_refusal_evidence(value, spec):
    require(
        type(value) is dict
        and set(value) == {"version", "scope_hash", "adapter_code_hash", "cases"}
        and type(value["version"]) is int
        and value["version"] == 1
        and value["scope_hash"] == capture_scope_hash(spec)
        and value["adapter_code_hash"] == capture_adapter_hash()
        and value["cases"]
        == [
            ["EXTRA_SPEC_FIELD", "CAPTURE_SPEC_FIELDS"],
            ["RETARGET_ADMISSION", "CAPTURE_ADMISSION_CONFLICT"],
        ],
        "CAPTURE_REFUSAL_EVIDENCE",
    )


def _check_smoke_stage(value, spec, summary, prefix, files):
    require(
        type(value) is dict
        and value.get("version") == 1
        and value.get("scope_hash") == capture_scope_hash(spec)
        and value.get("adapter_code_hash") == capture_adapter_hash()
        and value.get("summary") == summary
        and value.get("request_hashes")
        == [
            [r["request_sha256"], r["wire_sha256"], r["decoded_sha256"]] for r in prefix
        ]
        and value.get("files") == files
        and value.get("closure_basis")
        == "RESPONSES_RETURNED_FILES_FSYNC_CLOSED_NOT_UNIT_TERMINATION",
        "CAPTURE_SMOKE_STAGE_GATE",
    )
    _check_refusal_evidence(value.get("refusals"), spec)


def _program(spec, members, request, stage_gate):
    stages = ["MEMBERS"]
    static = {}
    for flag in ("L", "D", "P"):
        rows = request("stock_basic", {"list_status": flag})
        for row in rows:
            code = row["ts_code"]
            require(
                type(code) is str
                and re.fullmatch(r"[0-9]{6}\.(SH|SZ|BJ)", code)
                and row["symbol"] == code[:6]
                and code not in static,
                "CAPTURE_STATIC_IDENTITY",
            )
            require(
                type(row["market"]) is str
                and row["market"]
                in ("主板", "创业板", "科创板", "北交所", "CDR", "存托凭证")
                and type(row["curr_type"]) is str
                and row["curr_type"] in ("CNY", "USD", "HKD"),
                "CAPTURE_STATIC_IDENTITY",
            )
            require(
                row["exchange"] in ("SSE", "SZSE", "BSE")
                and row["exchange"]
                == {"SH": "SSE", "SZ": "SZSE", "BJ": "BSE"}[code[-2:]],
                "CAPTURE_STATIC_IDENTITY",
            )
            _day(row["list_date"], compact=True)
            if row["delist_date"] not in (None, ""):
                _day(row["delist_date"], compact=True)
            static[code] = row
    require(all(c in static for c in members), "CAPTURE_IDENTITY_UNRESOLVED")
    cohort = tuple(
        c
        for c in members
        if static[c]["exchange"] in ("SSE", "SZSE")
        and static[c]["market"] in ("主板", "创业板", "科创板")
        and static[c]["curr_type"] == "CNY"
        and re.fullmatch(r"6[0-9]{5}\.SH|(?:00|30)[0-9]{4}\.SZ", c)
    )
    require(cohort, "CAPTURE_EMPTY_COHORT")
    stages.append("METADATA")

    def calendar(start, end):
        all_rows = []
        opened = []
        expected = {d.strftime("%Y%m%d") for d in _days(start, end)}
        for exchange in ("SSE", "SZSE"):
            rows = request(
                "trade_cal",
                {
                    "exchange": exchange,
                    "start_date": start.strftime("%Y%m%d"),
                    "end_date": (end - timedelta(days=1)).strftime("%Y%m%d"),
                },
            )
            seen = set()
            sessions = []
            for row in rows:
                key = row["cal_date"]
                require(
                    row["exchange"] == exchange
                    and key in expected
                    and key not in seen
                    and type(row["is_open"]) is int
                    and row["is_open"] in (0, 1),
                    "CAPTURE_CALENDAR_SCOPE",
                )
                if row["pretrade_date"] not in (None, ""):
                    _day(row["pretrade_date"], compact=True)
                seen.add(key)
                if row["is_open"]:
                    sessions.append(key)
            require(seen == expected, "CAPTURE_CALENDAR_INCOMPLETE")
            all_rows.append({r["cal_date"]: r for r in rows})
            opened.append(tuple(sorted(sessions)))
        require(opened[0] == opened[1], "CAPTURE_VENUE_CALENDAR_CONFLICT")
        return opened[0], all_rows

    smoke_open, short_rows = calendar(date(2024, 10, 1), date(2024, 11, 1))
    require(len(smoke_open) >= 9, "CAPTURE_SMOKE_CALENDAR_INSUFFICIENT")
    selected = []
    for suffix in (".SH", ".SZ"):
        candidates = [
            c
            for c in cohort
            if c.endswith(suffix)
            and static[c]["list_date"] <= smoke_open[0]
            and (
                static[c]["delist_date"] in (None, "")
                or static[c]["delist_date"] > smoke_open[8]
            )
        ]
        require(candidates, "CAPTURE_SMOKE_IDENTITY_INSUFFICIENT")
        selected.append(candidates[0])
    observations = {}

    def bars(api, code, start, end, open_days, *, smoke):
        rows = request(api, {"ts_code": code, "start_date": start, "end_date": end})
        seen = set()
        for row in rows:
            key = row["trade_date"]
            _day(key, compact=True)
            require(
                row["ts_code"] == code
                and start <= key <= end
                and key in open_days
                and key not in seen,
                "CAPTURE_ROW_SCOPE_OR_DUPLICATE",
            )
            seen.add(key)
            if api in ("daily", "sw_daily"):
                _number(row["close"], positive=True)
            if api == "daily":
                _number(row["vol"])
                _number(row["pre_close"], positive=True)
            if api == "stk_limit":
                for name in ("pre_close", "up_limit", "down_limit"):
                    _number(row[name], positive=True)
                if row["up_limit"] is not None and row["down_limit"] is not None:
                    require(
                        row["up_limit"] > row["down_limit"], "CAPTURE_LIMIT_CONFLICT"
                    )
            identity = (api, code, key)
            if smoke:
                observations[identity] = row
            elif identity in observations:
                require(observations[identity] == row, "CAPTURE_OVERLAP_DRIFT")
        if smoke:
            require(
                seen == set(smoke_open[:9])
                and all(
                    all(row[k] is not None for k in SOURCE_FIELDS[api].split(","))
                    for row in rows
                ),
                "CAPTURE_SMOKE_NOT_REPRESENTATIVE",
            )

    for code in selected:
        for api in ("daily", "stk_limit"):
            bars(api, code, smoke_open[0], smoke_open[8], set(smoke_open), smoke=True)
    bars(
        "sw_daily",
        "801150.SI",
        smoke_open[0],
        smoke_open[8],
        set(smoke_open),
        smoke=True,
    )
    stages.append("SMOKE")
    stage_gate(
        {
            "cohort": list(cohort),
            "smoke_symbols": selected,
            "smoke_sessions": list(smoke_open[1:9]),
        }
    )
    if spec.bulk:
        long_open, long_rows = calendar(_day(spec.start), _day(spec.end))
        require(len(long_open) <= 4000, "CAPTURE_SW_ROW_DOMAIN")
        for short, long in zip(short_rows, long_rows, strict=True):
            for key in short.keys() & long.keys():
                require(short[key] == long[key], "CAPTURE_CALENDAR_DRIFT")
        start = _day(spec.start).strftime("%Y%m%d")
        end = (_day(spec.end) - timedelta(days=1)).strftime("%Y%m%d")
        for code in cohort:
            for api in ("daily", "stk_limit"):
                bars(api, code, start, end, set(long_open), smoke=False)
        bars("sw_daily", "801150.SI", start, end, set(long_open), smoke=False)
        stages.append("BULK")
    return {
        "cohort": list(cohort),
        "smoke_symbols": selected,
        "smoke_sessions": list(smoke_open[1:9]),
        "stages": stages,
    }


def _rows(fields, items, limits, api):
    require(
        set(fields) == set(SOURCE_FIELDS[api].split(","))
        and len(fields) == len(set(fields)),
        "CAPTURE_FIELDS",
    )
    require(len(items) <= ROW_CAPS.get(api, 6000), "CAPTURE_ROW_CAP")
    for row in items:
        require(
            len(row) == len(fields)
            and all(type(x) in (str, int, Decimal, type(None)) for x in row),
            "CAPTURE_ROW_SHAPE",
        )
        require(
            all(len(str(x)) <= limits.max_cell_chars for x in row), "CAPTURE_CELL_CAP"
        )
    return [dict(zip(fields, row, strict=True)) for row in items]


@dataclass(frozen=True, slots=True)
class RawCaptureManifest:
    body: bytes

    @property
    def payload(self) -> dict[str, Any]:
        value = _json(self.body)
        require(type(value) is dict, "CAPTURE_MANIFEST_SHAPE")
        return value

    @property
    def sha256(self):
        return digest(self.body)


def capture_resource_evidence():
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
    value["scope"] = "kernel entry setting, not workload peak or RSS"
    return value


def capture_source(
    spec: CaptureSpec, *, admission=None, budget=None, client_factory=None
):
    if admission is None:
        raise CaptureError("REAL_INPUT_NOT_ADMITTED")
    require(type(admission) is CaptureAdmission, "CAPTURE_ADMISSION_CONFLICT")
    admission.check(spec)
    if spec.mode == REAL:
        capture_resource_evidence()
    require(client_factory is None or spec.mode == FAKE, "CAPTURE_CLIENT_INJECTION")
    if budget is None:
        budget = CaptureBudget(Path(spec.output) / "data", spec, admission.policy)
    require(
        type(budget) is CaptureBudget
        and budget.spec == spec
        and budget.authorize is admission.policy,
        "CAPTURE_BUDGET_BINDING",
    )
    records = []
    client = None
    try:
        members, initial = _member_union(spec, budget)
        budget.reserve("CREDENTIAL_READ", read=4097)
        token = read_proxy_token(
            Path(spec.credential_file)
        )  # Explicit file only, never env fallback.
        if client_factory is not None:
            client = client_factory(token, spec)
        elif spec.mode == FAKE:
            client = _synthetic_client(token, spec, members)
        else:
            client = ProxyAPI(
                token,
                spec.limits.max_requests,
                endpoint=ENDPOINT,
                timeout=spec.limits.timeout_seconds,
                max_response_bytes=spec.limits.response_bytes,
                opener=build_opener(ProxyHandler({}), NoRedirect()),
            )
        require(
            type(client) is ProxyAPI
            and client.endpoint == ENDPOINT
            and client.http_attempts == 0
            and client.max_requests == spec.limits.max_requests
            and client.max_response_bytes == spec.limits.response_bytes,
            "CAPTURE_CLIENT_BINDING",
        )

        last_started = None

        def request(api, params):
            nonlocal last_started
            if spec.mode == REAL and last_started is not None:
                remaining = spec.limits.minimum_interval_ms / 1000 - (
                    time.monotonic() - last_started
                )
                if remaining > 0:
                    time.sleep(remaining)
            admission.check(spec)
            cap = spec.limits.response_bytes + 1
            budget.reserve("REQUEST", requests=1, wire=cap, decoded=cap)
            ordinal = len(records) + 1
            planned = {"api_name": api, "params": params, "fields": SOURCE_FIELDS[api]}
            request_audit = budget.write_audit(
                f"request-{ordinal:06d}.json",
                canonical_bytes(
                    {
                        "request": planned,
                        "scope_hash": capture_scope_hash(spec),
                        "request_sha256": digest(canonical_bytes(planned)),
                        "attempt_reserved_at": stamp(),
                    }
                ),
            )
            last_started = time.monotonic()
            captured = client.capture(api, fields=SOURCE_FIELDS[api], **params)
            require(
                type(captured) is ProxyCapture
                and captured.api_name == api
                and _json(captured.request_body)
                == {"api_name": api, "params": params, "fields": SOURCE_FIELDS[api]},
                "CAPTURE_REQUEST_BINDING",
            )
            raw_file = budget.write_raw(
                f"wire-{len(records) + 1:06d}.bin", captured.wire_body
            )
            record = {
                "request": _json(captured.request_body),
                "request_sha256": digest(captured.request_body),
                "request_audit": request_audit,
                "file": raw_file["name"],
                "wire_sha256": captured.wire_sha256,
                "decoded_sha256": captured.decoded_sha256,
                "encoding": captured.content_encoding,
                "rows": len(captured.items),
                "captured_at": stamp(),
                "provider_revision_id": None,
                "historical_provider_availability": None,
            }
            records.append(record)
            budget.write_audit(f"response-{ordinal:06d}.json", canonical_bytes(record))
            budget.reserve("ROWS", rows=len(captured.items))
            return _rows(captured.fields, captured.items, spec.limits, api)

        smoke_stage = None

        def stage_gate(summary):
            nonlocal smoke_stage
            proof = _refusal_evidence(spec, admission)
            _check_refusal_evidence(proof, spec)
            value = {
                "version": 1,
                "scope_hash": capture_scope_hash(spec),
                "adapter_code_hash": capture_adapter_hash(),
                "summary": summary,
                "request_hashes": [
                    [r["request_sha256"], r["wire_sha256"], r["decoded_sha256"]]
                    for r in records
                ],
                "files": list(budget.files),
                "refusals": proof,
                "closure_basis": "RESPONSES_RETURNED_FILES_FSYNC_CLOSED_NOT_UNIT_TERMINATION",
            }
            raw = canonical_bytes(value)
            smoke_stage = budget.write_audit("smoke-stage.json", raw)
            budget.reserve("SMOKE_STAGE_VERIFY", read=len(raw) + 1)
            checked = _read_regular(budget.root / "smoke-stage.json", len(raw))[0]
            require(checked == raw, "CAPTURE_SMOKE_STAGE_GATE")
            _check_smoke_stage(
                _json(checked), spec, summary, records, list(budget.files)
            )

        result = _program(spec, members, request, stage_gate)
        require(smoke_stage is not None, "CAPTURE_SMOKE_STAGE_GATE")
        for member in spec.member_files:
            budget.reserve("MEMBER_RECHECK", read=member.bytes + 1)
            raw, identity = _read_regular(Path(member.path), member.bytes)
            require(
                identity == initial[member.role] and digest(raw) == member.sha256,
                "CAPTURE_MEMBER_CHANGED",
            )
        verify_upper = (
            sum(f["bytes"] + 1 for f in budget.files)
            + 2 * spec.limits.audit_bytes
            + spec.limits.close_bytes
            + GOV_SOURCE
            + 128
        )
        budget.reserve("VERIFY_READ", read=verify_upper)
        payload = {
            "version": 1,
            "state": "CAPTURED_NOT_STUDY_QUALIFIED",
            "mode": spec.mode,
            "scope_hash": capture_scope_hash(spec),
            "spec": spec.payload,
            "adapter_code_hash": capture_adapter_hash(),
            "source_qualified": False,
            "model_calls": 0,
            "files": budget.files,
            "requests": records,
            "transport_attempts": client.http_attempts,
            "real_HTTP_attempts": client.http_attempts if spec.mode == REAL else 0,
            "protocol_publication": asdict(admission.protocol_publication),
            "task_publication": asdict(admission.task_publication),
            "sample_reservation": asdict(admission.reservation),
            "governance": admission.governance,
            "budget": budget.summary(),
            "smoke_stage": smoke_stage,
            **result,
            "availability_basis": "CURRENT_ACQUISITION_NOT_HISTORICAL_PROVIDER_TIME",
            "untouched_claim": False,
            "causal_pit_claim": False,
        }
        manifest = RawCaptureManifest(canonical_bytes(payload))
        budget.write_manifest(manifest.body)
        _verify_files(budget.root, manifest)
        require(
            budget.close(
                "COMPLETE",
                manifest_hash=manifest.sha256,
                transport_attempts=client.http_attempts,
            ),
            "CAPTURE_CLOSE_FAILED",
        )
        return manifest
    except BaseException as original:
        if not budget.closed:
            try:
                budget.close(
                    "FAILED_OR_INTERRUPTED",
                    error_code=getattr(original, "code", type(original).__name__),
                    transport_attempts=client.http_attempts
                    if client is not None
                    else 0,
                )
            except BaseException as cleanup:
                raise original from cleanup
        raise


def _verify_links(
    root: Path,
    spec: CaptureSpec,
    payload: dict[str, Any],
    read: Callable[[Path, int], bytes],
):
    """Pin already-SDK-verified owned proof bytes; never checkpoint that store."""
    proof: list[dict[str, Any]] = payload["governance"]["original_files"]
    require(type(proof) is list and len(proof) <= 128, "CAPTURE_REPLAY_PROOF")
    material = {}
    used = 0
    for item in proof:
        require(
            type(item) is dict
            and set(item) == {"name", "bytes", "sha256"}
            and type(item["name"]) is str,
            "CAPTURE_REPLAY_PROOF",
        )
        relative = Path(item["name"])
        require(
            not relative.is_absolute()
            and ".." not in relative.parts
            and relative.parts[0] in ("artifacts", "registries", ".foundation.clock"),
            "CAPTURE_REPLAY_PROOF",
        )
        require(
            type(item["bytes"]) is int and item["bytes"] >= 0, "CAPTURE_REPLAY_PROOF"
        )
        used += item["bytes"]
        require(
            used <= GOV_SOURCE and item["name"] not in material, "CAPTURE_REPLAY_PROOF"
        )
        raw = read(root.parent / "governance" / relative, item["bytes"])
        require(digest(raw) == item["sha256"], "CAPTURE_REPLAY_PROOF_CHANGED")
        material[item["name"]] = raw
    existing = set()
    pending = [root.parent / "governance"]
    nodes = 0
    while pending:
        with os.scandir(pending.pop()) as entries:
            for entry in entries:
                nodes += 1
                require(nodes <= 128, "CAPTURE_REPLAY_PROOF")
                info = entry.stat(follow_symlinks=False)
                require(
                    info.st_uid == os.getuid() and not stat.S_ISLNK(info.st_mode),
                    "CAPTURE_REPLAY_PROOF",
                )
                p = Path(entry.path)
                if stat.S_ISDIR(info.st_mode):
                    pending.append(p)
                else:
                    require(stat.S_ISREG(info.st_mode), "CAPTURE_REPLAY_PROOF")
                    existing.add(str(p.relative_to(root.parent / "governance")))
    require(existing == set(material), "CAPTURE_REPLAY_PROOF_CHANGED")
    pp = payload["protocol_publication"]
    tp = payload["task_publication"]
    sample = payload["sample_reservation"]
    envelopes = []
    for publication, kind in (
        (pp, "retrospective_study_protocol"),
        (tp, "retrospective_input_read_task"),
    ):
        ref = publication["ref"]
        h = ref["content_hash"]
        require(
            ref["artifact_type"] == kind
            and ref["schema_version"] == 1
            and re.fullmatch(r"sha256:[0-9a-f]{64}", h),
            "CAPTURE_REPLAY_PROOF",
        )
        document = _json(material[f"artifacts/sha256/{h[7:9]}/{h[7:]}"])
        require(
            document["artifact_type"] == kind
            and document["schema_version"] == 1
            and document["content_hash"] == h,
            "CAPTURE_REPLAY_PROOF",
        )
        envelopes.append(document["payload"])
    protocol, task = envelopes
    require(
        protocol["source_scope_hash"] == capture_scope_hash(spec)
        and protocol["adapter_code_hash"] == payload["adapter_code_hash"]
        and protocol["prior_observation_hash"] == spec.prior_observation_hash
        and task["phase"] == "INPUT_QUALIFICATION"
        and task["context_ref"]["content_hash"] == pp["ref"]["content_hash"]
        and task["source_slice"]["source_scope_hash"] == capture_scope_hash(spec)
        and sample["protocol_ref"] == pp["ref"]
        and sample["read_task_ref"] == tp["ref"]
        and sample["protocol_publication_entry_ref"] == pp["entry_ref"]
        and sample["producer_publication_entry_ref"] == tp["entry_ref"]
        and sample["study_ref"] is None
        and sample["record"]["purpose"] == "discovery"
        and sample["record"]["dataset_revision"] == protocol["capture_revision"]
        and sample["record"]["interval_start"] == spec.start + "T00:00:00.000000Z"
        and sample["record"]["interval_end"] == spec.end + "T00:00:00.000000Z",
        "CAPTURE_REPLAY_PROOF_JOIN",
    )


def _verify_files(
    root: Path, expected: RawCaptureManifest, *, read_limit=None, expect_closed=False
):
    payload = expected.payload
    spec = CaptureSpec.from_payload(payload["spec"])
    require(
        payload["version"] == 1
        and payload["scope_hash"] == capture_scope_hash(spec)
        and payload["adapter_code_hash"] == capture_adapter_hash()
        and payload["state"] == "CAPTURED_NOT_STUDY_QUALIFIED"
        and payload["mode"] == spec.mode
        and payload["source_qualified"] is False
        and payload["model_calls"] == 0,
        "CAPTURE_REPLAY_BINDING",
    )
    read_used = 0
    files = {}
    consumed = set()
    ceiling = spec.limits.read_bytes if read_limit is None else read_limit

    def read(path, cap):
        nonlocal read_used
        require(
            type(cap) is int and cap >= 0 and read_used + cap + 1 <= ceiling,
            "CAPTURE_REPLAY_READ_CAP",
        )
        read_used += cap + 1
        return _read_regular(path, cap)[0]

    require(
        read(root / "manifest.json", len(expected.body)) == expected.body,
        "CAPTURE_REPLAY_MANIFEST",
    )
    _verify_links(root, spec, payload, read)
    require(
        type(payload["files"]) is list
        and len(payload["files"]) <= spec.limits.max_requests + 3,
        "CAPTURE_REPLAY_FILE",
    )
    for f in payload["files"]:
        require(
            type(f) is dict
            and set(f) == {"name", "bytes", "sha256"}
            and type(f["name"]) is str
            and re.fullmatch(
                r"member-(?:receipt|Y|N)\.bin|wire-[0-9]{6}\.bin", f["name"]
            )
            and f["name"] not in files
            and type(f["bytes"]) is int
            and f["bytes"] >= 0,
            "CAPTURE_REPLAY_FILE",
        )
        files[f["name"]] = f

    def raw_file(name):
        require(name in files and name not in consumed, "CAPTURE_REPLAY_FILE_USE")
        f = files[name]
        consumed.add(name)
        raw = read(root / name, f["bytes"])
        require(
            len(raw) == f["bytes"] and digest(raw) == f["sha256"], "CAPTURE_REPLAY_HASH"
        )
        return raw

    member_payloads = {}
    for member in spec.member_files:
        f = files["member-" + member.role + ".bin"]
        require(
            f["sha256"] == member.sha256 and f["bytes"] == member.bytes,
            "CAPTURE_REPLAY_MEMBER",
        )
        member_payloads[member.role] = _json(raw_file(f["name"]))
    members = _members_from_payloads(spec, member_payloads)
    ordinal = 0

    def replay(api, params):
        nonlocal ordinal
        require(ordinal < len(payload["requests"]), "CAPTURE_REPLAY_REQUEST")
        record = payload["requests"][ordinal]
        ordinal += 1
        request = {"api_name": api, "params": params, "fields": SOURCE_FIELDS[api]}
        require(
            record["request"] == request
            and record["request_sha256"] == digest(canonical_bytes(request))
            and record["provider_revision_id"] is None
            and record["historical_provider_availability"] is None
            and record["file"] == f"wire-{ordinal:06d}.bin",
            "CAPTURE_REPLAY_REQUEST",
        )
        audit = record["request_audit"]
        require(
            audit["name"] == f"request-{ordinal:06d}.json", "CAPTURE_REPLAY_REQUEST"
        )
        request_raw = read(root / audit["name"], audit["bytes"])
        require(digest(request_raw) == audit["sha256"], "CAPTURE_REPLAY_REQUEST")
        request_info = _json(request_raw)
        require(
            request_info["request"] == request
            and request_info["scope_hash"] == capture_scope_hash(spec)
            and request_info["request_sha256"] == record["request_sha256"],
            "CAPTURE_REPLAY_REQUEST",
        )
        response_raw = canonical_bytes(record)
        require(
            read(root / f"response-{ordinal:06d}.json", len(response_raw))
            == response_raw,
            "CAPTURE_REPLAY_REQUEST",
        )
        wire = raw_file(record["file"])
        require(
            len(wire) <= spec.limits.response_bytes
            and digest(wire) == record["wire_sha256"],
            "CAPTURE_REPLAY_HASH",
        )
        if record["encoding"] == "gzip":
            with gzip.GzipFile(fileobj=io.BytesIO(wire)) as stream:
                raw = stream.read(spec.limits.response_bytes + 1)
        else:
            require(record["encoding"] == "identity", "CAPTURE_REPLAY_ENCODING")
            raw = wire
        require(
            len(raw) <= spec.limits.response_bytes
            and digest(raw) == record["decoded_sha256"],
            "CAPTURE_REPLAY_HASH",
        )
        reply = _json(raw)
        require(
            type(reply["code"]) is int and reply["code"] == 0, "CAPTURE_REPLAY_BUSINESS"
        )
        data = reply["data"]
        require(record["rows"] == len(data["items"]), "CAPTURE_REPLAY_ROWS")
        return _rows(data["fields"], data["items"], spec.limits, api)

    def replay_stage(summary):
        descriptor: dict[str, Any] = payload["smoke_stage"]
        require(
            type(descriptor) is dict
            and set(descriptor) == {"name", "bytes", "sha256"}
            and descriptor["name"] == "smoke-stage.json",
            "CAPTURE_SMOKE_STAGE_GATE",
        )
        raw = read(root / descriptor["name"], descriptor["bytes"])
        require(digest(raw) == descriptor["sha256"], "CAPTURE_SMOKE_STAGE_GATE")
        prefix_files = [f for f in payload["files"] if f["name"] in consumed]
        _check_smoke_stage(
            _json(raw), spec, summary, payload["requests"][:ordinal], prefix_files
        )

    result = _program(spec, members, replay, replay_stage)
    require(
        ordinal == len(payload["requests"])
        and consumed == set(files)
        and all(payload[k] == v for k, v in result.items())
        and payload["transport_attempts"] == ordinal
        and payload["real_HTTP_attempts"] == (ordinal if spec.mode == REAL else 0),
        "CAPTURE_REPLAY_PROGRAM",
    )
    expected_names = set(files) | {
        "reserve.json",
        "debits.jsonl",
        "manifest.json",
        "smoke-stage.json",
    }
    expected_names |= {
        f"{kind}-{i:06d}.json"
        for i in range(1, ordinal + 1)
        for kind in ("request", "response")
    }
    if expect_closed:
        expected_names.add("close.json")
    with os.scandir(root) as entries:
        actual_names = set()
        for entry in entries:
            info = entry.stat(follow_symlinks=False)
            require(
                stat.S_ISREG(info.st_mode)
                and info.st_uid == os.getuid()
                and info.st_nlink == 1
                and not stat.S_ISLNK(info.st_mode),
                "CAPTURE_REPLAY_LAYOUT",
            )
            actual_names.add(entry.name)
    require(actual_names == expected_names, "CAPTURE_REPLAY_LAYOUT")
    return read_used


def verify_capture(
    root: Path, expected_manifest: RawCaptureManifest, *, read_limit=None
):
    require(
        type(expected_manifest) is RawCaptureManifest, "CAPTURE_REPLAY_EXPECTED_HASH"
    )
    spec = CaptureSpec.from_payload(expected_manifest.payload["spec"])
    root = Path(root).absolute()
    require(root == Path(spec.output) / "data", "CAPTURE_REPLAY_ROOT")
    ceiling = spec.limits.read_bytes if read_limit is None else read_limit
    require(
        type(ceiling) is int
        and 0 <= ceiling <= spec.limits.read_bytes
        and len(expected_manifest.body) + spec.limits.close_bytes + 2 <= ceiling,
        "CAPTURE_REPLAY_READ_CAP",
    )
    close = _json(_read_regular(root / "close.json", spec.limits.close_bytes)[0])
    require(
        close["state"] == "COMPLETE"
        and close["manifest_hash"] == expected_manifest.sha256,
        "CAPTURE_REPLAY_CLOSE",
    )
    read_debit = _verify_files(
        root,
        expected_manifest,
        read_limit=ceiling - spec.limits.close_bytes - 1,
        expect_closed=True,
    )
    return {
        "verified": True,
        "manifest_sha256": expected_manifest.sha256,
        "source_qualified": False,
        "read_upper_debit": read_debit + spec.limits.close_bytes + 1,
    }


class _SyntheticReply:
    def __init__(self, raw):
        self.raw = raw
        self.status = 200
        self.headers = {"Content-Encoding": "identity"}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        return self.raw[:size]


class _SyntheticOpener:
    def __init__(self, members):
        self.members = members

    def open(self, request, *, timeout):
        body = _json(request.data)
        api = body["api_name"]
        params = body["params"]
        selected = body["fields"].split(",")
        rows = []
        if api == "stock_basic":
            if params["list_status"] == "L":
                for code in self.members:
                    rows.append(
                        {
                            "ts_code": code,
                            "symbol": code[:6],
                            "name": "Synthetic only",
                            "market": "主板",
                            "list_date": "19900101",
                            "delist_date": None,
                            "exchange": "SSE" if code.endswith("SH") else "SZSE",
                            "curr_type": "CNY",
                        }
                    )
        else:
            start = _day(params["start_date"], compact=True)
            end = _day(params["end_date"], compact=True) + timedelta(days=1)
            for d in _days(start, end):
                if api == "trade_cal":
                    previous = d - timedelta(days=1)
                    while previous.weekday() > 4:
                        previous -= timedelta(days=1)
                    rows.append(
                        {
                            "exchange": params["exchange"],
                            "cal_date": d.strftime("%Y%m%d"),
                            "is_open": int(d.weekday() < 5),
                            "pretrade_date": previous.strftime("%Y%m%d"),
                        }
                    )
                elif d.weekday() < 5:
                    price = 10 + d.day / 100
                    row = {
                        "ts_code": params["ts_code"],
                        "trade_date": d.strftime("%Y%m%d"),
                        "close": price,
                        "vol": 100,
                        "pre_close": 10,
                        "up_limit": 12,
                        "down_limit": 8,
                    }
                    rows.append(row)
        raw = json.dumps(
            {
                "code": 0,
                "data": {
                    "fields": selected,
                    "items": [[row[k] for k in selected] for row in rows],
                },
            }
        ).encode()
        return _SyntheticReply(raw)


def _synthetic_client(token, spec, members):
    require(spec.mode == FAKE, "CAPTURE_FIXTURE_SCOPE")
    return ProxyAPI(
        token,
        spec.limits.max_requests,
        endpoint=ENDPOINT,
        timeout=spec.limits.timeout_seconds,
        max_response_bytes=spec.limits.response_bytes,
        opener=_SyntheticOpener(members),
    )


def make_synthetic_capture_spec(root: Path, *, bulk=True) -> CaptureSpec:
    """Explicit fixture creation, not a real capture selector or authority."""
    root = root.absolute()
    inputs.no_links(root)
    require(not root.exists(), "CAPTURE_FIXTURE_EXISTS")
    _make_directory(root)
    token = root / "dummy-token"
    _write_regular(token, b"Z" * 56 + b"\n")
    descriptors = []
    entries = []
    for flag, code in (("Y", "600000.SH"), ("N", "000001.SZ")):
        raw = json.dumps(
            {
                "code": 0,
                "data": {
                    "fields": list(MEMBER_FIELDS),
                    "items": [["801150.SI", code, "20000101", None, flag]],
                },
            }
        ).encode()
        path = root / ("members-" + flag + ".json")
        _write_regular(path, raw)
        descriptors.append(MemberFile(flag, str(path), digest(raw), len(raw)))
        entries.append(
            {
                "request": {
                    "api_name": "index_member_all",
                    "params": {"l1_code": "801150.SI", "is_new": flag},
                    "fields": ",".join(MEMBER_FIELDS),
                },
                "status": "captured",
                "response_sha256": digest(raw),
                "response_bytes": len(raw),
                "rows": 1,
            }
        )
    raw = json.dumps(
        {"status": "captured_diagnostic_only", "requests": entries}
    ).encode()
    receipt = root / "receipt.json"
    _write_regular(receipt, raw)
    limits = CaptureLimits(
        32,
        1024**2,
        15,
        32 * 1024**2 + 32,
        32 * 1024**2 + 32,
        16 * 1024**2,
        16 * 1024**2,
        8 * 1024**2,
        256 * 1024,
        64 * 1024,
        8 * 1024**2,
        20000,
        256,
        500,
    )
    return CaptureSpec(
        FAKE,
        str(root / "out"),
        str(token),
        (MemberFile("receipt", str(receipt), digest(raw), len(raw)), *descriptors),
        "2024-10-01",
        "2024-11-01",
        bulk,
        limits,
        RetroResourceLimits(6 * 1024**3, 30, 40, 64 * 1024, 256 * 1024, 1),
        str(root),
        "sha256:" + "1" * 64,
    )


def synthetic_capture_protocol(spec):
    require(spec.mode == FAKE, "CAPTURE_FIXTURE_SCOPE")
    return RetrospectiveStudyProtocol(
        "SYNTHETIC-C0-CAPTURE-ONLY",
        "sha256:" + "2" * 64,
        "sha256:"
        + digest(
            _read_regular(
                PROJECT / "experiments/a_share_price_volume_retro_v1.py", 128 * 1024
            )[0]
        ),
        capture_adapter_hash(),
        capture_scope_hash(spec),
        spec.prior_observation_hash,
        (
            (
                "source-capture",
                spec.start + "T00:00:00.000000Z",
                spec.end + "T00:00:00.000000Z",
            ),
        ),
    )
