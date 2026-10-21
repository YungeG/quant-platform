"""Synthetic-only contract tests for D009; no market/Owner fixtures."""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import random
import shutil
from dataclasses import replace
from datetime import date, datetime, time, timedelta
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any, cast

import pytest

from experiments import a_share_price_volume_research_v1 as core
from experiments import run_a_share_price_volume_research_v1 as runner

D = Decimal
SOURCE = "a" * 64
REVISION = "synthetic-only"


def provenance(day: date, *, available: datetime | None = None) -> core.Provenance:
    event = datetime.combine(day, time(15), core.SHANGHAI)
    return core.Provenance(
        REVISION,
        "synthetic",
        SOURCE,
        event,
        available or event,
        event + timedelta(days=400),
    )


def plan_for(weeks: tuple[int, int, int] = (2, 2, 16)) -> core.Plan:
    start = date(2000, 1, 3)
    splits = []
    for partition, count in zip(core.PARTITIONS, weeks, strict=True):
        decision_from = start + timedelta(weeks=13)
        decision_to = decision_from + timedelta(weeks=count)
        read_to = decision_to + timedelta(weeks=1)
        splits.append(core.Split(partition, start, read_to, decision_from, decision_to))
        start = read_to
    first = splits[0].read_from
    stamp = datetime.combine(first - timedelta(days=1), time(), core.SHANGHAI)
    cal_provenance = core.Provenance(
        REVISION, "synthetic", SOURCE, stamp, stamp, stamp + timedelta(days=4000)
    )
    calendar = tuple(
        core.CalendarDay(
            first + timedelta(days=i),
            (first + timedelta(days=i)).weekday() < 5,
            cal_provenance,
        )
        for i in range((start - first).days)
    )
    return core.Plan(
        REVISION,
        (("synthetic", SOURCE),),
        calendar,
        tuple(splits),
        "synthetic two-stock SH/SZ pharma; not a real universe",
        True,
    )


def sessions_for(plan: core.Plan, partition: str) -> tuple[date, ...]:
    split = next(s for s in plan.splits if s.partition == partition)
    return tuple(
        d.day
        for d in plan.calendar
        if d.is_open and split.read_from <= d.day < split.read_to
    )


def key_at(
    plan: core.Plan,
    partition: str = "TRAIN",
    week: int = 0,
    instrument: str = "000001.XSHE",
) -> core.SampleKey:
    split = next(s for s in plan.splits if s.partition == partition)
    monday = split.decision_from + timedelta(weeks=week)
    session = max(
        d
        for d in sessions_for(plan, partition)
        if monday <= d < monday + timedelta(weeks=1)
    )
    return core.SampleKey(
        instrument,
        session,
        datetime.combine(session, time(23, 59, 59), core.SHANGHAI),
        plan.dataset_revision,
    )


def views_at(
    plan: core.Plan, partition: str = "TRAIN", week: int = 0, *, rebound: bool = False
) -> tuple[core.FeatureView, core.OutcomeView]:
    key = key_at(plan, partition, week)
    split = next(s for s in plan.splits if s.partition == partition)
    sessions = sessions_for(plan, partition)
    t = sessions.index(key.decision_session)
    stock = []
    industry = []
    with localcontext(core.CONTEXT):
        for i in range(t - 64, min(t + 6, len(sessions))):
            close = D(100 + i)
            if rebound:
                close = (
                    D(200) - D(i) / D(2)
                    if i <= t - 5
                    else D(200) - D(t - 5) / D(2) + D(i - (t - 5))
                )
            bar = core.DailyBar(
                sessions[i],
                close,
                provenance(sessions[i]),
                D(50 if t - 4 <= i <= t else 100),
                "share",
                True,
                False,
                True,
                close * D("1.1"),
                close * D("0.9"),
            )
            stock.append(bar)
            industry.append(replace(bar, close=D(1000 + i)))
    member = core.Membership(
        split.read_from,
        split.read_to,
        "XSHE",
        "801150",
        True,
        True,
        provenance(split.read_from),
    )
    return core.FeatureView(
        key,
        partition,
        member,
        tuple(b for b in stock if b.session <= key.decision_session),
        tuple(b for b in industry if b.session <= key.decision_session),
    ), core.OutcomeView(key, partition, tuple(stock))


