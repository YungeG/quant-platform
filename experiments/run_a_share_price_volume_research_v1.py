"""Synthetic-only D009 adapter and read-only frozen-file replay.

Run from the repository root with ``python -m experiments.run_a_share_price_volume_research_v1``.
There is deliberately no real Reader, reservation, training Owner or financial engine.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
import time as clock
from collections import Counter
from collections.abc import Sequence
from dataclasses import replace
from datetime import date, datetime, time, timedelta
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

from experiments import a_share_price_volume_research_v1 as core

MAX_SECONDS = 120
MAX_BYTES = 32 * 1024 * 1024
REVISION = "D009-v1.1-SYNTHETIC-ONLY"
DESIGN_SHA256 = "277f441848f200991df1b68f245996744892fbda7693a163bad9854867c9ec03"
INSTRUMENTS = ("000001.XSHE", "600001.XSHG")
BASE_FIELDS = (
    "sample_key",
    "instrument_id",
    "decision_session",
    "as_of",
    "dataset_revision",
    "partition",
)
FEATURE_FIELDS = BASE_FIELDS + (
    "r5",
    "r20",
    "a20",
    "ma20",
    "ma60",
    "trend",
    "industry_up",
    "rv",
    "nv",
    "price_valid",
    "reasons",
)
LABEL_FIELDS = BASE_FIELDS + (
    "y",
    "gain_5d",
    "trend_at_5d",
    "label_end",
    "label_available_at",
    "end_change",
    "adverse_change",
    "min_close_over_ma20",
    "reasons",
    "target_defined",
)
PREDICTION_FIELDS = (
    BASE_FIELDS
    + (
        "model_identity",
        "price_cell",
        "nv",
        "shuffled_nv",
        "trend",
        "industry_up",
        "rv",
    )
    + tuple("p_" + m for m in core.MODELS)
    + ("price_fallback", "pv_fallback", "shuffled_fallback")
)
EVALUATION_FIELDS = (
    PREDICTION_FIELDS
    + tuple("label_" + f for f in LABEL_FIELDS[len(BASE_FIELDS) :])
    + ("in_F", "in_E", "active_pv")
)
WEEK_FIELDS = (
    (
        "partition",
        "week",
        "decision_session",
        "mother_count",
        "r5_known_count",
        "up_candidate_count",
        "price_valid_count",
        "exclusion_reasons",
        "state",
        "half",
        "f_count",
        "e_count",
        "active_f_count",
        "active_e_count",
    )
    + tuple("brier_" + m for m in core.MODELS)
    + (
        "delta",
        "coverage_f",
        "coverage_e",
        "label_observability",
        "censor_low",
        "censor_high",
    )
)
EXPECTED_FILES = tuple(
    sorted(
        (
            "plan.json",
            "synthetic-source.json",
            "data-manifest.json",
            "read-admission.json",
            "feature-rows.csv",
            "label-rows.csv",
            "sample-exclusions.csv",
            "model-cards/frozen.json",
            *("model-cards/" + m + ".json" for m in core.MODELS),
            *("predictions-" + p + ".csv" for p in core.PARTITIONS),
            "predictions.csv",
            "predictions.json",
            "evaluation-rows.csv",
            "calendar-week-rows.csv",
            "diagnostics.json",
            "report.md",
            "execution-order.json",
            "execution-status.json",
            "file-manifest.json",
        )
    )
)


def _require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise core.ResearchContractError(code, message)


def _no_symlink(path: Path) -> None:
    _require(
        not any(p.is_symlink() for p in (path, *path.parents)),
        "SYMLINK_REJECTED",
        str(path),
    )


def _new_root(path: Path) -> Path:
    root = path.absolute()
    _no_symlink(root)
    _require(
        not root.exists(),
        "OUTPUT_CONFLICT",
        "output root must be new, including for another synthetic attempt",
    )
    root.parent.mkdir(parents=True, exist_ok=True)
    root.mkdir()
    (root / "model-cards").mkdir()
    return root


def _save(root: Path, relative: str, data: bytes, started: float) -> None:
    path = root / relative
    _no_symlink(path)
    _require(
        clock.monotonic() - started < MAX_SECONDS,
        "SYNTHETIC_TIME_CAP",
        "stop; no retry or cap extension",
    )
    used = sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
    _require(
        used + len(data) <= MAX_BYTES,
        "SYNTHETIC_STORAGE_CAP",
        "stop; preserve partial outputs",
    )
    try:
        with path.open("xb") as stream:
            stream.write(data)
    except FileExistsError as error:
        raise core.ResearchContractError("OUTPUT_CONFLICT", str(path)) from error


def _save_json(root: Path, relative: str, value: Any, started: float) -> None:
    _save(root, relative, core.canonical_bytes(value), started)


def _cell(value: Any) -> str:
    if value is None:
        return ""
    value = core.json_value(value)
    return (
        value
        if isinstance(value, str)
        else json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
    )


def _csv_bytes(fields: tuple[str, ...], rows: Sequence[dict[str, Any]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({f: _cell(row.get(f)) for f in fields})
    return stream.getvalue().encode("utf-8")


def _base(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "sample_key": core.identity(row["key"]),
        **row["key"],
        "partition": row["partition"],
    }


def _feature(row: dict[str, Any]) -> dict[str, Any]:
    return {**_base(row), **{f: row[f] for f in FEATURE_FIELDS[len(BASE_FIELDS) :]}}


def _label(row: dict[str, Any]) -> dict[str, Any]:
    return {**_base(row), **{f: row[f] for f in LABEL_FIELDS[len(BASE_FIELDS) :]}}


def _prediction(row: dict[str, Any], model_identity: str) -> dict[str, Any]:
    return {
        **_base(row),
        "model_identity": model_identity,
        **{
            f: row[f]
            for f in (
                "price_cell",
                "nv",
                "shuffled_nv",
                "trend",
                "industry_up",
                "rv",
                "price_fallback",
                "pv_fallback",
                "shuffled_fallback",
            )
        },
        **{
            "p_" + model: p
            for model, p in zip(core.MODELS, row["probabilities"], strict=True)
        },
    }


def _model_file(cards: dict[str, Any], model: str) -> dict[str, Any]:
    field = {
        "PRICE_ONLY": "price_cells",
        "PRICE_VOLUME": "volume_cells",
        "SHUFFLED_VOLUME": "shuffled_cells",
    }.get(model)
    return {
        "synthetic": True,
        "model": model,
        "model_identity": core.identity(cards),
        "plan_identity": cards["plan_identity"],
        "training_cutoff": cards["training_cutoff"],
        "training_count": cards["training_count"],
        "training_weeks": cards["training_weeks"],
        "thresholds": cards["thresholds"],
        "smoothing": 20,
        "support_rows": core.MIN_ROWS,
        "support_weeks": core.MIN_CELL_WEEKS,
        "seed": 2 if model == "SHUFFLED_VOLUME" else 0,
        "climatology_estimate": cards["climatology_estimate"],
        "climatology_probability": cards["climatology_probability"],
        "cells": cards[field] if field else [],
        "training_shuffle": cards["training_shuffle"],
    }


def _recipe(smoke: bool) -> dict[str, Any]:
    return {
        "kind": "SYNTHETIC_ONLY",
        "revision": REVISION,
        "start": "2000-01-03",
        "weeks": (2, 2, 16) if smoke else core.MIN_WEEKS,
        "instruments": INSTRUMENTS,
        "calendar": "Monday-Friday; artificial, no actual holiday inference",
        "warmup_sessions": 65,
        "tail_sessions": 5,
        "seed": 0,
        "price": "100 + accumulated daily changes; phases alternate 2 rising and 2 falling weeks",
        "daily_changes": (Decimal(".4"), Decimal(".4"), Decimal("-.1"), Decimal("-.1")),
        "stock_phase_offsets": (0, 2),
        "phase_volumes": (50, 200, 100, 100),
        "quantity_unit": "synthetic_share",
        "industry_close": "1000 + .1 * session_index",
        "limits": "artificial close * 1.1 / .9; not real exchange limits",
        "membership": "both synthetic members throughout each read interval; not PIT market evidence",
        "availability": "procedural synthetic event/availability at 15:00 on session; acquisition fixed 2060-01-01",
    }


def make_synthetic_plan(*, smoke: bool = False) -> core.Plan:
    """Short intervals change no support, horizon, fit, bin or resampling gate."""
    recipe = _recipe(smoke)
    source = core.identity(recipe)
    start = date(2000, 1, 3)
    splits = []
    for partition, weeks in zip(core.PARTITIONS, recipe["weeks"], strict=True):
        decision_from = start + timedelta(weeks=13)
        decision_to = decision_from + timedelta(weeks=weeks)
        read_to = decision_to + timedelta(weeks=1)
        splits.append(core.Split(partition, start, read_to, decision_from, decision_to))
        start = read_to
    first = splits[0].read_from
    stamp = datetime.combine(first - timedelta(days=1), time(), core.SHANGHAI)
    acquired = datetime(2060, 1, 1, tzinfo=core.SHANGHAI)
    p = core.Provenance(REVISION, "synthetic_recipe", source, stamp, stamp, acquired)
    calendar = tuple(
        core.CalendarDay(
            first + timedelta(days=i), (first + timedelta(days=i)).weekday() < 5, p
        )
        for i in range((start - first).days)
    )
    return core.Plan(
        REVISION,
        (("synthetic_recipe", source),),
        calendar,
        tuple(splits),
        "SYNTHETIC ONLY: two artificial SH/SZ ordinary pharma members",
        True,
    )


def _provenance(plan: core.Plan, day: date) -> core.Provenance:
    stamp = datetime.combine(day, time(15), core.SHANGHAI)
    return core.Provenance(
        plan.dataset_revision,
        "synthetic_recipe",
        plan.source_hashes[0][1],
        stamp,
        stamp,
        datetime(2060, 1, 1, tzinfo=core.SHANGHAI),
    )


def _sessions(plan: core.Plan, split: core.Split) -> tuple[date, ...]:
    return tuple(
        d.day
        for d in plan.calendar
        if d.is_open and split.read_from <= d.day < split.read_to
    )


def _stock_bar(
    plan: core.Plan, sessions: tuple[date, ...], index: int, stock: int
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


def _decisions(plan: core.Plan, split: core.Split) -> tuple[tuple[date, int], ...]:
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


def _key(plan: core.Plan, session: date, stock: int) -> core.SampleKey:
    return core.SampleKey(
        INSTRUMENTS[stock],
        session,
        datetime.combine(session, time(23, 59, 59), core.SHANGHAI),
        plan.dataset_revision,
    )


def _feature_views(plan: core.Plan, split: core.Split) -> tuple[core.FeatureView, ...]:
    sessions = _sessions(plan, split)
    result = []
    for day, t in _decisions(plan, split):
        for stock in range(2):
            history = tuple(
                _stock_bar(plan, sessions, i, stock) for i in range(t - 64, t + 1)
            )
            with localcontext(core.CONTEXT):
                industry = tuple(
                    core.DailyBar(
                        sessions[i],
                        Decimal(1000) + Decimal(".1") * i,
                        _provenance(plan, sessions[i]),
                        comparable=True,
                    )
                    for i in range(t - 64, t + 1)
                )
            member = core.Membership(
                split.read_from,
                split.read_to,
                "XSHE" if stock == 0 else "XSHG",
                "801150",
                True,
                True,
                _provenance(plan, split.read_from),
            )
            result.append(
                core.FeatureView(
                    _key(plan, day, stock), split.partition, member, history, industry
                )
            )
    return tuple(sorted(result, key=lambda r: r.key))


def _outcome_views(plan: core.Plan, split: core.Split) -> tuple[core.OutcomeView, ...]:
    sessions = _sessions(plan, split)
    return tuple(
        sorted(
            (
                core.OutcomeView(
                    _key(plan, day, stock),
                    split.partition,
                    tuple(
                        _stock_bar(plan, sessions, i, stock)
                        for i in range(t - 64, t + 6)
                    ),
                )
                for day, t in _decisions(plan, split)
                for stock in range(2)
            ),
            key=lambda r: r.key,
        )
    )


def _week_grid(
    plan: core.Plan, features: core.FeatureRows
) -> tuple[core.WeekSlot, ...]:
    slots = []
    for split in plan.splits:
        sessions = _sessions(plan, split)
        week = split.decision_from
        while week < split.decision_to:
            opened = [
                day for day in sessions if week <= day < week + timedelta(weeks=1)
            ]
            rows = [
                r
                for r in features
                if r.partition == split.partition
                and core.week_key(r.key.decision_session) == week
                and "OUTSIDE_DECLARED_UNIVERSE" not in r.reasons
            ]
            reasons = Counter(reason for r in rows for reason in r.reasons)
            slots.append(
                core.WeekSlot(
                    split.partition,
                    week,
                    opened[-1] if opened else None,
                    len(rows),
                    sum(r.r5 is not None for r in rows),
                    sum(r.r5 is not None and r.r5 > 0 for r in rows),
                    sum(r.price_valid for r in rows),
                    tuple(sorted(reasons.items())),
                )
            )
            week += timedelta(weeks=1)
    return tuple(slots)


def _report(report: core.DiagnosticReport) -> str:
    lines = [
        "# D009 v1.1 — SYNTHETIC ONLY",
        "",
        "This validates the statistical Core and frozen-file adapter, NOT a real price-volume effect.",
        "No real market Reader, reservation, financial run, formal ValidationReport or trading permission.",
        "",
        f"Local synthetic statistical verdict: **{report.verdict}**.",
        "Reasons: " + (", ".join(report.verdict_reasons) or "none") + ".",
        "",
        "| Partition | G weeks | E weeks | F rows | E rows | coverage_E | coverage_F | Delta Brier |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for part in report.partitions:
        counts = dict(part.counts)
        lines.append(
            "| "
            + " | ".join(
                _cell(v) or "null"
                for v in (
                    part.partition,
                    counts.get("N_grid"),
                    counts.get("W_eff"),
                    counts.get("F_rows"),
                    counts.get("E_rows"),
                    part.coverage_e,
                    part.coverage_f,
                    part.delta,
                )
            )
            + " |"
        )
    for method in (report.bootstrap_4, report.bootstrap_13):
        lines.extend(
            (
                "",
                f"{method.block_length}-week physical-slot bootstrap: interval={_cell(method.interval) or 'null'}, invalid={method.invalid_count}/{core.BOOTSTRAP_DRAWS}, seed={method.seed}.",
            )
        )
    held = report.partitions[2]
    lines.extend(
        (
            "",
            f"Original-grid half deltas: {_cell(tuple(h.delta for h in held.halves))}.",
            f"Full-F binary-completion stress bounds: {_cell(held.censor_bounds)}; censor-sensitive={_cell(report.censor_sensitive) or 'null'}.",
            "",
            "See diagnostics.json for class/component counts, fixed calibration bins, support fallbacks, observability, coverage denominators and shuffle limitations.",
            "",
            "Both inputs and availability/membership/limits are procedural synthetic fixtures. The price baseline is coarse; daily volume proves neither control nor causality. Y is the composite five-session continuation label, not simply a gain probability. No holdout is claimed from real previously consumed data.",
            "",
            "Real execution remains PLAN_ONLY: finite source windows, PIT qualification, consumption history, a legitimate public consumer, and a new cumulative execution budget are missing. No user approval is implied by these files.",
            "",
        )
    )
    return "\n".join(lines)


def run_synthetic(
    output_root: Path, *, smoke: bool = False, command: tuple[str, ...] = ()
) -> dict[str, Any]:
    """One bounded attempt; all writes exclusive, partial outputs retained on error."""
    started = clock.monotonic()
    root = _new_root(output_root)
    stages: list[str] = []
    try:
        plan = make_synthetic_plan(smoke=smoke)
        _save_json(root, "synthetic-source.json", _recipe(smoke), started)
        code_hashes = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (Path(core.__file__), Path(__file__))
        }
        parameters = {
            "sampling": "last scheduled open session/week 23:59:59 Asia/Shanghai",
            "candidate": "R5 > 0",
            "trend": "close > MA20 > MA60 and MA20 > MA20[t-5]",
            "label": "future close > current close AND same trend at t+5",
            "horizon": core.HORIZON,
            "warmup": core.WARMUP,
            "models": core.MODELS,
            "volume": "mean(V[t-4:t])/mean(V[t-24:t-5]); NV=(RV<=1)",
            "auxiliary_rv": Decimal(".8"),
            "bins": "TRAIN lower medians R5/R20/A20; equality low, plus T/I",
            "smoothing": 20,
            "support_rows": core.MIN_ROWS,
            "support_weeks": core.MIN_CELL_WEEKS,
            "min_effective_weeks": core.MIN_WEEKS,
            "held_out_min_class_weeks": 12,
            "relative_brier_gate": Decimal(".02"),
            "bootstrap": {
                "draws": core.BOOTSTRAP_DRAWS,
                "lengths": (4, 13),
                "seeds": (1, 3),
                "grid": "complete physical natural weeks, noncircular, no invalid redraw",
                "percentile_indices": (24, 974),
            },
            "shuffle_seed": 2,
            "master_seed": 0,
            "decimal_precision": 28,
            "rounding": "ROUND_HALF_EVEN",
            "probability_places": 12,
        }
        _save_json(
            root,
            "plan.json",
            {
                "synthetic": True,
                "state": "SYNTHETIC_ONLY",
                "objective": "validate incremental volume information beyond declared PRICE_ONLY for the composite continuation label",
                "design_sha256": DESIGN_SHA256,
                "core_plan": plan,
                "parameters": parameters,
                "code_sha256": code_hashes,
                "cap": {
                    "attempts": 1,
                    "seconds": MAX_SECONDS,
                    "storage_bytes": MAX_BYTES,
                    "real_authority": None,
                },
            },
            started,
        )
        _save_json(
            root,
            "read-admission.json",
            {
                "synthetic": True,
                "real_state": "DENIED_BEFORE_READER",
                "producer_ref": None,
                "reservation_ref": None,
                "qualification_refs": None,
                "real_reader_opened": False,
                "declared_synthetic_windows": plan.splits,
                "reasons": (
                    "NO_REAL_SOURCE_QUALIFICATION",
                    "NO_LEGITIMATE_STATISTICAL_CONSUMER",
                    "NO_NEW_REAL_EXECUTION_BUDGET",
                ),
                "permission": "None; procedural synthetic fixtures only, not a legal read admission",
            },
            started,
        )
        features: list[core.FeatureRow] = []
        labels: list[core.LabelRow] = []
        predictions: list[core.PredictionRows] = []
        stages.append("TRAIN_FEATURE_VIEW_OPENED")
        train_features = core.make_features(plan, _feature_views(plan, plan.splits[0]))
        features.extend(train_features)
        stages.append("TRAIN_LABEL_VIEW_OPENED_FOR_FIT")
        train_labels = core.make_labels(plan, _outcome_views(plan, plan.splits[0]))
        labels.extend(train_labels)
        cards = core.fit_models(plan, core.TrainPanel(train_features, train_labels))
        _save_json(root, "model-cards/frozen.json", cards, started)
        card_values = core.json_value(cards)
        for model in core.MODELS:
            _save_json(
                root,
                "model-cards/" + model + ".json",
                _model_file(card_values, model),
                started,
            )
        stages.append("MODEL_CARDS_FROZEN")
        for split in plan.splits:
            if split.partition == "TRAIN":
                rows = train_features
            else:
                stages.append(split.partition + "_FEATURE_VIEW_OPENED")
                rows = core.make_features(plan, _feature_views(plan, split))
                features.extend(rows)
            part_predictions = core.predict_models(plan, cards, rows)
            predictions.append(part_predictions)
            _save(
                root,
                "predictions-" + split.partition + ".csv",
                _csv_bytes(
                    PREDICTION_FIELDS,
                    [
                        _prediction(core.json_value(r), part_predictions.model_identity)
                        for r in part_predictions.rows
                    ],
                ),
                started,
            )
            stages.append(split.partition + "_PREDICTIONS_FROZEN")
        combined = core.PredictionRows(
            cards.plan_identity,
            core.identity(cards),
            cards.training_count,
            cards.training_weeks,
            tuple(
                sorted(
                    (r for part in predictions for r in part.rows), key=lambda r: r.key
                )
            ),
            tuple(s for part in predictions for s in part.shuffle),
        )
        expected_prediction_bytes = _csv_bytes(
            PREDICTION_FIELDS,
            [
                _prediction(core.json_value(r), combined.model_identity)
                for r in combined.rows
            ],
        )
        _save(root, "predictions.csv", expected_prediction_bytes, started)
        _save_json(root, "predictions.json", combined, started)
        stages.append("ALL_PREDICTIONS_FROZEN_BEFORE_EVALUATION_LABELS")
        # Score probabilities read back from the frozen CSV, not a new precision projection.
        disk_rows = list(
            csv.DictReader(
                io.StringIO((root / "predictions.csv").read_text(encoding="utf-8"))
            )
        )
        _require(
            (root / "predictions.csv").read_bytes() == expected_prediction_bytes,
            "FROZEN_PREDICTION_CONFLICT",
            "prediction file changed before evaluation",
        )
        scored_rows = []
        for pred, disk in zip(combined.rows, disk_rows, strict=True):
            ps = [Decimal(disk["p_" + model]) for model in core.MODELS]
            scored_rows.append(
                replace(pred, probabilities=(ps[0], ps[1], ps[2], ps[3]))
            )
        scored = replace(combined, rows=tuple(scored_rows))
        _require(
            core.identity(scored) == core.identity(combined),
            "FROZEN_PREDICTION_CONFLICT",
            "persisted probabilities changed identity",
        )
        for split in plan.splits[1:]:
            stages.append(
                split.partition + "_LABEL_VIEW_OPENED_AFTER_PREDICTION_FREEZE"
            )
            labels.extend(core.make_labels(plan, _outcome_views(plan, split)))
        frozen_features = tuple(sorted(features, key=lambda r: r.key))
        frozen_labels = tuple(sorted(labels, key=lambda r: r.key))
        grid = _week_grid(plan, frozen_features)
        report = core.evaluate_predictions(plan, scored, frozen_labels, grid)
        stages.append("PERSISTED_PROBABILITIES_EVALUATED_WITHOUT_REFIT")
        _save(
            root,
            "feature-rows.csv",
            _csv_bytes(
                FEATURE_FIELDS, [_feature(core.json_value(r)) for r in frozen_features]
            ),
            started,
        )
        _save(
            root,
            "label-rows.csv",
            _csv_bytes(
                LABEL_FIELDS, [_label(core.json_value(r)) for r in frozen_labels]
            ),
            started,
        )
        exclusions = [
            {**_base(core.json_value(row)), "view": view, "reason": reason}
            for view, rows in (("feature", frozen_features), ("label", frozen_labels))
            for row in rows
            for reason in row.reasons
        ]
        _save(
            root,
            "sample-exclusions.csv",
            _csv_bytes(BASE_FIELDS + ("view", "reason"), exclusions),
            started,
        )
        evaluations = []
        for evaluation in report.evaluation_rows:
            label_value = core.json_value(evaluation.label) if evaluation.label else {}
            evaluations.append(
                {
                    **_prediction(
                        core.json_value(evaluation.prediction), combined.model_identity
                    ),
                    **{
                        "label_" + f: label_value.get(f)
                        for f in LABEL_FIELDS[len(BASE_FIELDS) :]
                    },
                    "in_F": True,
                    "in_E": evaluation.evaluated,
                    "active_pv": evaluation.prediction.pv_fallback is None,
                }
            )
        _save(
            root,
            "evaluation-rows.csv",
            _csv_bytes(EVALUATION_FIELDS, evaluations),
            started,
        )
        week_rows = []
        for part in report.partitions:
            for week in part.weeks:
                value = core.json_value(week)
                week_rows.append(
                    {
                        **value["slot"],
                        **{
                            f: value[f]
                            for f in (
                                "state",
                                "half",
                                "f_count",
                                "e_count",
                                "active_f_count",
                                "active_e_count",
                                "delta",
                                "coverage_f",
                                "coverage_e",
                                "label_observability",
                                "censor_low",
                                "censor_high",
                            )
                        },
                        **{
                            "brier_" + m: p
                            for m, p in zip(core.MODELS, week.losses, strict=True)
                        },
                    }
                )
        _save(
            root, "calendar-week-rows.csv", _csv_bytes(WEEK_FIELDS, week_rows), started
        )
        _save_json(root, "diagnostics.json", report, started)
        _save(root, "report.md", _report(report).encode("utf-8"), started)
        _save_json(
            root,
            "data-manifest.json",
            {
                "synthetic": True,
                "dataset_revision": plan.dataset_revision,
                "universe": plan.universe_scope,
                "source_hashes": plan.source_hashes,
                "source_identity_kind": "SHA256 of persisted procedural synthetic recipe, NOT market data",
                "read_intervals": plan.splits,
                "units": {"close": "synthetic_price", "volume": "synthetic_share"},
                "availability_qualification_refs": None,
                "membership_qualification_refs": None,
                "prior_consumption_check": "not applicable to artificial fixtures; real history unknown",
                "mother_sample_rows": len(frozen_features),
                "feature_stock_bar_observations": len(frozen_features) * core.WARMUP,
                "feature_industry_bar_observations": len(frozen_features) * core.WARMUP,
                "label_stock_bar_observations": len(frozen_labels)
                * (core.WARMUP + core.HORIZON),
                "F_rows": len(combined.rows),
                "E_rows": sum(r.evaluated for r in report.evaluation_rows),
            },
            started,
        )
        _save_json(
            root,
            "execution-order.json",
            {
                "synthetic": True,
                "stages": stages,
                "fit_calls": 1,
                "real_readers": 0,
                "financial_runs": 0,
            },
            started,
        )
        _save_json(
            root,
            "execution-status.json",
            {
                "synthetic": True,
                "state": "OUTPUTS_FROZEN_PENDING_FILE_MANIFEST",
                "commit_rule": "complete only if file-manifest.json exists and verifies",
            },
            started,
        )
        files = {
            name: {
                "sha256": hashlib.sha256((root / name).read_bytes()).hexdigest(),
                "bytes": (root / name).stat().st_size,
            }
            for name in EXPECTED_FILES
            if name != "file-manifest.json"
        }
        manifest = {
            "synthetic": True,
            "state": "SYNTHETIC_COMPLETED",
            "format": "D009-v1.1-frozen-files",
            "files": files,
            "identities": {
                "plan": report.plan_identity,
                "model": report.model_identity,
                "predictions": report.predictions_identity,
                "calendar_grid": report.calendar_grid_identity,
            },
            "command": command,
            "python_version": sys.version.split()[0],
            "elapsed_seconds": Decimal(str(clock.monotonic() - started)),
            "cap": {"attempts": 1, "seconds": MAX_SECONDS, "storage_bytes": MAX_BYTES},
            "authenticity": "local byte consistency only; neither signed nor Owner-authenticated",
        }
        _save_json(root, "file-manifest.json", manifest, started)
        return manifest
    except Exception as error:
        # Do not overwrite, delete, retry, unlock or make an incomplete root replayable.
        failure = {
            "synthetic": True,
            "state": "LOCAL_BLOCKED",
            "stage": stages[-1] if stages else "INITIALIZATION",
            "error_code": getattr(error, "code", type(error).__name__),
            "elapsed_seconds": Decimal(str(clock.monotonic() - started)),
            "real_readers": 0,
            "financial_runs": 0,
        }
        try:
            with (root / "failure.json").open("xb") as stream:
                stream.write(core.canonical_bytes(failure))
        except OSError as recording_error:
            error.add_note(f"Could not persist failure metadata: {recording_error}")
        raise


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        _require(key not in result, "MALFORMED_JSON", "duplicate JSON key")
        result[key] = value
    return result


def _read_json(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    try:
        value = json.loads(data, object_pairs_hook=_unique_object)
        _require(
            isinstance(value, dict) and core.canonical_bytes(value) == data,
            "MALFORMED_JSON",
            "expected canonical JSON object",
        )
        return value
    except (ValueError, TypeError, UnicodeError) as error:
        if isinstance(error, core.ResearchContractError):
            raise
        raise core.ResearchContractError("MALFORMED_JSON", str(path)) from error


def replay(output_root: Path) -> str:
    """Verify bounded frozen-file consistency and emit stored text; no inference."""
    root = output_root.absolute()
    _no_symlink(root)
    _require(root.is_dir(), "INCOMPLETE_OUTPUT", "missing frozen output root")
    files = []
    used = 0
    for parent, dirs, names in root.walk(follow_symlinks=False):
        for name in (*dirs, *names):
            _no_symlink(parent / name)
        _require(
            all(parent == root and name == "model-cards" for name in dirs),
            "INCOMPLETE_OUTPUT",
            "unexpected directory outside frozen set",
        )
        for name in names:
            path = parent / name
            _require(
                path.relative_to(root).as_posix() in EXPECTED_FILES,
                "INCOMPLETE_OUTPUT",
                "unexpected file outside frozen set",
            )
            _require(path.is_file(), "UNEXPECTED_OUTPUT", "regular files only")
            used += path.stat().st_size
            _require(
                used <= MAX_BYTES and len(files) < len(EXPECTED_FILES),
                "REPLAY_STORAGE_CAP",
                "unexpected or oversized evidence",
            )
            files.append(path.relative_to(root).as_posix())
    _require(
        tuple(sorted(files)) == EXPECTED_FILES,
        "INCOMPLETE_OUTPUT",
        "missing, extra or uncommitted output",
    )
    manifest = _read_json(root / "file-manifest.json")
    _require(
        manifest.get("synthetic") is True
        and manifest.get("state") == "SYNTHETIC_COMPLETED"
        and manifest.get("format") == "D009-v1.1-frozen-files",
        "REPLAY_IDENTITY_CONFLICT",
        "only this synthetic frozen-file format is replayable",
    )
    entries = manifest.get("files")
    if not isinstance(entries, dict):
        raise core.ResearchContractError(
            "REPLAY_IDENTITY_CONFLICT", "file manifest must be an object"
        )
    _require(
        set(entries) == set(EXPECTED_FILES) - {"file-manifest.json"},
        "REPLAY_IDENTITY_CONFLICT",
        "exact file manifest required",
    )
    for name in EXPECTED_FILES:
        if name == "file-manifest.json":
            continue
        data = (root / name).read_bytes()
        _require(
            isinstance(entries[name], dict)
            and entries[name].get("bytes") == len(data)
            and entries[name].get("sha256") == hashlib.sha256(data).hexdigest(),
            "FILE_HASH_CONFLICT",
            name,
        )
    plan = _read_json(root / "plan.json")
    cards = _read_json(root / "model-cards/frozen.json")
    predictions = _read_json(root / "predictions.json")
    diagnostics = _read_json(root / "diagnostics.json")
    _require(
        plan.get("synthetic") is True
        and plan["core_plan"].get("synthetic") is True
        and plan.get("design_sha256") == DESIGN_SHA256,
        "REPLAY_IDENTITY_CONFLICT",
        "not this declared synthetic plan",
    )
    ids = {
        "plan": core.identity(plan["core_plan"]),
        "model": core.identity(cards),
        "predictions": core.identity(predictions),
        "calendar_grid": core.identity(
            [
                week["slot"]
                for part in diagnostics["partitions"]
                for week in part["weeks"]
            ]
        ),
    }
    _require(
        manifest.get("identities") == ids
        and cards.get("plan_identity") == ids["plan"]
        and predictions.get("plan_identity") == ids["plan"]
        and predictions.get("model_identity") == ids["model"]
        and all(
            diagnostics.get(name + "_identity") == value
            for name, value in (
                ("plan", ids["plan"]),
                ("model", ids["model"]),
                ("predictions", ids["predictions"]),
                ("calendar_grid", ids["calendar_grid"]),
            )
        ),
        "REPLAY_IDENTITY_CONFLICT",
        "plan/model/prediction/grid cross-bindings disagree",
    )
    _require(
        plan["core_plan"]["source_hashes"]
        == [
            [
                "synthetic_recipe",
                hashlib.sha256(
                    (root / "synthetic-source.json").read_bytes()
                ).hexdigest(),
            ]
        ],
        "REPLAY_IDENTITY_CONFLICT",
        "source recipe identity mismatch",
    )
    for model in core.MODELS:
        _require(
            _read_json(root / ("model-cards/" + model + ".json"))
            == core.json_value(_model_file(cards, model)),
            "REPLAY_IDENTITY_CONFLICT",
            "model card projection disagrees",
        )
    expected = _csv_bytes(
        PREDICTION_FIELDS,
        [_prediction(row, ids["model"]) for row in predictions["rows"]],
    )
    _require(
        (root / "predictions.csv").read_bytes() == expected,
        "REPLAY_IDENTITY_CONFLICT",
        "prediction CSV is not the frozen probability projection",
    )
    for partition in core.PARTITIONS:
        expected = _csv_bytes(
            PREDICTION_FIELDS,
            [
                _prediction(row, ids["model"])
                for row in predictions["rows"]
                if row["partition"] == partition
            ],
        )
        _require(
            (root / ("predictions-" + partition + ".csv")).read_bytes() == expected,
            "REPLAY_IDENTITY_CONFLICT",
            "partition prediction projection disagrees",
        )
    return (root / "report.md").read_text(encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--synthetic", action="store_true")
    modes.add_argument("--replay", type=Path)
    modes.add_argument(
        "--real",
        action="store_true",
        help="always denied before output creation/Reader",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="synthetic 2/2/16-week intervals; scientific gates unchanged",
    )
    args = parser.parse_args(argv)
    try:
        _require(
            not args.real,
            "REAL_EXECUTION_NOT_READY",
            "P0 source qualification, legitimate consumer and new cumulative budget are missing; no Reader opened",
        )
        if args.replay is not None:
            _require(
                args.output is None and not args.smoke,
                "INVALID_MODE",
                "replay is strictly read-only",
            )
            print(replay(args.replay), end="")
        else:
            _require(
                args.output is not None,
                "INVALID_MODE",
                "an explicit new output root is required",
            )
            run_synthetic(
                args.output,
                smoke=args.smoke,
                command=tuple(argv) if argv is not None else tuple(sys.argv[1:]),
            )
            print((args.output / "report.md").read_text(encoding="utf-8"), end="")
        return 0
    except (
        core.ResearchContractError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        print(f"LOCAL_BLOCKED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
