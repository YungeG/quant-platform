from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import shutil
import socket
import sys
import time
from pathlib import Path
from types import SimpleNamespace

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


def _full_owner_records() -> tuple[object, object, object, tuple[dict[str, object], ...]]:
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


def test_full_deadline_fails_closed_without_a_success_summary(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path,
) -> None:
    monkeypatch.setattr(runner, "smoke", lambda _root=None: {})

    def block_before_full_data() -> object:
        time.sleep(1.1)
        raise AssertionError("deadline did not interrupt before full retained data")

    monkeypatch.setattr(runner, "build_source", block_before_full_data)

    assert runner.main(["--full", "--max-seconds", "1", "--foundation-root", str(tmp_path / "foundation")]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "full preflight deadline exceeded after 1 seconds" in captured.err
    assert not (tmp_path / "foundation").exists()


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