def manual_features(
    plan: core.Plan, partition: str, *, count_per_week: int = 2
) -> core.FeatureRows:
    split = next(s for s in plan.splits if s.partition == partition)
    rows = []
    for week in range((split.decision_to - split.decision_from).days // 7):
        monday = split.decision_from + timedelta(weeks=week)
        if not any(
            d.is_open and monday <= d.day < monday + timedelta(weeks=1)
            for d in plan.calendar
        ):
            continue
        for stock in range(count_per_week):
            key = key_at(plan, partition, week, f"{stock:06d}.XSHE")
            nv = stock % 2
            rows.append(
                core.FeatureRow(
                    key,
                    partition,
                    D("0.02"),
                    D("0.08"),
                    D("0.01"),
                    D(100),
                    D(90),
                    True,
                    True,
                    D("0.5") if nv else D("1.5"),
                    nv,
                    True,
                )
            )
    return tuple(sorted(rows, key=lambda r: r.key))


def manual_label(
    plan: core.Plan, row: core.FeatureRow, y: int | None = None
) -> core.LabelRow:
    sessions = sessions_for(plan, row.partition)
    end = sessions[sessions.index(row.key.decision_session) + 5]
    value = row.nv if y is None else y
    assert value is not None
    return core.LabelRow(
        row.key,
        row.partition,
        value,
        bool(value),
        bool(value),
        end,
        datetime.combine(end, time(15), core.SHANGHAI),
        D("0.03") if value else D("-0.03"),
        D(0) if value else D("-0.03"),
        D("0.04"),
    )


def grid_for(plan: core.Plan, features: core.FeatureRows) -> tuple[core.WeekSlot, ...]:
    result = []
    for split in plan.splits:
        week = split.decision_from
        while week < split.decision_to:
            opened = [
                d.day
                for d in plan.calendar
                if d.is_open and week <= d.day < week + timedelta(weeks=1)
            ]
            rows = [
                r
                for r in features
                if r.partition == split.partition
                and core.week_key(r.key.decision_session) == week
                and "OUTSIDE_DECLARED_UNIVERSE" not in r.reasons
            ]
            reasons = {}
            for row in rows:
                for reason in row.reasons:
                    reasons[reason] = reasons.get(reason, 0) + 1
            result.append(
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
    return tuple(result)


def prediction(
    row: core.FeatureRow, *, p0: str = ".5", pv: str = ".8", active: bool = True
) -> core.PredictionRow:
    assert row.nv is not None and row.rv is not None
    ps = tuple(D(p).quantize(core.P_QUANTUM) for p in (".5", p0, pv, ".5"))
    return core.PredictionRow(
        row.key,
        row.partition,
        (0, 0, 0, 1, 1),
        row.nv,
        row.nv,
        True,
        True,
        row.rv,
        (ps[0], ps[1], ps[2], ps[3]),
        None,
        None if active else "ROWS_LT_50",
        None,
    )


def prediction_set(
    plan: core.Plan, rows: tuple[core.PredictionRow, ...]
) -> core.PredictionRows:
    return core.PredictionRows(
        core.identity(plan),
        "b" * 64,
        208,
        tuple(
            key_at(plan, "TRAIN", i).decision_session
            for i in range(
                min(
                    104,
                    (plan.splits[0].decision_to - plan.splits[0].decision_from).days
                    // 7,
                )
            )
        ),
        rows,
        (),
    )


def test_hand_calculated_features_and_label_smoke() -> None:
    plan = plan_for()
    fv, lv = views_at(plan)
    row = core.make_features(plan, (fv,))[0]
    label = core.make_labels(plan, (lv,))[0]
    with localcontext(core.CONTEXT):
        assert row.r5 == D(169) / D(164) - 1
        assert row.r20 == D(169) / D(149) - 1
        assert row.ma20 == D("159.5")
        assert row.ma60 == D("139.5")
        assert row.a20 == sum(
            (D(100 + i) / D(100 + i - 1) - 1 for i in range(50, 70)), D(0)
        ) / D(20)
        assert row.rv == D("0.5") and row.nv == 1
        assert row.trend and row.industry_up and row.predictable
        assert label.y == 1 and label.gain_5d and label.trend_at_5d
        assert label.end_change == D(174) / D(169) - 1
        assert label.adverse_change == 0
        assert label.min_close_over_ma20 == D(170) / D("159.5") - 1
    assert label.label_end == sessions_for(plan, "TRAIN")[74]
    assert label.label_end is not None
    assert label.label_available_at == provenance(label.label_end).available_at


def test_two_stock_same_interface_smoke_and_insufficient_is_not_success() -> None:
    plan = plan_for()
    fv, lv = views_at(plan)
    rebound, rebound_label = views_at(plan, rebound=True)
    key = replace(rebound.key, instrument_id="600001.XSHG")
    rebound, rebound_label = replace(rebound, key=key), replace(rebound_label, key=key)
    features = core.make_features(plan, (fv, rebound))
    labels = core.make_labels(plan, (lv, rebound_label))
    assert {r.trend for r in features} == {False, True}
    assert all(r.predictable and r.nv == 1 for r in features)
    assert {r.y for r in labels} == {0, 1}
    cards = core.fit_models(plan, core.TrainPanel(features, labels))
    predictions = core.predict_models(plan, cards, features)
    report = core.evaluate_predictions(
        plan, predictions, labels, grid_for(plan, features)
    )
    assert report.verdict == "insufficient"
    assert report.partitions[2].delta is None
    assert report.bootstrap_4.invalid_count == 1000
    assert report.bootstrap_13.interval is None
    assert all(p.probabilities[1] == p.probabilities[2] for p in predictions.rows)


def test_future_changes_and_acquisition_do_not_rewrite_features() -> None:
    plan = plan_for()
    fv, lv = views_at(plan)
    before = core.canonical_bytes(core.make_features(plan, (fv,)))
    altered = replace(
        lv,
        stock=tuple(
            replace(b, close=D(1), volume=D(9999))
            if b.session > fv.key.decision_session
            else b
            for b in lv.stock
        ),
    )
    assert core.make_labels(plan, (altered,))[0].y == 0
    assert before == core.canonical_bytes(core.make_features(plan, (fv,)))
    acquired = replace(
        fv,
        stock=tuple(
            replace(
                b,
                provenance=replace(
                    b.provenance,
                    acquired_at=b.provenance.acquired_at + timedelta(days=100),
                ),
            )
            for b in fv.stock
        ),
    )
    assert before == core.canonical_bytes(core.make_features(plan, (acquired,)))
    with pytest.raises(core.ResearchContractError, match="FUTURE_IN_FEATURE_VIEW"):
        core.make_features(plan, (replace(fv, stock=lv.stock),))


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"close": None}, "PRICE_MISSING"),
        ({"volume": None}, "VOLUME_MISSING"),
        ({"quantity_unit": "lot"}, "VOLUME_UNIT_MISMATCH"),
        ({"comparable": False}, "PRICE_SCALE_UNRESOLVED"),
        ({"listed": None}, "LISTING_OR_SUSPENSION_UNKNOWN"),
        ({"suspended": True}, "SUSPENDED"),
        ({"up_limit": None}, "LIMIT_STATUS_UNKNOWN"),
    ],
)
def test_no_fill_and_independent_reasons(change: dict[str, Any], reason: str) -> None:
    plan = plan_for()
    fv, _ = views_at(plan)
    altered = replace(fv, stock=(*fv.stock[:-1], replace(fv.stock[-1], **change)))
    row = core.make_features(plan, (altered,))[0]
    assert reason in row.reasons and not row.predictable


