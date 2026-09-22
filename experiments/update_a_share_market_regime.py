"""One-shot capture + frozen snapshot diagnosis; never a scheduler or trading signal."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import asdict
from datetime import date, datetime, time
from pathlib import Path

from experiments.a_share_market_regime import CHINA_TZ, DEFAULT_CONFIG, MarketPhase
from experiments.capture_a_share_market_regime import capture_snapshot

ROOT = Path(__file__).resolve().parents[1]
MAX_REPORT_BYTES = 1_000_000


def _now() -> datetime:
    return datetime.now(CHINA_TZ)


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate report JSON key")
        result[key] = value
    return result


def _bad_number(value):
    raise ValueError(f"non-finite report JSON number: {value}")


def _decode(raw: bytes) -> dict:
    if not raw or len(raw) > MAX_REPORT_BYTES:
        raise ValueError("snapshot report is empty or exceeds byte limit")
    try:
        payload = json.loads(raw, object_pairs_hook=_unique_keys, parse_constant=_bad_number)
    except (ValueError, UnicodeError) as error:
        raise ValueError("invalid snapshot report JSON") from error
    if type(payload) is not dict:
        raise ValueError("snapshot report must be an object")
    return payload


def _summary(payload: dict) -> dict:
    if payload.get("strategy") != "a_share_market_snapshot_v1" or payload.get("authority") != "diagnostic_only" or "screening" in payload:
        raise ValueError("expected an index-only current snapshot report, not historical or update JSON")
    for field in ("trade_authorized", "historical_confirmation_claimed"):
        if type(payload.get(field)) is not bool or payload[field]:
            raise ValueError("snapshot report must not claim trading or historical confirmation")
    config = payload.get("config")
    if type(config) is not dict or config != asdict(DEFAULT_CONFIG) or any(type(value) is not int for value in config.values()):
        raise ValueError("snapshot report must use the same fixed v1 parameters")
    result, sources = payload.get("result"), payload.get("sources")
    if type(result) is not dict or result.get("basis") != "snapshot" or type(sources) is not dict:
        raise ValueError("snapshot result, basis and source fingerprints are required")
    for key in ("prices", "calendar"):
        ref = sources.get(key)
        if type(ref) is not dict or type(ref.get("sha256")) is not str or re.fullmatch(r"[a-f0-9]{64}", ref["sha256"]) is None:
            raise ValueError("snapshot source SHA-256 is required; source paths are not followed")
    phase, stamp, target = result.get("phase"), result.get("as_of"), result.get("decision_date")
    if type(phase) is not str or phase not in {item.value for item in MarketPhase} or type(stamp) is not str:
        raise ValueError("invalid snapshot phase or as_of")
    as_of = datetime.fromisoformat(stamp)
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("snapshot as_of must include a timezone")
    as_of = as_of.astimezone(CHINA_TZ)
    if target is not None:
        if type(target) is not str:
            raise ValueError("invalid snapshot decision_date")
        day = date.fromisoformat(target)
        if datetime.combine(day, time(15), CHINA_TZ) > as_of:
            raise ValueError("snapshot decision_date is not a completed session at as_of")
        target = day.isoformat()
    elif phase != "unknown":
        raise ValueError("a known snapshot phase requires a decision_date")
    return {"as_of": as_of.isoformat(), "decision_date": target, "phase": phase}


def _compare(previous: dict | None, current: dict) -> dict:
    result = {"kind": "no_previous", "phase_changed": None, "previous": previous,
              "current": current, "market_transition_claimed": False}
    if previous is None:
        return result
    if datetime.fromisoformat(previous["as_of"]) > datetime.fromisoformat(current["as_of"]):
        result.update(kind="not_comparable", reason="previous_as_of_after_current")
    elif "unknown" in (previous["phase"], current["phase"]):
        result.update(kind="not_comparable", reason="unknown_phase")
    elif previous["decision_date"] > current["decision_date"]:
        result.update(kind="not_comparable", reason="previous_session_after_current")
    else:
        kind = "same_session_reassessment" if previous["decision_date"] == current["decision_date"] else "later_session_comparison"
        result.update(kind=kind, phase_changed=previous["phase"] != current["phase"])
    return result


def _write(path: Path, raw: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(raw)


def update_market_regime(*, start: date, output: Path, source: str, previous: Path | None = None) -> dict:
    """Capture exactly once, diagnose at capture completion, and retain an optional report comparison.

    Preflight errors raise without network or output writes. Once a new output directory
    is reserved, ordinary failures return a failed update receipt (exit 2). Missing
    diagnostic/comparison evidence is inconclusive (exit 1), never an unchanged phase.
    Previous source paths are not read; comparison concerns supplied report labels only.
    """
    if type(start) is not date or type(source) is not str or source not in ("csi", "sse"):
        raise ValueError("start must be a date and source must explicitly be csi or sse")
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"output must be a new directory: {output}")
    preflight = _now()
    previous_raw, previous_summary = None, None
    if previous is not None:
        with previous.open("rb") as stream:
            previous_raw = stream.read(MAX_REPORT_BYTES + 1)
        previous_summary = _summary(_decode(previous_raw))
        if datetime.fromisoformat(previous_summary["as_of"]) > preflight:
            raise ValueError("previous report as_of is in the future")
    output.mkdir(parents=True, exist_ok=False)
    report = {"operation": "a_share_market_regime_update_v1", "authority": "diagnostic_only",
              "trade_authorized": False, "price_source": source, "start": start.isoformat(),
              "output": str(output), "status": "failed", "exit_code": 2,
              "diagnostic": None, "comparison": None, "previous_report": None}
    stage = "retain_previous"
    try:
        if previous_raw is not None:
            retained = output / "previous.json"
            _write(retained, previous_raw)
            report["previous_report"] = {"path": str(previous), "retained_path": str(retained),
                                         "sha256": hashlib.sha256(previous_raw).hexdigest()}
        stage = "capture"
        inputs = output / "inputs"
        receipt = capture_snapshot(start=start, output=inputs, source=source)
        if receipt["status"] != "captured" or receipt["price_source"] != source:
            raise ValueError("capture did not complete with the selected source")
        as_of = receipt["completed_at"]
        if datetime.fromisoformat(as_of) < preflight:
            raise ValueError("capture clock moved behind update preflight")
        report["capture_receipt"] = {"path": str(inputs / "receipt.json"),
                                     "sha256": hashlib.sha256((inputs / "receipt.json").read_bytes()).hexdigest()}
        stage = "diagnostic"
        argv = [sys.executable, "-m", "experiments.run_a_share_market_regime",
                "--prices", str(inputs / "prices.csv"), "--calendar", str(inputs / "calendar.csv"),
                "--basis", "snapshot", "--as-of", as_of]
        process = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=30, check=False)
        if process.stderr:
            _write(output / "diagnostic.stderr.txt", process.stderr)
        if process.returncode not in (0, 1):
            raise ValueError(f"diagnostic exited {process.returncode}; inspect retained stderr")
        stage = "verify_diagnostic"
        payload = _decode(process.stdout)
        current = _summary(payload)
        if current["as_of"] != datetime.fromisoformat(as_of).astimezone(CHINA_TZ).isoformat():
            raise ValueError("diagnostic did not use capture completion as_of")
        for key, name in (("prices", "prices.csv"), ("calendar", "calendar.csv")):
            if payload["sources"][key]["sha256"] != receipt["normalized_sha256"][name]:
                raise ValueError("diagnostic inputs differ from captured CSV hashes")
        if process.returncode != (1 if current["phase"] == "unknown" else 0):
            raise ValueError("diagnostic exit code and phase disagree")
        comparison = _compare(previous_summary, current)
        regime_path = output / "regime.json"
        _write(regime_path, process.stdout)
        report["diagnostic"] = {**current, "path": str(regime_path), "exit_code": process.returncode,
                                "sha256": hashlib.sha256(process.stdout).hexdigest(), "replay_argv": argv}
        report["comparison"] = comparison
        code = 1 if process.returncode == 1 or comparison["kind"] == "not_comparable" else 0
        report.update(status="completed" if code == 0 else "inconclusive", exit_code=code)
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as error:
        report.update(status="failed", exit_code=2, error={"stage": stage, "type": type(error).__name__, "message": str(error)})
    _write(output / "update.json", (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode())
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="单次A股牛熊更新：显式采集、快照诊断和可选上次报告比较；不调度、不交易")
    parser.add_argument("--start", required=True, type=date.fromisoformat, help="有限历史窗口起日")
    parser.add_argument("--source", required=True, choices=("csi", "sse"), help="显式来源，不自动换源")
    parser.add_argument("--output", required=True, type=Path, help="必须不存在的新目录")
    parser.add_argument("--previous", type=Path, help="可选：上次snapshot诊断JSON，不是update.json；不查找隐式latest")
    args = parser.parse_args(argv)
    try:
        report = update_market_regime(start=args.start, output=args.output, source=args.source, previous=args.previous)
    except (OSError, ValueError, TypeError) as error:
        parser.error(str(error))
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
