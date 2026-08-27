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


def test_production_script_has_no_network_or_backtest_runtime_private_imports() -> None:
    source = SCRIPT.read_text()

    assert "urllib.request" not in source
    assert "requests" not in source
    assert "crypto_quant_backtest" not in source
    assert "from tests." not in source
