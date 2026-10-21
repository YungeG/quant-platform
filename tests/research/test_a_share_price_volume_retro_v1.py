"""Procedural SYNTHETIC DTOs only; never real market/credential/Owner fixtures."""

from __future__ import annotations

import ast
import hashlib
import json
import random
import shutil
from dataclasses import replace
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any, cast

import pytest

from experiments import a_share_price_volume_research_v1 as strict
from experiments import a_share_price_volume_retro_v1 as core
from experiments import run_a_share_price_volume_retro_v1 as runner

D = Decimal
MARKER = "d" * 64


def fail(*args: Any, **kwargs: Any) -> Any:
    raise AssertionError("forbidden I/O or numerical recomputation")


@pytest.fixture(scope="module")
def plan() -> core.RetrospectivePlan:
    return runner.make_fixture_plan(short=True)


@pytest.fixture(scope="module")
def packet() -> dict[str, Any]:
    return runner.build_retrospective_packet(short=True)


def number(value: Decimal | None) -> Decimal:
    assert value is not None
    return value


def classification(view: core.FeatureView) -> core.SnapshotClassification:
    assert view.classification is not None
    return view.classification


def manual_facts(
    plan: core.RetrospectivePlan, role: str, day, stock: int, *, outcome: bool = False
) -> tuple[core.PriceFact, ...]:
    split = next(split for split in plan.splits if split.partition == role)
    sessions = runner._sessions(plan, split)
    t = sessions.index(day)
    return tuple(
        core.PriceFact(runner.INSTRUMENTS[stock], session, MARKER)
        for session in sessions[t - 64 : t + 6 if outcome else t + 1]
    )


def manual_features(plan: core.RetrospectivePlan, role: str) -> core.FeatureRows:
    split = next(split for split in plan.splits if split.partition == role)
    return tuple(
        sorted(
            (
                core.FeatureRow(
                    runner._key(plan, day, stock),
                    role,
                    D(".02"),
                    D(".08"),
                    D(".01"),
                    D(100),
                    D(90),
                    True,
                    True,
                    D(".5") if stock else D("1.5"),
                    stock,
                    True,
                    stock_history_identity=core.identity(
                        manual_facts(plan, role, day, stock)
                    ),
                    price_facts=manual_facts(plan, role, day, stock),
                )
                for day, _ in runner._decisions(plan, split)
                for stock in range(2)
            ),
            key=lambda row: row.key,
        )
    )


def manual_labels(
    plan: core.RetrospectivePlan, features: core.FeatureRows
) -> core.LabelRows:
    rows = []
    for row in features:
        split = next(split for split in plan.splits if split.partition == row.partition)
        sessions = runner._sessions(plan, split)
        end = sessions[sessions.index(row.key.decision_session) + 5]
        y = row.nv
        assert y is not None
        stamp = plan.snapshot_observed_at + timedelta(
            seconds=1 if row.partition == "TRAIN" else 4
        )
        rows.append(
            core.LabelRow(
                row.key,
                row.partition,
                y,
                bool(y),
                bool(y),
                end,
                stamp,
                D(".03") if y else D("-.03"),
                D(0) if y else D("-.03"),
                D(".04"),
                stock_history_identity=row.stock_history_identity,
                price_facts=manual_facts(
                    plan,
                    row.partition,
                    row.key.decision_session,
                    runner.INSTRUMENTS.index(row.key.instrument_id),
                    outcome=True,
                ),
            )
        )
    return tuple(rows)


def manual_pipeline(plan: core.RetrospectivePlan):
    features = tuple(
        row for role in core.RETRO_PARTITIONS for row in manual_features(plan, role)
    )
    labels = manual_labels(plan, features)
    cards = core.fit_retrospective_models(
        plan,
        core.TrainPanel(
            tuple(row for row in features if row.partition == "TRAIN"),
            tuple(row for row in labels if row.partition == "TRAIN"),
        ),
        fitted_at=plan.snapshot_observed_at + timedelta(seconds=2),
    )
    predictions = core.predict_retrospective_models(
        plan,
        cards,
        features,
        predicted_at=plan.snapshot_observed_at + timedelta(seconds=3),
    )
    grid = runner.fixture_week_grid(plan, features)
    report = core.evaluate_retrospective_predictions(
        plan,
        predictions,
        labels,
        grid,
        evaluated_at=plan.snapshot_observed_at + timedelta(seconds=5),
    )
    return features, labels, cards, predictions, grid, report


