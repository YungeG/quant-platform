from __future__ import annotations

import copy
import importlib.util
import sys
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


def test_timeout_attempt_has_no_input_tree_and_binds_snapshot_authority(tmp_path: Path) -> None:
    snapshot_root, authority, catalog = _published_fixture(tmp_path)
    attempt_root = tmp_path / "attempts"

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
