import csv
import hashlib
import json
import subprocess
from dataclasses import asdict
from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest

from experiments import update_a_share_market_regime as update
from experiments.a_share_market_regime import CHINA_TZ, DEFAULT_CONFIG, INDEX_CODES

NOW = datetime(2026, 9, 22, 16, tzinfo=CHINA_TZ)


def previous_report(path, *, phase="bear", day="2026-09-22", as_of=None):
    payload = {
        "strategy": "a_share_market_snapshot_v1", "authority": "diagnostic_only",
        "trade_authorized": False, "historical_confirmation_claimed": False,
        "config": asdict(DEFAULT_CONFIG),
        "sources": {key: {"path": "/must-not-read-previous-sources", "sha256": letter * 64}
                    for key, letter in (("prices", "a"), ("calendar", "b"))},
        "result": {"basis": "snapshot", "phase": phase, "decision_date": day,
                   "as_of": as_of or (NOW - timedelta(minutes=1)).isoformat()},
    }
    path.write_text(json.dumps(payload))
    return payload


@pytest.fixture
def source(monkeypatch):
    """Synthetic business-day prices exercise the real diagnostic CLI, not exchange history."""
    state = {"calls": [], "now": NOW, "slope": 1, "failure": None, "tamper": False, "after_capture": None}
    monkeypatch.setattr(update, "_now", lambda: state["now"])

    def capture(*, start, output, source):
        state["calls"].append((start, output, source))
        output.mkdir(parents=True, exist_ok=False)
        if state["failure"]:
            (output / "receipt.json").write_text('{"status":"failed"}')
            raise OSError("synthetic source unavailable")
        completed = state["now"] + timedelta(seconds=1)
        days = [start + timedelta(days=i) for i in range((completed.date() - start).days + 1)]
        with (output / "calendar.csv").open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(("cal_date", "is_open"))
            writer.writerows((day.isoformat(), int(day.weekday() < 5)) for day in days)
        sessions = [day for day in days if day.weekday() < 5]
        with (output / "prices.csv").open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(("ts_code", "trade_date", "close", "available_at"))
            for code in INDEX_CODES:
                writer.writerows((code, day.isoformat(), 1000 + state["slope"] * i, completed.isoformat())
                                 for i, day in enumerate(sessions))
        receipt = {"status": "captured", "price_source": source, "completed_at": completed.isoformat(),
                   "normalized_sha256": {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                                         for name in ("prices.csv", "calendar.csv")}}
        (output / "receipt.json").write_text(json.dumps(receipt))
        if state["tamper"]:
            with (output / "prices.csv").open("a") as stream:
                stream.write("\n")  # Valid CSV, but not the bytes bound by capture.
        if state["after_capture"] is not None:
            state["after_capture"](output)
        return receipt

    monkeypatch.setattr(update, "capture_snapshot", capture)
    return state