def test_zero_baseline_and_known_actual_zero_are_distinct() -> None:
    plan = plan_for()
    fv, _ = views_at(plan)
    zero_baseline = replace(
        fv,
        stock=tuple(
            replace(b, volume=D(0)) if i < 60 else b for i, b in enumerate(fv.stock)
        ),
    )
    assert (
        "ZERO_VOLUME_BASELINE" in core.make_features(plan, (zero_baseline,))[0].reasons
    )
    zero_current = replace(
        fv,
        stock=tuple(
            replace(b, volume=D(0)) if i >= 60 else b for i, b in enumerate(fv.stock)
        ),
    )
    row = core.make_features(plan, (zero_current,))[0]
    assert row.rv == 0 and row.predictable


def test_late_revision_membership_timezone_and_snapshot_conflicts() -> None:
    plan = plan_for()
    fv, _ = views_at(plan)
    late = replace(
        fv.stock[-1],
        provenance=replace(
            fv.stock[-1].provenance, available_at=fv.key.as_of + timedelta(seconds=1)
        ),
    )
    assert (
        "NOT_AVAILABLE_AT_CUTOFF"
        in core.make_features(plan, (replace(fv, stock=(*fv.stock[:-1], late)),))[
            0
        ].reasons
    )
    assert fv.membership is not None
    member = replace(
        fv.membership,
        provenance=replace(
            fv.membership.provenance, available_at=fv.key.as_of + timedelta(days=1)
        ),
    )
    assert (
        "MEMBERSHIP_UNKNOWN"
        in core.make_features(plan, (replace(fv, membership=member),))[0].reasons
    )
    future_member = replace(
        fv.membership, effective_from=fv.key.decision_session + timedelta(days=1)
    )
    assert (
        "OUTSIDE_DECLARED_UNIVERSE"
        in core.make_features(plan, (replace(fv, membership=future_member),))[0].reasons
    )
    with pytest.raises(core.ResearchContractError, match="TIMEZONE_MISMATCH"):
        core.make_features(
            plan,
            (
                replace(
                    fv, key=replace(fv.key, as_of=fv.key.as_of.replace(tzinfo=None))
                ),
            ),
        )
    with pytest.raises(core.ResearchContractError, match="DUPLICATE_STOCK_DAY"):
        core.make_features(plan, (replace(fv, stock=(*fv.stock, fv.stock[-1])),))
    for field, value, code in (
        ("revision", "later", "REVISION_CONFLICT"),
        ("raw_sha256", "c" * 64, "SOURCE_IDENTITY_CONFLICT"),
    ):
        bad = replace(
            fv.stock[-1], provenance=replace(fv.stock[-1].provenance, **{field: value})
        )
        with pytest.raises(core.ResearchContractError, match=code):
            core.make_features(plan, (replace(fv, stock=(*fv.stock[:-1], bad)),))
    with pytest.raises(core.ResearchContractError, match="DUPLICATE_SAMPLE"):
        core.make_features(plan, (fv, fv))


def test_limit_touch_is_a_diagnostic_not_a_trade_claim() -> None:
    plan = plan_for()
    fv, _ = views_at(plan)
    bar = replace(fv.stock[-1], up_limit=fv.stock[-1].close)
    row = core.make_features(plan, (replace(fv, stock=(*fv.stock[:-1], bar)),))[0]
    assert "CLOSE_LIMIT_TOUCH" in row.reasons and row.price_valid


def test_future_scale_or_missing_labels_never_change_F() -> None:
    plan = plan_for()
    fv, lv = views_at(plan)
    features = core.make_features(plan, (fv,))
    labels = core.make_labels(plan, (lv,))
    cards = core.fit_models(plan, core.TrainPanel(features, labels))
    predictions = core.predict_models(plan, cards, features)
    bad = replace(lv, stock=(*lv.stock[:-1], replace(lv.stock[-1], comparable=False)))
    unknown = core.make_labels(plan, (bad,))
    assert unknown[0].y is None and not unknown[0].target_defined
    report = core.evaluate_predictions(
        plan, predictions, unknown, grid_for(plan, features)
    )
    assert dict(report.partitions[0].counts)["F_rows"] == 1
    assert dict(report.partitions[0].counts)["E_rows"] == 0
    assert report.partitions[0].weeks[0].state == "EMPTY_E_UNOBSERVABLE"
    assert core.identity(predictions) == report.predictions_identity
    late = replace(
        lv.stock[-1],
        provenance=replace(
            lv.stock[-1].provenance,
            available_at=datetime.combine(
                plan.splits[0].read_to, time(), core.SHANGHAI
            ),
        ),
    )
    assert (
        "LABEL_NOT_YET_AVAILABLE"
        in core.make_labels(plan, (replace(lv, stock=(*lv.stock[:-1], late)),))[
            0
        ].reasons
    )