def test_short_same_interface_is_insufficient_and_retains_unknown_history(
    packet,
) -> None:
    assert packet["diagnostics"].verdict == "insufficient"
    assert isinstance(packet["diagnostics"].bootstrap_4, core.BootstrapResult)
    assert all(
        isinstance(part, core.PartitionDiagnostics)
        for part in packet["diagnostics"].partitions
    )
    assert all(
        isinstance(week, core.WeekResult) and isinstance(week.slot, core.WeekSlot)
        for part in packet["diagnostics"].partitions
        for week in part.weeks
    )
    assert "TRAIN_WEEKS_LT_104" in packet["diagnostics"].verdict_reasons
    assert (
        packet["fit_calls"] == 1
        and packet["real_readers"] == packet["http_requests"] == 0
    )
    assert core.RETRO_PARTITIONS == ("TRAIN", "DEVELOPMENT", "RETROSPECTIVE_EVAL")
    assert core.MIN_WEEKS == (104, 26, 52) and core.BOOTSTRAP_DRAWS == 1000
    assert core.WARMUP == 65 and core.HORIZON == 5
    plan = packet["plan"]
    assert all(row.provenance.historical_available_at is None for row in plan.calendar)
    view = runner.fixture_feature_views(plan, plan.splits[0])[0]
    assert classification(view).provenance.observed_at > view.key.session_anchor
    assert all(
        bar.provenance.acquired_at > view.key.session_anchor for bar in view.stock
    )
    assert all(
        row.label_computed_at > row.key.session_anchor for row in packet["labels"]
    )
    assert (
        packet["diagnostics"].untouched_claim is False
        and packet["diagnostics"].causal_pit_claim is False
    )
    for flag in (
        "untouched_claim",
        "causal_pit_claim",
        "source_qualified",
        "formal_validation_report",
    ):
        assert packet[flag] is False
    assert "NOT_UNTOUCHED / NOT_CAUSAL_PIT" in runner.render_retrospective_report(
        packet
    )


def test_hand_calculated_rv_price_and_label(plan) -> None:
    views = runner.fixture_feature_views(plan, plan.splits[0])
    rows = core.make_retrospective_features(plan, views)
    view = views[0]
    row = rows[0]
    closes = [number(bar.close) for bar in view.stock]
    with localcontext(core.CONTEXT):
        assert row.r5 == closes[-1] / closes[-6] - 1
        assert row.r20 == closes[-1] / closes[-21] - 1
        assert row.rv == core._mean(
            tuple(number(bar.volume) for bar in view.stock[-5:])
        ) / core._mean(tuple(number(bar.volume) for bar in view.stock[-25:-5]))
        assert row.nv == int(number(row.rv) <= 1)
        outcome = runner.fixture_outcome_views(plan, plan.splits[0])
        labels = core.make_retrospective_labels(
            plan, outcome, computed_at=plan.snapshot_observed_at + timedelta(seconds=1)
        )
        future = outcome[0].stock[-5:]
        assert labels[0].gain_5d == (
            number(future[-1].close) > number(view.stock[-1].close)
        )
        label = labels[0]
        assert label.gain_5d is not None and label.trend_at_5d is not None
        assert label.y == int(label.gain_5d and label.trend_at_5d)
        assert labels[0].label_end == future[-1].session
        assert rows[0].stock_history_identity == labels[0].stock_history_identity


@pytest.mark.parametrize(
    "change,expected",
    [
        (
            {"event_time": datetime(2061, 1, 1, tzinfo=UTC)},
            "SNAPSHOT_TIME_INVALID",
        ),
        (
            {"acquired_at": datetime(1990, 1, 1, tzinfo=UTC)},
            "SNAPSHOT_TIME_INVALID",
        ),
        ({"observed_at": datetime(2050, 1, 1, tzinfo=None)}, "SNAPSHOT_TIME_INVALID"),  # noqa: DTZ001 -- intentional malformed timestamp
        (
            {"historical_available_at": datetime(1990, 1, 1, tzinfo=UTC)},
            "SNAPSHOT_TIME_INVALID",
        ),
        ({"raw_sha256": None}, "SOURCE_IDENTITY_CONFLICT"),
        ({"raw_sha256": "z" * 64}, "SOURCE_IDENTITY_CONFLICT"),
        ({"source": ""}, "SOURCE_IDENTITY_CONFLICT"),
    ],
)
def test_snapshot_metadata_never_coerces_missing_or_backdates(
    plan, change, expected
) -> None:
    with pytest.raises(core.RetrospectiveContractError, match=expected):
        replace(plan.calendar[0].provenance, **change)


def test_known_availability_is_retained_not_required_or_inferred(plan) -> None:
    value = plan.calendar[0].provenance
    known = replace(value, historical_available_at=value.event_time + timedelta(days=1))
    assert known.historical_available_at == value.event_time + timedelta(days=1)
    assert (
        value.historical_available_at is None and known.acquired_at == value.acquired_at
    )


