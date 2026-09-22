"""Synthetic D202 fixtures; no licensed captures, credentials or network access."""
from __future__ import annotations

import base64
import errno
import json
import os
import stat
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from crypto_quant_foundation import FoundationFailure, LocalFoundation

import intraday_market_data as market_data

from intraday_market_data import CaptureError, archive_capture, read_capture, replay_capture

SYMBOL = "SH603790"
NOW_NS = 1789092000000000000  # Synthetic receipt: 2026-09-11 02:00:00 UTC.
NOW = datetime(2026, 9, 11, 2, tzinfo=timezone.utc)


def record(event="frame", *, wall_ns=NOW_NS, **fields):
    return {
        "event": event,
        "received_at": datetime.fromtimestamp(wall_ns / 1e9, timezone.utc).isoformat(),
        "received_wall_ns": wall_ns,
        "received_monotonic_ns": 1000000 + wall_ns - NOW_NS,
        **fields,
    }


def frame(*items, wall_ns=NOW_NS):
    wire = json.dumps({"ts": wall_ns // 1000000, "list": list(items)}).encode()
    return record(wall_ns=wall_ns, opcode=1, payload_base64=base64.b64encode(wire).decode())


def capture(*records):
    return b"".join(json.dumps(row, separators=(",", ":")).encode() + b"\n" for row in records)


def trade(seq=10, *, direction: int | str = 128, code=SYMBOL):
    return {"type": "trade", "data": {"code": code, "startSeq": seq, "rowCount": 1,
            "rows": [{"seq": seq, "t": 100000, "p": 2000, "v": 2, "d": direction,
                      "buyer": 101, "seller": 99, "buyVol": 2, "sellVol": 3}]}}


def order_book():
    return {"type": "thousand", "data": {"code": SYMBOL, "price": 2000,
            "totalBuyVol": 500, "totalSellVol": 600, "totalBuyAmt": 1000000,
            "totalSellAmt": 1200000, "buyCount": 12, "sellCount": 15, "l2Time": 123,
            "buys": [{"p": 1999, "v": 2}], "sells": [{"p": 2001, "v": 3}]}}


def store(path):
    return LocalFoundation(path, clock=lambda: "2026-09-11T03:00:00.000000Z")


def test_archive_survives_reopen_preserves_exact_bytes_and_is_idempotent(tmp_path):
    source = capture(frame(trade()))
    first = archive_capture(store(tmp_path), source, symbol=SYMBOL)
    assert read_capture(store(tmp_path), first) == source
    assert archive_capture(store(tmp_path), source, symbol=SYMBOL) == first
    assert len(store(tmp_path).entries("intraday.d202.captures.v1")) == 1
    assert store(tmp_path).entries("research.artifacts.v1") == ()


@pytest.mark.parametrize("wrapped", [False, True])
def test_replay_handles_all_items_and_flat_or_singleton_wrapped_tables(tmp_path, wrapped):
    book = order_book()
    order = {"type": "entrust", "data": {"code": SYMBOL, "startSeq": 90, "rowCount": 1,
             "rows": [{"seq": 90, "t": 95959, "p": 2000, "v": 2, "d": "B"}]}}
    fill = trade()
    if wrapped:
        book["data"]["buys"] = [book["data"]["buys"]]
        book["data"]["sells"] = [book["data"]["sells"]]
        order["data"]["rows"] = [order["data"]["rows"]]
        fill["data"]["rows"] = [fill["data"]["rows"]]
    source = capture(frame(book, order, fill, {"type": "info", "msg": "synthetic"}))
    key = archive_capture(store(tmp_path), source, symbol=SYMBOL)
    events = replay_capture(store(tmp_path), key, assessed_at=NOW)
    assert [event.kind for event in events] == ["thousand", "entrust", "trade", "info"]
    assert events[0].data is not None
    assert events[1].data is not None
    assert events[2].data is not None
    assert events[0].data["buys"] == [{"p": 1999, "v": 2}]
    assert events[0].data["totalBuyVol"] == 500  # Not replaced by returned-level sum.
    assert events[0].data["l2Time"] == 123  # Opaque, not a UTC timestamp.
    assert events[1].data["d"] == "B"
    assert events[2].data["d"] == 128
    assert events[2].data["seq"] == 10
    assert "DIRECTION_UNKNOWN" in events[2].flags
    assert all("PROVIDER_TIME_UNKNOWN" in event.flags for event in events[:3])
    assert events[2].received_at == "2026-09-11T02:00:00.000000Z"
    assert (events[2].record, events[2].item, events[2].row) == (1, 2, 0)
    assert read_capture(store(tmp_path), key) == source


def test_sequence_diagnostics_preserve_every_row_and_received_order(tmp_path):
    source = capture(*(frame(trade(seq)) for seq in (10, 10, 12, 11, 13)))
    key = archive_capture(store(tmp_path), source, symbol=SYMBOL)
    events = replay_capture(store(tmp_path), key, assessed_at=NOW)
    assert [e.data["seq"] for e in events if e.data is not None] == [10, 10, 12, 11, 13]
    assert "REPEATED_SEQ" in events[1].flags
    assert "SEQUENCE_GAP" in events[2].flags
    assert "SEQUENCE_REGRESSION" in events[3].flags
    assert "SEQUENCE_GAP" not in events[4].flags  # High-water, not last-arrival seq.
    assert read_capture(store(tmp_path), key) == source


@pytest.mark.parametrize("boundary", [
    record("server_close", code=1006, payload_base64=""),
    record("transport_error", error_type="SyntheticDisconnect"),
    record("subscription_sent", command=[{"type": "trade", "code": SYMBOL, "enable": 1}]),
])
def test_connection_boundaries_reset_local_seq_without_claiming_gap_repair(tmp_path, boundary):
    source = capture(frame(trade(10)), boundary, frame(trade(10)))
    key = archive_capture(store(tmp_path), source, symbol=SYMBOL)
    events = replay_capture(store(tmp_path), key, assessed_at=NOW)
    assert len([e for e in events if e.kind == "trade"]) == 2
    assert "REPEATED_SEQ" not in events[-1].flags
    assert "GAP_UNKNOWN" in events[-1].flags
    assert "COMPLETENESS_UNKNOWN" in events[-1].flags


def test_overlapping_captures_are_not_deduplicated_across_replays(tmp_path):
    first = capture(frame(trade(10)))
    second = capture(frame(trade(10), wall_ns=NOW_NS + 1))
    one = archive_capture(store(tmp_path), first, symbol=SYMBOL)
    two = archive_capture(store(tmp_path), second, symbol=SYMBOL)
    assert one != two
    for key in (one, two, one):
        events = replay_capture(store(tmp_path), key, assessed_at=NOW)
        assert len(events) == 1
        assert "REPEATED_SEQ" not in events[0].flags
    assert read_capture(store(tmp_path), one) == first
    assert read_capture(store(tmp_path), two) == second


@pytest.mark.parametrize("seconds,flag", [
    (31, "STALE_CAPTURE"), (-1, "RECEIVED_AFTER_ASSESSMENT"), (30, None),
])
def test_explicit_assessment_measures_receipt_age_without_rewriting_time(tmp_path, seconds, flag):
    source = capture(frame(trade()))
    key = archive_capture(store(tmp_path), source, symbol=SYMBOL)
    events = replay_capture(store(tmp_path), key, assessed_at=NOW + timedelta(seconds=seconds), max_age_seconds=30)
    assert events[0].received_at == "2026-09-11T02:00:00.000000Z"
    assert events[0].received_wall_ns == NOW_NS
    assert "PROVIDER_TIME_UNKNOWN" in events[0].flags
    if flag:
        assert flag in events[0].flags
    else:
        assert "STALE_CAPTURE" not in events[0].flags
    assert read_capture(store(tmp_path), key) == source


@pytest.mark.parametrize("limit", [-1, True, float("nan"), float("inf"), 1e300])
def test_age_limits_fail_closed(tmp_path, limit):
    key = archive_capture(store(tmp_path), capture(frame(trade())), symbol=SYMBOL)
    with pytest.raises(CaptureError, match="AGE_LIMIT"):
        replay_capture(store(tmp_path), key, assessed_at=NOW, max_age_seconds=limit)


def test_naive_assessment_is_rejected(tmp_path):
    key = archive_capture(store(tmp_path), capture(frame(trade())), symbol=SYMBOL)
    with pytest.raises(CaptureError, match="ASSESSMENT_TIME"):
        replay_capture(store(tmp_path), key, assessed_at=NOW.replace(tzinfo=None))


def test_receipt_clock_regression_is_visible_and_does_not_sort_records(tmp_path):
    key = archive_capture(store(tmp_path), capture(frame(trade(10)), frame(trade(11), wall_ns=NOW_NS - 1)), symbol=SYMBOL)
    events = replay_capture(store(tmp_path), key, assessed_at=NOW)
    assert [e.received_wall_ns for e in events] == [NOW_NS, NOW_NS - 1]
    assert "RECEIVE_CLOCK_REGRESSION" in events[1].flags
    assert "GAP_UNKNOWN" in events[1].flags


def test_fresh_info_does_not_refresh_old_market_data(tmp_path):
    source = capture(frame(trade()), frame({"type": "info", "msg": "synthetic"}, wall_ns=NOW_NS + 31000000000))
    key = archive_capture(store(tmp_path), source, symbol=SYMBOL)
    result = replay_capture(store(tmp_path), key, assessed_at=NOW + timedelta(seconds=31))
    assert "STALE_CAPTURE" in result[0].flags
    assert "STALE_CAPTURE" not in result[1].flags
    assert "PROVIDER_TIME_UNKNOWN" in result[0].flags


def test_inconsistent_receipt_clocks_are_not_freshness_proof(tmp_path):
    event = frame(trade())
    event["received_wall_ns"] += 2000000000
    key = archive_capture(store(tmp_path), capture(event), symbol=SYMBOL)
    result = replay_capture(store(tmp_path), key, assessed_at=NOW + timedelta(seconds=2))
    assert "RECEIVE_CLOCK_MISMATCH" in result[0].flags


@pytest.mark.parametrize("event,flag", [
    (record("server_close", code=1000, payload_base64=""), "DISCONNECT"),
    (record("transport_error", error_type="SyntheticIOError"), "TRANSPORT_ERROR"),
    (record("handshake_rejected", http_status=401), "PERMISSION_DENIED"),
    (record("handshake_rejected", http_status=403), "PERMISSION_DENIED"),
    (record("handshake_rejected", http_status=503), "HANDSHAKE_REJECTED"),
    (frame({"type": "error", "msg": "synthetic-secret permission expired"}), "PROVIDER_ERROR"),
    (record("control_frame", opcode=0, payload_bytes=1), "UNSUPPORTED_CONTROL"),
    (record("control_frame", opcode=9, payload_bytes=True), "MALFORMED_DATA"),
])
def test_transport_and_permission_failures_are_not_normal_data(tmp_path, event, flag):
    key = archive_capture(store(tmp_path), capture(event), symbol=SYMBOL)
    result = replay_capture(store(tmp_path), key, assessed_at=NOW)
    assert flag in result[0].flags
    assert all(e.data is None for e in result)
    assert "synthetic-secret" not in repr(result)


@pytest.mark.parametrize("field,value", [
    ("seq", True), ("seq", -1), ("seq", "10"), ("p", -1), ("p", 2.5),
    ("v", False), ("v", "2"), ("t", 236060), ("buyer", -1), ("d", None),
])
def test_invalid_financial_fields_remain_raw_and_do_not_poison_sequence_state(tmp_path, field, value):
    bad = trade(900)
    bad["data"]["rows"][0][field] = value
    source = capture(frame(trade(10), bad, trade(11)))
    key = archive_capture(store(tmp_path), source, symbol=SYMBOL)
    result = replay_capture(store(tmp_path), key, assessed_at=NOW)
    assert len(result) == 3
    assert "MALFORMED_DATA" in result[1].flags
    assert result[1].data is not None and result[1].data[field] == value
    assert "SEQUENCE_REGRESSION" not in result[2].flags
    assert read_capture(store(tmp_path), key) == source


def test_invalid_row_does_not_hide_valid_siblings_and_count_mismatch_is_visible(tmp_path):
    item = trade()
    item["data"]["rows"] = [item["data"]["rows"][0], "synthetic-invalid-row", trade(11)["data"]["rows"][0]]
    key = archive_capture(store(tmp_path), capture(frame(item)), symbol=SYMBOL)
    result = replay_capture(store(tmp_path), key, assessed_at=NOW)
    assert [e.row for e in result] == [0, 1, 2]
    assert [e.data["seq"] for e in result if e.data is not None] == [10, 11]
    assert "MALFORMED_DATA" in result[1].flags
    assert all("ROW_COUNT_MISMATCH" in e.flags for e in result)


@pytest.mark.parametrize("rows", [[[[{"seq": 10}]]], [[{"seq": 10}], {"seq": 11}]])
def test_deeper_or_mixed_wrappers_fail_without_losing_other_items(tmp_path, rows):
    bad = trade()
    bad["data"]["rows"] = rows
    key = archive_capture(store(tmp_path), capture(frame(bad, trade())), symbol=SYMBOL)
    result = replay_capture(store(tmp_path), key, assessed_at=NOW)
    assert "MALFORMED_PAYLOAD" in result[0].flags
    assert result[1].kind == "trade"


@pytest.mark.parametrize("payload", [b"{", b"\xff", b'{"ts":1,"list":[],"list":[]}', b'{"ts":1e10000,"list":[]}'])
def test_bad_inner_json_is_retained_and_diagnosed_without_hiding_next_frame(tmp_path, payload):
    source = capture(record(opcode=1, payload_base64=base64.b64encode(payload).decode()), frame(trade()))
    key = archive_capture(store(tmp_path), source, symbol=SYMBOL)
    result = replay_capture(store(tmp_path), key, assessed_at=NOW + timedelta(seconds=31))
    assert {"MALFORMED_PAYLOAD", "STALE_CAPTURE"} <= set(result[0].flags)
    assert result[-1].kind == "trade"
    assert read_capture(store(tmp_path), key) == source


@pytest.mark.parametrize("event", [frame(), frame({"type": "info", "msg": "synthetic"}),
                                      record("control_frame", opcode=9, payload_bytes=0)])
def test_no_market_data_never_looks_like_a_successful_quote(tmp_path, event):
    key = archive_capture(store(tmp_path), capture(event), symbol=SYMBOL)
    result = replay_capture(store(tmp_path), key, assessed_at=NOW)
    assert result and all("NO_MARKET_DATA" in e.flags for e in result)


@pytest.mark.parametrize("tail", [b"{\n", b'{}\n', b'{"password":"synthetic-secret"}\n'])
def test_late_invalid_capture_record_leaves_store_untouched(tmp_path, tail):
    foundation = store(tmp_path / "store")
    with pytest.raises(CaptureError, match="CAPTURE_FORMAT"):
        archive_capture(foundation, capture(frame(trade())) + tail, symbol=SYMBOL)
    assert not (tmp_path / "store").exists()


def test_capture_size_record_and_projection_limits_fail_closed(tmp_path, monkeypatch):
    source = capture(frame(trade()), frame(trade(11)))
    with monkeypatch.context() as patch:
        patch.setattr(market_data, "MAX_CAPTURE_BYTES", len(source) - 1)
        with pytest.raises(CaptureError, match="CAPTURE_SIZE"):
            archive_capture(store(tmp_path), source, symbol=SYMBOL)
    with monkeypatch.context() as patch:
        patch.setattr(market_data, "MAX_RECORDS", 1)
        with pytest.raises(CaptureError, match="CAPTURE_RECORD_LIMIT"):
            archive_capture(store(tmp_path), source, symbol=SYMBOL)
    assert store(tmp_path).entries(market_data.LOG_NAME) == ()
    key = archive_capture(store(tmp_path), source, symbol=SYMBOL)
    monkeypatch.setattr(market_data, "MAX_OBSERVATIONS", 1)
    with pytest.raises(CaptureError, match="REPLAY_LIMIT"):
        replay_capture(store(tmp_path), key, assessed_at=NOW)
    assert read_capture(store(tmp_path), key) == source


@pytest.mark.parametrize("error_number", [errno.ENOSPC, errno.EACCES])
def test_failed_atomic_publication_keeps_previous_capture_and_can_retry(tmp_path, monkeypatch, error_number):
    original = capture(frame(trade()))
    next_source = capture(frame(trade(11)))
    first = archive_capture(store(tmp_path), original, symbol=SYMBOL)
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}

    def fail_replace(*_args, **_kwargs):
        raise OSError(error_number, "synthetic-storage-failure")

    with monkeypatch.context() as patch:
        patch.setattr(os, "replace", fail_replace)
        with pytest.raises(FoundationFailure) as failure:
            archive_capture(store(tmp_path), next_source, symbol=SYMBOL)
    assert failure.value.code == "LOG_PUBLICATION_FAILED"
    after = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after
    assert read_capture(store(tmp_path), first) == original
    second = archive_capture(store(tmp_path), next_source, symbol=SYMBOL)
    assert read_capture(store(tmp_path), second) == next_source
    assert len(store(tmp_path).entries(market_data.LOG_NAME)) == 2


def test_capture_key_hash_is_checked_even_with_valid_foundation_log(tmp_path):
    wrong_key = SYMBOL + ":" + "0" * 64
    store(tmp_path).append(market_data.LOG_NAME, wrong_key, capture(frame(trade())))
    with pytest.raises(CaptureError, match="CAPTURE_INTEGRITY"):
        read_capture(store(tmp_path), wrong_key)


def cli(*args):
    return subprocess.run([sys.executable, "-m", "intraday_market_data", *map(str, args)],
                          cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, timeout=10)


def cli_source(tmp_path, source):
    path = tmp_path / "synthetic-capture.jsonl"
    path.write_bytes(source)
    path.chmod(0o600)
    return path


def test_cli_archive_reopen_replay_is_private_and_never_qualified(tmp_path):
    source = capture(frame(trade(), {"type": "info", "msg": "synthetic-secret"}))
    source_path = cli_source(tmp_path, source)
    root = tmp_path / "private-store"
    archived = cli("archive", "--store", root, "--source", source_path, "--symbol", SYMBOL)
    assert archived.returncode == 0 and archived.stdout
    key = json.loads(archived.stdout)["capture_key"]
    replayed = cli("replay", "--store", root, "--capture-key", key, "--assessed-at", NOW.isoformat())
    assert replayed.returncode == 0
    summary = json.loads(replayed.stdout)
    assert summary["status"] == "limited"
    assert summary["supplier_contract_verified"] is False
    assert summary["qualified_market_data"] is False
    assert summary["valid_market_observations"] == 1
    assert "DIRECTION_UNKNOWN" in summary["quality_flags"]
    assert "synthetic-secret" not in archived.stdout + archived.stderr + replayed.stdout + replayed.stderr
    assert read_capture(store(root), key) == source
    repeated = cli("archive", "--store", root, "--source", source_path, "--symbol", SYMBOL)
    assert repeated.returncode == 0 and json.loads(repeated.stdout)["capture_key"] == key
    assert len(store(root).entries(market_data.LOG_NAME)) == 1
    for path in (root, *root.rglob("*")):
        assert stat.S_IMODE(path.stat().st_mode) == (0o700 if path.is_dir() else 0o600)


@pytest.mark.parametrize("event,seconds,flag", [
    (frame(trade()), 31, "STALE_CAPTURE"),
    (frame({"type": "error", "msg": "synthetic-secret"}), 0, "PROVIDER_ERROR"),
    (frame(), 0, "NO_MARKET_DATA"),
])
def test_cli_quality_faults_exit_nonzero_without_payloads(tmp_path, event, seconds, flag):
    source = cli_source(tmp_path, capture(event))
    root = tmp_path / "private-store"
    archived = cli("archive", "--store", root, "--source", source, "--symbol", SYMBOL)
    key = json.loads(archived.stdout)["capture_key"]
    replayed = cli("replay", "--store", root, "--capture-key", key,
                   "--assessed-at", (NOW + timedelta(seconds=seconds)).isoformat())
    assert replayed.returncode == 1
    assert json.loads(replayed.stdout)["status"] == "degraded"
    assert flag in json.loads(replayed.stdout)["quality_flags"]
    assert "synthetic-secret" not in replayed.stdout + replayed.stderr


@pytest.mark.parametrize("unsafe", ["shared", "unmarked", "symlink", "parent-symlink"])
def test_cli_refuses_unsafe_store_without_relaxing_permissions(tmp_path, unsafe):
    source = cli_source(tmp_path, capture(frame(trade())))
    target = tmp_path / "target"
    target.mkdir(mode=0o755 if unsafe == "shared" else 0o700)
    root = target
    if unsafe in ("symlink", "parent-symlink"):
        root = tmp_path / "alias"
        root.symlink_to(target, target_is_directory=True)
        if unsafe == "parent-symlink":
            root = root / "child"
    before = target.stat().st_mode
    result = cli("archive", "--store", root, "--source", source, "--symbol", SYMBOL)
    assert result.returncode == 2
    assert target.stat().st_mode == before
    assert not list(target.iterdir())


def test_cli_invalid_source_and_arguments_do_not_publish_or_echo_input(tmp_path):
    source = cli_source(tmp_path, b'{"password":"synthetic-secret"}\n')
    root = tmp_path / "private-store"
    result = cli("archive", "--store", root, "--source", source, "--symbol", SYMBOL)
    assert result.returncode == 2
    assert json.loads(result.stdout)["code"] == "CAPTURE_FORMAT"
    assert not root.exists()
    result = cli("replay", "--store", root, "--capture-key", "synthetic-secret",
                 "--assessed-at", NOW.isoformat(), "--max-age-seconds", "synthetic-secret")
    assert result.returncode == 2
    assert "synthetic-secret" not in result.stdout + result.stderr


@pytest.mark.parametrize("field,value", [("price", True), ("totalBuyVol", -1), ("buyCount", "12"),
                                         ("l2Time", None), ("buys", [{"p": 2000, "v": -1}])])
def test_bad_books_remain_diagnostic_not_valid_quotes(tmp_path, field, value):
    item = order_book()
    item["data"][field] = value
    source = capture(frame(item))
    key = archive_capture(store(tmp_path), source, symbol=SYMBOL)
    result = replay_capture(store(tmp_path), key, assessed_at=NOW)
    assert {"MALFORMED_DATA", "NO_MARKET_DATA"} <= set(result[0].flags)
    assert result[0].data is not None and result[0].data[field] == value
    assert read_capture(store(tmp_path), key) == source


def test_symbol_mismatch_and_flow_names_do_not_share_sequence_state(tmp_path):
    order = trade(10, direction="B")
    order["type"] = "entrust"
    source = capture(frame(trade(10), order, trade(999, code="SZ000001"), trade(11)))
    key = archive_capture(store(tmp_path), source, symbol=SYMBOL)
    result = replay_capture(store(tmp_path), key, assessed_at=NOW)
    assert "REPEATED_SEQ" not in result[1].flags
    assert "SYMBOL_MISMATCH" in result[2].flags
    assert not {"SEQUENCE_GAP", "SEQUENCE_REGRESSION"}.intersection(result[3].flags)


@pytest.mark.parametrize("change", [
    {"received_wall_ns": True}, {"received_monotonic_ns": -1},
    {"received_at": "2026-09-11T02:00:00"}, {"received_at": "0001-01-01T00:00:00+14:00"},
    {"payload_base64": "%%%"}, {"event": "unknown"}, {"credential": "synthetic-secret"},
])
def test_invalid_outer_metadata_never_reaches_publication(tmp_path, change):
    foundation = store(tmp_path / "store")
    with pytest.raises(CaptureError, match="CAPTURE_FORMAT"):
        archive_capture(foundation, capture({**frame(trade()), **change}), symbol=SYMBOL)
    assert not (tmp_path / "store").exists()


def test_table_limit_and_foundation_tampering_fail_closed(tmp_path, monkeypatch):
    item = trade()
    item["data"]["rows"] *= 2
    source = capture(frame(item))
    key = archive_capture(store(tmp_path), source, symbol=SYMBOL)
    with monkeypatch.context() as patch:
        patch.setattr(market_data, "MAX_TABLE_ROWS", 1)
        with pytest.raises(CaptureError, match="REPLAY_LIMIT"):
            replay_capture(store(tmp_path), key, assessed_at=NOW)
    assert read_capture(store(tmp_path), key) == source
    next(tmp_path.rglob("*.jsonl")).write_bytes(b'{"synthetic_tamper":true}\n')
    with pytest.raises(FoundationFailure):
        read_capture(store(tmp_path), key)


@pytest.mark.parametrize("unsafe", ["symlink", "shared", "fifo"])
def test_cli_source_must_be_private_regular_and_not_a_symlink(tmp_path, unsafe):
    source = cli_source(tmp_path, capture(frame(trade())))
    if unsafe == "symlink":
        alias = tmp_path / "alias.jsonl"
        alias.symlink_to(source)
        source = alias
    elif unsafe == "shared":
        source.chmod(0o644)
    else:
        source = tmp_path / "fifo.jsonl"
        os.mkfifo(source, 0o600)
    root = tmp_path / "private-store"
    result = cli("archive", "--store", root, "--source", source, "--symbol", SYMBOL)
    assert result.returncode == 2
    assert not root.exists()