def test_holiday_last_session_and_missing_stock_does_not_skip_horizon() -> None:
    plan = plan_for()
    friday = key_at(plan).decision_session
    plan = replace(
        plan,
        calendar=tuple(
            replace(day, is_open=False) if day.day == friday else day
            for day in plan.calendar
        ),
    )
    fv, lv = views_at(plan)
    assert fv.key.decision_session == friday - timedelta(days=1)
    label = core.make_labels(plan, (lv,))[0]
    expected = sessions_for(plan, "TRAIN")[
        sessions_for(plan, "TRAIN").index(fv.key.decision_session) + 5
    ]
    assert label.label_end == expected
    missing = replace(lv, stock=tuple(b for b in lv.stock if b.session != expected))
    assert core.make_labels(plan, (missing,))[0].y is None
    with pytest.raises(core.ResearchContractError, match="CALENDAR_GAP"):
        core.make_features(replace(plan, calendar=plan.calendar[1:]), (fv,))


def test_split_purge_and_invalid_plan() -> None:
    plan = plan_for()
    fv, lv = views_at(plan, week=1)
    boundary = plan.splits[0].decision_to
    plan = replace(
        plan, splits=(replace(plan.splits[0], read_to=boundary), *plan.splits[1:])
    )
    labels = core.make_labels(
        plan, (replace(lv, stock=tuple(b for b in lv.stock if b.session < boundary)),)
    )
    assert labels[0].reasons == ("LABEL_WINDOW_OUTSIDE_SPLIT",)
    too_short = replace(
        plan,
        splits=(
            replace(
                plan.splits[0], read_from=fv.key.decision_session - timedelta(days=20)
            ),
            *plan.splits[1:],
        ),
    )
    with pytest.raises(core.ResearchContractError, match="READ_WINDOW_VIOLATION"):
        core.make_features(too_short, (fv,))
    bounded = replace(
        fv,
        stock=tuple(b for b in fv.stock if b.session >= too_short.splits[0].read_from),
        industry=tuple(
            b for b in fv.industry if b.session >= too_short.splits[0].read_from
        ),
    )
    assert (
        "INSUFFICIENT_HISTORY" in core.make_features(too_short, (bounded,))[0].reasons
    )
    overlap = replace(
        plan_for(),
        splits=(
            plan_for().splits[0],
            replace(plan_for().splits[1], read_from=plan_for().splits[0].read_from),
            plan_for().splits[2],
        ),
    )
    with pytest.raises(core.ResearchContractError, match="SPLIT_OVERLAP"):
        core.make_features(overlap, ())


def test_exact_fit_support_smoothing_and_train_only_medians() -> None:
    plan = plan_for((104, 26, 52))
    rows = manual_features(plan, "TRAIN")
    labels = tuple(manual_label(plan, r) for r in rows)
    cards = core.fit_models(plan, core.TrainPanel(rows, labels))
    assert cards.training_count == 208 and len(cards.training_weeks) == 104
    assert cards.climatology_probability == D("0.500000000000")
    assert cards.thresholds == core.Thresholds(D(".02"), D(".08"), D(".01"))
    assert len(cards.price_cells) == 1 and cards.price_cells[0].fallback is None
    assert all(c.fallback is None and c.count == 104 for c in cards.volume_cells)
    with localcontext(core.CONTEXT):
        assert cards.volume_cells[1].estimate == D(114) / D(124)
        assert cards.volume_cells[1].probability == (D(114) / D(124)).quantize(
            core.P_QUANTUM
        )
        assert cards.volume_cells[0].estimate == D(10) / D(124)
    dev = manual_features(plan, "DEVELOPMENT")
    predictions = core.predict_models(plan, cards, dev)
    assert all(p.price_cell[:3] == (0, 0, 0) for p in predictions.rows)
    assert all(p.pv_fallback is None for p in predictions.rows)
    with pytest.raises(core.ResearchContractError, match="NON_TRAIN_FIT"):
        core.fit_models(
            plan, core.TrainPanel(dev, tuple(manual_label(plan, r) for r in dev))
        )
    with pytest.raises(core.ResearchContractError, match="EMPTY_TRAIN"):
        core.fit_models(plan, core.TrainPanel((), ()))
    modified = tuple(replace(r, r5=D(i + 1)) for i, r in enumerate(rows[:4]))
    tied = core.fit_models(
        plan, core.TrainPanel(modified, tuple(manual_label(plan, r) for r in modified))
    )
    assert tied.thresholds.r5 == D(2)
    assert core._cell(modified[1], tied.thresholds)[0] == 0


def test_support_requires_rows_AND_distinct_weeks_and_unseen_is_not_unknown() -> None:
    assert (
        core._support(
            50, tuple(date(2000, 1, 3) + timedelta(weeks=i) for i in range(11))
        )
        == "WEEKS_LT_12"
    )
    assert (
        core._support(
            49, tuple(date(2000, 1, 3) + timedelta(weeks=i) for i in range(12))
        )
        == "ROWS_LT_50"
    )
    plan = plan_for()
    rows = manual_features(plan, "TRAIN")
    cards = core.fit_models(
        plan, core.TrainPanel(rows, tuple(manual_label(plan, r) for r in rows))
    )
    unseen = replace(rows[0], trend=False, r5=D(1))
    pred = core.predict_models(plan, cards, (unseen,)).rows[0]
    assert pred.price_fallback == pred.pv_fallback == "UNSEEN_CELL"
    assert pred.probabilities[1] == pred.probabilities[2] == pred.probabilities[0]
    with pytest.raises(core.ResearchContractError, match="MALFORMED_FEATURE"):
        core.predict_models(plan, cards, (replace(rows[0], a20=None),))
    with pytest.raises(core.ResearchContractError, match="MODEL_PLAN_CONFLICT"):
        core.predict_models(replace(plan, universe_scope="another scope"), cards, rows)