@pytest.mark.parametrize(
    "kind,expected",
    [
        ("unknown_source", "SOURCE_IDENTITY_CONFLICT"),
        ("revision", "REVISION_CONFLICT"),
        ("observation", "SNAPSHOT_TIME_INVALID"),
        ("classification_instrument", "COHORT_CONFLICT"),
        ("classification_venue", "COHORT_CONFLICT"),
        ("cohort", "COHORT_CONFLICT"),
        ("anchor", "INVALID_SESSION_ANCHOR"),
        ("timezone", "TIMEZONE_MISMATCH"),
        ("overlap", "SPLIT_OVERLAP"),
    ],
)
def test_bounded_snapshot_plan_and_position_conflicts(plan, kind, expected) -> None:
    views = runner.fixture_feature_views(plan, plan.splits[0])
    view = views[0]
    changed_plan = plan
    if kind in ("unknown_source", "revision", "observation"):
        p = view.stock[0].provenance
        if kind == "unknown_source":
            p = replace(p, source="unregistered")
        elif kind == "revision":
            p = replace(p, revision="other")
        else:
            p = replace(p, observed_at=p.observed_at + timedelta(days=1))
        view = replace(
            view, stock=(replace(view.stock[0], provenance=p), *view.stock[1:])
        )
    elif kind.startswith("classification_"):
        value = (
            {"instrument_id": "600001.XSHG"}
            if kind.endswith("instrument")
            else {"venue": "XSHG"}
        )
        view = replace(view, classification=replace(classification(view), **value))
    elif kind == "cohort":
        changed_plan = replace(plan, cohort=("600001.XSHG",))
    elif kind == "anchor":
        view = replace(
            view,
            key=replace(
                view.key, session_anchor=view.key.session_anchor - timedelta(seconds=1)
            ),
        )
    elif kind == "timezone":
        view = replace(
            view,
            key=replace(
                view.key,
                session_anchor=view.key.session_anchor.astimezone(UTC),
            ),
        )
    else:
        a, b, c = plan.splits
        changed_plan = replace(plan, splits=(a, replace(b, read_from=a.read_from), c))
    with pytest.raises(core.RetrospectiveContractError, match=expected):
        core.make_retrospective_features(changed_plan, (view, *views[1:]))


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"volume": None}, "VOLUME_MISSING"),
        ({"listed": None}, "LISTING_OR_SUSPENSION_UNKNOWN"),
        ({"suspended": None}, "LISTING_OR_SUSPENSION_UNKNOWN"),
        ({"comparable": None}, "PRICE_SCALE_UNRESOLVED"),
        ({"close": None}, "PRICE_MISSING"),
        ({"quantity_unit": None}, "VOLUME_UNIT_MISMATCH"),
    ],
)
def test_unknown_inputs_stay_unknown_without_fill(plan, change, reason) -> None:
    views = runner.fixture_feature_views(plan, plan.splits[0])
    # Change a per-stock/per-session fact consistently in every overlapping view.
    instrument = views[0].key.instrument_id
    day = views[0].stock[-1].session
    changed = tuple(
        replace(
            view,
            stock=tuple(
                replace(bar, **change)
                if view.key.instrument_id == instrument and bar.session == day
                else bar
                for bar in view.stock
            ),
        )
        for view in views
    )
    row = core.make_retrospective_features(plan, changed)[0]
    assert reason in row.reasons and not row.predictable
    if change.get("close", "not-missing") is None:
        assert row.r5 is None


def test_zero_volume_is_not_missing_and_zero_baseline_is_distinct(plan) -> None:
    views = runner.fixture_feature_views(plan, plan.splits[0])
    cutoff = views[0].stock[-5].session
    zero_current = tuple(
        replace(
            view,
            stock=tuple(
                replace(bar, volume=D(0)) if bar.session >= cutoff else bar
                for bar in view.stock
            ),
        )
        for view in views
    )
    row = core.make_retrospective_features(plan, zero_current)[0]
    assert row.rv == 0 and row.nv == 1 and "VOLUME_MISSING" not in row.reasons
    all_zero = tuple(
        replace(view, stock=tuple(replace(bar, volume=D(0)) for bar in view.stock))
        for view in views
    )
    row = core.make_retrospective_features(plan, all_zero)[0]
    assert row.rv is None and "ZERO_VOLUME_BASELINE" in row.reasons


def test_classification_unknown_and_missing_limit_are_not_normal_state(plan) -> None:
    views = runner.fixture_feature_views(plan, plan.splits[0])
    unknown_plan = replace(
        plan,
        cohort_classifications=tuple(
            replace(item, ordinary_a_share=None) for item in plan.cohort_classifications
        ),
    )
    unknown = runner.fixture_feature_views(unknown_plan, unknown_plan.splits[0])
    assert (
        "CLASSIFICATION_UNKNOWN"
        in core.make_retrospective_features(unknown_plan, unknown)[0].reasons
    )
    no_limits = tuple(
        replace(
            view,
            stock=tuple(
                replace(bar, up_limit=None, down_limit=None) for bar in view.stock
            ),
        )
        for view in views
    )
    assert (
        "LIMIT_STATUS_UNKNOWN"
        in core.make_retrospective_features(plan, no_limits)[0].reasons
    )
    with pytest.raises(core.RetrospectiveContractError, match="CLASSIFICATION_INVALID"):
        replace(classification(views[0]), selected=1)


def test_future_feature_bar_is_rejected_and_future_outcomes_do_not_rewrite_features(
    plan,
) -> None:
    views = runner.fixture_feature_views(plan, plan.splits[0])
    outcome = runner.fixture_outcome_views(plan, plan.splits[0])[0]
    view = replace(views[0], stock=(*views[0].stock, outcome.stock[-1]))
    with pytest.raises(core.RetrospectiveContractError, match="FUTURE_IN_FEATURE_VIEW"):
        core.make_retrospective_features(plan, (view, *views[1:]))
    before = core.make_retrospective_features(plan, views)
    core.make_retrospective_labels(
        plan,
        runner.fixture_outcome_views(plan, plan.splits[0]),
        computed_at=plan.snapshot_observed_at + timedelta(seconds=1),
    )
    assert before == core.make_retrospective_features(plan, views)


