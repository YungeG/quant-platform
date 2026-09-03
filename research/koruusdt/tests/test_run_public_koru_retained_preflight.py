from __future__ import annotations

import copy
import importlib.util
import json
import os
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "research/koruusdt/run_public_koru_retained_preflight.py"
SPEC = importlib.util.spec_from_file_location("public_koru_preflight", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def _tiny_catalog(raw: bytes = b"frozen") -> dict[str, object]:
    catalog: dict[str, object] = {
        "type": runner.INPUT_CATALOG_SCHEMA,
        "schema_version": 1,
        "full_mode_config": runner._raw_snapshot_catalog_config(),
        "files": [{"path": "data/fixture.txt", "sha256": runner._hash(raw), "size_bytes": len(raw)}],
        "catalog_sha256": "",
    }
    catalog["catalog_sha256"] = runner._catalog_digest(catalog)
    return catalog


def _published_fixture(tmp_path: Path, raw: bytes = b"frozen") -> tuple[Path, dict[str, object], dict[str, object]]:
    catalog = _tiny_catalog(raw)
    root = tmp_path / "raw-snapshot-foundation"
    members = (
        runner.RawBlobSnapshotSourceMember(
            runner._snapshot_member_mapping(catalog)["data/fixture.txt"], raw, "0644",
        ),
    )
    publication = runner.publish_raw_blob_snapshot(
        runner.LocalFoundation(root),
        members=members,
        provenance={
            "type": runner.RAW_SNAPSHOT_PROVENANCE_SCHEMA,
            "schema_version": 1,
            "input_catalog": catalog,
            "member_keys": runner._snapshot_member_mapping(catalog),
        },
    )
    return root, runner._input_snapshot_authority(publication, catalog), catalog


def test_prepare_publishes_reusable_raw_snapshot_and_exact_owner_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_data = tmp_path / "source" / "data"
    source_data.mkdir(parents=True)
    (source_data / "fixture.txt").write_bytes(b"frozen")
    catalog = _tiny_catalog()
    monkeypatch.setattr(runner, "DATA", source_data)
    monkeypatch.setattr(runner, "_build_input_catalog", lambda _config: catalog)

    first = runner.prepare_input_snapshot_authority(tmp_path / "foundation")
    second = runner.prepare_input_snapshot_authority(tmp_path / "foundation")

    assert second == first
    assert first["publication_entry_ref"]["log_name"] == "research.raw_snapshots.v1"
    foundation = runner.LocalFoundation(tmp_path / "foundation")
    assert len(foundation.entries("research.raw_snapshots.v1")) == 1
    assert runner._open_input_snapshot_authority(tmp_path / "foundation", first)[0] == catalog


def test_source_mutation_after_publication_cannot_change_verified_snapshot_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_data = tmp_path / "source" / "data"
    source_data.mkdir(parents=True)
    source = source_data / "fixture.txt"
    source.write_bytes(b"frozen")
    catalog = _tiny_catalog()
    monkeypatch.setattr(runner, "DATA", source_data)
    monkeypatch.setattr(runner, "_build_input_catalog", lambda _config: catalog)
    authority = runner.prepare_input_snapshot_authority(tmp_path / "foundation")
    source.write_bytes(b"changed")

    opened_catalog, view = runner._open_input_snapshot_authority(tmp_path / "foundation", authority)
    member_key = runner._snapshot_member_mapping(opened_catalog)["data/fixture.txt"]
    assert view.member_bytes(member_key) == b"frozen"


@pytest.mark.parametrize("field", ["manifest_ref", "snapshot_id", "provenance_hash", "publication_entry_ref"])
def test_changed_snapshot_authority_fails_before_attempt_or_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str,
) -> None:
    snapshot_root, authority, _catalog = _published_fixture(tmp_path)
    changed = copy.deepcopy(authority)
    if field == "manifest_ref":
        changed[field]["content_hash"] = "sha256:" + "0" * 64
    elif field == "publication_entry_ref":
        changed[field]["receipt_hash"] = "sha256:" + "0" * 64
    else:
        changed[field] = "sha256:" + "0" * 64
    monkeypatch.setattr(runner.subprocess, "Popen", lambda *_args, **_kwargs: pytest.fail("child must not start"))
    attempt_root = tmp_path / "attempts"

    with pytest.raises(ValueError):
        runner.full_preflight(
            attempt_root, 1, input_snapshot_authority=changed, raw_snapshot_foundation_root=snapshot_root,
        )

    assert not attempt_root.exists()


