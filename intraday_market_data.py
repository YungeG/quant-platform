"""Bounded D202 acquisition and offline archive/replay, never governed evidence.

Offline APIs consume explicit capture bytes; capture uses an explicitly requested
loopback subscription. Foundation owns persistence. Provider semantics stay unknown.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import re
import stat
import subprocess
from collections import Counter
from pathlib import Path
from dataclasses import dataclass, replace
from datetime import datetime, timezone

from crypto_quant_foundation import FoundationFailure, LocalFoundation

from intraday_d202_transport import MAX_FRAMES, MAX_PAYLOAD_BYTES, capture_record

LOG_NAME = "intraday.d202.captures.v1"  # Operational only; NOT an artifact owner log.
MAX_CAPTURE_BYTES = 16 * 1024 * 1024
MAX_RECORDS = 10000
MAX_TABLE_ROWS = 10000
MAX_OBSERVATIONS = 100000
_SYMBOL = r"(?:SH|SZ)[0-9]{6}"
_EVENTS = {
    "frame": {"opcode", "payload_base64"},
    "subscription_sent": {"command"},
    "unsubscribe_sent": set(),
    "server_close": {"code", "payload_base64"},
    "control_frame": {"opcode", "payload_bytes"},
    "handshake_rejected": {"http_status"},
    "transport_error": {"error_type"},
}
_METADATA = {"event", "received_at", "received_wall_ns", "received_monotonic_ns"}


class CaptureError(ValueError):
    """A bounded, non-payload-bearing archive/replay failure code."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CaptureError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _nonfinite(_value):
    raise CaptureError("NONFINITE_JSON")


def _finite_float(value):
    try:
        result = float(value)
        if not math.isfinite(result):
            raise CaptureError("NONFINITE_JSON")
        return result
    except (ValueError, TypeError, OverflowError):
        raise CaptureError("NONFINITE_JSON") from None


def _json(source):
    try:
        return json.loads(source, object_pairs_hook=_object, parse_constant=_nonfinite, parse_float=_finite_float)
    except (ValueError, TypeError, RecursionError):
        # Normalize parser/callback failures before they can expose input context.
        raise CaptureError("JSON_FORMAT") from None


def _aware_time(value):
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise CaptureError("NAIVE_RECEIVE_TIME")
    return parsed.astimezone(timezone.utc)


def _records(source: bytes) -> list[dict]:
    if type(source) is not bytes or not 0 < len(source) <= MAX_CAPTURE_BYTES:
        raise CaptureError("CAPTURE_SIZE")
    lines = source.splitlines()
    if not 0 < len(lines) <= MAX_RECORDS:
        raise CaptureError("CAPTURE_RECORD_LIMIT")
    result = []
    try:
        for line in lines:
            row = _json(line.decode("utf-8"))
            if not isinstance(row, dict) or row.get("event") not in _EVENTS:
                raise CaptureError("CAPTURE_FORMAT")
            if row.keys() != _METADATA | _EVENTS[row["event"]]:
                raise CaptureError("CAPTURE_FIELDS")
            _aware_time(row["received_at"])
            for key in ("received_wall_ns", "received_monotonic_ns"):
                if type(row[key]) is not int or row[key] < 0:
                    raise CaptureError("CAPTURE_CLOCK")
            if row["event"] == "frame":
                if type(row.get("opcode")) is not int or row["opcode"] not in (1, 2):
                    raise CaptureError("CAPTURE_OPCODE")
                base64.b64decode(row["payload_base64"], validate=True)
            result.append(row)
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError) as error:
        raise CaptureError("CAPTURE_FORMAT") from error
    return result


def _capture_key(source: bytes, symbol: str) -> str:
    if not isinstance(symbol, str) or re.fullmatch(_SYMBOL, symbol) is None:
        raise CaptureError("SYMBOL_FORMAT")
    _records(source)
    return f"{symbol}:{hashlib.sha256(source).hexdigest()}"


def archive_capture(foundation: LocalFoundation, source: bytes, *, symbol: str) -> str:
    """Atomically retain one bounded capture; return a file key, not a market event ID.

    Exact repeat imports are idempotent. Different captures (including overlapping
    history or reconnects) are never merged. No bytes are written on format failure.
    """
    key = _capture_key(source, symbol)
    foundation.append(log_name=LOG_NAME, event_id=key, payload=source)
    return key