@pytest.mark.parametrize("domain", ("stock", "industry"))
def test_overlapping_views_cannot_disagree_about_one_snapshot_fact(
    plan, domain
) -> None:
    views = list(runner.fixture_feature_views(plan, plan.splits[0]))
    view = views[1]
    bars = list(getattr(view, domain))
    bars[-1] = replace(bars[-1], close=number(bars[-1].close) + D(1))
    if domain == "stock":
        # The next week of this same stock overlaps the first week's t-close.
        view = views[2]
        bars = list(view.stock)
        day = views[0].stock[-1].session
        bars = [
            replace(bar, close=number(bar.close) + D(1)) if bar.session == day else bar
            for bar in bars
        ]
        views[2] = replace(view, stock=tuple(bars))
    else:
        views[1] = replace(view, industry=tuple(bars))
    with pytest.raises(core.RetrospectiveContractError, match="SNAPSHOT_FACT_CONFLICT"):
        core.make_retrospective_features(plan, tuple(views))


def test_label_history_mismatch_cannot_silently_train_another_target(plan) -> None:
    features = core.make_retrospective_features(
        plan, runner.fixture_feature_views(plan, plan.splits[0])
    )
    outcomes = runner.fixture_outcome_views(plan, plan.splits[0])
    # Change every repeated occurrence consistently inside the outcome batch;
    # the source metadata remains unchanged, so cross-batch binding is essential.
    instrument, day = outcomes[0].key.instrument_id, outcomes[0].key.decision_session
    changed = tuple(
        replace(
            view,
            stock=tuple(
                replace(bar, close=number(bar.close) + D(1))
                if view.key.instrument_id == instrument and bar.session == day
                else bar
                for bar in view.stock
            ),
        )
        for view in outcomes
    )
    labels = core.make_retrospective_labels(
        plan, changed, computed_at=plan.snapshot_observed_at + timedelta(seconds=1)
    )
    with pytest.raises(core.RetrospectiveContractError, match="SNAPSHOT_FACT_CONFLICT"):
        core.fit_retrospective_models(
            plan,
            core.TrainPanel(features, labels),
            fitted_at=plan.snapshot_observed_at + timedelta(seconds=2),
        )


def test_fixed_cohort_view_cannot_be_dropped_from_mother_sample(plan) -> None:
    views = runner.fixture_feature_views(plan, plan.splits[0])
    with pytest.raises(core.RetrospectiveContractError, match="INCOMPLETE_COHORT_GRID"):
        core.make_retrospective_features(plan, views[1:])
    missing = tuple(
        replace(view, stock=())
        if view.key.instrument_id == views[0].key.instrument_id
        else view
        for view in views
    )
    row = core.make_retrospective_features(plan, missing)[0]
    assert not row.predictable and "PRICE_MISSING" in row.reasons


@pytest.mark.parametrize("where", ("fit", "predict", "evaluate", "labels"))
def test_actual_computation_time_order_is_enforced(plan, packet, where) -> None:
    with pytest.raises(
        core.RetrospectiveContractError, match="COMPUTATION_TIME_INVALID"
    ):
        if where == "fit":
            core.fit_retrospective_models(
                plan,
                core.TrainPanel(
                    tuple(
                        row for row in packet["features"] if row.partition == "TRAIN"
                    ),
                    tuple(row for row in packet["labels"] if row.partition == "TRAIN"),
                ),
                fitted_at=plan.snapshot_observed_at,
            )
        elif where == "predict":
            core.predict_retrospective_models(
                plan,
                packet["models"],
                packet["features"],
                predicted_at=plan.snapshot_observed_at,
            )
        elif where == "labels":
            core.make_retrospective_labels(
                plan,
                runner.fixture_outcome_views(plan, plan.splits[0]),
                computed_at=plan.snapshot_observed_at - timedelta(seconds=1),
            )
        else:
            core.evaluate_retrospective_predictions(
                plan,
                packet["predictions"],
                packet["labels"],
                packet["calendar_grid"],
                evaluated_at=plan.snapshot_observed_at,
            )


@pytest.mark.parametrize("unknown", (False, True))
def test_outcomes_known_or_unknown_must_follow_prediction_freeze(
    plan, packet, unknown
) -> None:
    rows = []
    for row in packet["labels"]:
        if row.partition != "TRAIN":
            row = replace(row, label_computed_at=packet["predictions"].predicted_at)
            if unknown:
                row = replace(
                    row,
                    y=None,
                    gain_5d=None,
                    trend_at_5d=None,
                    reasons=("LABEL_UNOBSERVABLE",),
                )
        rows.append(row)
    with pytest.raises(
        core.RetrospectiveContractError, match="OUTCOME_BEFORE_PREDICTIONS"
    ):
        core.evaluate_retrospective_predictions(
            plan,
            packet["predictions"],
            tuple(rows),
            packet["calendar_grid"],
            evaluated_at=plan.snapshot_observed_at + timedelta(seconds=5),
        )


def test_evaluation_checks_feature_history_binding_even_for_censored_label(
    packet,
) -> None:
    labels = tuple(
        replace(
            row,
            stock_history_identity="f" * 64,
            y=None,
            gain_5d=None,
            trend_at_5d=None,
            reasons=("LABEL_UNOBSERVABLE",),
        )
        if row.key == packet["predictions"].rows[-1].key
        else row
        for row in packet["labels"]
    )
    with pytest.raises(core.RetrospectiveContractError, match="SNAPSHOT_FACT_CONFLICT"):
        core.evaluate_retrospective_predictions(
            packet["plan"],
            packet["predictions"],
            labels,
            packet["calendar_grid"],
            evaluated_at=packet["diagnostics"].evaluated_at,
        )


