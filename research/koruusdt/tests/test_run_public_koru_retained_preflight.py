from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import shutil
import socket
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from crypto_quant_foundation import FoundationFailure

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "research/koruusdt/run_public_koru_retained_preflight.py"
SPEC = importlib.util.spec_from_file_location("public_koru_preflight", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def _write_manifest(path: Path, value: dict[str, object]) -> None:
    value["manifest_sha256"] = ""
    value["manifest_sha256"] = "sha256:" + hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _authority_copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    authority = tmp_path / "authority"
    shutil.copytree(runner.AUTHORITY_ROOT, authority)
    monkeypatch.setattr(runner, "AUTHORITY_ROOT", authority)
    monkeypatch.setattr(runner, "AUTHORITY_MANIFEST", authority / "manifest.json")
    return authority


def _tree_snapshot(root: Path) -> tuple[bool, tuple[tuple[str, bytes | None], ...]]:
    if not root.exists():
        return False, ()
    return True, tuple(
        (path.relative_to(root).as_posix(), path.read_bytes() if path.is_file() else None)
        for path in sorted(root.rglob("*"))
    )


def _tiny_catalog(config: dict[str, object], files: list[dict[str, object]] | None = None) -> dict[str, object]:
    catalog: dict[str, object] = {
        "type": runner.INPUT_CATALOG_SCHEMA,
        "schema_version": 1,
        "full_mode_config": config,
        "files": files or [],
        "catalog_sha256": "",
    }
    catalog["catalog_sha256"] = runner._catalog_digest(catalog)
    return catalog


def _fake_child(monkeypatch: pytest.MonkeyPatch, source: str) -> None:
    monkeypatch.setattr(
        runner,
        "_child_command",
        lambda staging, _attempt_id, _catalog_sha256: [sys.executable, "-c", source, str(staging)],
    )


def _copying_ioctl(destination_fd: int, source_fd: int) -> None:
    os.lseek(source_fd, 0, os.SEEK_SET)
    os.ftruncate(destination_fd, 0)
    while chunk := os.read(source_fd, 1024 * 1024):
        os.write(destination_fd, chunk)
    os.lseek(source_fd, 0, os.SEEK_SET)
    os.lseek(destination_fd, 0, os.SEEK_SET)


def _small_full_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, with_file: bool = False,
) -> dict[str, object]:
    monkeypatch.setattr(runner, "_ficlone_ioctl", _copying_ioctl)
    config = runner._full_mode_config(1)
    if not with_file:
        catalog = _tiny_catalog(config)
        monkeypatch.setattr(runner, "_build_input_catalog", lambda _config: catalog)
        return catalog
    data = tmp_path / "source-data" / "data"
    data.mkdir(parents=True)
    fixture = data / "fixture.txt"
    fixture.write_text("frozen", encoding="utf-8")
    catalog = _tiny_catalog(config, [{
        "path": "data/fixture.txt", "sha256": runner._hash(fixture.read_bytes()), "size_bytes": len(fixture.read_bytes()),
    }])
    monkeypatch.setattr(runner, "DATA", data)
    monkeypatch.setattr(runner, "_build_input_catalog", lambda _config: catalog)
    return catalog


@pytest.mark.parametrize("member_key, _expected_hash", runner.APPROVED_MEMBER_HASHES)
def test_authority_rejects_each_copied_member_byte(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, member_key: str, _expected_hash: str
) -> None:
    authority = _authority_copy(tmp_path, monkeypatch)
    target = authority / member_key
    raw = target.read_bytes()
    target.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])

    with pytest.raises(ValueError, match="authority mismatch"):
        runner._authority_manifest()


def test_authority_rejects_self_consistent_manifest_member_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority = _authority_copy(tmp_path, monkeypatch)
    manifest_path = authority / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["members"][0]["source_fixture_path"] = "provenance-only-but-wrong"
    _write_manifest(manifest_path, manifest)

    with pytest.raises(ValueError, match="authority mismatch"):
        runner._authority_manifest()