def test_owner_log_unpublication_rejects_snapshot_authority(tmp_path: Path) -> None:
    snapshot_root, authority, _catalog = _published_fixture(tmp_path)
    (snapshot_root / "registries" / "research.raw_snapshots.v1.jsonl").unlink()

    with pytest.raises(ValueError, match="publication entry"):
        runner._open_input_snapshot_authority(snapshot_root, authority)


def test_timeout_attempt_has_no_input_tree_and_binds_snapshot_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot_root, authority, catalog = _published_fixture(tmp_path)
    attempt_root = tmp_path / "attempts"
    monkeypatch.setattr(runner, "_verify_koru_discovery_snapshot_scope", lambda _catalog, _view: runner._fixed_koru_discovery_scope())

    with pytest.raises(runner.FullPreflightDeadlineExceeded):
        runner.full_preflight(
            attempt_root, 1, input_snapshot_authority=authority, raw_snapshot_foundation_root=snapshot_root,
            _child_test_mode=runner._TIMEOUT_TEST_MODE,
        )

    attempt_id = next((attempt_root / "timed-out").iterdir()).name
    archive = attempt_root / "timed-out" / attempt_id
    receipt = runner._load_receipt(attempt_root, attempt_id)
    assert receipt is not None
    assert receipt["input_catalog_sha256"] == catalog["catalog_sha256"]
    assert receipt["input_snapshot_authority"] == authority
    assert receipt["attempt_identity"]["input_snapshot_authority"] == authority
    assert runner._load_canonical(archive / runner.TIMEOUT_MARKER, "timeout")["input_snapshot_authority"] == authority
    assert not (archive / "input").exists()
    assert not any(path.is_symlink() or (path.is_file() and path.stat().st_nlink > 1) for path in archive.rglob("*"))
    assert "FICLONE" not in SCRIPT.read_text(encoding="utf-8")
    assert runner.recover_attempt(attempt_root, attempt_id) == receipt


def test_success_receipt_and_attempt_identity_bind_snapshot_authority(tmp_path: Path) -> None:
    _snapshot_root, authority, catalog = _published_fixture(tmp_path)
    config = runner._full_mode_config(1, authority)
    identity = runner._attempt_identity(runner._attempt_preimage(config, catalog["catalog_sha256"], 0, None))
    receipt = runner._success_receipt(tmp_path, identity, {
        "timings": {"snapshot_open_elapsed_ns": 1, "child_elapsed_ns": 2},
        "owner_log_checkpoint": {"log_name": runner.OWNER_LOG, "upper_log_sequence": 1, "head_receipt_hash": "sha256:" + "1" * 64},
        "reader_set": {"reader_set_digest": "sha256:" + "2" * 64, "premium_reader_ids": []},
    })

    runner._validate_receipt(receipt, identity)
    assert identity["input_snapshot_authority"] == authority
    assert receipt["input_snapshot_authority"] == authority


def test_smoke_remains_zero_write_and_offline(tmp_path: Path) -> None:
    before = tuple(tmp_path.iterdir())
    result = runner.smoke(tmp_path)
    assert result["network_performed"] is False
    assert result["holdout_touched"] is False
    assert tuple(tmp_path.iterdir()) == before


def test_full_reader_uses_verified_member_bytes_not_working_tree_paths() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    full_body = source[source.index("def _child_full_preflight("):source.index("def _same_owner_log_cover(")]
    assert "open_input_snapshot_authority" in full_body
    assert "staging / \"input\"" not in full_body
    assert "member_bytes" in source


@dataclass(frozen=True)
class _TinySourceRequest:
    timeline_window_start: object
    timeline_window_end_exclusive: object
    request_hash: str


@dataclass(frozen=True)
class _TinySourceProjection:
    fragment_digest: str
    request: _TinySourceRequest


def _tiny_source_projection() -> _TinySourceProjection:
    return _TinySourceProjection(
        "sha256:" + "3" * 64,
        _TinySourceRequest(
            runner.UtcInstant(runner.START_MS * 1_000_000),
            runner.UtcInstant(runner.END_MS * 1_000_000),
            "sha256:" + "4" * 64,
        ),
    )