def test_missing_outcomes_do_not_change_F_and_week_grid_keeps_null_slots(
    packet,
) -> None:
    predictions = packet["predictions"]
    labels = tuple(
        row
        for row in packet["labels"]
        if row.partition != "RETROSPECTIVE_EVAL"
        or core.week_key(row.key.decision_session)
        != packet["plan"].splits[2].decision_from
    )
    report = core.evaluate_retrospective_predictions(
        packet["plan"],
        predictions,
        labels,
        packet["calendar_grid"],
        evaluated_at=packet["diagnostics"].evaluated_at,
    )
    before = packet["diagnostics"].partitions[2]
    after = report.partitions[2]
    assert dict(before.counts)["F_rows"] == dict(after.counts)["F_rows"]
    assert len(after.weeks) == 16 and after.weeks[0].delta is None
    assert len(report.bootstrap_4.values) == len(report.bootstrap_13.values) == 1000


def test_numeric_parity_with_independent_strict_synthetic_fixture_and_positive_gate() -> (
    None
):
    """A receives its own artificial historical-availability DTOs, never B sources."""
    plan = runner.make_fixture_plan(short=False)
    features, labels, cards, predictions, grid, report = manual_pipeline(plan)
    stamp = datetime.combine(
        plan.splits[0].read_from - timedelta(days=1), time(), strict.SHANGHAI
    )
    p = strict.Provenance(
        plan.dataset_revision,
        plan.source_hashes[0][0],
        plan.source_hashes[0][1],
        stamp,
        stamp,
        plan.snapshot_observed_at,
    )
    old = strict.Plan(
        plan.dataset_revision,
        plan.source_hashes,
        tuple(strict.CalendarDay(day.day, day.is_open, p) for day in plan.calendar),
        tuple(
            strict.Split(
                role,
                split.read_from,
                split.read_to,
                split.decision_from,
                split.decision_to,
            )
            for role, split in zip(strict.PARTITIONS, plan.splits, strict=True)
        ),
        "independent synthetic A parity fixture",
        True,
    )
    role_map: dict[str, str] = dict(
        zip(core.RETRO_PARTITIONS, strict.PARTITIONS, strict=True)
    )

    def key(row):
        k = row.key
        return strict.SampleKey(
            k.instrument_id, k.decision_session, k.session_anchor, k.dataset_revision
        )

    old_features = tuple(
        strict.FeatureRow(
            key(row),
            role_map[row.partition],
            row.r5,
            row.r20,
            row.a20,
            row.ma20,
            row.ma60,
            row.trend,
            row.industry_up,
            row.rv,
            row.nv,
            row.price_valid,
            row.reasons,
        )
        for row in features
    )
    old_labels = tuple(
        strict.LabelRow(
            key(row),
            role_map[row.partition],
            row.y,
            row.gain_5d,
            row.trend_at_5d,
            row.label_end,
            datetime.combine(cast(Any, row.label_end), time(15), strict.SHANGHAI),
            row.end_change,
            row.adverse_change,
            row.min_close_over_ma20,
        )
        for row in labels
    )
    old_cards = strict.fit_models(
        old,
        strict.TrainPanel(
            tuple(row for row in old_features if row.partition == "TRAIN"),
            tuple(row for row in old_labels if row.partition == "TRAIN"),
        ),
    )
    old_predictions = strict.predict_models(old, old_cards, old_features)
    old_grid = tuple(
        strict.WeekSlot(
            role_map[row.partition],
            row.week,
            row.decision_session,
            row.mother_count,
            row.r5_known_count,
            row.up_candidate_count,
            row.price_valid_count,
            row.exclusion_reasons,
        )
        for row in grid
    )
    old_report = strict.evaluate_predictions(old, old_predictions, old_labels, old_grid)
    assert core.json_value(cards.thresholds) == strict.json_value(old_cards.thresholds)
    assert core.json_value(cards.price_cells) == strict.json_value(
        old_cards.price_cells
    )
    assert core.json_value(cards.volume_cells) == strict.json_value(
        old_cards.volume_cells
    )
    assert tuple(row.probabilities for row in predictions.rows) == tuple(
        row.probabilities for row in old_predictions.rows
    )
    assert core.json_value(report.bootstrap_4) == strict.json_value(
        old_report.bootstrap_4
    )
    assert core.json_value(report.bootstrap_13) == strict.json_value(
        old_report.bootstrap_13
    )
    assert (
        report.verdict == "retrospective_incremental_association"
        and old_report.verdict == "incremental_in_declared_E"
    )
    assert (
        report.bootstrap_4.interval is not None
        and report.bootstrap_13.interval is not None
    )
    assert report.bootstrap_4.interval[0] > 0 and report.bootstrap_13.interval[0] > 0
    assert report.untouched_claim is False and report.causal_pit_claim is False
    assert strict.PARTITIONS == ("TRAIN", "DEVELOPMENT", "HELD_OUT")


