"""Synthetic loopback WebSocket only; never contact the D202 service in tests."""
from __future__ import annotations

import base64
import errno
import hashlib
import json
import os
import resource
import signal
import stat
import socketserver
import struct
import subprocess
import sys
import threading
from contextlib import contextmanager
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from pathlib import Path

import pytest
from crypto_quant_foundation import FoundationFailure, LocalFoundation

from intraday_market_data import archive_capture, capture_d202, read_capture, replay_capture

ROOT = Path(__file__).resolve().parents[2]
SYMBOL = "SH603790"
PAYLOAD = json.dumps({"ts": 1789092000000, "list": [
    {"type": "thousand", "data": {"code": SYMBOL, "price": 2000,
     "totalBuyVol": 500, "totalSellVol": 600, "totalBuyAmt": 10, "totalSellAmt": 12,
     "buyCount": 2, "sellCount": 3, "l2Time": 123,
     "buys": [{"p": 1999, "v": 2}], "sells": [{"p": 2001, "v": 3}]}},
    {"type": "entrust", "data": {"code": SYMBOL, "startSeq": 90, "rowCount": 1,
     "rows": [{"seq": 90, "t": 95959, "p": 2000, "v": 2, "d": "B"}]}},
    {"type": "trade", "data": {"code": SYMBOL, "startSeq": 10, "rowCount": 1,
     "rows": [{"seq": 10, "t": 100000, "p": 2000, "v": 2, "d": 128,
               "buyer": 101, "seller": 99, "buyVol": 2, "sellVol": 3}]}},
]}).encode()


def cli(*args):
    return subprocess.run([sys.executable, "-m", "intraday_market_data", *map(str, args)],
                          cwd=ROOT, capture_output=True, text=True, timeout=12)


def server_frame(payload, opcode=1, *, fin=True):
    header = bytes([(0x80 if fin else 0) | opcode])
    return header + (bytes([len(payload)]) if len(payload) < 126 else b"\x7e" + struct.pack("!H", len(payload))) + payload


def client_frame(reader):
    header = reader.read(2)
    if len(header) != 2:
        return None, b""
    length = header[1] & 127
    if length == 126:
        length = struct.unpack("!H", reader.read(2))[0]
    assert length < 65536 and header[1] & 128
    mask = reader.read(4)
    payload = reader.read(length)
    return header[0] & 15, bytes(value ^ mask[i % 4] for i, value in enumerate(payload))


