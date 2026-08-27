from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "build_discovery_source_targets_v2.py"
SPEC = importlib.util.spec_from_file_location("build_discovery_source_targets_v2", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class Ref:
    def __init__(self, content_hash: str) -> None:
        self.content_hash = content_hash

    def to_canonical_dict(self) -> dict[str, object]:
        return {"content_hash": self.content_hash}


class Canonical:
    def __init__(self, name: str, event_count: int = 0) -> None:
        self.name = name
        self.event_count = event_count

    def to_canonical_dict(self) -> dict[str, object]:
        return {"name": self.name, "event_count": self.event_count}


def stream(states: tuple[bool, ...]):
    events = tuple(
        SimpleNamespace(
            event_hash=f"sha256:{index:064x}",
            payload={
                "candidate": {
                    "targets": ({"value": "0.1" if state else "0"},)
                }
            },
        )
        for index, state in enumerate(states, 1)
    )
    return SimpleNamespace(
        parameter_ref=Ref("sha256:" + "1" * 64),
        stream_key="stream",
        target_stream_digest="sha256:" + "2" * 64,
        events=events,
    )


def test_manifest_self_hash_and_gap_boundary_fixture_are_exact() -> None:
    for path in (builder.BASE_MANIFEST, builder.EXECUTION_MANIFEST, builder.GAP_AUDIT):
        builder.validate_self_hash(builder.load_json(path), path)

    boundaries = builder.validate_gap_audit(builder.load_json(builder.GAP_AUDIT))

    assert len(boundaries) == 611
    assert boundaries == tuple(
        sorted(boundaries, key=lambda value: value.boundary.epoch_nanoseconds)
    )


def test_accepted_funding_and_calendar_unit_fixtures_replay_offline() -> None:
    execution = builder.load_json(builder.EXECUTION_MANIFEST)
    files = builder._files(execution)
    funding, funding_summary = builder._funding_result(execution, files)
    authority, authority_summary = builder._authority_result(
        builder.load_json(builder.GAP_AUDIT)
    )

    assert funding.normalization_hash == (
        "sha256:27a6d00659b9d3a27647f850fff97cfebd5630895ba6dc09243b741e9f297631"
    )
    assert funding_summary["authority_source"] == (
        "accepted_backtest_funding_fixture_byte_exact_mirror"
    )
    assert authority_summary["source_snapshot_id"] == (
        "sha256:f4c5e93cc274e9e5ea6ba52f79d90900fff3963a2c569b4c5b97a0668e76e838"
    )
    assert [ref.content_hash for ref in authority.refs] == [
        "sha256:dcffef007cd8a9c00319259663c32cd09812904562229b3a2084d03718624d35",
        "sha256:d9a75b431730740b6e5793f99a71978513422ed78f6dd7bda4485f20a75a9926",
        "sha256:dca20ef381e3e95469e7507d422430317e471677a1d2450b188a918cbb146e18",
    ]


def test_retained_aug24_authorities_reconstruct_with_accepted_operations() -> None:
    execution = builder.load_json(builder.EXECUTION_MANIFEST)
    base = builder.load_json(builder.BASE_MANIFEST)
    files = builder._files(execution)
    aggregate, aggregate_summary = builder._retained_aggregate_capture(execution, files)
    mark, mark_summary = builder._retained_price_result(
        builder.BinanceUsdmKoruPriceBarsSourceKindV1.MARK_PRICE,
        execution,
        base,
        files,
    )

    assert aggregate.capture_hash == aggregate_summary["capture_hash"]
    assert mark.projected_row_count == 11
    assert mark_summary["repository_derived_artifacts"]["zip_sha256"] != (
        mark_summary["accepted_capture_evidence"]["zip_sha256"]
    )


def test_target_stream_validation_fails_closed() -> None:
    valid = SimpleNamespace(
        streams=(stream((True, False)),) + tuple(stream(()) for _ in range(7))
    )
    assert len(builder.validate_target_streams(valid)) == 8

    nonalternating = SimpleNamespace(
        streams=(stream((True, True, False)),) + tuple(stream(()) for _ in range(7))
    )
    with pytest.raises(ValueError, match="nonalternating or nonflat"):
        builder.validate_target_streams(nonalternating)

    nonflat = SimpleNamespace(
        streams=(stream((True,)),) + tuple(stream(()) for _ in range(7))
    )
    with pytest.raises(ValueError, match="nonalternating or nonflat"):
        builder.validate_target_streams(nonflat)


def test_profile_and_bundle_summaries_retain_canonical_flags_and_limitations() -> None:
    hash_value = "sha256:" + "3" * 64
    profile = SimpleNamespace(
        request=SimpleNamespace(request_hash=hash_value),
        result_digest=hash_value,
        profile_composition_request_hash=hash_value,
        resolved_profile=Canonical("resolved"),
        profile_registry=Canonical("registry"),
        financial_dispatcher_spec=Canonical("dispatcher"),
        source_profile_authority_hash=hash_value,
        source_profile_authority_ref=Ref(hash_value),
        source_stream_hashes=(("source", hash_value),),
        source_stream_counts=(("source", 2),),
        source_authority_verified=True,
        limitations=("development_profile", "deployment_unauthorized"),
    )
    profile_value = builder.profile_summary(profile)

    assert profile_value["source_event_count"] == 2
    assert profile_value["source_authority_verified"] is True
    assert profile_value["limitations"] == [
        "development_profile",
        "deployment_unauthorized",
    ]

    stream_manifest = Canonical("stream", event_count=2)
    manifest = SimpleNamespace(
        bundle_key="development-v2-test",
        schema_version=2,
        content_hash=hash_value,
        streams=(stream_manifest,),
        to_canonical_dict=lambda: {"content_hash": hash_value},
    )
    bundle_ref = Ref(hash_value)
    bundle_ref.bundle_key = "development-v2-test"
    reader = SimpleNamespace(
        bundle_ref=bundle_ref,
        manifest=manifest,
        streams={"stream": (Canonical("event"),)},
    )
    bundle = SimpleNamespace(
        request=SimpleNamespace(
            request_hash=hash_value,
            to_canonical_dict=lambda: {"limitations": ("development_only",)},
        ),
        result_digest=hash_value,
        bundle_ref=bundle_ref,
        manifest=manifest,
        reader=reader,
        authority_refs=(Ref(hash_value),),
        authority_artifacts=(
            SimpleNamespace(
                artifact_type="source_profile_authority",
                schema_version=2,
                content_hash=hash_value,
            ),
        ),
        development_only=True,
        deployment_authorized=False,
    )
    bundle_value = builder.bundle_summary(bundle)

    assert bundle_value["event_count_total"] == 2
    assert bundle_value["development_only"] is True
    assert bundle_value["deployment_authorized"] is False
    assert bundle_value["limitations"] == ["development_only"]


def test_production_script_has_no_network_or_private_fixture_imports() -> None:
    source = SCRIPT.read_text()

    assert "urllib.request" not in source
    assert "requests" not in source
    assert "from crypto_quant_backtest." not in source
    assert "from tests." not in source