def test_full_natural_grid_bootstrap_matches_null_preserving_reference() -> None:
    plan = runner.make_fixture_plan(short=True)
    grid = runner.fixture_week_grid(plan, manual_features(plan, "RETROSPECTIVE_EVAL"))
    grid = tuple(row for row in grid if row.partition == "RETROSPECTIVE_EVAL")
    values = tuple(None if i % 3 == 0 else D(i) / D(100) for i in range(len(grid)))
    # Physical noncircular starts; compare every draw, preserving original null positions.
    for block, seed in ((4, 1), (13, 3)):
        actual = core._bootstrap(values, block, seed)
        assert len(actual.values) == 1000
        rng = random.Random(seed)
        draws = []
        with localcontext(core.CONTEXT):
            for _ in range(1000):
                positions = []
                while len(positions) < len(values):
                    start = rng.randrange(len(values) - block + 1)
                    positions.extend(range(start, start + block))
                vals = [
                    values[i] for i in positions[: len(values)] if values[i] is not None
                ]
                draws.append(sum(vals, D(0)) / D(len(vals)) if vals else None)
        assert actual.values == tuple(draws)
        assert actual.invalid_count == sum(value is None for value in draws)
    invalid = core._bootstrap((None,) * 16, 4, 1)
    assert (
        invalid.invalid_count == 1000
        and invalid.interval is None
        and len(invalid.values) == 1000
    )


