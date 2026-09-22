"""Private transport worker for intraday_market_data, not a standalone data publisher.

Uses an already-installed websocket-client in the selected interpreter. Raw output
is restricted to an inherited private regular-file descriptor; stdout/stderr are
never the capture channel. The Platform parent owns the hard wall-clock deadline.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import stat
import time
from datetime import datetime, timezone

MAX_PAYLOAD_BYTES = 8 * 1024 * 1024
MAX_FRAMES = 5000
MAX_RAW_BYTES = 15 * 1024 * 1024  # Reserve room under Platform's 16 MiB archive cap.


def capture_record(event: str, **fields) -> bytes:
    wall = time.time_ns()
    return (json.dumps({
        "event": event,
        "received_at": datetime.fromtimestamp(wall / 1e9, timezone.utc).isoformat(),
        "received_wall_ns": wall,
        "received_monotonic_ns": time.monotonic_ns(),
        **fields,
    }, separators=(",", ":")) + "\n").encode()


def _run(args, raw) -> None:
    def record(event, **fields):
        line = capture_record(event, **fields)
        if raw.tell() + len(line) > MAX_RAW_BYTES:
            raise BufferError
        raw.write(line)
        raw.flush()

    try:
        import websocket
    except ImportError:
        record("transport_error", error_type="TRANSPORT_RUNTIME_UNAVAILABLE")
        return
    commands = [
        {"type": "thousand", "code": args.symbol, "enable": 1, "levels": args.levels},
        {"type": "entrust", "code": args.symbol, "enable": 1, "count": 50, "filter": 0},
        {"type": "trade", "code": args.symbol, "enable": 1, "count": 50},
    ]
    ws = None
    try:
        ws = websocket.create_connection(
            f"ws://127.0.0.1:{args.port}/d202", timeout=5,
            http_no_proxy=["127.0.0.1", "localhost"],
            enable_multithread=False, skip_utf8_validation=True,
        )
        ws.send(json.dumps(commands, separators=(",", ":")))
        record("subscription_sent", command=commands)
        deadline = time.monotonic() + args.seconds
        frames = payload_bytes = 0
        while time.monotonic() < deadline:
            if frames >= args.max_frames:
                raise BufferError
            ws.settimeout(min(0.5, max(0.001, deadline - time.monotonic())))
            try:
                opcode, payload = ws.recv_data(control_frame=True)
            except websocket.WebSocketTimeoutException:
                continue
            frames += 1
            data = payload.encode("utf-8") if isinstance(payload, str) else payload
            if opcode == websocket.ABNF.OPCODE_CLOSE:
                record("server_close", code=int.from_bytes(data[:2], "big") if len(data) >= 2 else None,
                       payload_base64=base64.b64encode(data).decode("ascii"))
                break
            if opcode not in (websocket.ABNF.OPCODE_TEXT, websocket.ABNF.OPCODE_BINARY):
                record("control_frame", opcode=opcode, payload_bytes=len(data))
                continue
            if payload_bytes + len(data) > args.max_bytes:
                raise BufferError
            payload_bytes += len(data)
            record("frame", opcode=opcode, payload_base64=base64.b64encode(data).decode("ascii"))
    except websocket.WebSocketBadStatusException as error:
        record("handshake_rejected", http_status=error.status_code)
    except (BufferError, MemoryError):
        record("transport_error", error_type="CAPTURE_RESOURCE_LIMIT")
    except (OSError, websocket.WebSocketException):
        record("transport_error", error_type="TRANSPORT_FAILURE")
    finally:
        if ws is not None:
            try:
                if ws.connected:
                    ws.settimeout(1)
                    ws.send(json.dumps([{"type": command["type"], "code": args.symbol, "enable": 0}
                                        for command in commands]))
                    record("unsubscribe_sent")
            except (OSError, websocket.WebSocketException):
                record("transport_error", error_type="UNSUBSCRIBE_FAILED")
            finally:
                ws.close(timeout=1)


def main() -> None:
    import resource  # Linux-only worker; importing the archive module needs no resource module.

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-fd", type=int, required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--seconds", type=float, required=True)
    parser.add_argument("--levels", type=int, required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--max-frames", type=int, required=True)
    parser.add_argument("--max-bytes", type=int, required=True)
    args = parser.parse_args()
    info = os.fstat(args.output_fd)
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600):
        raise ValueError("PRIVATE_OUTPUT_REQUIRED")
    # Bound message assembly in the library, including hostile oversized/fragmented frames.
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1024 * 1024, 16 * 1024 * 1024))
    with os.fdopen(args.output_fd, "wb", buffering=0) as raw:
        _run(args, raw)


if __name__ == "__main__":
    main()