def test_authority_rejects_manifest_byte_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority = _authority_copy(tmp_path, monkeypatch)
    manifest_path = authority / "manifest.json"
    manifest_path.write_bytes(manifest_path.read_bytes().replace(b"\n", b"\r\n", 1))

    with pytest.raises(ValueError, match="manifest bytes are noncanonical"):
        runner._authority_manifest()


def test_smoke_validates_authority_and_stops_before_economics() -> None:
    result = runner.smoke()

    assert result["authority_member_count"] == 8
    assert result["network_performed"] is False
    assert result["holdout_touched"] is False
    assert result["stopped_before"] == "full_retained_source_replay_and_economics"


def test_smoke_rejects_holdout_boundary_even_with_rehashed_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    execution_path = tmp_path / "execution.json"
    execution = json.loads(runner.EXECUTION_MANIFEST.read_text(encoding="utf-8"))
    execution["backtest_authority_interval"]["end_ms_exclusive"] += 1
    _write_manifest(execution_path, execution)
    monkeypatch.setattr(runner, "EXECUTION_MANIFEST", execution_path)

    with pytest.raises(ValueError, match="does not exclude holdout"):
        runner.smoke()


@pytest.mark.parametrize("existing", (False, True), ids=("nonexistent", "empty"))
def test_smoke_foundation_root_is_byte_for_byte_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, existing: bool
) -> None:
    root = tmp_path / "foundation"
    if existing:
        root.mkdir()
    before = _tree_snapshot(root)

    def foundation_forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("smoke must not initialize Foundation")

    monkeypatch.setattr(runner, "LocalFoundation", foundation_forbidden)
    assert runner.main(["--smoke", "--foundation-root", str(root)]) == 0
    assert _tree_snapshot(root) == before


def test_smoke_rejects_preinitialized_foundation_root_without_mutation(tmp_path: Path) -> None:
    root = tmp_path / "foundation"
    foundation = runner.LocalFoundation(root)
    foundation.append(runner.OWNER_LOG, "pre-existing-evidence", b"not-preflight-evidence")
    before = _tree_snapshot(root)

    with pytest.raises(ValueError, match="Foundation state is not an input"):
        runner.main(["--smoke", "--foundation-root", str(root)])

    assert _tree_snapshot(root) == before


def test_full_preflight_publication_store_reads_back_owner_logs_and_detects_tampering(
    tmp_path: Path,
) -> None:
    root = tmp_path / "foundation"
    foundation = runner.LocalFoundation(root, clock=lambda: "2030-01-02T03:04:05.000000Z")
    store = runner.KoruEconomicsArtifactStoreV1(foundation)
    envelope = runner.ArtifactEnvelope.create("strategy_definition", 1, {"strategy_id": "fixture"})

    ref = store.put(envelope=envelope)
    assert store.read(ref=ref).envelope == envelope
    entries = foundation.entries(runner.OWNER_LOG)
    assert len(entries) == 1
    assert entries[0].event_id == runner._artifact_event_id(ref)
    assert json.loads(entries[0].payload) == runner._artifact_publication_record(envelope, ref)
    assert foundation.append(runner.OWNER_LOG, entries[0].event_id, entries[0].payload).entry_ref == entries[0].entry_ref

    digest = ref.content_hash.removeprefix("sha256:")
    (root / "artifacts" / "sha256" / digest[:2] / digest).write_bytes(b"tampered")
    with pytest.raises(FoundationFailure, match="ARTIFACT_INTEGRITY"):
        store.read(ref=ref)


class _CanonicalFixture:
    def __init__(self, value: dict[str, object]) -> None:
        self._value = value

    def to_canonical_dict(self) -> dict[str, object]:
        return self._value


def _digest(number: int) -> str:
    return f"sha256:{number:064x}"


def _fixture_ref(artifact_type: str, number: int) -> _CanonicalFixture:
    return _CanonicalFixture({
        "type": "artifact_ref",
        "artifact_type": artifact_type,
        "schema_version": 1,
        "content_hash": _digest(number),
    })