def read_capture(foundation: LocalFoundation, capture_key: str) -> bytes:
    """Verify Foundation's log and the exact source hash before returning raw bytes."""
    if not isinstance(capture_key, str) or re.fullmatch(_SYMBOL + r":[0-9a-f]{64}", capture_key) is None:
        raise CaptureError("CAPTURE_KEY")
    # ponytail: bounded offline archives scan one log; not a continuous feed store.
    for entry in foundation.entries(log_name=LOG_NAME):
        if entry.event_id == capture_key:
            if hashlib.sha256(entry.payload).hexdigest() != capture_key.split(":")[1]:
                raise CaptureError("CAPTURE_INTEGRITY")
            _records(entry.payload)
            return entry.payload
    raise CaptureError("CAPTURE_NOT_FOUND")


@dataclass(frozen=True)
class Observation:
    """A diagnostic projection located by capture line/item/row, never a MarketEvent."""

    record: int
    item: int | None
    row: int | None
    kind: str
    symbol: str | None
    received_at: str
    received_wall_ns: int
    proxy_ts: object
    data: dict | None
    flags: tuple[str, ...]


def _flag(observation: Observation, *flags: str) -> Observation:
    return replace(observation, flags=tuple(sorted(set(observation.flags).union(flags))))


def _sequence_flags(observation: Observation, state: dict) -> Observation:
    if observation.kind not in ("entrust", "trade") or observation.data is None:
        return observation
    seq = observation.data.get("seq")
    if type(seq) is not int or seq < 0:
        return _flag(observation, "MALFORMED_DATA")
    if {"MALFORMED_DATA", "SYMBOL_MISMATCH"}.intersection(observation.flags):
        return observation
    scope = (observation.symbol, observation.kind)
    seen, high = state.get(scope, (set(), -1))
    if seq in seen:
        observation = _flag(observation, "REPEATED_SEQ")
    if seq < high:
        observation = _flag(observation, "SEQUENCE_REGRESSION")
    if high >= 0 and seq > high + 1:
        observation = _flag(observation, "SEQUENCE_GAP")
    seen.add(seq)
    state[scope] = (seen, max(high, seq))
    return observation


def _table(value):
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], list):
        value = value[0]
    if not isinstance(value, list) or any(isinstance(row, list) for row in value):
        raise CaptureError("MARKET_FORMAT")
    if len(value) > MAX_TABLE_ROWS:
        raise CaptureError("REPLAY_LIMIT")
    return value


def _valid_ints(data, keys) -> bool:
    return isinstance(data, dict) and all(type(data.get(key)) is int and data[key] >= 0 for key in keys)


def _project_row(base: Observation, row, index: int) -> Observation:
    base = replace(base, row=index)
    if not isinstance(row, dict):
        return _flag(replace(base, kind="error"), "MALFORMED_DATA")
    base = replace(base, data=dict(row))
    keys = ("seq", "t", "p", "v")
    if base.kind == "trade":
        keys += ("buyer", "seller", "buyVol", "sellVol")
    valid = _valid_ints(row, keys) and type(row.get("d")) in (int, str)
    if valid:
        t = row["t"]  # HHmmss is validated, but deliberately gets NO trading date.
        valid = t // 10000 < 24 and t // 100 % 100 < 60 and t % 100 < 60
    return base if valid else _flag(base, "MALFORMED_DATA")


def _has_market_data(event: Observation) -> bool:
    return (event.kind in ("thousand", "entrust", "trade") and event.data is not None
            and not {"MALFORMED_DATA", "SYMBOL_MISMATCH"}.intersection(event.flags))