def _publish_tiny_source_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, dict[str, object], dict[str, object]]:
    raw_root, raw_authority, _catalog = _published_fixture(tmp_path)
    source = _tiny_source_projection()
    source_bytes = runner.canonical_bytes(runner.ArtifactEnvelope.create(
        "binance_usdm_koru_tradifi_source_projection_authority_v1", 1, {"fixture": "tiny"},
    ))
    built: list[object] = []

    def build(*, phase_completed: Callable[[str, dict[str, int]], None] | None = None) -> _TinySourceProjection:
        assert runner._RAW_INPUT_VIEW is not None
        if phase_completed is not None:
            for phase in runner.SOURCE_PROJECTION_PHASES[1:7]:
                phase_completed(phase, {"synthetic_input_count": 1})
        built.append(object())
        return source

    monkeypatch.setattr(runner, "build_source", build)
    monkeypatch.setattr(runner, "serialize_binance_usdm_koru_tradifi_source_projection_authority_v1", lambda value: source_bytes)
    monkeypatch.setattr(runner, "open_binance_usdm_koru_tradifi_source_projection_authority_v1", lambda value: source if value == source_bytes else pytest.fail("unexpected source bytes"))
    monkeypatch.setattr(runner, "_verify_koru_discovery_snapshot_scope", lambda _catalog, _view: runner._fixed_koru_discovery_scope())

    root = runner._prepare_source_projection_publication_root(tmp_path / "source-publications")
    identity = runner._source_projection_identity(raw_authority, "fixture-source-v1")
    paths = runner._source_projection_paths(root, "fixture-source-v1")
    runner._create_new_json(paths["identity"], identity)
    paths["staging"].mkdir(parents=True)
    runner._publish_source_projection_in_staging(paths["staging"], identity, raw_root)
    authority, checkpoint = runner._validate_source_projection_complete(paths["staging"], identity)
    os.rename(paths["staging"], paths["published"])
    runner._create_new_json(paths["receipt"], runner._source_projection_success_receipt(identity, authority, checkpoint))

    assert len(built) == 1
    return root, authority, raw_authority


def test_source_projection_publication_binds_fixed_scope_raw_snapshot_and_owner_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, authority, raw_authority = _publish_tiny_source_projection(tmp_path, monkeypatch)

    opened = runner.open_koru_source_projection_authority(root, authority)
    foundation = runner.LocalFoundation(
        runner._source_projection_paths(root, authority["publication_attempt_id"])["published"] / "foundation"
    )
    entries = foundation.entries(runner.SOURCE_PROJECTION_LOG)

    assert opened == _tiny_source_projection()
    assert authority["raw_snapshot_authority"] == raw_authority
    assert authority["discovery_scope"] == runner._fixed_koru_discovery_scope()
    assert len(entries) == 1
    assert runner._source_projection_publication_fact(authority) == json.loads(entries[0].payload)


@pytest.mark.parametrize("tamper", ["source_ref", "source_envelope", "owner_log_missing", "owner_log_substitute"])
def test_source_projection_open_rejects_tampered_artifact_or_exact_owner_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tamper: str,
) -> None:
    root, authority, _raw_authority = _publish_tiny_source_projection(tmp_path, monkeypatch)
    paths = runner._source_projection_paths(root, authority["publication_attempt_id"])
    foundation_root = paths["published"] / "foundation"
    foundation = runner.LocalFoundation(foundation_root)
    if tamper == "source_ref":
        authority = copy.deepcopy(authority)
        authority["source_projection_authority_ref"]["content_hash"] = "sha256:" + "0" * 64
    elif tamper == "source_envelope":
        ref = authority["source_projection_authority_ref"]
        artifact = foundation_root / "artifacts" / "sha256" / ref["content_hash"][7:9] / ref["content_hash"][7:]
        artifact.write_bytes(b"{}")
    elif tamper == "owner_log_missing":
        (foundation_root / "registries" / f"{runner.SOURCE_PROJECTION_LOG}.jsonl").unlink()
    else:
        registry = foundation_root / "registries" / f"{runner.SOURCE_PROJECTION_LOG}.jsonl"
        registry.unlink()
        foundation.append(runner.SOURCE_PROJECTION_LOG, "substitute", b"{}")

    with pytest.raises(ValueError):
        runner.open_koru_source_projection_authority(root, authority)