def _owner_publication_inputs() -> tuple[object, object]:
    bindings = []
    for number in range(1, 5):
        premium_id = f"KORU-PRM-{number:02d}"
        bindings.append(SimpleNamespace(
            premium_id=premium_id,
            strategy_ref=_fixture_ref("strategy_definition", number),
            parameter_ref=_fixture_ref("strategy_parameter_set", number),
            recipe_digest=_digest(10 + number),
            compiler_result_ref=_fixture_ref("koru_directional_target_compile_result", 20),
            compiler_result_digest=_digest(20),
            scope_ref=_fixture_ref("koru_directional_discovery_scope", 21),
            scope_digest=_digest(21),
            source_fragment_digest=_digest(22),
            target_stream_key=premium_id,
            target_stream_digest=_digest(30 + number),
            overlay_bundle_ref=_CanonicalFixture({
                "type": "market_bundle_ref",
                "bundle_key": f"overlay-{premium_id}",
                "manifest_hash": _digest(40 + number),
            }),
            overlay_bundle_digest=_digest(40 + number),
            economics_bundle_ref=_CanonicalFixture({
                "type": "market_bundle_ref",
                "bundle_key": "economics",
                "manifest_hash": _digest(50),
            }),
            economics_bundle_digest=_digest(50),
            economics_authority_digest=_digest(51),
            reader=SimpleNamespace(manifest=_CanonicalFixture({
                "type": "market_bundle_manifest",
                "bundle_key": f"overlay-{premium_id}",
                "content_hash": _digest(40 + number),
            })),
        ))
    return (
        SimpleNamespace(fragment_digest=_digest(22), request=SimpleNamespace(request_hash=_digest(23))),
        SimpleNamespace(bindings=tuple(bindings), reader_set_digest=_digest(60)),
    )


def _full_owner_records() -> tuple[Any, Any, Any, tuple[dict[str, object], ...]]:
    source, readers = _owner_publication_inputs()
    economics = SimpleNamespace(
        authority_digest=_digest(51),
        bundle_ref=_fixture_ref("economics_bundle", 50),
        authority_refs=(_fixture_ref("economics_terms", 52),),
    )
    envelope = runner.ArtifactEnvelope.create("strategy_definition", 1, {"strategy_id": "fixture"})
    artifact_record = runner._artifact_publication_record(envelope, runner.ArtifactRef.from_envelope(envelope))
    return source, economics, readers, runner._expected_owner_records(source, economics, readers, (artifact_record,))


@pytest.mark.parametrize("omit_or_substitute", ["omit", "substitute"])
def test_owner_log_records_compiler_and_each_overlay_exactly(
    tmp_path: Path, omit_or_substitute: str
) -> None:
    source, _economics, readers, expected = _full_owner_records()
    publication_records = runner._owner_publication_records(source, readers)
    expected_ids = [runner._owner_record_event_id(record) for record in expected]

    assert len(expected) == 8
    assert len(set(expected_ids)) == len(expected_ids)
    assert [record["type"] for record in expected].count("koru_source_projection_publication_v1") == 1
    assert [record["type"] for record in expected].count("koru_artifact_publication_v1") == 1
    assert [record["type"] for record in expected].count("koru_premium_reader_set_publication_v1") == 1
    compiler = publication_records[0]
    assert compiler["type"] == "koru_compiler_result_publication_v1"
    assert set(compiler) >= {
        "compiler_result_ref", "compiler_result_digest", "source_fragment_digest",
        "scope_ref", "scope_digest", "ordered_prm_recipes",
    }
    assert [row["target_stream_digest"] for row in compiler["ordered_prm_recipes"]] == [
        _digest(number) for number in range(31, 35)
    ]
    assert [record["premium_id"] for record in publication_records[1:]] == [
        "KORU-PRM-01", "KORU-PRM-02", "KORU-PRM-03", "KORU-PRM-04",
    ]
    assert all(set(record) >= {
        "overlay_bundle_ref", "overlay_bundle_digest", "overlay_manifest",
        "target_stream_ref", "target_stream_key", "target_stream_digest",
        "recipe_refs", "economics_bundle_ref", "economics_bundle_digest",
        "economics_authority_digest",
    } for record in publication_records[1:])

    published = list(expected)
    if omit_or_substitute == "omit":
        published.pop(1)
    else:
        published[-1] = {**published[-1], "reader_set_digest": _digest(99)}
    foundation = runner.LocalFoundation(
        tmp_path / omit_or_substitute, clock=lambda: "2030-01-02T03:04:05.000000Z"
    )
    for record in published:
        runner._append_owner_record(foundation, record)

    if omit_or_substitute == "omit":
        assert len(foundation.entries(runner.OWNER_LOG)) == len(expected) - 1
    else:
        assert len(foundation.entries(runner.OWNER_LOG)) == len(expected)
    with pytest.raises(ValueError, match="cover"):
        runner._checkpoint_summary(foundation, expected)