def _project_item(base: Observation, item: dict, expected_symbol: str):
    kind = item.get("type")
    if kind not in ("thousand", "entrust", "trade"):
        if kind == "info":
            return [replace(base, kind="info")]
        flag = "PROVIDER_ERROR" if kind == "error" else "UNSUPPORTED_TYPE"
        return [replace(base, kind="error", flags=(*base.flags, flag))]
    data = item.get("data")
    if not isinstance(data, dict):
        raise CaptureError("MARKET_FORMAT")
    symbol = data.get("code")
    flags = set(base.flags) | {"PROVIDER_TIME_UNKNOWN", "COMPLETENESS_UNKNOWN"}
    if symbol != expected_symbol:
        flags.add("SYMBOL_MISMATCH")
    base = replace(base, kind=kind, symbol=symbol if isinstance(symbol, str) else None)
    if kind == "thousand":
        projected = {**data, "buys": _table(data.get("buys")), "sells": _table(data.get("sells"))}
        flags.add("DEPTH_SCOPE_UNKNOWN")
        keys = ("price", "totalBuyVol", "totalSellVol", "totalBuyAmt", "totalSellAmt", "l2Time", "buyCount", "sellCount")
        if not _valid_ints(data, keys) or any(not _valid_ints(row, ("p", "v")) for side in ("buys", "sells") for row in projected[side]):
            flags.add("MALFORMED_DATA")
        return [replace(base, data=projected, flags=tuple(sorted(flags)))]
    flags |= {"SEQUENCE_SCOPE_UNKNOWN", "HISTORY_BOUNDARY_UNKNOWN", "DIRECTION_UNKNOWN"}
    rows = _table(data.get("rows"))
    if not _valid_ints(data, ("startSeq", "rowCount")):
        flags.add("MALFORMED_DATA")
    if data.get("rowCount") != len(rows):
        flags.add("ROW_COUNT_MISMATCH")
    base = replace(base, flags=tuple(sorted(flags)))
    if not rows:
        return [_flag(base, "EMPTY_BATCH")]
    return [_project_row(base, row, i) for i, row in enumerate(rows)]