@pytest.fixture(scope="module")
def frozen(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("retro-v1-fixture") / "new"
    runner.run_fixture(root, short=True)
    return root


def snapshot(root: Path) -> dict[str, tuple[str, int]]:
    return {
        path.name: (
            hashlib.sha256(path.read_bytes()).hexdigest(),
            path.stat().st_mtime_ns,
        )
        for path in root.iterdir()
    }


def test_fixture_files_real_flags_replay_without_any_recomputation(
    frozen, monkeypatch
) -> None:
    before = snapshot(frozen)
    assert tuple(sorted(before)) == runner.EXPECTED_FILES
    packet = json.loads((frozen / "packet.json").read_bytes())
    prediction = json.loads((frozen / "predictions.json").read_bytes())
    assert all(
        set(row).isdisjoint({"y", "label_y", "label_computed_at"})
        for row in prediction["rows"]
    )
    assert packet["execution_order"] == list(runner.STAGES)
    for row in prediction["rows"]:
        assert all(len(value.split(".")[1]) == 12 for value in row["probabilities"])
    for name in (
        "make_retrospective_features",
        "make_retrospective_labels",
        "fit_retrospective_models",
        "predict_retrospective_models",
        "evaluate_retrospective_predictions",
    ):
        monkeypatch.setattr(core, name, fail)
    for name in (
        "build_retrospective_packet",
        "make_fixture_plan",
        "fixture_feature_views",
        "fixture_outcome_views",
    ):
        monkeypatch.setattr(runner, name, fail)
    assert (
        runner.replay_retrospective_packet(frozen) == (frozen / "report.md").read_text()
    )
    assert snapshot(frozen) == before


def test_physical_freeze_order_one_fit_and_determinism(
    tmp_path, frozen, monkeypatch
) -> None:
    root = tmp_path / "ordered"
    feature = runner.fixture_feature_views
    outcome = runner.fixture_outcome_views
    fit = core.fit_retrospective_models
    fits = 0

    def feature_views(plan, split):
        if split.partition != "TRAIN":
            assert (root / "model-cards.json").is_file()
        return feature(plan, split)

    def outcome_views(plan, split):
        if split.partition != "TRAIN":
            assert (root / "predictions.json").is_file()
            assert (root / "model-cards.json").is_file()
            assert "label_computed_at" not in (root / "predictions.json").read_text()
        return outcome(plan, split)

    def once(*args, **kwargs):
        nonlocal fits
        fits += 1
        assert fits == 1
        return fit(*args, **kwargs)

    monkeypatch.setattr(runner, "fixture_feature_views", feature_views)
    monkeypatch.setattr(runner, "fixture_outcome_views", outcome_views)
    monkeypatch.setattr(core, "fit_retrospective_models", once)
    runner.run_fixture(root, short=True)
    assert fits == 1
    for name in runner.EXPECTED_FILES:
        if name != "file-manifest.json":
            assert (root / name).read_bytes() == (frozen / name).read_bytes()


@pytest.mark.parametrize("kind", ("time", "bytes", "source"))
def test_failure_retains_nonreplayable_partial_no_retry(
    tmp_path, monkeypatch, kind
) -> None:
    root = tmp_path / kind
    code = "FIXTURE_RESOURCE_CAP"
    if kind == "time":
        monkeypatch.setattr(runner, "MAX_SECONDS", 0)
    elif kind == "bytes":
        monkeypatch.setattr(runner, "MAX_BYTES", 1)
    else:
        code = "SOURCE_IDENTITY_CONFLICT"

        def bad(*args, **kwargs):
            raise core.RetrospectiveContractError(code, "synthetic failure")

        monkeypatch.setattr(runner, "fixture_feature_views", bad)
    with pytest.raises(core.RetrospectiveContractError, match=code):
        runner.run_fixture(root, short=True)
    assert not (root / "file-manifest.json").exists()
    failure = json.loads((root / "failure.json").read_text())
    assert failure["error_code"] == code and failure["real_readers"] == 0
    with pytest.raises(core.RetrospectiveContractError, match="INCOMPLETE_OUTPUT"):
        runner.replay_retrospective_packet(root)


@pytest.mark.parametrize(
    "change,code",
    [
        ("probability", "FILE_HASH_CONFLICT"),
        ("extra", "INCOMPLETE_OUTPUT"),
        ("missing", "INCOMPLETE_OUTPUT"),
        ("symlink", "SYMLINK_REJECTED"),
        ("binding", "REPLAY_IDENTITY_CONFLICT"),
        ("duplicate", "MALFORMED_PACKET"),
    ],
)
def test_replay_fails_closed_on_tampering(tmp_path, frozen, change, code) -> None:
    root = tmp_path / change
    shutil.copytree(frozen, root)
    path = root / "predictions.json"
    if change == "probability":
        path.write_bytes(
            path.read_bytes().replace(b"0.500000000000", b"0.900000000000", 1)
        )
    elif change == "extra":
        (root / "extra.json").write_text("{}")
    elif change == "missing":
        path.unlink()
    elif change == "symlink":
        path.unlink()
        path.symlink_to(frozen / "predictions.json")
    else:
        if change == "binding":
            payload = json.loads(path.read_bytes())
            payload["model_identity"] = "0" * 64
            path.write_bytes(core.canonical_bytes(payload))
        else:
            path.write_bytes(b'{"rows":[],"rows":[]}')
        manifest = json.loads((root / "file-manifest.json").read_bytes())
        manifest["files"][path.name] = {
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        (root / "file-manifest.json").write_bytes(core.canonical_bytes(manifest))
    with pytest.raises(core.RetrospectiveContractError, match=code):
        runner.replay_retrospective_packet(root)


def test_real_invalid_modes_and_path_conflicts_before_work(
    tmp_path, frozen, monkeypatch, capsys
) -> None:
    monkeypatch.setattr(runner, "build_retrospective_packet", fail)
    root = tmp_path / "not-created"
    assert runner.main(("--real", "--output", str(root))) == 2
    assert not root.exists() and "REAL_EXECUTION_NOT_READY" in capsys.readouterr().err
    assert runner.main(("--replay", str(frozen), "--output", str(root))) == 2
    before = snapshot(frozen)
    with pytest.raises(core.RetrospectiveContractError, match="OUTPUT_CONFLICT"):
        runner.run_fixture(frozen)
    assert snapshot(frozen) == before
    alias = tmp_path / "alias"
    alias.symlink_to(frozen, target_is_directory=True)
    with pytest.raises(core.RetrospectiveContractError, match="SYMLINK_REJECTED"):
        runner.run_fixture(alias / "child")
    with pytest.raises(core.RetrospectiveContractError, match="SYMLINK_REJECTED"):
        runner.replay_retrospective_packet(alias)


def test_price_only_outcome_projection_does_not_require_volume_or_limits(plan) -> None:
    features = core.make_retrospective_features(
        plan, runner.fixture_feature_views(plan, plan.splits[0])
    )
    outcomes = tuple(
        replace(
            view,
            stock=tuple(
                replace(
                    bar, volume=None, quantity_unit=None, up_limit=None, down_limit=None
                )
                for bar in view.stock
            ),
        )
        for view in runner.fixture_outcome_views(plan, plan.splits[0])
    )
    labels = core.make_retrospective_labels(
        plan, outcomes, computed_at=plan.snapshot_observed_at + timedelta(seconds=1)
    )
    assert features[0].stock_history_identity == labels[0].stock_history_identity
    core.fit_retrospective_models(
        plan,
        core.TrainPanel(features, labels),
        fitted_at=plan.snapshot_observed_at + timedelta(seconds=2),
    )


def test_classification_cannot_drift_between_partition_calls(plan) -> None:
    core.make_retrospective_features(
        plan, runner.fixture_feature_views(plan, plan.splits[0])
    )
    views = runner.fixture_feature_views(plan, plan.splits[1])
    changed = tuple(
        replace(
            view, classification=replace(classification(view), ordinary_a_share=None)
        )
        for view in views
    )
    with pytest.raises(core.RetrospectiveContractError, match="SNAPSHOT_FACT_CONFLICT"):
        core.make_retrospective_features(plan, changed)


def test_future_label_must_match_later_excluded_feature_even_when_its_label_is_omitted(
    packet,
) -> None:
    plan = packet["plan"]
    target = next(
        row
        for row in packet["predictions"].rows
        if row.partition == "RETROSPECTIVE_EVAL"
    )
    features = tuple(
        replace(row, rv=None, nv=None, reasons=("VOLUME_MISSING",))
        if row.key.instrument_id == target.key.instrument_id
        and row.key.decision_session > target.key.decision_session
        else row
        for row in packet["features"]
    )
    predictions = core.predict_retrospective_models(
        plan,
        packet["models"],
        features,
        predicted_at=packet["predictions"].predicted_at,
    )
    original = next(row for row in packet["labels"] if row.key == target.key)
    outcomes = runner.fixture_outcome_views(plan, plan.splits[2])
    changed = tuple(
        replace(
            view,
            stock=tuple(
                replace(bar, close=number(bar.close) + D(10))
                if view.key.instrument_id == target.key.instrument_id
                and bar.session == original.label_end
                else bar
                for bar in view.stock
            ),
        )
        for view in outcomes
    )
    changed_labels = core.make_retrospective_labels(
        plan, changed, computed_at=plan.snapshot_observed_at + timedelta(seconds=4)
    )
    assert (
        next(
            row for row in changed_labels if row.key == target.key
        ).stock_history_identity
        == target.stock_history_identity
    )
    labels = tuple(
        row for row in packet["labels"] if row.partition != "RETROSPECTIVE_EVAL"
    ) + tuple(
        row
        for row in changed_labels
        if not (
            row.key.instrument_id == target.key.instrument_id
            and row.key.decision_session > target.key.decision_session
        )
    )
    with pytest.raises(core.RetrospectiveContractError, match="SNAPSHOT_FACT_CONFLICT"):
        core.evaluate_retrospective_predictions(
            plan,
            predictions,
            labels,
            runner.fixture_week_grid(plan, features),
            evaluated_at=packet["diagnostics"].evaluated_at,
        )


@pytest.mark.parametrize(
    "binding",
    (
        "prediction_plan",
        "diagnostic_plan",
        "diagnostic_model",
        "diagnostic_predictions",
        "diagnostic_grid",
    ),
)
def test_replay_rejects_internal_identity_mismatch_even_with_rehashed_manifest(
    tmp_path, frozen, binding
) -> None:
    root = tmp_path / binding
    shutil.copytree(frozen, root)
    packet = json.loads((root / "packet.json").read_bytes())
    names = {
        "diagnostic_plan": "plan_identity",
        "diagnostic_model": "model_identity",
        "diagnostic_predictions": "predictions_identity",
        "diagnostic_grid": "calendar_grid_identity",
    }
    changed = ["packet.json"]
    if binding == "prediction_plan":
        predictions = json.loads((root / "predictions.json").read_bytes())
        predictions["plan_identity"] = "0" * 64
        packet["predictions"] = predictions
        packet["prediction_freeze_sha256"] = core.identity(predictions)
        packet["diagnostics"]["predictions_identity"] = core.identity(predictions)
        (root / "predictions.json").write_bytes(core.canonical_bytes(predictions))
        changed.append("predictions.json")
    else:
        packet["diagnostics"][names[binding]] = "0" * 64
    (root / "packet.json").write_bytes(core.canonical_bytes(packet))
    manifest = json.loads((root / "file-manifest.json").read_bytes())
    for name in changed:
        raw = (root / name).read_bytes()
        manifest["files"][name] = {
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    (root / "file-manifest.json").write_bytes(core.canonical_bytes(manifest))
    with pytest.raises(
        core.RetrospectiveContractError, match="REPLAY_IDENTITY_CONFLICT"
    ):
        runner.replay_retrospective_packet(root)


def test_prediction_cannot_change_fitted_train_features(packet) -> None:
    features = tuple(
        replace(row, rv=D(".8"), nv=1) if row.partition == "TRAIN" else row
        for row in packet["features"]
    )
    with pytest.raises(core.RetrospectiveContractError, match="SNAPSHOT_FACT_CONFLICT"):
        core.predict_retrospective_models(
            packet["plan"],
            packet["models"],
            features,
            predicted_at=packet["predictions"].predicted_at,
        )


def test_replay_cannot_restate_the_human_report_with_a_new_self_manifest(
    tmp_path, frozen
) -> None:
    root = tmp_path / "restated"
    shutil.copytree(frozen, root)
    report = root / "report.md"
    report.write_text(
        report.read_text().replace(
            "insufficient", "retrospective_incremental_association"
        )
    )
    manifest = json.loads((root / "file-manifest.json").read_bytes())
    raw = report.read_bytes()
    manifest["files"]["report.md"] = {
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    (root / "file-manifest.json").write_bytes(core.canonical_bytes(manifest))
    with pytest.raises(
        core.RetrospectiveContractError, match="REPLAY_IDENTITY_CONFLICT"
    ):
        runner.replay_retrospective_packet(root)


def test_core_is_pure_and_adapter_has_no_real_IO_imports() -> None:
    for module in (core, runner):
        assert module.__file__ is not None
        tree = ast.parse(Path(module.__file__).read_text())
        imports = {
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        } | {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        assert not any(
            name.startswith(
                (
                    "crypto_quant",
                    "duckdb",
                    "pandas",
                    "tushare",
                    "requests",
                    "urllib",
                    "socket",
                    "subprocess",
                    "os",
                )
            )
            for name in imports
        )
        if module is core:
            calls = {
                node.func.id
                for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            }
            assert not calls & {"open", "exec", "eval"}
            assert not any(
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr
                in ("read_text", "read_bytes", "write_text", "now", "today")
                for node in ast.walk(tree)
            )
            forbidden = {
                "make_features",
                "make_labels",
                "fit_models",
                "predict_models",
                "evaluate_predictions",
                "_index",
                "_sample",
                "_prices",
            }
            assert not any(
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "_reference"
                and node.attr in forbidden
                for node in ast.walk(tree)
            )