def test_shuffle_is_fixed_partition_local_key_sorted_and_discloses_noops() -> None:
    plan = plan_for()
    rows = manual_features(plan, "TRAIN", count_per_week=8)
    thresholds = core.Thresholds(D(".02"), D(".08"), D(".01"))
    shuffled, stats = core._shuffle(rows, thresholds)
    assert shuffled == core._shuffle(tuple(reversed(rows)), thresholds)[0]
    dev = manual_features(plan, "DEVELOPMENT", count_per_week=8)
    all_assignments, _ = core._shuffle((*rows, *dev), thresholds)
    assert all(all_assignments[k] == v for k, v in shuffled.items())
    for week in {core.week_key(r.key.decision_session) for r in rows}:
        group = [r for r in rows if core.week_key(r.key.decision_session) == week]
        assert sorted(shuffled[r.key] for r in group) == sorted(
            r.nv for r in group if r.nv is not None
        )
    assert stats[0].changed_rows > 0
    single, single_stats = core._shuffle((rows[0],), thresholds)
    assert single[rows[0].key] == rows[0].nv and single_stats[0].singleton_groups == 1
    same = tuple(replace(r, nv=1, rv=D(".5")) for r in rows)
    assert core._shuffle(same, thresholds)[1][0].unshufflable_rows == len(same)


def test_complete_grid_states_nulls_and_original_half_boundary() -> None:
    plan = plan_for()
    split = plan.splits[2]
    closed = split.decision_from
    plan = replace(
        plan,
        calendar=tuple(
            replace(d, is_open=False)
            if closed <= d.day < closed + timedelta(weeks=1)
            else d
            for d in plan.calendar
        ),
    )
    features = manual_features(plan, "HELD_OUT")
    first = split.decision_from + timedelta(weeks=1)
    features = tuple(
        replace(r, r5=D(-1), reasons=("NO_UP_CANDIDATE",))
        if core.week_key(r.key.decision_session) == first
        else r
        for r in features
    )
    empty_f = split.decision_from + timedelta(weeks=2)
    features = tuple(
        replace(r, reasons=("VOLUME_MISSING",), rv=None, nv=None)
        if core.week_key(r.key.decision_session) == empty_f
        else r
        for r in features
    )
    preds = tuple(prediction(r) for r in features if r.predictable)
    empty_e = split.decision_from + timedelta(weeks=3)
    labels = tuple(
        manual_label(plan, r)
        for r in features
        if r.predictable and core.week_key(r.key.decision_session) != empty_e
    )
    report = core.evaluate_predictions(
        plan, prediction_set(plan, preds), labels, grid_for(plan, features)
    )
    held = report.partitions[2]
    assert [w.state for w in held.weeks[:5]] == [
        "STRUCTURAL_CLOSED",
        "NO_UP_CANDIDATE",
        "EMPTY_F_UNOBSERVABLE",
        "EMPTY_E_UNOBSERVABLE",
        "EVALUABLE",
    ]
    assert all(w.delta is None for w in held.weeks[:4])
    assert held.halves[0].grid_slots == 8 and held.halves[0].effective_weeks == 4
    assert held.weeks[7].half == 0 and held.weeks[8].half == 1
    with pytest.raises(core.ResearchContractError, match="CALENDAR_GRID_GAP"):
        core.evaluate_predictions(
            plan, prediction_set(plan, preds), labels, grid_for(plan, features)[:-1]
        )


def test_bootstrap_matches_physical_slot_reference_including_null_and_no_redraw() -> (
    None
):
    values = tuple(D(i) / D(100) if i % 3 else None for i in range(26))
    result = core._bootstrap(values, 4, 1)
    rng = random.Random(1)
    expected = []
    with localcontext(core.CONTEXT):
        for _ in range(1000):
            slots = []
            while len(slots) < len(values):
                start = rng.randrange(len(values) - 4 + 1)
                slots.extend(values[start : start + 4])
            known = [v for v in slots[: len(values)] if v is not None]
            expected.append(sum(known, D(0)) / D(len(known)) if known else None)
    assert result.values == tuple(expected)
    ordered = sorted(v for v in expected if v is not None)
    assert result.interval == (ordered[24], ordered[974])
    sparse = core._bootstrap((D(1),) + (None,) * 51, 4, 1)
    assert 0 < sparse.invalid_count < 1000
    assert sparse.interval is None and len(sparse.values) == 1000
    assert core._bootstrap((None,) * 52, 13, 3).invalid_count == 1000
    assert core._bootstrap((D(1),) * 12, 13, 3).reason == "GRID_SHORTER_THAN_BLOCK"


def ci(lower: str, upper: str, *, length: int = 4) -> core.BootstrapResult:
    return core.BootstrapResult(
        length,
        1 if length == 4 else 3,
        (D(".002"),) * 1000,
        0,
        (D(lower), D(upper)),
        None,
    )


@pytest.mark.parametrize(
    "a,b,expected",
    [
        ((".001", ".004"), ("-.003", "-.001"), "insufficient"),
        ((".001", ".004"), ("-.001", ".003"), "insufficient"),
        ((".001", ".004"), ("0", ".003"), "insufficient"),
        (("-.003", "-.001"), ("-.004", "-.001"), "no_declared_advantage"),
        (("-.001", ".003"), ("-.001", ".003"), "no_declared_advantage"),
        (("0", ".003"), ("0", ".003"), "no_declared_advantage"),
        ((".001", ".004"), (".001", ".004"), "incremental_in_declared_E"),
    ],
)
def test_signed_intervals_and_ordered_verdict(
    a: tuple[str, str], b: tuple[str, str], expected: str
) -> None:
    verdict, _ = core._decide(
        (),
        ci(*a),
        ci(*b, length=13),
        (D(".01"), D(".01")),
        (D(".25"), D(".24"), D(".23"), D(".24")),
        D(".04"),
    )
    assert verdict == expected