def _epoch_ns(value: datetime) -> int:
    delta = value.astimezone(timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return (delta.days * 86400 + delta.seconds) * 1000000000 + delta.microseconds * 1000


def _assessment(assessed_at: datetime, max_age_seconds: float) -> tuple[int, int]:
    try:
        if not isinstance(assessed_at, datetime) or assessed_at.utcoffset() is None:
            raise CaptureError("ASSESSMENT_TIME")
        assessed_ns = _epoch_ns(assessed_at)
    except (ValueError, TypeError, OverflowError) as error:
        raise CaptureError("ASSESSMENT_TIME") from error
    try:
        if type(max_age_seconds) not in (int, float) or max_age_seconds < 0:
            raise CaptureError("AGE_LIMIT")
        limit = max_age_seconds * 1000000000
        if not math.isfinite(limit):
            raise CaptureError("AGE_LIMIT")
        return assessed_ns, int(limit)
    except (ValueError, TypeError, OverflowError) as error:
        raise CaptureError("AGE_LIMIT") from error


def _receipt_flags(base: Observation, record: dict, assessed_ns: int, limit: int, previous) -> Observation:
    age = assessed_ns - base.received_wall_ns
    if age < 0:
        base = _flag(base, "RECEIVED_AFTER_ASSESSMENT")
    elif age > limit:
        base = _flag(base, "STALE_CAPTURE")
    # The probe samples wall/ISO separately. One second is a diagnostic tolerance,
    # not a supplier clock or source latency guarantee.
    if abs(_epoch_ns(_aware_time(record["received_at"])) - base.received_wall_ns) > 1000000000:
        base = _flag(base, "RECEIVE_CLOCK_MISMATCH")
    if previous is not None and (base.received_wall_ns < previous[0] or record["received_monotonic_ns"] < previous[1]):
        base = _flag(base, "RECEIVE_CLOCK_REGRESSION")
    return base


def _transport_flags(base: Observation, record: dict) -> Observation:
    flags = {
        "server_close": ("DISCONNECT",),
        "transport_error": ("TRANSPORT_ERROR",),
        "handshake_rejected": ("HANDSHAKE_REJECTED",),
    }
    base = _flag(base, *flags.get(base.kind, ()))
    if base.kind == "handshake_rejected" and record.get("http_status") in (401, 403):
        base = _flag(base, "PERMISSION_DENIED")
    if base.kind == "control_frame":
        if not _valid_ints(record, ("opcode", "payload_bytes")):
            base = _flag(base, "MALFORMED_DATA")
        if record.get("opcode") not in (9, 10):
            base = _flag(base, "UNSUPPORTED_CONTROL")
    return base


def replay_capture(
    foundation: LocalFoundation, capture_key: str, *, assessed_at: datetime, max_age_seconds: float = 30,
) -> tuple[Observation, ...]:
    """Replay in captured order with original receipt times and explicit unknowns.

    The caller supplies assessment time. No current clock, provider availability,
    trading date or buy/sell interpretation is synthesized during replay.
    """
    assessed_ns, limit = _assessment(assessed_at, max_age_seconds)
    source = read_capture(foundation, capture_key)
    result = []
    sequences: dict = {}
    gap_unknown = False
    previous = None
    for index, record in enumerate(_records(source), 1):
        if len(result) >= MAX_OBSERVATIONS:
            raise CaptureError("REPLAY_LIMIT")
        base = Observation(
            record=index, item=None, row=None, kind=record["event"], symbol=None,
            received_at=_aware_time(record["received_at"]).isoformat(timespec="microseconds").replace("+00:00", "Z"),
            received_wall_ns=record["received_wall_ns"], proxy_ts=None, data=None, flags=(),
        )
        base = _receipt_flags(base, record, assessed_ns, limit, previous)
        previous = (record["received_wall_ns"], record["received_monotonic_ns"])
        if "RECEIVE_CLOCK_REGRESSION" in base.flags:
            sequences.clear()
            gap_unknown = True
        if record["event"] in ("subscription_sent", "server_close", "transport_error", "handshake_rejected"):
            sequences.clear()
            gap_unknown = gap_unknown or index > 1 or record["event"] != "subscription_sent"
        if gap_unknown:
            base = _flag(base, "GAP_UNKNOWN")
        if record["event"] != "frame":
            result.append(_transport_flags(base, record))
            continue
        try:
            wire = _json(base64.b64decode(record["payload_base64"], validate=True).decode("utf-8"))
            if not isinstance(wire, dict) or not isinstance(wire.get("list"), list):
                raise CaptureError("MARKET_FORMAT")
        except (ValueError, TypeError, RecursionError):
            result.append(_flag(replace(base, kind="error"), "MALFORMED_PAYLOAD"))
            continue
        if type(wire.get("ts")) is not int or wire["ts"] < 0:
            base = _flag(base, "MALFORMED_DATA")
        if not wire["list"]:
            result.append(_flag(base, "EMPTY_FRAME"))
        for item_index, item in enumerate(wire["list"]):
            item_base = replace(base, item=item_index, proxy_ts=wire.get("ts"))
            try:
                if not isinstance(item, dict):
                    raise CaptureError("MARKET_FORMAT")
                projected = _project_item(item_base, item, capture_key.split(":")[0])
            except CaptureError as error:
                if error.code == "REPLAY_LIMIT":
                    raise
                projected = [_flag(replace(item_base, kind="error"), "MALFORMED_PAYLOAD")]
            except (ValueError, TypeError):
                projected = [_flag(replace(item_base, kind="error"), "MALFORMED_PAYLOAD")]
            if len(result) + len(projected) > MAX_OBSERVATIONS:
                raise CaptureError("REPLAY_LIMIT")
            result.extend(_sequence_flags(event, sequences) for event in projected)
    if not any(_has_market_data(event) for event in result):
        result = [_flag(event, "NO_MARKET_DATA") for event in result]
    return tuple(result)


_STORE_MARKER = b"intraday.d202.offline-store.v1\n"
_LIMITATIONS = {
    "PROVIDER_TIME_UNKNOWN", "COMPLETENESS_UNKNOWN", "DEPTH_SCOPE_UNKNOWN",
    "SEQUENCE_SCOPE_UNKNOWN", "HISTORY_BOUNDARY_UNKNOWN", "DIRECTION_UNKNOWN",
    "EMPTY_BATCH", "EMPTY_FRAME",
}


def _safe_path(path: Path) -> Path:
    path = path.absolute()
    if ".." in path.parts or any(part.is_symlink() for part in (path, *path.parents)):
        raise CaptureError("UNSAFE_PATH")
    return path


def _source_bytes(path: Path) -> bytes:
    path = _safe_path(path)
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid() or stat.S_IMODE(before.st_mode) != 0o600:
            raise CaptureError("PRIVATE_SOURCE_REQUIRED")
        if before.st_size > MAX_CAPTURE_BYTES:
            raise CaptureError("CAPTURE_SIZE")
        source = handle.read(MAX_CAPTURE_BYTES + 1)
        after = os.fstat(handle.fileno())
        if before.st_size != len(source) or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise CaptureError("SOURCE_CHANGED")
        return source


def _private_store(path: Path, *, create: bool) -> LocalFoundation:
    root = _safe_path(path)
    marker = root / ".d202-offline-store"
    if not root.exists() and create:
        root.mkdir(mode=0o700)  # Parent must already exist; never adopt another store.
        with marker.open("xb") as handle:
            handle.write(_STORE_MARKER)
    if not root.is_dir() or marker.is_symlink() or not marker.is_file():
        raise CaptureError("PRIVATE_STORE_REQUIRED")
    for member in (root, *root.rglob("*")):
        info = member.lstat()
        mode = 0o700 if stat.S_ISDIR(info.st_mode) else 0o600
        if (not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode))
                or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != mode):
            raise CaptureError("PRIVATE_STORE_REQUIRED")
    if marker.stat().st_size != len(_STORE_MARKER) or marker.read_bytes() != _STORE_MARKER:
        raise CaptureError("PRIVATE_STORE_REQUIRED")
    return LocalFoundation(root)