def test_source_projection_rejects_raw_mismatch_and_partial_holdout_before_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_root, authority, _catalog = _published_fixture(tmp_path)
    changed = copy.deepcopy(authority)
    changed["manifest_ref"]["content_hash"] = "sha256:" + "0" * 64
    built: list[object] = []
    monkeypatch.setattr(runner, "build_source", lambda: built.append(object()))

    with pytest.raises(ValueError):
        runner.publish_koru_source_projection_authority(raw_root, changed, tmp_path / "publications", "mismatch")
    assert built == []

    manifest_ref = authority["manifest_ref"]
    manifest_path = raw_root / "artifacts" / "sha256" / manifest_ref["content_hash"][7:9] / manifest_ref["content_hash"][7:]
    manifest_path.write_bytes(b"{}")
    with pytest.raises(ValueError):
        runner.publish_koru_source_projection_authority(raw_root, authority, tmp_path / "publications", "manifest-tamper")
    assert built == []


def _write_self_hashed_manifest(path: Path, value: dict[str, object]) -> None:
    value = {**value, "manifest_sha256": ""}
    value["manifest_sha256"] = runner._hash(runner._canonical_json(value))
    path.write_bytes(runner._canonical_json(value))


def _published_snapshot_with_unreferenced_holdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, dict[str, object]]:
    source_data = runner.DATA
    data = tmp_path / "reduced" / "data"
    authority_root = data / "public_preflight_sources_v1"
    shutil.copytree(source_data / "public_preflight_sources_v1", authority_root)
    interval = {
        "start_ms": runner.START_MS,
        "end_ms_exclusive": runner.END_MS,
        "start_utc_inclusive": "2026-07-15T10:00:00.000Z",
        "end_utc_exclusive": "2026-08-24T11:00:00.000Z",
        "semantics": "half-open",
    }
    _write_self_hashed_manifest(data / "execution_data_manifest.json", {
        "backtest_authority_interval": interval, "files": [],
    })
    _write_self_hashed_manifest(data / "manifest.json", {})
    _write_self_hashed_manifest(data / "execution_gap_impact.json", {})
    (data / "binance_mark_raw.csv").write_bytes((source_data / "binance_mark_raw.csv").read_bytes())
    (data / "binance_index_raw.csv").write_bytes((source_data / "binance_index_raw.csv").read_bytes())
    holdout_path = "data/holdout/KORUUSDT-2026-08-25.csv"
    holdout = data.parent / holdout_path
    holdout.parent.mkdir(parents=True)
    holdout.write_bytes((source_data / "binance_mark_raw.csv").read_bytes())
    monkeypatch.setattr(runner, "DATA", data)
    monkeypatch.setattr(runner, "AUTHORITY_ROOT", authority_root)
    monkeypatch.setattr(runner, "AUTHORITY_MANIFEST", authority_root / "manifest.json")
    monkeypatch.setattr(runner, "EXECUTION_MANIFEST", data / "execution_data_manifest.json")
    monkeypatch.setattr(runner, "BASE_MANIFEST", data / "manifest.json")
    monkeypatch.setattr(runner, "GAP_AUDIT", data / "execution_gap_impact.json")

    catalog = runner._build_input_catalog(runner._raw_snapshot_catalog_config())
    assert set(runner._snapshot_member_mapping(catalog).values()) == runner._allowed_koru_discovery_input_member_cover()
    catalog["files"] = sorted([
        *catalog["files"],
        {"path": holdout_path, "sha256": runner._hash(holdout.read_bytes()), "size_bytes": holdout.stat().st_size},
    ], key=lambda row: row["path"])
    catalog["catalog_sha256"] = runner._catalog_digest(catalog)
    member_keys = runner._snapshot_member_mapping(catalog)
    raw_snapshot_root = tmp_path / "raw-snapshot-foundation"
    publication = runner.publish_raw_blob_snapshot(
        runner.LocalFoundation(raw_snapshot_root),
        members=tuple(
            runner.RawBlobSnapshotSourceMember(
                member_keys[row["path"]], (data.parent / row["path"]).read_bytes(), "0644",
            )
            for row in catalog["files"]
        ),
        provenance={
            "type": runner.RAW_SNAPSHOT_PROVENANCE_SCHEMA,
            "schema_version": 1,
            "input_catalog": catalog,
            "member_keys": member_keys,
        },
    )
    return raw_snapshot_root, runner._input_snapshot_authority(publication, catalog)


