"""C0 raw-producer tests: new dummy sources only, no actual provider or key."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from experiments.a_share_ingestion import retro_capture_v1 as capture


def deny():
    raise capture.CaptureError("REAL_INPUT_NOT_ADMITTED")


def allow():
    pass  # Trusted synthetic fixture policy only, never a real source grant.


def test_capture_scope_is_pure_and_defaults_do_not_grant_authority(
    tmp_path, monkeypatch
):
    spec = capture.make_synthetic_capture_spec(tmp_path / "fixture", bulk=False)

    def forbidden(*args, **kwargs):
        pytest.fail("scope calculation must not open/stat any file")

    monkeypatch.setattr(Path, "stat", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    assert capture.capture_scope_hash(spec).startswith("sha256:")
    with pytest.raises(capture.CaptureError, match="REAL_INPUT_NOT_ADMITTED"):
        capture.capture_source(spec)


def test_capture_spec_rejects_unsafe_mode_and_endpoint_without_io(tmp_path):
    spec = capture.make_synthetic_capture_spec(tmp_path / "fixture", bulk=False)
    with pytest.raises(capture.CaptureError):
        replace(spec, endpoint="https://tt.xiaodefa.cn/")
    with pytest.raises(capture.CaptureError):
        replace(spec, mode="approved")
    with pytest.raises(capture.CaptureError):
        capture.CaptureSpec.from_payload({**spec.payload, "approved": True})


def test_capture_budget_predebit_and_close_are_not_refillable(tmp_path):
    spec = capture.make_synthetic_capture_spec(tmp_path / "fixture", bulk=False)
    budget = capture.CaptureBudget(Path(spec.output) / "data", spec, allow)
    budget.reserve("REQUEST", requests=1, wire=spec.limits.response_bytes + 1)
    assert budget.summary()["requests"] == 1
    before = budget.summary()
    with pytest.raises(capture.CaptureError, match="CAPTURE_BUDGET"):
        budget.reserve("REQUEST", requests=spec.limits.max_requests)
    assert budget.summary()["requests"] == before["requests"]
    assert budget.close("FAILED")
    with pytest.raises(capture.CaptureError):
        budget.reserve("REQUEST", requests=1)
    with pytest.raises(capture.CaptureError):
        capture.CaptureBudget(Path(spec.output) / "data", spec, allow)


def test_capture_synthetic_program_uses_public_governance_and_safe_raw(tmp_path):
    spec = capture.make_synthetic_capture_spec(tmp_path / "fixture", bulk=True)
    protocol = capture.synthetic_capture_protocol(spec)
    admission = capture.issue_capture_admission(spec, protocol, runtime_authorize=allow)
    result = capture.capture_source(spec, admission=admission)
    payload = result.payload
    assert payload["state"] == "CAPTURED_NOT_STUDY_QUALIFIED"
    assert payload["mode"] == "SYNTHETIC_CAPTURE_FIXTURE"
    assert payload["stages"] == ["MEMBERS", "METADATA", "SMOKE", "BULK"]
    assert payload["source_qualified"] is False and payload["model_calls"] == 0
    assert payload["budget"]["requests"] == 17
    assert payload["cohort"] == ["000001.SZ", "600000.SH"]
    assert len(payload["smoke_sessions"]) == 8
    assert capture.verify_capture(Path(spec.output) / "data", result)["verified"]
    assert "Z" * 56 not in json.dumps(payload)


def admitted(tmp_path, *, bulk=False, policy=allow):
    spec = capture.make_synthetic_capture_spec(tmp_path / "fixture", bulk=bulk)
    admission = capture.issue_capture_admission(
        spec, capture.synthetic_capture_protocol(spec), runtime_authorize=policy
    )
    return spec, admission


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_requests", True),
        ("raw_bytes", 0),
        ("read_bytes", -1),
        ("response_bytes", 17 * 1024**2),
        ("minimum_interval_ms", 0),
    ],
)
def test_capture_limits_are_natural_bounded_values(tmp_path, field, value):
    spec = capture.make_synthetic_capture_spec(tmp_path / "fixture")
    with pytest.raises(capture.CaptureError, match="CAPTURE_LIMITS"):
        replace(spec.limits, **{field: value})


def test_issue_denial_precedes_all_stat_and_token_access(tmp_path, monkeypatch):
    spec = capture.make_synthetic_capture_spec(tmp_path / "fixture")
    protocol = capture.synthetic_capture_protocol(spec)

    def forbidden(*a, **kw):
        pytest.fail("not permitted before actual host policy")

    monkeypatch.setattr(Path, "stat", forbidden)
    monkeypatch.setattr(capture, "read_proxy_token", forbidden)
    with pytest.raises(capture.CaptureError, match="REAL_INPUT_NOT_ADMITTED"):
        capture.issue_capture_admission(spec, protocol)


def test_admission_cannot_retarget_a_valid_proof_or_replace_live_policy(
    tmp_path, monkeypatch
):
    revoked = [False]

    def policy():
        if revoked[0]:
            deny()

    spec, admission = admitted(tmp_path, policy=policy)
    changed = replace(spec, bulk=True)
    forged = replace(admission, scope_hash=capture.capture_scope_hash(changed))

    def forbidden(*args, **kwargs):
        pytest.fail("forged admission must fail before any stat")

    with monkeypatch.context() as patch:
        patch.setattr(Path, "stat", forbidden)
        with pytest.raises(capture.CaptureError, match="ADMISSION_CONFLICT"):
            capture.capture_source(changed, admission=forged)
    revoked[0] = True
    with pytest.raises(capture.CaptureError, match="REAL_INPUT_NOT_ADMITTED"):
        capture.capture_source(spec, admission=replace(admission, policy=allow))
    assert not (Path(spec.output) / "data").exists()


def test_budget_policy_cannot_substitute_the_admitted_policy(tmp_path):
    spec, admission = admitted(tmp_path)
    budget = capture.CaptureBudget(Path(spec.output) / "data", spec, lambda: None)
    with pytest.raises(capture.CaptureError, match="BUDGET_BINDING"):
        capture.capture_source(spec, admission=admission, budget=budget)
    assert budget.summary()["requests"] == 0
    assert budget.close("REJECTED")


def test_original_governance_clock_and_bytes_stay_unchanged(tmp_path):
    import hashlib

    spec, admission = admitted(tmp_path)
    gov = Path(spec.output) / "governance"

    def identity():
        return {
            str(p.relative_to(gov)): (
                hashlib.sha256(p.read_bytes()).hexdigest(),
                p.stat().st_mtime_ns,
            )
            for p in gov.rglob("*")
            if p.is_file()
        }

    before = identity()
    result = capture.capture_source(spec, admission=admission)
    for _ in range(3):
        assert capture.verify_capture(Path(spec.output) / "data", result)["verified"]
    assert identity() == before
    assert admission.governance["io_account"]["sdk_calls_reserved"] == 128
    assert admission.governance["private_clock_calls"] <= 8


def test_missing_original_sample_is_not_repaired_in_private_verifier(
    tmp_path, monkeypatch
):
    spec = capture.make_synthetic_capture_spec(tmp_path / "fixture")
    original_copy = capture._copy_governance

    def removed(source, target, budget):
        (source / "registries" / "validation.sample-consumption.v1.jsonl").unlink()
        return original_copy(source, target, budget)

    monkeypatch.setattr(capture, "_copy_governance", removed)
    with pytest.raises(capture.CaptureError, match="PREFIX_SHAPE"):
        capture.issue_capture_admission(
            spec, capture.synthetic_capture_protocol(spec), runtime_authorize=allow
        )
    assert not (
        Path(spec.output)
        / "governance/registries/validation.sample-consumption.v1.jsonl"
    ).exists()
    assert not (Path(spec.output) / "data").exists()


def test_source_code_pin_failure_keeps_account_and_zero_source_reads(
    tmp_path, monkeypatch
):
    from experiments import run_a_share_price_volume_retro_real_v1 as runner

    spec = capture.make_synthetic_capture_spec(tmp_path / "fixture")
    monkeypatch.setitem(
        runner.CATALOG_GOVERNANCE_CODE_PINS,
        "foundation/src/crypto_quant_foundation/storage.py",
        "0" * 64,
    )
    with pytest.raises(capture.CaptureError, match="CODE_PIN"):
        capture.issue_capture_admission(
            spec, capture.synthetic_capture_protocol(spec), runtime_authorize=allow
        )
    assert (Path(spec.output) / "governance-account/close.json").exists()
    assert not (Path(spec.output) / "data").exists()


def test_member_hash_failure_precedes_even_dummy_token_read(tmp_path, monkeypatch):
    spec, admission = admitted(tmp_path)
    Path(spec.member_files[1].path).write_bytes(b"changed")
    monkeypatch.setattr(
        capture,
        "read_proxy_token",
        lambda *a: pytest.fail("token read after member failure"),
    )
    with pytest.raises(capture.CaptureError):
        capture.capture_source(spec, admission=admission)
    close = json.loads((Path(spec.output) / "data/close.json").read_text())
    assert (
        close["transport_attempts"] == 0 and close["state"] == "FAILED_OR_INTERRUPTED"
    )


def test_network_predebits_do_not_refund_short_fake_responses(tmp_path):
    spec = capture.make_synthetic_capture_spec(tmp_path / "fixture")
    spec = replace(spec, limits=replace(spec.limits, max_requests=3))
    admission = capture.issue_capture_admission(
        spec, capture.synthetic_capture_protocol(spec), runtime_authorize=allow
    )
    with pytest.raises(capture.CaptureError, match="BUDGET_EXHAUSTED"):
        capture.capture_source(spec, admission=admission)
    root = Path(spec.output) / "data"
    close = json.loads((root / "close.json").read_text())
    assert close["transport_attempts"] == close["budget"]["requests"] == 3
    assert close["budget"]["wire"] == 3 * (spec.limits.response_bytes + 1)
    assert len(list(root.glob("request-*.json"))) == 3
    assert not (root / "manifest.json").exists()


class MutatingOpener:
    def __init__(self, members, mutate):
        self.base = capture._SyntheticOpener(members)
        self.mutate = mutate

    def open(self, req, *, timeout):
        reply = self.base.open(req, timeout=timeout)
        request = json.loads(req.data)
        payload = json.loads(reply.raw)
        self.mutate(request, payload)
        return capture._SyntheticReply(json.dumps(payload).encode())


@pytest.mark.parametrize(
    "fault", ["wrong_stock", "duplicate", "calendar", "empty_limit", "drift"]
)
def test_scope_duplicate_empty_calendar_and_overlap_failures_stop_no_retry(
    tmp_path, fault
):
    spec, admission = admitted(tmp_path, bulk=True)

    def mutate(req, payload):
        api = req["api_name"]
        data = payload["data"]
        if api == "daily" and fault == "wrong_stock":
            data["items"][0][0] = "999999.SZ"
        if api == "daily" and fault == "duplicate":
            data["items"].append(data["items"][0])
        if (
            api == "trade_cal"
            and req["params"]["exchange"] == "SZSE"
            and fault == "calendar"
        ):
            data["items"][0][2] = 1 - data["items"][0][2]
        if api == "stk_limit" and fault == "empty_limit":
            data["items"] = []
        if (
            api == "daily"
            and req["params"]["end_date"] == "20241031"
            and fault == "drift"
        ):
            data["items"][0][2] += 1

    def factory(token, s):
        return capture.ProxyAPI(
            token,
            s.limits.max_requests,
            max_response_bytes=s.limits.response_bytes,
            opener=MutatingOpener(("000001.SZ", "600000.SH"), mutate),
        )

    with pytest.raises(capture.CaptureError):
        capture.capture_source(spec, admission=admission, client_factory=factory)
    root = Path(spec.output) / "data"
    close = json.loads((root / "close.json").read_text())
    assert (
        close["state"] == "FAILED_OR_INTERRUPTED"
        and not (root / "manifest.json").exists()
    )
    assert close["budget"]["requests"] == close["transport_attempts"]
    assert close["real_HTTP_attempts"] == 0


@pytest.mark.parametrize("signal", [KeyboardInterrupt, SystemExit])
def test_original_stop_is_not_hidden_by_close_failure(tmp_path, monkeypatch, signal):
    spec, admission = admitted(tmp_path)
    budget = capture.CaptureBudget(Path(spec.output) / "data", spec, admission.policy)

    def factory(*a):
        raise signal()

    def bad_close(*a, **k):
        raise RuntimeError("secondary")

    monkeypatch.setattr(budget, "close", bad_close)
    with pytest.raises(signal):
        capture.capture_source(
            spec, admission=admission, budget=budget, client_factory=factory
        )


def test_close_fifo_and_repeated_close_cannot_claim_verification(tmp_path):
    import os

    spec = capture.make_synthetic_capture_spec(tmp_path / "fixture")
    budget = capture.CaptureBudget(Path(spec.output) / "data", spec, allow)
    os.mkfifo(budget.root / "close.json", 0o600)
    assert (
        not budget.close("FAILED")
        and budget.closed
        and budget.poisoned
        and not budget.close_verified
    )
    with pytest.raises(capture.CaptureError):
        budget.close("AGAIN")


def test_source_deletion_does_not_turn_replay_into_recapture(tmp_path, monkeypatch):
    spec, admission = admitted(tmp_path)
    result = capture.capture_source(spec, admission=admission)
    for m in spec.member_files:
        Path(m.path).unlink()
    Path(spec.credential_file).unlink()
    monkeypatch.setattr(
        capture, "read_proxy_token", lambda *a: pytest.fail("replay token")
    )
    monkeypatch.setattr(
        capture.ProxyAPI, "capture", lambda *a, **k: pytest.fail("replay recapture")
    )
    assert capture.verify_capture(Path(spec.output) / "data", result)["verified"]


@pytest.mark.parametrize(
    "which", ["wire", "request", "response", "gov_clock", "smoke", "extra"]
)
def test_replay_rejects_tampering_and_unexpected_material(tmp_path, which):
    spec, admission = admitted(tmp_path)
    result = capture.capture_source(spec, admission=admission)
    root = Path(spec.output) / "data"
    target = {
        "wire": root / "wire-000001.bin",
        "request": root / "request-000001.json",
        "response": root / "response-000001.json",
        "gov_clock": Path(spec.output) / "governance/.foundation.clock",
        "smoke": root / "smoke-stage.json",
        "extra": root / "unexpected.json",
    }[which]
    target.write_bytes(target.read_bytes() + b" " if target.exists() else b"{}")
    with pytest.raises(capture.CaptureError):
        capture.verify_capture(root, result)


def test_reversed_member_interval_rejected_before_credential(tmp_path, monkeypatch):
    spec = capture.make_synthetic_capture_spec(tmp_path / "fixture")
    member = spec.member_files[1]
    body = json.loads(Path(member.path).read_text())
    body["data"]["items"][0][3] = "19990101"  # in_date is 20000101.
    raw = json.dumps(body).encode()
    Path(member.path).write_bytes(raw)
    altered = replace(member, bytes=len(raw), sha256=capture.digest(raw))
    receipt = spec.member_files[0]
    data = json.loads(Path(receipt.path).read_text())
    data["requests"][0]["response_sha256"] = altered.sha256
    data["requests"][0]["response_bytes"] = altered.bytes
    raw = json.dumps(data).encode()
    Path(receipt.path).write_bytes(raw)
    spec = replace(
        spec,
        member_files=(
            replace(receipt, bytes=len(raw), sha256=capture.digest(raw)),
            altered,
            spec.member_files[2],
        ),
    )
    admission = capture.issue_capture_admission(
        spec, capture.synthetic_capture_protocol(spec), runtime_authorize=allow
    )
    monkeypatch.setattr(
        capture,
        "read_proxy_token",
        lambda *a: pytest.fail("reversed interval reached token"),
    )
    with pytest.raises(capture.CaptureError, match="MEMBER_INTERVAL"):
        capture.capture_source(spec, admission=admission)


def test_account_names_and_roots_are_directory_synced(tmp_path, monkeypatch):
    import os
    import stat

    spec = capture.make_synthetic_capture_spec(tmp_path / "fixture")
    real = os.fsync
    events = []

    def observe(fd):
        events.append("directory" if stat.S_ISDIR(os.fstat(fd).st_mode) else "file")
        return real(fd)

    monkeypatch.setattr(capture.os, "fsync", observe)
    budget = capture.CaptureBudget(Path(spec.output) / "data", spec, allow)
    budget.reserve("REQUEST", requests=1)
    assert budget.close("FIXTURE_DONE")
    assert events.count("directory") >= 3


def test_smoke_gate_write_failure_prevents_every_bulk_request(tmp_path, monkeypatch):
    spec, admission = admitted(tmp_path, bulk=True)
    real_write = capture._write_regular
    calls = []

    def fail_stage(path, raw, **kwargs):
        if path.name == "smoke-stage.json":
            raise OSError("injected stage durability failure")
        return real_write(path, raw, **kwargs)

    class Logged(capture._SyntheticOpener):
        def open(self, request, **kwargs):
            calls.append(json.loads(request.data))
            return super().open(request, **kwargs)

    def factory(token, s):
        return capture.ProxyAPI(
            token,
            s.limits.max_requests,
            max_response_bytes=s.limits.response_bytes,
            opener=Logged(("000001.SZ", "600000.SH")),
        )

    monkeypatch.setattr(capture, "_write_regular", fail_stage)
    with pytest.raises(OSError, match="stage durability"):
        capture.capture_source(spec, admission=admission, client_factory=factory)
    assert len(calls) == 10
    assert (
        json.loads((Path(spec.output) / "data/close.json").read_text())["state"]
        == "FAILED_OR_INTERRUPTED"
    )


@pytest.mark.parametrize("fault", ["wrong_code", "missing_case"])
def test_refusal_evidence_is_code_bound_and_required_before_bulk(
    tmp_path, monkeypatch, fault
):
    spec, admission = admitted(tmp_path, bulk=True)
    original = capture._refusal_evidence

    def wrong(*args):
        evidence = original(*args)
        if fault == "wrong_code":
            evidence["adapter_code_hash"] = "sha256:" + "0" * 64
        else:
            evidence["cases"] = []
        return evidence

    monkeypatch.setattr(capture, "_refusal_evidence", wrong)
    with pytest.raises(capture.CaptureError, match="REFUSAL_EVIDENCE"):
        capture.capture_source(spec, admission=admission)
    close = json.loads((Path(spec.output) / "data/close.json").read_text())
    assert close["transport_attempts"] == 10
    assert close["state"] == "FAILED_OR_INTERRUPTED"


def test_directory_sync_failure_poison_is_not_refunded(tmp_path, monkeypatch):
    spec = capture.make_synthetic_capture_spec(tmp_path / "fixture")
    budget = capture.CaptureBudget(Path(spec.output) / "data", spec, allow)

    def bad(*args):
        raise OSError("directory sync failed")

    monkeypatch.setattr(capture, "_sync_directory", bad)
    with pytest.raises(OSError, match="directory sync"):
        budget.reserve("REQUEST", requests=1)
    assert budget.poisoned and budget.summary()["requests"] == 1
    with pytest.raises(capture.CaptureError, match="BUDGET_CLOSED"):
        budget.reserve("REQUEST", requests=1)


def test_file_stop_outranks_secondary_directory_sync_error(tmp_path, monkeypatch):
    import os
    import stat

    def sync(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            raise RuntimeError("secondary dir error")
        raise KeyboardInterrupt()

    monkeypatch.setattr(capture.os, "fsync", sync)
    with pytest.raises(KeyboardInterrupt):
        capture._write_regular(tmp_path / "owned.bin", b"fixture")


@pytest.mark.parametrize("read_limit", [0, 100])
def test_replay_budget_denial_precedes_even_close_file_read(
    tmp_path, monkeypatch, read_limit
):
    spec, admission = admitted(tmp_path)
    manifest = capture.capture_source(spec, admission=admission)

    def forbidden(*args, **kwargs):
        pytest.fail("replay file read happened before allowance check")

    monkeypatch.setattr(capture, "_read_regular", forbidden)
    with pytest.raises(capture.CaptureError, match="REPLAY_READ_CAP"):
        capture.verify_capture(
            Path(spec.output) / "data", manifest, read_limit=read_limit
        )