@contextmanager
def endpoint(*messages, http_status=101, ready: threading.Event | None = None):
    seen = {"commands": [], "closed": False, "errors": [], "pongs": [], "requests": 0}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            pass

        def do_GET(self):
            self.connection.settimeout(3)
            try:
                seen["requests"] += 1
                assert self.path == "/d202"
                if http_status != 101:
                    self.send_error(http_status, "synthetic-secret")
                    return
                self.send_response(101)
                self.send_header("Upgrade", "websocket")
                self.send_header("Connection", "Upgrade")
                # RFC 6455 requires SHA-1 for this handshake, not for data integrity.
                # pi-lens-ignore: python-weak-hash
                accept = hashlib.sha1((self.headers["Sec-WebSocket-Key"] + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode(), usedforsecurity=False).digest()
                self.send_header("Sec-WebSocket-Accept", base64.b64encode(accept).decode())
                self.end_headers()
                opcode, command = client_frame(self.rfile)
                assert opcode == 1
                seen["commands"].append(json.loads(command))
                if ready is not None:
                    ready.set()
                for message in messages:
                    self.wfile.write(message)
                    self.wfile.flush()
                while True:
                    opcode, command = client_frame(self.rfile)
                    if opcode in (None, 8):
                        if opcode == 8:
                            self.wfile.write(server_frame(command, 8))
                            self.wfile.flush()
                        seen["closed"] = True
                        return
                    if opcode == 1:
                        seen["commands"].append(json.loads(command))
                    elif opcode == 10:
                        seen["pongs"].append(command)
            except (OSError, ValueError, AssertionError) as error:
                seen["errors"].append(type(error).__name__)
            finally:
                self.close_connection = True

    with socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
        thread.start()
        try:
            yield server.server_address[1], seen
        finally:
            server.shutdown()
            thread.join(timeout=3)
            assert not thread.is_alive()


@pytest.mark.parametrize("opcode", [1, 2])
def test_capture_cli_retains_raw_then_reopens_and_replays_through_platform(tmp_path, opcode):
    raw_path = tmp_path / "synthetic.jsonl"
    store_path = tmp_path / "store"
    with endpoint(server_frame(PAYLOAD, opcode)) as (port, seen):
        result = cli("capture", "--store", store_path, "--raw-path", raw_path,
                     "--symbol", SYMBOL, "--port", port, "--seconds", "0.1")
    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads(result.stdout)
    assert summary["status"] == "limited"
    assert summary["offline"] is False
    assert summary["qualified_market_data"] is False
    assert summary["supplier_contract_verified"] is False
    assert summary["valid_market_observations"] == 3
    raw = raw_path.read_bytes()
    assert read_capture(LocalFoundation(store_path), summary["capture_key"]) == raw
    events = replay_capture(LocalFoundation(store_path), summary["capture_key"],
                            assessed_at=datetime.fromisoformat(summary["assessed_at"]))
    assert {event.kind for event in events} >= {"thousand", "entrust", "trade"}
    assert any("DIRECTION_UNKNOWN" in event.flags for event in events)
    frames = [json.loads(line) for line in raw.splitlines() if json.loads(line)["event"] == "frame"]
    assert base64.b64decode(frames[0]["payload_base64"]) == PAYLOAD
    assert {command["type"] for command in seen["commands"][0]} == {"thousand", "entrust", "trade"}
    assert all(command["code"] == SYMBOL and command["enable"] == 0 for command in seen["commands"][1])
    assert seen["closed"] and not seen["errors"]


def test_capture_degrades_when_a_requested_stream_is_missing(tmp_path):
    payload = json.dumps({"ts": 1789092000000, "list": [json.loads(PAYLOAD)["list"][2]]}).encode()
    with endpoint(server_frame(payload)) as (port, _seen):
        result = cli("capture", "--store", tmp_path / "store", "--raw-path", tmp_path / "raw.jsonl",
                     "--port", port, "--seconds", "0.1")
    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["status"] == "degraded"
    assert summary["missing_types"] == ["entrust", "thousand"]
    assert summary["valid_market_observations"] == 1
    assert summary["qualified_market_data"] is False


@pytest.mark.parametrize("http_status", [401, 403])
def test_capture_archives_permission_failure_without_echoing_server_text(tmp_path, http_status):
    raw_path = tmp_path / "raw.jsonl"
    store_path = tmp_path / "store"
    with endpoint(http_status=http_status) as (port, _seen):
        result = cli("capture", "--store", store_path, "--raw-path", raw_path,
                     "--port", port, "--seconds", "0.1")
    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["status"] == "degraded"
    assert "PERMISSION_DENIED" in summary["quality_flags"]
    assert "synthetic-secret" not in result.stdout + result.stderr
    assert read_capture(LocalFoundation(store_path), summary["capture_key"]) == raw_path.read_bytes()


@pytest.mark.parametrize("messages,flag", [
    ((), "NO_MARKET_DATA"),
    ((server_frame(b'{"ts":1,"list":[{"type":"info","msg":"synthetic-secret"}]}'),), "NO_MARKET_DATA"),
    ((server_frame(PAYLOAD), server_frame(b'{"ts":1,"list":[{"type":"error","msg":"synthetic-secret"}]}')), "PROVIDER_ERROR"),
    ((server_frame(PAYLOAD), server_frame(b"\xff")), "MALFORMED_PAYLOAD"),
    ((server_frame(PAYLOAD), server_frame(b"\x03\xe8", 8)), "DISCONNECT"),
])
def test_capture_faults_are_retained_and_never_reported_as_normal(tmp_path, messages, flag):
    raw_path = tmp_path / "raw.jsonl"
    store_path = tmp_path / "store"
    with endpoint(*messages) as (port, _seen):
        result = cli("capture", "--store", store_path, "--raw-path", raw_path,
                     "--port", port, "--seconds", "0.1")
    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert summary["status"] == "degraded" and flag in summary["quality_flags"]
    assert read_capture(LocalFoundation(store_path), summary["capture_key"]) == raw_path.read_bytes()
    assert "synthetic-secret" not in result.stdout + result.stderr


@pytest.mark.parametrize("option,value,retained_frames", [
    ("--max-frames", 1, 1), ("--max-bytes", len(PAYLOAD) - 1, 0),
])
def test_capture_resource_limit_retains_prefix_without_claiming_success(tmp_path, option, value, retained_frames):
    raw_path = tmp_path / "raw.jsonl"
    store_path = tmp_path / "store"
    with endpoint(server_frame(PAYLOAD)) as (port, seen):
        result = cli("capture", "--store", store_path, "--raw-path", raw_path,
                     "--port", port, "--seconds", "0.1", option, value)
    assert result.returncode == 1
    summary = json.loads(result.stdout)
    assert "TRANSPORT_ERROR" in summary["quality_flags"]
    rows = [json.loads(line) for line in raw_path.read_bytes().splitlines()]
    assert sum(row["event"] == "frame" for row in rows) == retained_frames
    assert any(row.get("error_type") == "CAPTURE_RESOURCE_LIMIT" for row in rows)
    assert read_capture(LocalFoundation(store_path), summary["capture_key"]) == raw_path.read_bytes()
    assert seen["closed"] and not seen["errors"]


def test_capture_reassembles_fragmented_payload_and_replies_to_ping(tmp_path):
    frames = (server_frame(PAYLOAD[:100], fin=False), server_frame(b"synthetic-ping", 9),
              server_frame(PAYLOAD[100:], opcode=0))
    raw_path = tmp_path / "raw.jsonl"
    with endpoint(*frames) as (port, seen):
        result = cli("capture", "--store", tmp_path / "store", "--raw-path", raw_path,
                     "--port", port, "--seconds", "0.1")
    assert result.returncode == 0
    summary = json.loads(result.stdout)
    assert summary["missing_types"] == [] and summary["valid_market_observations"] == 3
    rows = [json.loads(line) for line in raw_path.read_bytes().splitlines()]
    data = [base64.b64decode(row["payload_base64"]) for row in rows if row["event"] == "frame"]
    assert data == [PAYLOAD]
    assert seen["pongs"] == [b"synthetic-ping"]
    assert seen["closed"] and not seen["errors"]


@pytest.mark.parametrize("error_number", [errno.ENOSPC, errno.EACCES])
def test_capture_keeps_raw_and_previous_archive_on_publication_failure(tmp_path, monkeypatch, error_number):
    store_path = tmp_path / "store"
    foundation = LocalFoundation(store_path)
    raw_path = tmp_path / "raw.jsonl"
    with endpoint(server_frame(PAYLOAD)) as (port, _seen):
        first = capture_d202(foundation, raw_path=tmp_path / "first.jsonl", port=port, seconds=0.1)
    original = read_capture(foundation, first)
    before = {p.relative_to(store_path): p.read_bytes() for p in store_path.rglob("*") if p.is_file()}

    def fail_replace(*_args, **_kwargs):
        raise OSError(error_number, "synthetic-storage-failure")

    with endpoint(server_frame(PAYLOAD)) as (port, _seen), monkeypatch.context() as patch:
        patch.setattr(os, "replace", fail_replace)
        with pytest.raises(FoundationFailure) as failure:
            capture_d202(foundation, raw_path=raw_path, port=port, seconds=0.1)
    assert failure.value.code == "LOG_PUBLICATION_FAILED"
    assert read_capture(LocalFoundation(store_path), first) == original
    assert {p.relative_to(store_path): p.read_bytes() for p in store_path.rglob("*") if p.is_file()} == before
    assert stat.S_IMODE(raw_path.stat().st_mode) == 0o600
    raw = raw_path.read_bytes()
    assert any(json.loads(line)["event"] == "frame" for line in raw.splitlines())
    second = archive_capture(LocalFoundation(store_path), raw, symbol=SYMBOL)
    assert second != first and read_capture(LocalFoundation(store_path), second) == raw
    assert raw_path.read_bytes() == raw


def test_capture_deadline_kills_and_reaps_uncooperative_worker(tmp_path):
    pid_file = tmp_path / "worker.pid"
    runtime = tmp_path / "uncooperative-python"
    runtime.write_text("#!/usr/bin/python3\nimport os, time\nfrom pathlib import Path\n"
                       f"Path({str(pid_file)!r}).write_text(str(os.getpid()))\ntime.sleep(60)\n")
    runtime.chmod(0o700)
    raw_path = tmp_path / "raw.jsonl"
    try:
        result = cli("capture", "--store", tmp_path / "store", "--raw-path", raw_path,
                     "--seconds", "0.01", "--transport-python", runtime)
        assert result.returncode == 1
        assert not Path(f"/proc/{int(pid_file.read_text())}").exists()
    finally:
        if pid_file.exists():
            try:
                os.kill(int(pid_file.read_text()), signal.SIGKILL)
            except ProcessLookupError:
                pass
    rows = [json.loads(line) for line in raw_path.read_bytes().splitlines()]
    assert rows[-1]["error_type"] == "CAPTURE_DEADLINE"
    summary = json.loads(result.stdout)
    assert read_capture(LocalFoundation(tmp_path / "store"), summary["capture_key"]) == raw_path.read_bytes()


def test_capture_interrupt_retains_raw_and_leaves_no_worker(tmp_path):
    ready = threading.Event()
    raw_path = tmp_path / "raw.jsonl"
    # Inspect the OS child relationship before the CLI exits; init reaping an
    # orphan after exit must not hide a missing wait in the capture parent.
    check_cleanup = (
        "import atexit, os, runpy\n"
        "def check():\n"
        "    try: os.waitpid(-1, os.WNOHANG)\n"
        "    except ChildProcessError: return\n"
        "    print('UNREAPED_WORKER')\n"
        "atexit.register(check)\n"
        "runpy.run_module('intraday_market_data', run_name='__main__')\n"
    )
    with endpoint(server_frame(PAYLOAD), ready=ready) as (port, seen):
        with subprocess.Popen([sys.executable, "-c", check_cleanup, "capture",
                               "--store", str(tmp_path / "store"), "--raw-path", str(raw_path),
                               "--port", str(port), "--seconds", "30"], cwd=ROOT,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                              start_new_session=True) as process:
            try:
                assert ready.wait(timeout=5)
                children = Path(f"/proc/{process.pid}/task/{process.pid}/children").read_text().split()
                assert len(children) == 1
                assert resource.prlimit(int(children[0]), resource.RLIMIT_AS) == (268435456, 268435456)
                assert resource.prlimit(int(children[0]), resource.RLIMIT_FSIZE) == (16777216, 16777216)
                process.send_signal(signal.SIGINT)
                stdout, stderr = process.communicate(timeout=5)
                assert process.returncode == 1, stdout + stderr
                assert "UNREAPED_WORKER" not in stdout
                assert all(not Path(f"/proc/{child}").exists() for child in children)
            finally:
                # Kill only this test-owned process group if an assertion/timeout fails.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=3)
    rows = [json.loads(line) for line in raw_path.read_bytes().splitlines()]
    assert rows[-1]["error_type"] == "CAPTURE_INTERRUPTED"
    summary = json.loads(stdout)
    assert summary["status"] == "degraded"
    assert read_capture(LocalFoundation(tmp_path / "store"), summary["capture_key"]) == raw_path.read_bytes()
    assert seen["closed"] and not seen["errors"]


@pytest.mark.parametrize("option,value", [
    ("--seconds", "0"), ("--seconds", "31"), ("--seconds", "nan"), ("--seconds", "inf"),
    ("--levels", "0"), ("--levels", "1001"), ("--port", "0"), ("--port", "65536"),
    ("--max-frames", "0"), ("--max-frames", "5001"),
    ("--max-bytes", "0"), ("--max-bytes", "8388609"),
    ("--symbol", "synthetic-secret"), ("--transport-python", "relative-python"),
])
def test_capture_invalid_arguments_do_not_create_raw_or_connect(tmp_path, option, value):
    raw_path = tmp_path / "raw.jsonl"
    store_path = tmp_path / "store"
    with endpoint() as (port, seen):
        result = cli("capture", "--store", store_path, "--raw-path", raw_path,
                     "--port", port, "--seconds", "0.1", option, value)
    assert result.returncode == 2 and json.loads(result.stdout)["status"] == "failed"
    assert not raw_path.exists() and seen["requests"] == 0
    assert LocalFoundation(store_path).entries("intraday.d202.captures.v1") == ()
    assert "synthetic-secret" not in result.stdout + result.stderr


@pytest.mark.parametrize("unsafe", ["existing", "symlink", "parent-symlink", "shared-parent", "traversal", "fifo"])
def test_capture_refuses_unsafe_raw_destination_without_modifying_existing_files(tmp_path, unsafe):
    parent = tmp_path / "raw-parent"
    parent.mkdir(mode=0o700)
    raw_path = parent / "raw.jsonl"
    target = tmp_path / "target"
    target.write_bytes(b"do-not-touch")
    target.chmod(0o640)
    if unsafe == "existing":
        raw_path = target
    elif unsafe == "symlink":
        raw_path.symlink_to(target)
    elif unsafe == "parent-symlink":
        alias = tmp_path / "alias"
        alias.symlink_to(parent, target_is_directory=True)
        raw_path = alias / "raw.jsonl"
    elif unsafe == "shared-parent":
        parent.chmod(0o755)
    elif unsafe == "traversal":
        raw_path = parent / ".." / "raw.jsonl"
    else:
        os.mkfifo(raw_path, 0o600)
    before = raw_path.lstat() if raw_path.exists() else None
    parent_mode = parent.stat().st_mode
    with endpoint() as (port, seen):
        result = cli("capture", "--store", tmp_path / "store", "--raw-path", raw_path,
                     "--port", port, "--seconds", "0.1")
    assert result.returncode == 2 and seen["requests"] == 0
    assert target.read_bytes() == b"do-not-touch" and stat.S_IMODE(target.stat().st_mode) == 0o640
    assert parent.stat().st_mode == parent_mode
    if before is None:
        assert not raw_path.exists()
    else:
        after = raw_path.lstat()
        assert (after.st_ino, after.st_mode, after.st_size, after.st_mtime_ns, after.st_ctime_ns) == (
            before.st_ino, before.st_mode, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
    assert LocalFoundation(tmp_path / "store").entries("intraday.d202.captures.v1") == ()


@pytest.mark.parametrize("failure,code", [
    ("absent", "TRANSPORT_START_FAILED"), ("no-site-packages", "TRANSPORT_RUNTIME_UNAVAILABLE"),
    ("nonzero", "TRANSPORT_PROCESS_FAILED"),
])
def test_capture_runtime_failures_are_private_retained_diagnostics(tmp_path, failure, code):
    runtime = tmp_path / "python"
    if failure != "absent":
        action = 'exec /usr/bin/python3 -S "$@"' if failure == "no-site-packages" else "exit 7"
        runtime.write_text("#!/bin/sh\necho synthetic-secret\necho synthetic-secret >&2\n" + action + "\n")
        runtime.chmod(0o700)
    raw_path = tmp_path / "raw.jsonl"
    with endpoint() as (port, seen):
        result = cli("capture", "--store", tmp_path / "store", "--raw-path", raw_path,
                     "--port", port, "--seconds", "0.1", "--transport-python", runtime)
    assert result.returncode == 1 and seen["requests"] == 0
    assert "synthetic-secret" not in result.stdout + result.stderr
    rows = [json.loads(line) for line in raw_path.read_bytes().splitlines()]
    assert rows[-1]["error_type"] == code
    assert stat.S_IMODE(raw_path.stat().st_mode) == 0o600
    summary = json.loads(result.stdout)
    assert summary["status"] == "degraded" and summary["qualified_market_data"] is False
    assert read_capture(LocalFoundation(tmp_path / "store"), summary["capture_key"]) == raw_path.read_bytes()


def test_capture_incomplete_oversized_message_stops_without_claiming_market_data(tmp_path):
    # Ten wire bytes advertise 1 GiB; never allocate or send a giant test payload.
    header = b"\x82\x7f" + struct.pack("!Q", 1 << 30)
    raw_path = tmp_path / "raw.jsonl"
    with endpoint(header) as (port, seen):
        result = cli("capture", "--store", tmp_path / "store", "--raw-path", raw_path,
                     "--port", port, "--seconds", "0.1")
    assert result.returncode == 1
    rows = [json.loads(line) for line in raw_path.read_bytes().splitlines()]
    assert not any(row["event"] == "frame" for row in rows)
    assert seen["closed"] and not seen["errors"]
    summary = json.loads(result.stdout)
    assert "NO_MARKET_DATA" in summary["quality_flags"]
    assert summary["status"] == "degraded" and summary["valid_market_observations"] == 0
    assert read_capture(LocalFoundation(tmp_path / "store"), summary["capture_key"]) == raw_path.read_bytes()