def capture_d202(
    foundation: LocalFoundation, *, raw_path: Path, symbol: str = "SH603790",
    seconds: float = 5, levels: int = 10, port: int = 18087,
    max_frames: int = MAX_FRAMES, max_bytes: int = MAX_PAYLOAD_BYTES,
    transport_python: Path = Path("/usr/bin/python3"),
) -> str:
    """Bound one loopback subscription, retain raw first, then publish via Foundation.

    No reconnect, login, service startup or semantic certification. The selected
    interpreter must already have websocket-client. The raw file survives any
    archive failure and is never overwritten. A returned key means retained,
    not healthy; callers must replay it to inspect quality.
    """
    if not isinstance(symbol, str) or re.fullmatch(_SYMBOL, symbol) is None:
        raise CaptureError("SYMBOL_FORMAT")
    if type(seconds) not in (int, float) or not 0 < seconds <= 30:
        raise CaptureError("CAPTURE_DURATION")
    for value, ceiling in ((levels, 1000), (port, 65535), (max_frames, MAX_FRAMES), (max_bytes, MAX_PAYLOAD_BYTES)):
        if type(value) is not int or not 1 <= value <= ceiling:
            raise CaptureError("CAPTURE_LIMIT")
    raw_path = _safe_path(raw_path)
    parent = raw_path.parent.stat()
    if parent.st_uid != os.getuid() or stat.S_IMODE(parent.st_mode) != 0o700:
        raise CaptureError("PRIVATE_SOURCE_REQUIRED")
    if not transport_python.is_absolute():
        raise CaptureError("TRANSPORT_RUNTIME")
    descriptor = os.open(raw_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "wb", buffering=0) as raw:
        os.fchmod(raw.fileno(), 0o600)  # Only this newly-created descriptor, never an existing file.
        command = [str(transport_python), "-I", "-B", str(Path(__file__).with_name("intraday_d202_transport.py")),
                   "--output-fd", str(raw.fileno()), "--symbol", symbol, "--seconds", str(seconds),
                   "--levels", str(levels), "--port", str(port), "--max-frames", str(max_frames), "--max-bytes", str(max_bytes)]
        failure = None
        try:
            with subprocess.Popen(command, pass_fds=(raw.fileno(),), stdin=subprocess.DEVNULL,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                  env={"PATH": os.defpath, "LANG": "C.UTF-8"}) as process:
                try:
                    returncode = process.wait(timeout=seconds + 8)
                except (subprocess.TimeoutExpired, KeyboardInterrupt):
                    # Reap explicitly, including SIGINT; Popen.__exit__ only
                    # briefly waits on KeyboardInterrupt and can leave a child.
                    process.kill()
                    process.wait()
                    raise
            if returncode != 0:
                failure = "TRANSPORT_PROCESS_FAILED"
        except subprocess.TimeoutExpired:
            failure = "CAPTURE_DEADLINE"
        except KeyboardInterrupt:
            failure = "CAPTURE_INTERRUPTED"
        except OSError:
            failure = "TRANSPORT_START_FAILED"
        if failure is not None:
            raw.write(capture_record("transport_error", error_type=failure))
    source = _source_bytes(raw_path)
    key = archive_capture(foundation, source, symbol=symbol)
    if read_capture(foundation, key) != source:
        raise CaptureError("CAPTURE_INTEGRITY")
    return key