def test_owner_log_records_publish_read_back_and_replay_stably(tmp_path: Path) -> None:
    _source, _economics, _readers, expected = _full_owner_records()
    foundation = runner.LocalFoundation(
        tmp_path / "foundation", clock=lambda: "2030-01-02T03:04:05.000000Z"
    )

    for record in expected:
        runner._append_owner_record(foundation, record)
    summary = runner._checkpoint_summary(foundation, expected)
    assert [record["event_id"] for record in summary["publication_records"]] == [
        runner._owner_record_event_id(record) for record in expected
    ]
    entries = foundation.entries(runner.OWNER_LOG)
    assert len(entries) == len(expected)

    replayed = _full_owner_records()[3]
    assert replayed == expected
    for record in replayed:
        runner._append_owner_record(foundation, record)
    assert foundation.entries(runner.OWNER_LOG) == entries
    assert runner._checkpoint_summary(foundation, replayed) == summary


def test_full_rejects_invalid_max_seconds(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        runner.main(["--full", "--max-seconds", "301"])

    assert caught.value.code == 2
    assert "must be an integer from 1 to 300" in capsys.readouterr().err


def test_ioctl_seam_snapshot_is_distinct_read_only_and_survives_source_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog = _small_full_inputs(tmp_path, monkeypatch, with_file=True)
    staging = tmp_path / "staging"
    staging.mkdir()

    runner._probe_ficlone(staging)
    runner._freeze_input_snapshot(staging / "input", catalog)
    source = tmp_path / "source-data" / "data" / "fixture.txt"
    destination = staging / "input" / "data" / "fixture.txt"
    source.write_text("changed", encoding="utf-8")

    assert destination.read_text(encoding="utf-8") == "frozen"
    assert source.stat().st_ino != destination.stat().st_ino
    assert destination.stat().st_mode & 0o777 == 0o444


def test_actual_ficlone_snapshot_survives_source_mutation_when_supported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = tmp_path / "source-data" / "data"
    data.mkdir(parents=True)
    source = data / "fixture.txt"
    source.write_text("frozen", encoding="utf-8")
    monkeypatch.setattr(runner, "DATA", data)
    config = runner._full_mode_config(1)
    catalog = _tiny_catalog(config, [{
        "path": "data/fixture.txt", "sha256": runner._hash(source.read_bytes()), "size_bytes": 6,
    }])
    staging = tmp_path / "staging"
    staging.mkdir()

    try:
        runner._probe_ficlone(staging)
        runner._freeze_input_snapshot(staging / "input", catalog)
    except runner.SnapshotCapabilityUnavailable:
        pytest.skip("filesystem does not support FICLONE")
    source.write_text("changed", encoding="utf-8")

    assert (staging / "input" / "data" / "fixture.txt").read_text(encoding="utf-8") == "frozen"


def test_ficlone_probe_fails_closed_when_ioctl_is_unsupported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unsupported(_destination_fd: int, _source_fd: int) -> None:
        raise OSError(95, "Operation not supported")

    monkeypatch.setattr(runner, "_ficlone_ioctl", unsupported)
    staging = tmp_path / "staging"
    staging.mkdir()

    with pytest.raises(runner.SnapshotCapabilityUnavailable):
        runner._probe_ficlone(staging)


def test_ficlone_cross_device_fails_closed(tmp_path: Path) -> None:
    destination_root = Path("/dev/shm")
    if not destination_root.is_dir() or destination_root.stat().st_dev == tmp_path.stat().st_dev:
        pytest.skip("no cross-device writable tmpfs")
    source = tmp_path / "source"
    source.write_text("frozen", encoding="utf-8")
    destination = destination_root / f"koru-ficlone-{os.getpid()}-{time.monotonic_ns()}"

    try:
        with pytest.raises(runner.SnapshotCapabilityUnavailable, match="different devices"):
            runner._clone_held_file(source, destination, runner._hash(source.read_bytes()), 6)
    finally:
        destination.unlink(missing_ok=True)


def test_input_clone_mismatch_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    catalog = _small_full_inputs(tmp_path, monkeypatch, with_file=True)
    calls = 0

    def probe_only_copy(destination_fd: int, source_fd: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            _copying_ioctl(destination_fd, source_fd)

    monkeypatch.setattr(runner, "_ficlone_ioctl", probe_only_copy)
    staging = tmp_path / "staging"
    staging.mkdir()
    runner._probe_ficlone(staging)

    with pytest.raises(runner.SnapshotCatalogMismatch, match="does not match catalog"):
        runner._freeze_input_snapshot(staging / "input", catalog)


def test_snapshot_failure_receipt_is_exact_and_never_starts_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _small_full_inputs(tmp_path, monkeypatch)

    def unsupported(_destination_fd: int, _source_fd: int) -> None:
        raise OSError(95, "Operation not supported")

    def child_forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("child must not start after snapshot failure")

    monkeypatch.setattr(runner, "_ficlone_ioctl", unsupported)
    monkeypatch.setattr(runner.subprocess, "Popen", child_forbidden)
    root = tmp_path / "attempt-root"

    with pytest.raises(runner.FullPreflightSnapshotFailed) as raised:
        runner.full_preflight(root, 1)

    attempt_id = raised.value.receipt_path.stem
    identity = runner._load_attempt_identity(root, attempt_id)
    receipt = runner._load_receipt(root, attempt_id)
    assert receipt == runner._snapshot_failure_receipt(identity, "snapshot_capability_unavailable")
    assert not (root / ".staging" / attempt_id).exists()
    assert not any(path.name in {"foundation", "market"} for path in root.rglob("*"))


def test_catalog_mismatch_receipt_is_exact_and_never_starts_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _small_full_inputs(tmp_path, monkeypatch, with_file=True)
    (tmp_path / "source-data" / "data" / "fixture.txt").write_text("changed", encoding="utf-8")
    monkeypatch.setattr(
        runner.subprocess,
        "Popen",
        lambda *_args, **_kwargs: pytest.fail("child must not start after catalog mismatch"),
    )
    root = tmp_path / "attempt-root"

    with pytest.raises(runner.FullPreflightSnapshotFailed) as raised:
        runner.full_preflight(root, 1)

    attempt_id = raised.value.receipt_path.stem
    identity = runner._load_attempt_identity(root, attempt_id)
    assert runner._load_receipt(root, attempt_id) == runner._snapshot_failure_receipt(
        identity, "snapshot_catalog_mismatch",
    )
    assert not (root / ".staging" / attempt_id).exists()
    assert not any(path.name in {"foundation", "market"} for path in root.rglob("*"))


def test_actual_child_timeout_archives_only_forensic_foundation_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog = _small_full_inputs(tmp_path, monkeypatch)

    with pytest.raises(runner.FullPreflightDeadlineExceeded) as raised:
        runner.full_preflight(
            tmp_path / "attempt-root", 1, _child_test_mode=runner._TIMEOUT_TEST_MODE,
        )

    root = tmp_path / "attempt-root"
    attempt_id = next((root / "timed-out").iterdir()).name
    archive = root / "timed-out" / attempt_id
    receipt = runner._load_receipt(root, attempt_id)
    assert receipt is not None
    assert receipt["attempt_id"] == attempt_id
    assert receipt["attempt_identity"]["attempt_id"] == attempt_id
    assert receipt["input_catalog_sha256"] == catalog["catalog_sha256"]
    assert receipt["final_authority"] == []
    assert receipt["child_status"]["timed_out"] is True
    assert receipt["archive_state"] == "archived"
    assert receipt["cleanup_state"] == "process_group_reaped"
    assert set(receipt["timings"]) == set(runner.TIMING_KEYS)
    assert runner._load_canonical(archive / runner.TIMEOUT_MARKER, "timeout state")["timings"] == receipt["timings"]
    assert runner._verify_input_snapshot(archive / "input") == catalog

    envelope = runner.ArtifactEnvelope.create(
        "strategy_definition", 1, {"strategy_id": "timeout-integration"},
    )
    ref = runner.ArtifactRef.from_envelope(envelope)
    foundation = runner.LocalFoundation(archive / "foundation")
    assert foundation.read(ref=ref).envelope == envelope
    record = runner._artifact_publication_record(envelope, ref)
    entries = foundation.entries(runner.OWNER_LOG)
    assert len(entries) == 1
    assert entries[0].event_id == runner._owner_record_event_id(record)
    assert entries[0].payload == runner.canonical_bytes(record)
    assert runner._load_canonical(archive / "timeout-test-ready.json", "timeout test") == {
        "type": "koru_retained_preflight_timeout_test_v1",
        "artifact_ref": json.loads(runner.canonical_bytes(ref)),
        "envelope": json.loads(runner.canonical_bytes(envelope)),
        "owner_record": json.loads(runner.canonical_bytes(record)),
    }
    assert not (archive / runner.COMPLETE_MARKER).exists()
    assert not (root / ".staging" / attempt_id).exists()
    assert not (root / "attempts" / attempt_id).exists()
    with pytest.raises(ValueError, match="no consumable success receipt"):
        runner.read_success_receipt(root, attempt_id)
    assert raised.value.receipt_path == root / "receipts" / f"{attempt_id}.json"


def test_timeout_kills_and_reaps_term_resistant_process_group(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _small_full_inputs(tmp_path, monkeypatch)
    pids = tmp_path / "pids"
    _fake_child(monkeypatch, """
from pathlib import Path
import signal, subprocess, sys, time, os
root, pids = Path(sys.argv[1]), Path(sys.argv[2])
signal.signal(signal.SIGTERM, lambda *_: None)
child = subprocess.Popen([sys.executable, '-c', 'import signal,time; signal.signal(signal.SIGTERM, lambda *_: None); time.sleep(30)'])
pids.write_text(f'{os.getpid()} {child.pid}')
(root / 'foundation').mkdir()
(root / 'foundation' / 'created').write_text('state')
time.sleep(30)
""".replace("sys.argv[2]", repr(str(pids))))

    with pytest.raises(runner.FullPreflightDeadlineExceeded):
        runner.full_preflight(tmp_path / "attempt-root", 1)

    parent_pid, child_pid = (int(value) for value in pids.read_text().split())
    for pid in (parent_pid, child_pid):
        deadline = time.monotonic() + 1
        while True:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
            if time.monotonic() >= deadline:
                pytest.fail(f"process {pid} survived timeout cleanup")
            time.sleep(0.02)


def test_input_catalog_mutation_rejects_child_success_before_promotion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _small_full_inputs(tmp_path, monkeypatch, with_file=True)
    _fake_child(monkeypatch, """
from pathlib import Path
import sys
root = Path(sys.argv[1])
path = root / 'input' / 'data' / 'fixture.txt'
path.chmod(0o644)
path.write_text('mutated')
""")

    with pytest.raises(ValueError, match="frozen input catalog mismatch"):
        runner.full_preflight(tmp_path / "attempt-root", 1)

    root = tmp_path / "attempt-root"
    attempt_id = next((root / ".staging").iterdir()).name
    assert not (root / "attempts" / attempt_id).exists()
    assert not (root / "receipts" / f"{attempt_id}.json").exists()


def test_duplicate_attempt_id_is_locked_and_retry_id_is_new(tmp_path: Path) -> None:
    root = runner._prepare_attempt_root(tmp_path / "attempt-root")
    config = runner._full_mode_config(1)
    catalog = _tiny_catalog(config)
    first = runner._attempt_identity(runner._attempt_preimage(config, catalog["catalog_sha256"], 0, None))
    retry = runner._attempt_identity(runner._attempt_preimage(
        config, catalog["catalog_sha256"], 1, first["attempt_id"],
    ))
    assert first["attempt_id"] != retry["attempt_id"]
    paths = runner._attempt_paths(root, first["attempt_id"])
    with runner._attempt_lock(paths["lock"]):
        runner._reserve_attempt(root, first)
        with pytest.raises(FileExistsError):
            runner._reserve_attempt(root, first)


def _promoted_unreceipted_fixture(tmp_path: Path) -> tuple[Path, dict[str, object], str]:
    root = runner._prepare_attempt_root(tmp_path / "attempt-root")
    config = runner._full_mode_config(1)
    catalog = _tiny_catalog(config)
    identity = runner._attempt_identity(runner._attempt_preimage(config, catalog["catalog_sha256"], 0, None))
    attempt_id = identity["attempt_id"]
    assert type(attempt_id) is str
    runner._reserve_attempt(root, identity)
    published = runner._attempt_paths(root, attempt_id)["published"]
    (published / "input").mkdir(parents=True)
    (published / "market").mkdir()
    runner._atomic_write(published / "input" / "catalog.json", catalog)
    _source, _economics, readers, expected_values = _full_owner_records()
    expected = tuple(json.loads(runner.canonical_bytes(record)) for record in expected_values)
    foundation = runner.LocalFoundation(published / "foundation", clock=lambda: "2020-01-02T03:04:05.000000Z")
    for record in expected:
        runner._append_owner_record(foundation, record)
    owner_log = runner._checkpoint_summary(foundation, expected)
    reader_record = expected[-1]
    marker = {
        "type": "koru_retained_preflight_complete_v1",
        "schema_version": 1,
        "attempt_id": attempt_id,
        "input_catalog_sha256": catalog["catalog_sha256"],
        "expected_owner_records": list(expected),
        "owner_log": owner_log,
        "reader_set": {
            "reader_set_digest": reader_record["reader_set_digest"],
            "premium_reader_ids": [binding.premium_id for binding in readers.bindings],
        },
        "timings": {
            "catalog_elapsed_ns": 1,
            "clone_elapsed_ns": 2,
            "verify_elapsed_ns": 3,
            "child_elapsed_ns": 4,
        },
        "result": {
            "mode": "full",
            "network_performed": False,
            "holdout_touched": False,
            "premium_reader_ids": [binding.premium_id for binding in readers.bindings],
            "owner_log": owner_log,
            "stopped_before": "Experiment_Holdout_and_Backtest",
        },
    }
    runner._atomic_write(published / runner.COMPLETE_MARKER, marker)
    return root, identity, attempt_id


def test_promoted_but_unreceipted_attempt_recovers_exactly_one_receipt(tmp_path: Path) -> None:
    root, _identity, attempt_id = _promoted_unreceipted_fixture(tmp_path)

    first = runner.recover_attempt(root, attempt_id)
    second = runner.recover_attempt(root, attempt_id)

    assert first == second
    assert first["outcome"] == "success"
    assert len(list((root / "receipts").iterdir())) == 1
    assert runner.read_success_receipt(root, attempt_id) == first


def test_recovery_rejects_receipt_when_complete_timings_change(tmp_path: Path) -> None:
    root, _identity, attempt_id = _promoted_unreceipted_fixture(tmp_path)
    receipt = runner.recover_attempt(root, attempt_id)
    marker_path = root / "attempts" / attempt_id / runner.COMPLETE_MARKER
    marker = runner._load_canonical(marker_path, "complete marker")
    marker["timings"]["child_elapsed_ns"] += 1
    runner._atomic_write(marker_path, marker)

    with pytest.raises(ValueError, match="does not bind promoted authority"):
        runner.recover_attempt(root, attempt_id)
    assert receipt["timings"]["child_elapsed_ns"] == 4


def test_conflicting_receipt_for_promoted_attempt_fails_closed(tmp_path: Path) -> None:
    root, identity, attempt_id = _promoted_unreceipted_fixture(tmp_path)
    conflict = {
        "type": runner.RECEIPT_SCHEMA,
        "schema_version": 1,
        "outcome": "timeout",
        "attempt_id": attempt_id,
        "attempt_identity": identity,
        "input_catalog_sha256": identity["frozen_input_catalog_sha256"],
        "final_authority": [],
        "child_status": {"exit_code": -9, "timed_out": True},
        "archive_state": "archived",
        "cleanup_state": "process_group_reaped",
        "timings": {
            "catalog_elapsed_ns": 1,
            "clone_elapsed_ns": 2,
            "verify_elapsed_ns": 3,
            "child_elapsed_ns": 4,
        },
    }
    timed_out = runner._attempt_paths(root, attempt_id)["timed_out"]
    timed_out.mkdir()
    runner._atomic_write(timed_out / runner.TIMEOUT_MARKER, runner._timeout_state(
        identity, -9, conflict["timings"],
    ))
    runner._create_new_json(runner._attempt_paths(root, attempt_id)["receipt"], conflict)

    with pytest.raises(ValueError, match="promoted attempt conflicts"):
        runner.recover_attempt(root, attempt_id)


def test_promote_renames_one_container_and_fsyncs_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = runner._prepare_attempt_root(tmp_path / "attempt-root")
    attempt_id = "attempt-fixture"
    paths = runner._attempt_paths(root, attempt_id)
    (paths["staging"] / "foundation").mkdir(parents=True)
    (paths["staging"] / "foundation" / "state").write_text("state")
    synced: list[Path] = []
    monkeypatch.setattr(runner, "_fsync_directory", lambda path: synced.append(path))

    promoted = runner._promote_attempt_container(root, attempt_id)

    assert promoted == paths["published"]
    assert (promoted / "foundation" / "state").read_text() == "state"
    assert not paths["staging"].exists()
    assert synced == [root / "attempts"]


def test_pi_lens_ignores_only_the_byte_exact_vendor_html() -> None:
    policy = json.loads((ROOT / ".pi-lens.json").read_text(encoding="utf-8"))
    authority_root = "research/koruusdt/data/public_preflight_sources_v1"

    assert policy["ignore"].count(authority_root + "/krx/landing.html") == 1
    assert not any(
        value.startswith(authority_root) and value != authority_root + "/krx/landing.html"
        for value in policy["ignore"]
    )


def test_smoke_stays_offline_when_socket_operations_are_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("network attempted")

    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(socket.socket, "connect", fail)
    monkeypatch.setattr(socket.socket, "connect_ex", fail)

    assert runner.main(["--smoke"]) == 0


def test_runner_uses_only_public_package_roots_and_no_experiment_api() -> None:
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"), filename=str(SCRIPT))
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    imported.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    crypto = {module for module in imported if module.startswith("crypto_quant")}

    assert crypto <= {
        "crypto_quant_bundle_builder",
        "crypto_quant_domain",
        "crypto_quant_foundation",
    }
    assert not any(module in {"requests", "urllib.request", "http.client"} for module in imported)
    assert "execute_experiment" not in SCRIPT.read_text(encoding="utf-8")