@pytest.mark.parametrize(
    "change,expected",
    [
        ({"validity": ("NO_ACTIVE_PV_COVERAGE_E",)}, "insufficient"),
        ({"relative": D(".01")}, "no_declared_advantage"),
        ({"relative": None}, "no_declared_advantage"),
        ({"half_deltas": (D(0), D(".01"))}, "insufficient"),
        ({"brier": (D(".25"), D(".24"), D(".23"), D(".23"))}, "insufficient"),
        ({"brier": (D(".22"), D(".24"), D(".23"), D(".24"))}, "no_declared_advantage"),
        (
            {"ci13": replace(ci(".001", ".004", length=13), invalid_count=1)},
            "insufficient",
        ),
        ({"ci13": ci(".004", ".001", length=13)}, "insufficient"),
        ({"ci13": ci("NaN", ".004", length=13)}, "insufficient"),
        ({"blocked": ("OUTPUT_CONFLICT",), "validity": ("EMPTY",)}, "blocked"),
    ],
)
def test_validity_precedence_and_no_auxiliary_override(
    change: dict[str, Any], expected: str
) -> None:
    args: dict[str, Any] = {
        "validity": (),
        "ci4": ci(".001", ".004"),
        "ci13": ci(".001", ".004", length=13),
        "half_deltas": (D(".01"), D(".01")),
        "brier": (D(".25"), D(".24"), D(".23"), D(".24")),
        "relative": D(".04"),
    }
    args.update(change)
    assert core._decide(**args)[0] == expected


def test_week_equal_weight_coverage_and_censor_stress_hand_calculation() -> None:
    plan = plan_for()
    features = manual_features(plan, "HELD_OUT")[:2]
    # Sorting is stock-major: use two different stocks in the same week.
    features = tuple(
        r
        for r in manual_features(plan, "HELD_OUT")
        if r.key.decision_session == key_at(plan, "HELD_OUT").decision_session
    )
    preds = tuple(prediction(r) for r in features)
    labels = (
        manual_label(plan, features[0], 1),
        replace(
            manual_label(plan, features[1]),
            y=None,
            gain_5d=None,
            trend_at_5d=None,
            reasons=("PRICE_SCALE_UNRESOLVED", "LABEL_UNOBSERVABLE"),
            target_defined=False,
        ),
    )
    report = core.evaluate_predictions(
        plan, prediction_set(plan, preds), labels, grid_for(plan, features)
    )
    held = report.partitions[2]
    assert held.delta == D(".21")
    assert held.censor_bounds == (D("-.09"), D(".21"))
    assert held.coverage_e == held.coverage_f == 1
    assert held.weeks[0].label_observability == D(".5")
    assert held.undefined_target_count == 1 and report.censor_sensitive
    assert held.label_components == ((True, True, True, 1),)
    assert held.observability_groups == ((False, 0, 0), (True, 1, 2))
    assert report.predictions_identity == core.identity(prediction_set(plan, preds))
    assert dict(held.counts)["E_rows"] == 1
    # One week has 100 stocks, the other one stock: neither dominates weight.
    many = [
        replace(
            features[0], key=replace(features[0].key, instrument_id=f"{i:06d}.XSHE")
        )
        for i in range(100)
    ]
    next_row = replace(features[0], key=key_at(plan, "HELD_OUT", 1, "999999.XSHE"))
    all_features = (*many, next_row)
    all_preds = tuple(
        prediction(r, active=i == 0, pv=".8" if i < 100 else ".2")
        for i, r in enumerate(all_features)
    )
    all_labels = tuple(manual_label(plan, r, 1) for r in all_features)
    summary = core.evaluate_predictions(
        plan, prediction_set(plan, all_preds), all_labels, grid_for(plan, all_features)
    ).partitions[2]
    assert summary.delta == D("-.09")  # mean(.21,-.39), not stock-weighted
    assert summary.coverage_e == D(".005")  # mean(1/100,0/1)
    assert [w.active_e_count for w in summary.weeks[:2]] == [1, 0]


def test_zero_brier_is_null_relative_not_infinity() -> None:
    plan = plan_for()
    row = manual_features(plan, "HELD_OUT")[0]
    pred = prediction(row, p0="1", pv="1")
    report = core.evaluate_predictions(
        plan,
        prediction_set(plan, (pred,)),
        (manual_label(plan, row, 1),),
        grid_for(plan, (row,)),
    )
    assert report.partitions[2].brier[1] == 0
    assert report.partitions[2].relative_improvement is None


def test_persisted_probability_mask_and_decimal_context_determinism() -> None:
    plan = plan_for()
    fv, lv = views_at(plan)
    ordinary = core.make_features(plan, (fv,))
    labels = core.make_labels(plan, (lv,))
    cards = core.fit_models(plan, core.TrainPanel(ordinary, labels))
    pred = core.predict_models(plan, cards, ordinary)
    with localcontext() as context:
        context.prec = 4
        assert core.make_features(plan, (fv,)) == ordinary
        assert core.fit_models(plan, core.TrainPanel(ordinary, labels)) == cards
        assert core.predict_models(plan, cards, ordinary) == pred
        report = core.evaluate_predictions(plan, pred, labels, grid_for(plan, ordinary))
    assert report == core.evaluate_predictions(
        plan, pred, labels, grid_for(plan, ordinary)
    )
    bad = replace(pred.rows[0], probabilities=(D(".5"),) * 4)
    with pytest.raises(
        core.ResearchContractError, match="PERSISTED_PROBABILITY_REQUIRED"
    ):
        core.evaluate_predictions(
            plan, replace(pred, rows=(bad,)), labels, grid_for(plan, ordinary)
        )
    with pytest.raises(core.ResearchContractError, match="INVALID_NUMERIC_VALUE"):
        replace(fv.stock[0], close=cast(Any, 1.0))


