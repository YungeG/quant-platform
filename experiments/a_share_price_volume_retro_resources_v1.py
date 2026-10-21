"""Bounded owned user-transient workers; no market/credential/network Reader.

memory.max charges descendants/cache, not just RSS. Controller logs/journal are
bounded here; the admitted Adapter separately bounds its data publications.
Resource receipts and planned budgets are never source-access permission.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

GIB = 1024**3
MIB = 1024**2
MEMORY_MAX = 6 * GIB
MIN_AVAILABLE = 8 * GIB
CLOSE_SECONDS = 10
CLOSE_BYTES = 16384
_WORKER_MODULE = "experiments.a_share_price_volume_retro_resources_v1"
_ALLOWED_MODULES = (
    _WORKER_MODULE,
    "experiments.run_a_share_price_volume_retro_real_v1",
)


class RetroResourceError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _require(value, code):
    if not value:
        raise RetroResourceError(code)


@dataclass(frozen=True, slots=True)
class RetroResourceLimits:
    memory_bytes: int
    deadline_seconds: int
    total_seconds: int
    output_bytes: int
    storage_bytes: int
    max_attempts: int

    def __post_init__(self):
        _require(
            all(type(v) is int and v > 0 for v in asdict(self).values()),
            "INVALID_LIMITS",
        )
        _require(32 * MIB <= self.memory_bytes <= MEMORY_MAX, "INVALID_LIMITS")
        _require(
            self.total_seconds >= self.deadline_seconds + CLOSE_SECONDS,
            "INVALID_LIMITS",
        )
        _require(
            self.output_bytes >= 64
            and self.storage_bytes >= self.output_bytes + CLOSE_BYTES,
            "INVALID_LIMITS",
        )

    @property
    def compute_threads(self):
        return 4

    @property
    def duckdb_managed_bytes(self):
        return 2 * GIB

    @property
    def min_available_bytes(self):
        return MIN_AVAILABLE


def _json(value) -> bytes:
    return (
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
        + b"\n"
    )


def available_memory_bytes() -> int:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise RetroResourceError("HOST_MEMORY_UNKNOWN")


def probe_resource_control() -> dict[str, Any]:
    """Read-only hint; not proof that any worker actually has an applied cap."""
    if (
        sys.platform != "linux"
        or not shutil.which("systemd-run")
        or not shutil.which("systemctl")
    ):
        return {
            "backend_available": False,
            "hard_limit_verified": False,
            "reason": "user-systemd-unavailable",
        }
    try:
        r = subprocess.run(
            [
                "systemctl",
                "--user",
                "show",
                "app.slice",
                "--property=LoadState",
                "--value",
            ],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        available = (
            r.returncode == 0
            and r.stdout.strip() == "loaded"
            and Path("/sys/fs/cgroup/cgroup.controllers").is_file()
        )
    except (OSError, subprocess.SubprocessError):
        available = False
    return {
        "backend_available": available,
        "hard_limit_verified": False,
        "reason": None if available else "user-manager-unavailable",
    }


def _no_links(path: Path):
    _require(not any(p.is_symlink() for p in (path, *path.parents)), "SYMLINK_REJECTED")


def _read_json_regular(path: Path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        _require(
            stat.S_ISREG(info.st_mode)
            and info.st_uid == os.getuid()
            and info.st_size <= 65536,
            "BUDGET_INVALID",
        )
        raw = os.read(fd, 65537)
        _require(len(raw) <= 65536, "BUDGET_INVALID")
        value = json.loads(raw)
        _require(_json(value) == raw, "BUDGET_INVALID")
        return value
    finally:
        os.close(fd)


def _replace_json(path: Path, value):
    temp = path.parent / (".budget-" + uuid.uuid4().hex)
    try:
        with temp.open("xb") as stream:
            stream.write(_json(value))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def _reserve(root: Path, limits: RetroResourceLimits, unit: str):
    """Reserve before launch. Immutable markers detect torn/reset counter state."""
    _no_links(root)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    _require(root.is_dir() and root.stat().st_uid == os.getuid(), "OUTPUT_NOT_OWNED")
    lock = os.open(
        root / ".resource.lock",
        os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK,
        0o600,
    )
    try:
        _require(stat.S_ISREG(os.fstat(lock).st_mode), "BUDGET_INVALID")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RetroResourceError("WORKER_ALREADY_ACTIVE") from error
        path = root / "budget.json"
        declared = asdict(limits)
        if path.exists() or path.is_symlink():
            state = _read_json_regular(path)
            _require(
                set(state)
                == {
                    "limits",
                    "attempts_reserved",
                    "seconds_reserved",
                    "bytes_reserved",
                    "active_unit",
                },
                "BUDGET_INVALID",
            )
            _require(state["limits"] == declared, "BUDGET_CONFLICT")
        else:
            _require(
                not any(p.name != ".resource.lock" for p in root.iterdir()),
                "OUTPUT_OCCUPIED",
            )
            state = {
                "limits": declared,
                "attempts_reserved": 0,
                "seconds_reserved": 0,
                "bytes_reserved": 0,
                "active_unit": None,
            }
        for key in ("attempts_reserved", "seconds_reserved", "bytes_reserved"):
            _require(type(state[key]) is int and state[key] >= 0, "BUDGET_INVALID")
        n = state["attempts_reserved"]
        _require(
            state["seconds_reserved"] == n * (limits.deadline_seconds + CLOSE_SECONDS)
            and state["bytes_reserved"] == n * (limits.output_bytes + CLOSE_BYTES),
            "BUDGET_INVALID",
        )
        markers = list(root.glob("attempt-*.reserve.json"))
        _require(len(markers) == n, "BUDGET_INVALID")
        for i in range(1, n + 1):
            marker = _read_json_regular(root / f"attempt-{i}.reserve.json")
            _require(
                marker["attempt"] == i and marker["limits"] == declared,
                "BUDGET_INVALID",
            )
        _require(state["active_unit"] is None, "WORKER_STATUS_UNRESOLVED")
        _require(
            n < limits.max_attempts
            and state["seconds_reserved"] + limits.deadline_seconds + CLOSE_SECONDS
            <= limits.total_seconds
            and state["bytes_reserved"] + limits.output_bytes + CLOSE_BYTES
            <= limits.storage_bytes,
            "BUDGET_EXHAUSTED",
        )
        attempt = n + 1
        for suffix in ("stdout", "stderr", "json", "reserve.json"):
            _require(
                not (root / f"attempt-{attempt}.{suffix}").exists(), "BUDGET_INVALID"
            )
        marker = {"attempt": attempt, "unit": unit, "limits": declared}
        with (root / f"attempt-{attempt}.reserve.json").open("xb") as stream:
            stream.write(_json(marker))
            stream.flush()
            os.fsync(stream.fileno())
        state.update(
            attempts_reserved=attempt,
            seconds_reserved=state["seconds_reserved"]
            + limits.deadline_seconds
            + CLOSE_SECONDS,
            bytes_reserved=state["bytes_reserved"] + limits.output_bytes + CLOSE_BYTES,
            active_unit=unit,
        )
        _replace_json(path, state)
        return lock, attempt
    except BaseException:
        os.close(lock)
        raise


def _mark_closed(root, unit, attempt):
    state = _read_json_regular(root / "budget.json")
    _require(
        state["active_unit"] == unit and state["attempts_reserved"] == attempt,
        "BUDGET_INVALID",
    )
    state["active_unit"] = None
    _replace_json(root / "budget.json", state)


def _systemctl(unit: str, args: tuple[str, ...], until: float):
    _require(
        re.fullmatch(r"retro-resource-[0-9a-f]{32}\.service", unit) is not None,
        "UNIT_ID_INVALID",
    )
    remaining = until - time.monotonic()
    _require(remaining > 0, "CLOSE_DEADLINE")
    return subprocess.run(
        ["systemctl", "--user", *args, unit],
        capture_output=True,
        text=True,
        timeout=min(2, remaining),
        check=False,
    )


def _properties(unit, until):
    r = _systemctl(
        unit,
        (
            "show",
            "--property=LoadState",
            "--property=ActiveState",
            "--property=SubState",
            "--property=MainPID",
            "--property=ControlGroup",
            "--property=Result",
            "--property=MemoryPeak",
            "--property=MemoryMax",
            "--property=ExecMainCode",
            "--property=ExecMainStatus",
        ),
        until,
    )
    values = dict(line.split("=", 1) for line in r.stdout.splitlines() if "=" in line)
    # A failed command with no exact not-found proof is UNKNOWN, never inactive.
    if r.returncode != 0 and values.get("LoadState") != "not-found":
        raise RetroResourceError("WORKER_STATUS_UNRESOLVED")
    return values


def _finish(unit, process, until):
    """Catch all cleanup errors; retain an unresolved durable lease if not proven closed."""
    info = {}
    props = {}
    closed = process is None
    if process is None:
        return True, info, props
    try:
        for label, args in (
            ("kill", ("kill", "--kill-whom=all", "--signal=SIGKILL")),
            ("stop", ("stop",)),
        ):
            try:
                info[label] = _systemctl(unit, args, until).returncode
            except Exception as error:  # noqa: BLE001 -- cleanup must retain every failure, not skip the durable lease
                info[label] = type(error).__name__
        try:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=max(0.01, min(1, until - time.monotonic())))
            info["broker_closed"] = True
        except Exception as error:  # noqa: BLE001 -- unknown broker state must remain unresolved
            info["broker_closed"] = False
            info["broker_error"] = type(error).__name__
        try:
            props = _properties(unit, until)
            terminal = props.get("LoadState") == "not-found" or (
                props.get("ActiveState") in ("inactive", "failed")
                and props.get("MainPID") == "0"
            )
            group = props.get("ControlGroup", "")
            populated = False
            if group:
                _require(Path(group).name == unit, "UNIT_ID_INVALID")
                event = Path("/sys/fs/cgroup") / group.lstrip("/") / "cgroup.events"
                if event.exists():
                    populated = "populated 1" in event.read_text().splitlines()
            closed = bool(info.get("broker_closed")) and terminal and not populated
        except Exception as error:  # noqa: BLE001 -- failed status proof is recorded, never treated as inactive
            info["status_error"] = type(error).__name__
    finally:
        for stream in (process.stdout, process.stderr):
            try:
                if stream is not None:
                    stream.close()
            except Exception as error:  # noqa: BLE001 -- bounded cleanup diagnostics survive closure errors
                info["stream_error"] = type(error).__name__
    return closed, info, props


def worker_resource_evidence() -> dict[str, Any]:
    unit = os.environ.get("RETRO_RESOURCE_UNIT", "")
    _require(
        re.fullmatch(r"retro-resource-[0-9a-f]{32}\.service", unit) is not None,
        "RESOURCE_NOT_ENFORCED",
    )
    raw = Path("/proc/self/cgroup").read_text().strip()
    _require(raw.startswith("0::/"), "RESOURCE_NOT_ENFORCED")
    relative = raw.split("::", 1)[1]
    _require(Path(relative).name == unit, "RESOURCE_NOT_ENFORCED")
    group = Path("/sys/fs/cgroup") / relative.lstrip("/")
    value = (group / "memory.max").read_text().strip()
    _require(value.isdecimal(), "RESOURCE_NOT_ENFORCED")
    cap = int(value)
    _require(
        str(cap) == os.environ.get("RETRO_RESOURCE_MEMORY") and cap <= MEMORY_MAX,
        "RESOURCE_NOT_ENFORCED",
    )
    _require(os.environ.get("OPENBLAS_NUM_THREADS") == "1", "RESOURCE_NOT_ENFORCED")
    return {
        "cgroup": relative,
        "memory_max": cap,
        "memory_current": int((group / "memory.current").read_text()),
        "blas_threads": os.environ["OPENBLAS_NUM_THREADS"],
        "allocated_bytes": 4096,
    }


def run_bounded_worker(
    worker_module: str,
    worker_args: tuple[str, ...],
    output_root: Path,
    limits: RetroResourceLimits,
) -> dict[str, Any]:
    _require(worker_module in _ALLOWED_MODULES, "WORKER_NOT_ALLOWED")
    _require(
        type(worker_args) is tuple
        and all(type(a) is str and "\x00" not in a for a in worker_args),
        "INVALID_WORKER_ARGS",
    )
    _require(type(limits) is RetroResourceLimits, "INVALID_LIMITS")
    if worker_module != _WORKER_MODULE:
        _require(limits.memory_bytes == MEMORY_MAX, "RESOURCE_NOT_ENFORCED")
    root = Path(output_root).absolute()
    _no_links(root)
    unit = "retro-resource-" + uuid.uuid4().hex + ".service"
    lock, attempt = _reserve(root, limits, unit)
    start = time.monotonic()
    until = start + limits.deadline_seconds + CLOSE_SECONDS
    process = None
    stop = None
    code = None
    used = 0
    evidence = None
    props = {}
    error = None
    minimum = None
    last_check = 0.0
    stdout = root / f"attempt-{attempt}.stdout"
    stderr = root / f"attempt-{attempt}.stderr"
    try:
        _require(probe_resource_control()["backend_available"], "RESOURCE_UNAVAILABLE")
        minimum = available_memory_bytes()
        _require(minimum >= MIN_AVAILABLE, "HOST_MEMORY_LOW")
        command = [
            "systemd-run",
            "--user",
            "--wait",
            "--pipe",
            "--quiet",
            "--unit=" + unit,
            "--property=WorkingDirectory=" + str(Path(__file__).resolve().parents[1]),
            "--property=MemoryAccounting=yes",
            "--property=CPUQuota=400%",
            "--property=MemoryMax=" + str(limits.memory_bytes),
            "--property=MemorySwapMax=0",
            "--property=RuntimeMaxSec=" + str(limits.deadline_seconds) + "s",
            "--property=TimeoutStopSec=1s",
            "--property=KillMode=control-group",
            "--property=SendSIGKILL=yes",
            "--property=TasksMax=64",
            "--setenv=OPENBLAS_NUM_THREADS=1",
            "--setenv=RETRO_RESOURCE_UNIT=" + unit,
            "--setenv=RETRO_RESOURCE_MEMORY=" + str(limits.memory_bytes),
            sys.executable,
            "-B",
            "-m",
            worker_module,
            *worker_args,
        ]
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        assert process.stdout is not None and process.stderr is not None
        with (
            stdout.open("xb") as out,
            stderr.open("xb") as err,
            selectors.DefaultSelector() as selector,
        ):
            selector.register(process.stdout, selectors.EVENT_READ, out)
            selector.register(process.stderr, selectors.EVENT_READ, err)
            while selector.get_map():
                now = time.monotonic()
                if now - last_check >= 0.2:
                    value = available_memory_bytes()
                    minimum = min(minimum, value)
                    last_check = now
                    if value < MIN_AVAILABLE and stop is None:
                        stop = "HOST_MEMORY_LOW"
                if now - start >= limits.deadline_seconds + 2 and stop is None:
                    stop = "DEADLINE"
                if stop is not None:
                    _systemctl(
                        unit, ("kill", "--kill-whom=all", "--signal=SIGKILL"), until
                    )
                for key, _ in selector.select(timeout=0.05):
                    chunk = os.read(key.fd, 8192)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    left = max(0, limits.output_bytes - used)
                    key.data.write(chunk[:left])
                    used += min(len(chunk), left)
                    if len(chunk) > left and stop is None:
                        stop = "OUTPUT_LIMIT"
                if time.monotonic() >= until - 4:
                    stop = stop or "DEADLINE"
                    break
        code = process.wait(timeout=max(0.01, min(1, until - time.monotonic())))
        props = _properties(unit, until)
        if code != 0 and stop is None:
            result = props.get("Result", "")
            stop = (
                "MEMORY_LIMIT"
                if result == "oom-kill"
                else "DEADLINE"
                if result == "timeout"
                else "WORKER_FAILED"
            )
        if worker_module == _WORKER_MODULE and stdout.stat().st_size:
            try:
                evidence = json.loads(stdout.read_bytes().splitlines()[0])
            except (ValueError, IndexError):
                pass
        if code == 0 and worker_module == _WORKER_MODULE:
            _require(
                isinstance(evidence, dict)
                and evidence.get("memory_max") == limits.memory_bytes,
                "RESOURCE_NOT_ENFORCED",
            )
    except Exception as exc:  # noqa: BLE001 -- re-raised only after durable closure evidence and lock release
        stop = stop or (
            exc.code if isinstance(exc, RetroResourceError) else "CONTROLLER_FAILED"
        )
        error = exc if isinstance(exc, RetroResourceError) else RetroResourceError(stop)
    finally:
        try:
            closed, cleanup, final_props = _finish(unit, process, until)
        except Exception as exc:  # noqa: BLE001 -- an unexpected cleanup fault cannot discard the active lease
            closed = False
            cleanup = {"unexpected_cleanup_error": type(exc).__name__}
            final_props = {}
        if not closed:
            stop = "WORKER_STATUS_UNRESOLVED"
            error = RetroResourceError(stop)
        if process is not None:
            for stream in (process.stdout, process.stderr):
                try:
                    if stream is not None:
                        stream.close()
                except Exception as exc:  # noqa: BLE001 -- include any final descriptor error in the receipt
                    cleanup["final_stream_error"] = type(exc).__name__
        record = {
            "state": "COMPLETE" if code == 0 and stop is None and closed else "FAILED",
            "attempt": attempt,
            "unit": unit,
            "returncode": code,
            "stop_category": stop,
            "elapsed_ms": int((time.monotonic() - start) * 1000),
            "memory_bytes_requested": limits.memory_bytes,
            "resource_limit_kind": "cgroup-v2-memory.max-includes-children-and-cache",
            "worker_evidence": evidence,
            "unit_properties": props,
            "final_unit_properties": final_props,
            "termination_verified": closed,
            "controller_output_bytes": used,
            "controller_storage_scope": "logs and journal only; Adapter must bound data publication",
            "cleanup": cleanup,
            "minimum_host_available_bytes": minimum,
            "controller_source_reads": 0,
            "controller_http_requests": 0,
            "source_reads": 0 if worker_module == _WORKER_MODULE else None,
            "http_requests": 0 if worker_module == _WORKER_MODULE else None,
        }
        try:
            raw = _json(record)
            _require(len(raw) <= CLOSE_BYTES - 4096, "CLOSURE_RESERVE_EXCEEDED")
            with (root / f"attempt-{attempt}.json").open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            if closed:
                _mark_closed(root, unit, attempt)
        except Exception as exc:  # noqa: BLE001 -- failed publication keeps the lease; error is raised after unlocking
            error = RetroResourceError("CLOSURE_FAILED")
            error.__cause__ = exc
        finally:
            os.close(lock)
    if error is not None:
        raise error
    return record


def _probe_worker(scenario):
    evidence = worker_resource_evidence()
    print(json.dumps(evidence), flush=True)
    if scenario == "ok":
        data = bytearray(4096)
        assert len(data) == 4096
    elif scenario == "memory":
        _require(evidence["memory_max"] <= 256 * MIB, "LARGE_NEGATIVE_PROBE_REFUSED")
        data = bytearray(evidence["memory_max"] + 64 * MIB)
        assert data
    elif scenario == "deadline":
        time.sleep(60)  # Deliberate owned timeout fixture.
    elif scenario == "stubborn":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        if os.fork() == 0:
            time.sleep(60)
        time.sleep(60)
    elif scenario == "output":
        while True:
            print("x" * 4096, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--probe-worker",
        choices=("ok", "memory", "deadline", "output", "stubborn"),
        required=True,
    )
    _probe_worker(parser.parse_args().probe_worker)


if __name__ == "__main__":
    main()