def test_full_preflight_rejects_unreferenced_holdout_before_child_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_snapshot_root, authority = _published_snapshot_with_unreferenced_holdout(tmp_path, monkeypatch)
    attempt_root = tmp_path / "attempts"
    monkeypatch.setattr(runner, "build_source", lambda: pytest.fail("source build must not start"))
    monkeypatch.setattr(runner.subprocess, "Popen", lambda *_args, **_kwargs: pytest.fail("child must not start"))

    with pytest.raises(ValueError, match="exact KORU discovery member cover"):
        runner.full_preflight(
            attempt_root, 1, input_snapshot_authority=authority, raw_snapshot_foundation_root=raw_snapshot_root,
        )

    assert not attempt_root.exists()


def test_source_projection_rejects_unreferenced_holdout_raw_member_before_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_snapshot_root, authority = _published_snapshot_with_unreferenced_holdout(tmp_path, monkeypatch)
    monkeypatch.setattr(runner, "build_source", lambda: pytest.fail("source build must not start"))
    publication_root = tmp_path / "source-projections"

    with pytest.raises(ValueError, match="exact KORU discovery member cover"):
        runner.publish_koru_source_projection_authority(raw_snapshot_root, authority, publication_root, "holdout")

    assert not publication_root.exists()


def test_source_projection_timeout_and_non_success_receipts_have_no_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_root, authority, _catalog = _published_fixture(tmp_path)
    monkeypatch.setattr(runner, "_verify_koru_discovery_snapshot_scope", lambda _catalog, _view: runner._fixed_koru_discovery_scope())

    timeout = runner.publish_koru_source_projection_authority(
        raw_root, authority, tmp_path / "timeout-publications", "timeout", max_seconds=1,
        _child_test_mode=runner._SOURCE_PUBLICATION_TIMEOUT_TEST_MODE,
    )
    failed = runner.publish_koru_source_projection_authority(
        raw_root, authority, tmp_path / "failed-publications", "failed", max_seconds=1,
        _child_test_mode=runner._SOURCE_PUBLICATION_FAILURE_TEST_MODE,
    )

    assert timeout["outcome"] == "timeout"
    assert failed["outcome"] == "non_success"
    assert timeout["final_authority"] == failed["final_authority"] == []
    assert tuple((tmp_path / "timeout-publications" / "source-projections").iterdir()) == ()
    assert tuple((tmp_path / "failed-publications" / "source-projections").iterdir()) == ()


@pytest.mark.parametrize("phase", runner.SOURCE_PROJECTION_PHASES)
def test_source_projection_timeout_receipt_records_monotonic_phase_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str,
) -> None:
    raw_root, authority, _catalog = _published_fixture(tmp_path)
    monkeypatch.setattr(runner, "_verify_koru_discovery_snapshot_scope", lambda _catalog, _view: runner._fixed_koru_discovery_scope())

    receipt = runner.publish_koru_source_projection_authority(
        raw_root, authority, tmp_path / "publications", f"timeout-{phase}", max_seconds=1,
        _child_test_mode=runner._SOURCE_PUBLICATION_TIMEOUT_AFTER_PHASE_TEST_PREFIX + phase,
    )

    progress = receipt["diagnostic_progress"]
    completed = progress["completed_phases"]
    assert receipt["outcome"] == "timeout"
    assert receipt["final_authority"] == []
    assert completed == list(runner.SOURCE_PROJECTION_PHASES[:len(completed)])
    assert completed[-1] == phase
    assert progress["current_phase"] == (
        "complete" if phase == runner.SOURCE_PROJECTION_PHASES[-1]
        else runner.SOURCE_PROJECTION_PHASES[runner.SOURCE_PROJECTION_PHASES.index(phase) + 1]
    )
    elapsed = [progress["completed_elapsed_ns"][completed_phase] for completed_phase in completed]
    assert elapsed == sorted(elapsed)
    assert progress["snapshot_authority_identity"] == authority
    assert progress["input_counts"]["synthetic_completed_phase_count"] == len(completed)
    runner._validate_source_projection_receipt(receipt, receipt["identity"])


def test_source_projection_operation_is_offline_and_stops_before_economics() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    body = source[source.index("def _publish_source_projection_in_staging("):source.index("def _validate_source_projection_complete(")]
    assert "with _raw_input_snapshot_context" in body
    assert "publish_koru_tradifi_economics_bundle_v3" not in body
    assert "build_koru_premium_reader_set_v1" not in body
    assert "Experiment" not in body