def test_core_has_no_IO_private_SDK_or_financial_path() -> None:
    path = Path(core.__file__)
    tree = ast.parse(path.read_text())
    imports = {
        node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not any(
        name.startswith(
            ("crypto_quant", "socket", "subprocess", "os", "pathlib", "requests")
        )
        for name in imports
    )
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not calls & {"open", "exec", "eval"}
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in ("now", "today", "write_text", "read_text")
        for node in ast.walk(tree)
    )


def test_full_statistical_fixture_reaches_positive_gate_without_changing_defaults() -> (
    None
):
    """A constructed DTO correlation tests acceptance, not a market effect."""
    plan = plan_for((104, 26, 52))
    features = tuple(r for part in core.PARTITIONS for r in manual_features(plan, part))
    labels = tuple(manual_label(plan, r) for r in features)
    cards = core.fit_models(
        plan,
        core.TrainPanel(
            tuple(r for r in features if r.partition == "TRAIN"),
            tuple(r for r in labels if r.partition == "TRAIN"),
        ),
    )
    predictions = core.predict_models(plan, cards, features)
    report = core.evaluate_predictions(
        plan, predictions, labels, grid_for(plan, features)
    )
    assert core.MIN_WEEKS == (104, 26, 52)
    assert report.verdict == "incremental_in_declared_E"
    assert report.bootstrap_4.interval and report.bootstrap_4.interval[0] > 0
    assert report.bootstrap_13.interval and report.bootstrap_13.interval[0] > 0
    assert report.partitions[2].coverage_e == 1
    assert all(h.delta is not None and h.delta > 0 for h in report.partitions[2].halves)