def test_cli_update_smoke_and_exact_replay(tmp_path, source, capsys):
    output = tmp_path / "new output"
    assert update.main(["--start", "2025-11-01", "--source", "sse", "--output", str(output)]) == 0
    console = json.loads(capsys.readouterr().out)
    receipt = json.loads((output / "update.json").read_text())
    assert console == receipt and receipt["status"] == "completed"
    assert receipt["price_source"] == "sse" and len(source["calls"]) == 1
    assert receipt["diagnostic"]["phase"] == "bull"
    assert receipt["comparison"]["kind"] == "no_previous"
    assert receipt["comparison"]["phase_changed"] is None
    assert receipt["diagnostic"]["as_of"] == (NOW + timedelta(seconds=1)).isoformat()
    raw = (output / "regime.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == receipt["diagnostic"]["sha256"]
    replay = subprocess.run(receipt["diagnostic"]["replay_argv"], cwd=update.ROOT,
                            capture_output=True, timeout=10, check=False)
    assert replay.returncode == 0 and replay.stdout == raw and replay.stderr == b""
    assert not receipt["trade_authorized"] and not receipt["comparison"]["market_transition_claimed"]


def test_same_session_reassessment_is_not_a_market_transition(tmp_path, source):
    previous = tmp_path / "old.json"
    previous_report(previous)
    old_bytes = previous.read_bytes()
    receipt = update.update_market_regime(start=date(2025, 11, 1), output=tmp_path / "new", source="sse", previous=previous)
    comparison = receipt["comparison"]
    assert receipt["status"] == "completed" and receipt["exit_code"] == 0
    assert comparison["kind"] == "same_session_reassessment" and comparison["phase_changed"] is True
    assert not comparison["market_transition_claimed"]
    assert previous.read_bytes() == (tmp_path / "new/previous.json").read_bytes() == old_bytes
    assert receipt["previous_report"]["sha256"] == hashlib.sha256(old_bytes).hexdigest()


@pytest.mark.parametrize(("phase", "changed"), [("bear", True), ("bull", False)])
def test_later_session_compares_reports_without_claiming_continuity(tmp_path, source, phase, changed):
    previous = tmp_path / "old.json"
    previous_report(previous, phase=phase, day="2026-09-18", as_of="2026-09-18T16:00:00+08:00")
    receipt = update.update_market_regime(start=date(2025, 11, 1), output=tmp_path / "new", source="csi", previous=previous)
    assert receipt["comparison"]["kind"] == "later_session_comparison"
    assert receipt["comparison"]["phase_changed"] is changed
    assert not receipt["comparison"]["market_transition_claimed"]
    assert source["calls"][0][2] == "csi"


@pytest.mark.parametrize("unknown_side", ["current", "previous"])
def test_unknown_never_reuses_previous_phase_or_claims_no_change(tmp_path, source, unknown_side):
    previous = tmp_path / "old.json"
    previous_report(previous, phase="unknown" if unknown_side == "previous" else "bear")
    start = date(2026, 9, 20) if unknown_side == "current" else date(2025, 11, 1)
    receipt = update.update_market_regime(start=start, output=tmp_path / "new", source="sse", previous=previous)
    assert receipt["exit_code"] == 1 and receipt["status"] == "inconclusive"
    assert receipt["comparison"]["kind"] == "not_comparable"
    assert receipt["comparison"]["phase_changed"] is None
    assert receipt["diagnostic"]["phase"] == ("unknown" if unknown_side == "current" else "bull")
    assert len(source["calls"]) == 1


def test_capture_failure_is_retained_without_current_diagnosis(tmp_path, source, capsys):
    source["failure"] = True
    previous = tmp_path / "old.json"
    previous_report(previous)
    output = tmp_path / "failed"
    assert update.main(["--start", "2025-11-01", "--source", "sse", "--output", str(output), "--previous", str(previous)]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report == json.loads((output / "update.json").read_text())
    assert report["status"] == "failed" and report["error"]["stage"] == "capture"
    assert report["diagnostic"] is None and report["comparison"] is None
    assert json.loads((output / "inputs/receipt.json").read_text())["status"] == "failed"
    assert not (output / "regime.json").exists() and len(source["calls"]) == 1


def test_existing_output_is_not_overwritten_or_recaptured(tmp_path, source, capsys):
    output = tmp_path / "once"
    update.update_market_regime(start=date(2025, 11, 1), output=output, source="sse")
    before = {p: p.read_bytes() for p in output.rglob("*") if p.is_file()}
    with pytest.raises(SystemExit) as error:
        update.main(["--start", "2025-11-01", "--source", "sse", "--output", str(output)])
    assert error.value.code == 2 and len(source["calls"]) == 1
    assert "new directory" in capsys.readouterr().err
    assert all(path.read_bytes() == raw for path, raw in before.items())


@pytest.mark.parametrize("problem", ["historical", "trading", "flag_int", "config", "float_config", "naive", "future",
    "future_session", "missing_session", "phase", "basis", "hash", "duplicate", "nan", "not_object", "oversized", "screening"])
def test_bad_previous_fails_before_capture_and_output(tmp_path, source, problem):
    previous = tmp_path / "previous.json"
    data = previous_report(previous)
    if problem == "historical":
        data["strategy"] = "a_share_market_regime_v1"
    elif problem == "trading":
        data["trade_authorized"] = True
    elif problem == "flag_int":
        data["historical_confirmation_claimed"] = 0
    elif problem == "config":
        data["config"]["ma_window"] = 201
    elif problem == "float_config":
        data["config"]["ma_window"] = 200.0
    elif problem == "naive":
        data["result"]["as_of"] = "2026-09-22T15:30:00"
    elif problem == "future":
        data["result"]["as_of"] = (NOW + timedelta(hours=1)).isoformat()
    elif problem == "future_session":
        data["result"]["decision_date"] = "2026-09-23"
    elif problem == "missing_session":
        data["result"]["decision_date"] = None
    elif problem == "phase":
        data["result"]["phase"] = "buy"
    elif problem == "basis":
        data["result"]["basis"] = "historical"
    elif problem == "hash":
        data["sources"]["prices"]["sha256"] = "not-a-hash"
    elif problem == "screening":
        data["screening"] = {}
    raw = json.dumps(data)
    if problem == "duplicate":
        raw = '{"strategy":"forged",' + raw[1:]
    elif problem == "nan":
        raw = '{"extra":NaN,' + raw[1:]
    elif problem == "not_object":
        raw = "[]"
    elif problem == "oversized":
        raw = " " * (update.MAX_REPORT_BYTES + 1)
    previous.write_text(raw)
    with pytest.raises(ValueError):
        update.update_market_regime(start=date(2025, 11, 1), output=tmp_path / "unused", source="sse", previous=previous)
    assert source["calls"] == [] and not (tmp_path / "unused").exists()


def test_previous_bytes_are_frozen_before_capture(tmp_path, source):
    previous = tmp_path / "old.json"
    previous_report(previous)
    original = previous.read_bytes()
    source["after_capture"] = lambda _: previous.write_text("changed externally")
    receipt = update.update_market_regime(start=date(2025, 11, 1), output=tmp_path / "new", source="sse", previous=previous)
    assert receipt["status"] == "completed"
    assert (tmp_path / "new/previous.json").read_bytes() == original
    assert receipt["comparison"]["previous"]["phase"] == "bear"


def test_changed_csv_hash_prevents_publishing_diagnosis(tmp_path, source):
    source["tamper"] = True
    output = tmp_path / "tampered"
    receipt = update.update_market_regime(start=date(2025, 11, 1), output=output, source="sse")
    assert receipt["status"] == "failed" and receipt["exit_code"] == 2
    assert receipt["error"]["stage"] == "verify_diagnostic"
    assert not (output / "regime.json").exists()


def test_diagnostic_failure_retains_stderr(tmp_path, source):
    source["after_capture"] = lambda output: (output / "prices.csv").unlink()
    output = tmp_path / "bad"
    receipt = update.update_market_regime(start=date(2025, 11, 1), output=output, source="sse")
    assert receipt["status"] == "failed" and receipt["error"]["stage"] == "diagnostic"
    assert (output / "diagnostic.stderr.txt").read_bytes()
    assert not (output / "regime.json").exists()


@pytest.mark.parametrize("failure", ["timeout", "bad_json"])
def test_diagnostic_transport_or_json_failure_is_not_success(tmp_path, source, monkeypatch, failure):
    def failed(argv, **kwargs):
        assert kwargs["timeout"] == 30 and kwargs.get("shell", False) is False
        if failure == "timeout":
            raise subprocess.TimeoutExpired(argv, 30)
        return SimpleNamespace(returncode=0, stdout=b"not json", stderr=b"")
    monkeypatch.setattr(update.subprocess, "run", failed)
    output = tmp_path / "failed"
    receipt = update.update_market_regime(start=date(2025, 11, 1), output=output, source="sse")
    assert receipt["status"] == "failed" and receipt["exit_code"] == 2
    assert not (output / "regime.json").exists() and len(source["calls"]) == 1


def test_cli_requires_explicit_source_and_rejects_missing_previous(tmp_path, source, capsys):
    for args in (["--start", "2025-11-01", "--output", str(tmp_path / "unused")],
                 ["--start", "2025-11-01", "--source", "sse", "--output", str(tmp_path / "unused"),
                  "--previous", str(tmp_path / "absent.json")]):
        with pytest.raises(SystemExit) as error:
            update.main(args)
        assert error.value.code == 2
    assert source["calls"] == [] and not (tmp_path / "unused").exists()
    assert capsys.readouterr().out == ""