def _replay_summary(foundation, capture_key, assessed_at, max_age_seconds) -> tuple[dict, int]:
    events = replay_capture(foundation, capture_key, assessed_at=assessed_at, max_age_seconds=max_age_seconds)
    flags = dict(sorted(Counter(flag for event in events for flag in event.flags).items()))
    degraded = bool(set(flags) - _LIMITATIONS)
    return {"status": "degraded" if degraded else "limited", "capture_key": capture_key,
            "assessed_at": assessed_at.isoformat(timespec="microseconds").replace("+00:00", "Z"),
            "max_age_seconds": max_age_seconds, "observations": len(events),
            "valid_market_observations": sum(_has_market_data(event) for event in events),
            "valid_market_kinds": dict(sorted(Counter(event.kind for event in events if _has_market_data(event)).items())),
            "kinds": dict(sorted(Counter(event.kind for event in events).items())),
            "quality_flags": flags}, 1 if degraded else 0


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse otherwise echoes arbitrary invalid option values.
        raise CaptureError("CLI_ARGUMENTS")


def _run_cli(argv) -> tuple[dict, int]:
    parser = _Parser(description="Bounded D202 acquisition and offline replay; never qualified market data.")
    commands = parser.add_subparsers(dest="command", required=True)
    archive = commands.add_parser("archive", help="Retain an existing private JSONL capture")
    archive.add_argument("--store", required=True, type=Path)
    archive.add_argument("--source", required=True, type=Path)
    archive.add_argument("--symbol", required=True)
    replay = commands.add_parser("replay", help="Assess an archived capture at an explicit time")
    replay.add_argument("--store", required=True, type=Path)
    replay.add_argument("--capture-key", required=True)
    replay.add_argument("--assessed-at", required=True)
    replay.add_argument("--max-age-seconds", type=float, default=30)
    collect = commands.add_parser("capture", help="Bound one authorized subscription to an existing loopback proxy")
    collect.add_argument("--store", required=True, type=Path)
    collect.add_argument("--raw-path", required=True, type=Path)
    collect.add_argument("--symbol", default="SH603790")
    collect.add_argument("--seconds", type=float, default=5)
    collect.add_argument("--levels", type=int, default=10)
    collect.add_argument("--port", type=int, default=18087)
    collect.add_argument("--max-frames", type=int, default=MAX_FRAMES)
    collect.add_argument("--max-bytes", type=int, default=MAX_PAYLOAD_BYTES)
    collect.add_argument("--transport-python", type=Path, default=Path("/usr/bin/python3"))
    args = parser.parse_args(argv)
    common = {"offline": args.command != "capture", "supplier_contract_verified": False, "qualified_market_data": False}
    if args.command == "capture":
        foundation = _private_store(args.store, create=True)
        key = capture_d202(foundation, raw_path=args.raw_path, symbol=args.symbol, seconds=args.seconds,
                           levels=args.levels, port=args.port, max_frames=args.max_frames, max_bytes=args.max_bytes,
                           transport_python=args.transport_python)
        summary, status = _replay_summary(foundation, key, datetime.now(timezone.utc), 30)
        missing = sorted({"thousand", "entrust", "trade"} - summary["valid_market_kinds"].keys())
        if missing:
            summary["status"], status = "degraded", 1
        return {**common, **summary, "requested_seconds": args.seconds, "missing_types": missing}, status
    if args.command == "archive":
        source = _source_bytes(args.source)
        _capture_key(source, args.symbol)  # Preflight before even creating CLI store metadata.
        foundation = _private_store(args.store, create=True)
        key = archive_capture(foundation, source, symbol=args.symbol)
        return {**common, "status": "archived", "capture_key": key, "bytes": len(source),
                "raw_records": len(source.splitlines()), "replay_required": True}, 0
    try:
        assessed_at = _aware_time(args.assessed_at)
    except (ValueError, TypeError, OverflowError) as error:
        raise CaptureError("ASSESSMENT_TIME") from error
    foundation = _private_store(args.store, create=False)
    summary, status = _replay_summary(foundation, args.capture_key, assessed_at, args.max_age_seconds)
    return {**common, **summary}, status


def main(argv: list[str] | None = None) -> int:
    """Print only safe summaries/codes. 0=stored/limited, 1=degraded, 2=failed."""
    previous_umask = os.umask(0o077)
    try:
        summary, status = _run_cli(argv)
    except (CaptureError, FoundationFailure) as error:
        summary, status = {"status": "failed", "code": error.code}, 2
    except OSError:
        summary, status = {"status": "failed", "code": "FILE_IO_ERROR"}, 2
    finally:
        os.umask(previous_umask)
    print(json.dumps(summary, sort_keys=True))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