@pytest.fixture(scope="module")
def frozen_smoke(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("d009-synthetic") / "study"
    runner.run_synthetic(root, smoke=True, command=("test", "--synthetic", "--smoke"))
    return root


def file_snapshot(root: Path) -> dict[str, tuple[str, int]]:
    return {
        p.relative_to(root).as_posix(): (
            hashlib.sha256(p.read_bytes()).hexdigest(),
            p.stat().st_mtime_ns,
        )
        for p in root.rglob("*")
        if p.is_file()
    }


def test_runner_smoke_frozen_files_replay_and_persisted_scoring(
    frozen_smoke: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = file_snapshot(frozen_smoke)
    assert tuple(sorted(before)) == runner.EXPECTED_FILES
    plan = json.loads((frozen_smoke / "plan.json").read_text())
    admission = json.loads((frozen_smoke / "read-admission.json").read_text())
    assert plan["parameters"]["min_effective_weeks"] == [104, 26, 52]
    assert plan["parameters"]["bootstrap"]["draws"] == 1000
    assert plan["cap"]["real_authority"] is None
    assert admission["real_state"] == "DENIED_BEFORE_READER"
    assert admission["producer_ref"] is None and admission["reservation_ref"] is None
    assert admission["real_reader_opened"] is False
    with (frozen_smoke / "predictions.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 20 and not set(rows[0]) & {"y", "gain_5d", "trend_at_5d"}
    assert all(len(r["p_PRICE_VOLUME"].split(".")[1]) == 12 for r in rows)
    diagnostics = json.loads((frozen_smoke / "diagnostics.json").read_text())
    assert diagnostics["verdict"] == "insufficient"
    assert "TRAIN_WEEKS_LT_104" in diagnostics["verdict_reasons"]
    with (frozen_smoke / "evaluation-rows.csv").open() as stream:
        scored = list(csv.DictReader(stream))
    held = [r for r in scored if r["partition"] == "HELD_OUT" and r["in_E"] == "true"]
    with localcontext(core.CONTEXT):
        actual = sum(
            (D(r["p_PRICE_ONLY"]) - D(r["label_y"])) ** 2
            - (D(r["p_PRICE_VOLUME"]) - D(r["label_y"])) ** 2
            for r in held
        ) / D(len(held))
    assert D(diagnostics["partitions"][2]["delta"]) == actual

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError(
            "replay must not build views, features, labels, models or scores"
        )

    for name in (
        "make_features",
        "make_labels",
        "fit_models",
        "predict_models",
        "evaluate_predictions",
    ):
        monkeypatch.setattr(core, name, forbidden)
    for name in ("make_synthetic_plan", "_feature_views", "_outcome_views"):
        monkeypatch.setattr(runner, name, forbidden)
    assert runner.replay(frozen_smoke) == (frozen_smoke / "report.md").read_text()
    assert file_snapshot(frozen_smoke) == before


def test_runner_physical_freeze_order_one_fit_and_deterministic_outputs(
    tmp_path: Path, frozen_smoke: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "ordered"
    original_features, original_labels, original_fit = (
        runner._feature_views,
        runner._outcome_views,
        core.fit_models,
    )
    fit_calls = 0
    frozen_cards: bytes | None = None

    def feature_views(
        plan: core.Plan, split: core.Split
    ) -> tuple[core.FeatureView, ...]:
        nonlocal frozen_cards
        if split.partition != "TRAIN":
            assert all(
                (root / ("model-cards/" + name + ".json")).is_file()
                for name in core.MODELS
            )
            data = (root / "model-cards/frozen.json").read_bytes()
            if frozen_cards is None:
                frozen_cards = data
            assert data == frozen_cards
        return original_features(plan, split)

    def outcome_views(
        plan: core.Plan, split: core.Split
    ) -> tuple[core.OutcomeView, ...]:
        if split.partition != "TRAIN":
            assert (root / ("predictions-" + split.partition + ".csv")).is_file()
            assert (root / "predictions.csv").is_file() and (
                root / "predictions.json"
            ).is_file()
            assert (
                "label_y" not in (root / "predictions.csv").read_text().splitlines()[0]
            )
        return original_labels(plan, split)

    def fit(plan: core.Plan, panel: core.TrainPanel) -> core.FrozenModelCards:
        nonlocal fit_calls
        fit_calls += 1
        assert fit_calls == 1
        return original_fit(plan, panel)

    monkeypatch.setattr(runner, "_feature_views", feature_views)
    monkeypatch.setattr(runner, "_outcome_views", outcome_views)
    monkeypatch.setattr(core, "fit_models", fit)
    runner.run_synthetic(root, smoke=True)
    assert fit_calls == 1
    for name in runner.EXPECTED_FILES:
        if name != "file-manifest.json":
            assert (root / name).read_bytes() == (frozen_smoke / name).read_bytes(), (
                name
            )
    stages = json.loads((root / "execution-order.json").read_text())["stages"]
    assert stages.index("MODEL_CARDS_FROZEN") < stages.index(
        "DEVELOPMENT_FEATURE_VIEW_OPENED"
    )
    assert stages.index(
        "ALL_PREDICTIONS_FROZEN_BEFORE_EVALUATION_LABELS"
    ) < stages.index("HELD_OUT_LABEL_VIEW_OPENED_AFTER_PREDICTION_FREEZE")


def test_real_invalid_modes_and_output_conflicts_are_before_work(
    tmp_path: Path,
    frozen_smoke: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("invalid mode/conflict must be rejected before any work")

    monkeypatch.setattr(runner, "make_synthetic_plan", forbidden)
    root = tmp_path / "real-never-created"
    assert runner.main(("--real", "--output", str(root))) == 2
    assert not root.exists() and "REAL_EXECUTION_NOT_READY" in capsys.readouterr().err
    before = file_snapshot(frozen_smoke)
    with pytest.raises(core.ResearchContractError, match="OUTPUT_CONFLICT"):
        runner.run_synthetic(frozen_smoke)
    assert file_snapshot(frozen_smoke) == before
    assert runner.main(("--replay", str(frozen_smoke), "--output", str(root))) == 2
    assert not root.exists()
    alias = tmp_path / "alias"
    alias.symlink_to(frozen_smoke, target_is_directory=True)
    with pytest.raises(core.ResearchContractError, match="SYMLINK_REJECTED"):
        runner.replay(alias)
    with pytest.raises(core.ResearchContractError, match="SYMLINK_REJECTED"):
        runner.run_synthetic(alias / "never-created")
    assert not (frozen_smoke / "never-created").exists()


@pytest.mark.parametrize("failure", ("time", "source"))
def test_runner_caps_and_source_failure_preserve_nonreplayable_partial_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    root = tmp_path / failure
    if failure == "time":
        monkeypatch.setattr(runner, "MAX_SECONDS", 0)
        code = "SYNTHETIC_TIME_CAP"
    else:
        code = "SOURCE_IDENTITY_CONFLICT"

        def denied(*args: Any, **kwargs: Any) -> Any:
            raise core.ResearchContractError(code, "synthetic boundary rejection")

        monkeypatch.setattr(runner, "_feature_views", denied)
    with pytest.raises(core.ResearchContractError, match=code):
        runner.run_synthetic(root, smoke=True)
    assert not (root / "file-manifest.json").exists()
    assert not (root / "diagnostics.json").exists()
    failure_record = json.loads((root / "failure.json").read_text())
    assert failure_record["error_code"] == code and failure_record["real_readers"] == 0
    assert failure_record["state"] == "LOCAL_BLOCKED"
    with pytest.raises(core.ResearchContractError, match="INCOMPLETE_OUTPUT"):
        runner.replay(root)


@pytest.mark.parametrize(
    "change, expected",
    (
        ("probability", "FILE_HASH_CONFLICT"),
        ("extra", "INCOMPLETE_OUTPUT"),
        ("missing", "INCOMPLETE_OUTPUT"),
        ("symlink", "SYMLINK_REJECTED"),
        ("binding", "REPLAY_IDENTITY_CONFLICT"),
        ("duplicate_json", "MALFORMED_JSON"),
    ),
)
def test_replay_rejects_tampering_without_recomputation(
    tmp_path: Path, frozen_smoke: Path, change: str, expected: str
) -> None:
    root = tmp_path / "tampered"
    shutil.copytree(frozen_smoke, root)
    if change == "probability":
        path = root / "predictions.csv"
        path.write_bytes(
            path.read_bytes().replace(b"0.500000000000", b"0.900000000000", 1)
        )
    elif change == "extra":
        (root / "extra.json").write_text("{}")
    elif change == "missing":
        (root / "label-rows.csv").unlink()
    elif change == "symlink":
        path = root / "predictions.csv"
        path.unlink()
        path.symlink_to(frozen_smoke / "predictions.csv")
    else:
        path = root / "predictions.json"
        if change == "binding":
            value = json.loads(path.read_bytes())
            value["model_identity"] = "0" * 64
            path.write_bytes(core.canonical_bytes(value))
        else:
            path.write_bytes(b'{"rows":[],"rows":[]}')
        manifest_path = root / "file-manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["files"]["predictions.json"] = {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size,
        }
        manifest_path.write_bytes(core.canonical_bytes(manifest))
    with pytest.raises(core.ResearchContractError, match=expected):
        runner.replay(root)


def test_runner_has_no_real_reader_owner_or_network_imports() -> None:
    tree = ast.parse(Path(runner.__file__).read_text())
    imports = {
        node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    } | {
        a.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for a in node.names
    }
    assert not any(
        name.startswith(("crypto_quant", "requests", "socket", "subprocess", "urllib"))
        for name in imports
    )
    assert runner.MAX_SECONDS == 120 and runner.MAX_BYTES == 32 * 1024 * 1024
