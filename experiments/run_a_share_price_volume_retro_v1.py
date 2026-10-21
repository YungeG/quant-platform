"""RETRO-V1 code-only fixture adapter. Real data is refused before any output I/O.

Use python -m experiments.run_a_share_price_volume_retro_v1 --help.
Replay verifies bounded local byte consistency; it does not refit or authenticate owners.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time as clock
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import date, datetime, time, timedelta
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

from experiments import a_share_price_volume_retro_v1 as core

MAX_SECONDS = 120
MAX_BYTES = 32 * 1024 * 1024
REVISION = "RETRO-V1-PROCEDURAL-FIXTURE"
CLOCK_BASIS = "SIMULATED_FIXTURE_CLOCK_NOT_WALL_CLOCK"
INSTRUMENTS = ("000001.XSHE", "600001.XSHG")
EXPECTED_FILES = (
    "file-manifest.json",
    "model-cards.json",
    "packet.json",
    "predictions.json",
    "report.md",
)
STAGES = (
    "TRAIN_FEATURES",
    "TRAIN_LABELS_FOR_FIT",
    "MODEL_CARDS_FROZEN",
    "TRAIN_PREDICTIONS",
    "DEVELOPMENT_FEATURES",
    "DEVELOPMENT_PREDICTIONS",
    "RETROSPECTIVE_EVAL_FEATURES",
    "RETROSPECTIVE_EVAL_PREDICTIONS",
    "ALL_PREDICTIONS_FROZEN",
    "DEVELOPMENT_LABELS_AFTER_FREEZE",
    "RETROSPECTIVE_EVAL_LABELS_AFTER_FREEZE",
    "EVALUATED_WITHOUT_REFIT",
)


def recipe(short: bool = False) -> dict[str, Any]:
    return {
        "kind": "PROCEDURAL_SYNTHETIC_FIXTURE_NOT_MARKET_DATA",
        "revision": REVISION,
        "start": "2000-01-03",
        "weeks": (2, 2, 16) if short else core.MIN_WEEKS,
        "instruments": INSTRUMENTS,
        "calendar": "artificial Monday-Friday, no holiday authority",
        "warmup_sessions": 65,
        "tail_sessions": 5,
        "daily_changes": (Decimal(".4"), Decimal(".4"), Decimal("-.1"), Decimal("-.1")),
        "phase_volumes": (50, 200, 100, 100),
        "phase_offsets": (0, 2),
        "snapshot_observed_at": "2060-01-01T00:00:00+08:00",
        "historical_provider_availability": None,
        "classification": "artificial fixed post-hoc cohort, not historical membership",
    }


def make_fixture_plan(*, short: bool = False) -> core.RetrospectivePlan:
    value = recipe(short)
    digest = core.identity(value)
    observed = datetime(2060, 1, 1, tzinfo=core.SHANGHAI)
    first = date(2000, 1, 3)
    cursor = first
    splits = []
    for role, weeks in zip(core.RETRO_PARTITIONS, value["weeks"], strict=True):
        decision_from = cursor + timedelta(weeks=13)
        decision_to = decision_from + timedelta(weeks=weeks)
        read_to = decision_to + timedelta(weeks=1)
        splits.append(core.Split(role, cursor, read_to, decision_from, decision_to))
        cursor = read_to
    event = datetime.combine(first, time(), core.SHANGHAI)
    provenance = core.SnapshotProvenance(
        REVISION, "synthetic_recipe", digest, event, observed, observed, None
    )
    calendar = tuple(
        core.CalendarDay(
            first + timedelta(days=i),
            (first + timedelta(days=i)).weekday() < 5,
            provenance,
        )
        for i in range((cursor - first).days)
    )
    return core.RetrospectivePlan(
        REVISION,
        (("synthetic_recipe", digest),),
        calendar,
        tuple(splits),
        "SYNTHETIC fixed two-stock cohort; no real/PIT industry assertion",
        observed,
        INSTRUMENTS,
        True,
        tuple(
            core.SnapshotClassification(
                instrument,
                instrument.rsplit(".", 1)[1],
                "801150",
                True,
                True,
                replace(provenance, event_time=observed),
            )
            for instrument in INSTRUMENTS
        ),
    )


def _sessions(plan: core.RetrospectivePlan, split: core.Split) -> tuple[date, ...]:
    return tuple(
        row.day
        for row in plan.calendar
        if row.is_open and split.read_from <= row.day < split.read_to
    )


def _provenance(plan: core.RetrospectivePlan, day: date) -> core.SnapshotProvenance:
    return core.SnapshotProvenance(
        plan.dataset_revision,
        "synthetic_recipe",
        plan.source_hashes[0][1],
        datetime.combine(day, time(15), core.SHANGHAI),
        plan.snapshot_observed_at,
        plan.snapshot_observed_at,
        None,
    )


def _bar(
    plan: core.RetrospectivePlan, sessions: tuple[date, ...], index: int, stock: int
) -> core.DailyBar:
    with localcontext(core.CONTEXT):
        increments = tuple(
            Decimal(".4") if (i // 5 + stock * 2) % 4 < 2 else Decimal("-.1")
            for i in range(20)
        )
        count = index + 1
        close = (
            Decimal(100)
            + Decimal(count // 20) * sum(increments, core.ZERO)
            + sum(increments[: count % 20], core.ZERO)
        )
        phase = (index // 5 + stock * 2) % 4
        return core.DailyBar(
            sessions[index],
            close,
            _provenance(plan, sessions[index]),
            Decimal((50, 200, 100, 100)[phase]),
            "synthetic_share",
            True,
            False,
            True,
            close * Decimal("1.1"),
            close * Decimal(".9"),
        )


def _decisions(
    plan: core.RetrospectivePlan, split: core.Split
) -> tuple[tuple[date, int], ...]:
    sessions = _sessions(plan, split)
    return tuple(
        (day, i)
        for i, day in enumerate(sessions)
        if split.decision_from <= day < split.decision_to
        and not any(
            core.week_key(later) == core.week_key(day)
            for later in sessions[i + 1 : i + 6]
        )
    )


def _key(
    plan: core.RetrospectivePlan, day: date, stock: int
) -> core.RetrospectiveSampleKey:
    return core.RetrospectiveSampleKey(
        INSTRUMENTS[stock],
        day,
        datetime.combine(day, time(23, 59, 59), core.SHANGHAI),
        plan.dataset_revision,
    )


def fixture_feature_views(
    plan: core.RetrospectivePlan, split: core.Split
) -> tuple[core.FeatureView, ...]:
    sessions = _sessions(plan, split)
    result = []
    for day, index in _decisions(plan, split):
        for stock in range(2):
            history = tuple(
                _bar(plan, sessions, i, stock) for i in range(index - 64, index + 1)
            )
            with localcontext(core.CONTEXT):
                industry = tuple(
                    core.DailyBar(
                        sessions[i],
                        Decimal(1000) + Decimal(".1") * i,
                        _provenance(plan, sessions[i]),
                        comparable=True,
                    )
                    for i in range(index - 64, index + 1)
                )
            classification = plan.cohort_classifications[stock]
            result.append(
                core.FeatureView(
                    _key(plan, day, stock),
                    split.partition,
                    classification,
                    history,
                    industry,
                )
            )
    return tuple(sorted(result, key=lambda row: row.key))


def fixture_outcome_views(
    plan: core.RetrospectivePlan, split: core.Split
) -> tuple[core.OutcomeView, ...]:
    sessions = _sessions(plan, split)
    return tuple(
        sorted(
            (
                core.OutcomeView(
                    _key(plan, day, stock),
                    split.partition,
                    tuple(
                        _bar(plan, sessions, i, stock)
                        for i in range(index - 64, index + 6)
                    ),
                )
                for day, index in _decisions(plan, split)
                for stock in range(2)
            ),
            key=lambda row: row.key,
        )
    )


def fixture_week_grid(
    plan: core.RetrospectivePlan, features: core.FeatureRows
) -> tuple[core.WeekSlot, ...]:
    result = []
    for split in plan.splits:
        sessions = _sessions(plan, split)
        week = split.decision_from
        while week < split.decision_to:
            opened = [
                day for day in sessions if week <= day < week + timedelta(weeks=1)
            ]
            rows = [
                row
                for row in features
                if row.partition == split.partition
                and core.week_key(row.key.decision_session) == week
            ]
            reasons = Counter(reason for row in rows for reason in row.reasons)
            result.append(
                core.WeekSlot(
                    split.partition,
                    week,
                    opened[-1] if opened else None,
                    len(rows),
                    sum(row.r5 is not None for row in rows),
                    sum(row.r5 is not None and row.r5 > 0 for row in rows),
                    sum(row.price_valid for row in rows),
                    tuple(sorted(reasons.items())),
                )
            )
            week += timedelta(weeks=1)
    return tuple(result)


def build_retrospective_packet(
    *, short: bool = False, on_freeze: Callable[[str, bytes], None] | None = None
) -> dict[str, Any]:
    """Procedural fixture only. Optional publication callback is not a real Reader."""
    plan = make_fixture_plan(short=short)
    stages = []
    source = recipe(short)
    features = []
    labels = []
    predictions = []
    moment = plan.snapshot_observed_at
    publish = on_freeze if on_freeze is not None else lambda name, body: None
    stages.append("TRAIN_FEATURES")
    train_features = core.make_retrospective_features(
        plan, fixture_feature_views(plan, plan.splits[0])
    )
    features.extend(train_features)
    stages.append("TRAIN_LABELS_FOR_FIT")
    train_labels = core.make_retrospective_labels(
        plan,
        fixture_outcome_views(plan, plan.splits[0]),
        computed_at=moment + timedelta(seconds=1),
    )
    labels.extend(train_labels)
    cards = core.fit_retrospective_models(
        plan,
        core.TrainPanel(train_features, train_labels),
        fitted_at=moment + timedelta(seconds=2),
    )
    publish("model-cards.json", core.canonical_bytes(cards))
    stages.append("MODEL_CARDS_FROZEN")
    for split in plan.splits:
        if split.partition == "TRAIN":
            rows = train_features
        else:
            stages.append(split.partition + "_FEATURES")
            rows = core.make_retrospective_features(
                plan, fixture_feature_views(plan, split)
            )
            features.extend(rows)
        result = core.predict_retrospective_models(
            plan, cards, rows, predicted_at=moment + timedelta(seconds=3)
        )
        predictions.append(result)
        stages.append(split.partition + "_PREDICTIONS")
    combined = core.PredictionRows(
        cards.plan_identity,
        core.identity(cards),
        cards.training_count,
        cards.training_weeks,
        moment + timedelta(seconds=3),
        tuple(
            sorted(
                (row for part in predictions for row in part.rows),
                key=lambda row: row.key,
            )
        ),
        tuple(value for part in predictions for value in part.shuffle),
        tuple(
            sorted(
                (entry for part in predictions for entry in part.feature_scope),
                key=lambda entry: entry[1],
            )
        ),
        core._all_facts(tuple(part.feature_facts for part in predictions)),
    )
    frozen = core.canonical_bytes(combined)
    publish("predictions.json", frozen)
    stages.append("ALL_PREDICTIONS_FROZEN")
    # Score the exact serialized p12 values, without fitting or projecting again.
    disk = json.loads(frozen)
    scored_rows = tuple(
        replace(
            row, probabilities=tuple(Decimal(value) for value in saved["probabilities"])
        )
        for row, saved in zip(combined.rows, disk["rows"], strict=True)
    )
    scored = replace(combined, rows=scored_rows)
    if core.identity(scored) != core.identity(combined):
        raise core.RetrospectiveContractError(
            "FROZEN_PREDICTION_CONFLICT", "serialized probabilities changed"
        )
    for split in plan.splits[1:]:
        stages.append(split.partition + "_LABELS_AFTER_FREEZE")
        labels.extend(
            core.make_retrospective_labels(
                plan,
                fixture_outcome_views(plan, split),
                computed_at=moment + timedelta(seconds=4),
            )
        )
    frozen_features = tuple(sorted(features, key=lambda row: row.key))
    frozen_labels = tuple(sorted(labels, key=lambda row: row.key))
    grid = fixture_week_grid(plan, frozen_features)
    report = core.evaluate_retrospective_predictions(
        plan, scored, frozen_labels, grid, evaluated_at=moment + timedelta(seconds=5)
    )
    stages.append("EVALUATED_WITHOUT_REFIT")
    if tuple(stages) != STAGES or core.canonical_bytes(combined) != frozen:
        raise core.RetrospectiveContractError(
            "FREEZE_ORDER_CONFLICT", "fixture stages or predictions changed"
        )
    return {
        "format": "RETRO-V1-FIXTURE-PACKET",
        "fixture_only": True,
        "clock_basis": CLOCK_BASIS,
        "data_mode": "CURRENT_SNAPSHOT_RETROSPECTIVE",
        "untouched_claim": False,
        "causal_pit_claim": False,
        "source_qualified": False,
        "formal_validation_report": False,
        "recipe": source,
        "plan": plan,
        "features": frozen_features,
        "labels": frozen_labels,
        "models": cards,
        "predictions": combined,
        "calendar_grid": grid,
        "diagnostics": report,
        "execution_order": tuple(stages),
        "fit_calls": 1,
        "real_readers": 0,
        "http_requests": 0,
        "model_freeze_sha256": core.identity(cards),
        "prediction_freeze_sha256": hashlib.sha256(frozen).hexdigest(),
        "real_admission": "DENIED_NO_ACCEPTED_RETROSPECTIVE_CONSUMER_OR_EXECUTION_BUDGET",
    }


def render_retrospective_report(packet: dict[str, Any]) -> str:
    value = core.json_value(packet)
    report = value["diagnostics"]
    lines = [
        "# RETRO-V1 — SYNTHETIC ENGINEERING FIXTURE",
        "",
        "CURRENT_SNAPSHOT_RETROSPECTIVE / NOT_UNTOUCHED / NOT_CAUSAL_PIT",
        "This exercises local numerical/adapter contracts, not a real volume effect or a ValidationReport.",
        "Snapshot and computation stamps use a SIMULATED fixture clock, not actual wall-clock evidence.",
        "",
        f"Fixture verdict: **{report['verdict']}**.",
        "Reasons: " + (", ".join(report["verdict_reasons"]) or "none") + ".",
        "",
        "| Role | Effective weeks | F rows | E rows | coverage_E | Delta Brier |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for part in report["partitions"]:
        counts = dict(part["counts"])
        lines.append(
            "| "
            + " | ".join(
                str(item) if item is not None else "null"
                for item in (
                    part["partition"],
                    counts.get("W_eff"),
                    counts.get("F_rows"),
                    counts.get("E_rows"),
                    part["coverage_e"],
                    part["delta"],
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "Four controls, one fit; original support, effective-week and bootstrap rules remain unchanged.",
            "Historical session anchors are positions only. Unknown historical availability remains unknown; acquisition/observation/computation times are not backdated.",
            "The final role is RETROSPECTIVE_EVAL, never an untouched holdout. Snapshot revision/cohort and censoring bias remain explicit.",
            "Real data remains denied pending an accepted additive consumer contract, frozen inputs and a new finite execution package.",
            "",
        ]
    )
    return "\n".join(lines)


def _no_links(path: Path) -> None:
    if any(value.is_symlink() for value in (path, *path.parents)):
        raise core.RetrospectiveContractError(
            "SYMLINK_REJECTED", "ordinary owned paths only"
        )


def _save(root: Path, name: str, raw: bytes, start: float) -> None:
    _no_links(root / name)
    used = sum(value.stat().st_size for value in root.iterdir() if value.is_file())
    if clock.monotonic() - start >= MAX_SECONDS or used + len(raw) > MAX_BYTES:
        raise core.RetrospectiveContractError(
            "FIXTURE_RESOURCE_CAP", "preserve partial; no automatic retry"
        )
    with (root / name).open("xb") as stream:
        stream.write(raw)


def run_fixture(output: Path, *, short: bool = False) -> dict[str, Any]:
    start = clock.monotonic()
    root = output.absolute()
    _no_links(root)
    if root.exists():
        raise core.RetrospectiveContractError(
            "OUTPUT_CONFLICT", "new output root required"
        )
    root.parent.mkdir(parents=True, exist_ok=True)
    root.mkdir()
    try:
        packet = build_retrospective_packet(
            short=short, on_freeze=lambda name, raw: _save(root, name, raw, start)
        )
        _save(root, "packet.json", core.canonical_bytes(packet), start)
        _save(root, "report.md", render_retrospective_report(packet).encode(), start)
        entries = {
            name: {
                "sha256": hashlib.sha256((root / name).read_bytes()).hexdigest(),
                "bytes": (root / name).stat().st_size,
            }
            for name in EXPECTED_FILES
            if name != "file-manifest.json"
        }
        manifest = {
            "format": "RETRO-V1-FIXTURE-FILES",
            "state": "FIXTURE_COMPLETE",
            "fixture_only": True,
            "files": entries,
            "elapsed_seconds": Decimal(str(clock.monotonic() - start)),
            "limits": {"seconds": MAX_SECONDS, "bytes": MAX_BYTES},
            "identity_scope": "local byte consistency only, not signed or Owner-authenticated",
        }
        _save(root, "file-manifest.json", core.canonical_bytes(manifest), start)
        return manifest
    except Exception as error:
        failure = {
            "state": "LOCAL_BLOCKED",
            "fixture_only": True,
            "error_code": getattr(error, "code", type(error).__name__),
            "real_readers": 0,
        }
        with (root / "failure.json").open("xb") as stream:
            stream.write(core.canonical_bytes(failure))
        raise


def _read_json(path: Path) -> dict[str, Any]:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise core.RetrospectiveContractError(
                    "MALFORMED_PACKET", "duplicate JSON key"
                )
            result[key] = value
        return result

    raw = path.read_bytes()
    value = json.loads(raw, object_pairs_hook=unique)
    if not isinstance(value, dict) or core.canonical_bytes(value) != raw:
        raise core.RetrospectiveContractError(
            "MALFORMED_PACKET", "canonical object required"
        )
    return value


def replay_retrospective_packet(output: Path) -> str:
    root = output.absolute()
    _no_links(root)
    if not root.is_dir():
        raise core.RetrospectiveContractError(
            "INCOMPLETE_OUTPUT", "missing fixture root"
        )
    files = tuple(root.iterdir())
    if tuple(sorted(path.name for path in files)) != EXPECTED_FILES:
        raise core.RetrospectiveContractError(
            "INCOMPLETE_OUTPUT", "exact five-file fixture required"
        )
    for path in files:
        _no_links(path)
    if (
        any(not path.is_file() for path in files)
        or sum(path.stat().st_size for path in files) > MAX_BYTES
    ):
        raise core.RetrospectiveContractError(
            "REPLAY_RESOURCE_CAP", "bounded regular files only"
        )
    manifest = _read_json(root / "file-manifest.json")
    if (
        manifest.get("format") != "RETRO-V1-FIXTURE-FILES"
        or manifest.get("state") != "FIXTURE_COMPLETE"
        or manifest.get("fixture_only") is not True
    ):
        raise core.RetrospectiveContractError(
            "REPLAY_IDENTITY_CONFLICT", "only this fixture format is supported"
        )
    entries = manifest.get("files")
    if not isinstance(entries, dict) or set(entries) != set(EXPECTED_FILES) - {
        "file-manifest.json"
    }:
        raise core.RetrospectiveContractError(
            "REPLAY_IDENTITY_CONFLICT", "exact manifest required"
        )
    for name, item in entries.items():
        raw = (root / name).read_bytes()
        if (
            not isinstance(item, dict)
            or item.get("bytes") != len(raw)
            or item.get("sha256") != hashlib.sha256(raw).hexdigest()
        ):
            raise core.RetrospectiveContractError(
                "FILE_HASH_CONFLICT", "fixture file differs"
            )
    packet = _read_json(root / "packet.json")
    cards = _read_json(root / "model-cards.json")
    predictions = _read_json(root / "predictions.json")
    diagnostics = packet.get("diagnostics")
    if not isinstance(diagnostics, dict):
        raise core.RetrospectiveContractError(
            "REPLAY_IDENTITY_CONFLICT", "diagnostic object required"
        )
    if (
        packet.get("format") != "RETRO-V1-FIXTURE-PACKET"
        or packet.get("fixture_only") is not True
        or packet.get("clock_basis") != CLOCK_BASIS
        or packet.get("data_mode") != "CURRENT_SNAPSHOT_RETROSPECTIVE"
        or packet.get("untouched_claim") is not False
        or packet.get("causal_pit_claim") is not False
        or packet.get("source_qualified") is not False
        or packet.get("formal_validation_report") is not False
        or packet.get("real_readers") != 0
        or packet.get("http_requests") != 0
        or packet.get("fit_calls") != 1
        or packet.get("execution_order") != list(STAGES)
        or packet.get("model_freeze_sha256") != core.identity(cards)
        or packet.get("prediction_freeze_sha256") != core.identity(predictions)
        or packet.get("models") != cards
        or packet.get("predictions") != predictions
        or cards.get("plan_identity") != core.identity(packet.get("plan"))
        or predictions.get("model_identity") != core.identity(cards)
        or predictions.get("plan_identity") != core.identity(packet.get("plan"))
        or diagnostics.get("plan_identity") != core.identity(packet.get("plan"))
        or diagnostics.get("model_identity") != core.identity(cards)
        or diagnostics.get("predictions_identity") != core.identity(predictions)
        or diagnostics.get("calendar_grid_identity")
        != core.identity(packet.get("calendar_grid"))
        or diagnostics.get("data_mode") != "CURRENT_SNAPSHOT_RETROSPECTIVE"
        or diagnostics.get("untouched_claim") is not False
        or diagnostics.get("causal_pit_claim") is not False
        or packet.get("plan", {}).get("fixture_only") is not True
    ):
        raise core.RetrospectiveContractError(
            "REPLAY_IDENTITY_CONFLICT", "fixture bindings or interpretation changed"
        )
    report_text = (root / "report.md").read_text()
    if report_text != render_retrospective_report(packet):
        raise core.RetrospectiveContractError(
            "REPLAY_IDENTITY_CONFLICT", "human report differs from frozen diagnostics"
        )
    return report_text


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--synthetic", action="store_true")
    mode.add_argument("--replay", type=Path)
    mode.add_argument(
        "--real",
        action="store_true",
        help="always refused before output creation or a Reader",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--short",
        action="store_true",
        help="short fixture, not relaxed scientific gates",
    )
    args = parser.parse_args(argv)
    try:
        if args.real:
            raise core.RetrospectiveContractError(
                "REAL_EXECUTION_NOT_READY",
                "no accepted retrospective consumer, frozen input or real budget; no Reader opened",
            )
        if args.replay is not None:
            if args.output is not None or args.short:
                raise core.RetrospectiveContractError(
                    "INVALID_MODE", "replay is read-only"
                )
            print(replay_retrospective_packet(args.replay), end="")
        else:
            if args.output is None:
                raise core.RetrospectiveContractError(
                    "INVALID_MODE", "explicit new fixture output required"
                )
            run_fixture(args.output, short=args.short)
            print((args.output / "report.md").read_text(), end="")
        return 0
    except (
        core.RetrospectiveContractError,
        OSError,
        ValueError,
        KeyError,
        TypeError,
    ) as error:
        print(
            f"LOCAL_BLOCKED: {getattr(error, 'code', type(error).__name__)}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
