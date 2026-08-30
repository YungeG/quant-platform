from datetime import date, timedelta
from decimal import Decimal

import pytest

from experiments.a_share_risk_state import (
    EARLY_CONFIRMATION_CONFIG,
    BreadthSnapshot,
    CloseSeries,
    PricePoint,
    RiskPhase,
    classify_phase,
    evaluate_early_warning,
    evaluate_risk_state,
    evaluate_risk_state_from_breadth,
)


DECISION_DATE = date(2025, 6, 30)


def series(
    instrument: str,
    closes: tuple[int, ...],
    *,
    end: date = DECISION_DATE,
    turnovers: tuple[int, ...] | None = None,
) -> CloseSeries:
    if turnovers is not None and len(turnovers) != len(closes):
        raise ValueError("turnovers must align with closes")
    start = end - timedelta(days=len(closes) - 1)
    return CloseSeries(
        instrument,
        tuple(
            PricePoint(
                start + timedelta(days=index),
                Decimal(close),
                None if turnovers is None else Decimal(turnovers[index]),
            )
            for index, close in enumerate(closes)
        ),
    )


def rising(instrument: str, count: int = 120) -> CloseSeries:
    return series(instrument, tuple(range(100, 100 + count)))


def flat(instrument: str, count: int = 120) -> CloseSeries:
    return series(instrument, (100,) * count)


def falling(instrument: str, count: int = 60) -> CloseSeries:
    return series(instrument, tuple(range(200, 200 - count, -1)))


def early_target(*, expanding_turnover: bool = True) -> CloseSeries:
    closes = tuple(90 if index % 2 == 0 else 110 for index in range(270)) + tuple(
        range(100, 130)
    )
    turnovers = (100,) * 295 + ((200,) * 5 if expanding_turnover else (100,) * 5)
    return series("kstar-growth", closes, turnovers=turnovers)


def warning(*, active: bool = True):
    target = early_target(expanding_turnover=active)
    current_breadth = BreadthSnapshot(
        DECISION_DATE,
        Decimal("0.70") if active else Decimal("0.45"),
        Decimal("0.95"),
        95,
        100,
    )
    prior_breadth = BreadthSnapshot(
        target.points[-11].trading_date,
        Decimal("0.40"),
        Decimal("0.95"),
        95,
        100,
    )
    sectors = (
        (rising("semiconductor", 300), rising("software", 300), flat("equipment", 300))
        if active
        else (flat("semiconductor", 300), flat("software", 300), flat("equipment", 300))
    )
    return evaluate_early_warning(
        target=target,
        benchmark=flat("csi-300", 300),
        current_breadth=current_breadth,
        prior_breadth=prior_breadth,
        sectors=sectors,
    )


def confirmation(*, active: bool):
    constituents = (
        (rising("a", 60), rising("b", 60), rising("c", 60))
        if active
        else (rising("a", 60), falling("b"), falling("c"))
    )
    return evaluate_risk_state(
        target=rising("kstar-growth"),
        benchmark=flat("csi-300"),
        constituents=constituents,
        expected_constituent_count=3,
        config=EARLY_CONFIRMATION_CONFIG,
    )


def test_all_conditions_enable_risk_on() -> None:
    signal = evaluate_risk_state(
        target=rising("kstar-growth"),
        benchmark=flat("csi-300"),
        constituents=(rising("a", 60), rising("b", 60), falling("c")),
        expected_constituent_count=3,
    )

    assert signal.risk_on is True
    assert signal.trend_ok is True
    assert signal.relative_strength_ok is True
    assert signal.breadth == Decimal("2") / Decimal("3")
    assert signal.coverage == Decimal("1")


def test_relative_underperformance_disables_risk_on() -> None:
    signal = evaluate_risk_state(
        target=rising("kstar-growth"),
        benchmark=series("csi-300", tuple(range(100, 340, 2))),
        constituents=(rising("a", 60), rising("b", 60), rising("c", 60)),
        expected_constituent_count=3,
    )

    assert signal.relative_strength_ok is False
    assert signal.risk_on is False


def test_weak_breadth_disables_risk_on() -> None:
    signal = evaluate_risk_state(
        target=rising("kstar-growth"),
        benchmark=flat("csi-300"),
        constituents=(rising("a", 60), falling("b"), falling("c")),
        expected_constituent_count=3,
    )

    assert signal.breadth == Decimal("1") / Decimal("3")
    assert signal.breadth_ok is False
    assert signal.risk_on is False


def test_incomplete_constituent_coverage_fails_closed() -> None:
    signal = evaluate_risk_state(
        target=rising("kstar-growth"),
        benchmark=flat("csi-300"),
        constituents=(rising("a", 60), rising("b", 60)),
        expected_constituent_count=3,
    )

    assert signal.breadth == Decimal("1")
    assert signal.coverage == Decimal("2") / Decimal("3")
    assert signal.coverage_ok is False
    assert signal.risk_on is False


def test_target_and_benchmark_decision_dates_must_match() -> None:
    with pytest.raises(ValueError, match="same decision date"):
        evaluate_risk_state(
            target=rising("kstar-growth"),
            benchmark=series(
                "csi-300",
                (100,) * 120,
                end=DECISION_DATE - timedelta(days=1),
            ),
            constituents=(rising("a", 60),),
            expected_constituent_count=1,
        )


def test_relative_windows_must_align() -> None:
    benchmark_points = list(flat("csi-300").points)
    shifted = tuple(
        PricePoint(
            point.trading_date
            - (timedelta(days=1) if index <= 59 else timedelta()),
            point.close,
        )
        for index, point in enumerate(benchmark_points)
    )
    benchmark = CloseSeries("csi-300", shifted)

    with pytest.raises(ValueError, match="relative windows must align"):
        evaluate_risk_state(
            target=rising("kstar-growth"),
            benchmark=benchmark,
            constituents=(rising("a", 60),),
            expected_constituent_count=1,
        )


def test_leading_conditions_raise_watch_signal() -> None:
    signal = warning()

    assert signal.watch is True
    assert signal.conditions_met == 5
    assert signal.breadth_acceleration == Decimal("0.30")
    assert signal.turnover_ratio > Decimal("1.30")
    assert signal.sector_diffusion == Decimal("2") / Decimal("3")


def test_fewer_than_three_conditions_stay_off() -> None:
    signal = warning(active=False)

    assert signal.watch is False
    assert signal.conditions_met == 2
    assert signal.breadth_acceleration_ok is False
    assert signal.turnover_expansion_ok is False
    assert signal.sector_diffusion_ok is False


def test_turnover_evidence_is_required() -> None:
    target = early_target()
    target_without_turnover = CloseSeries(
        target.instrument,
        tuple(PricePoint(point.trading_date, point.close) for point in target.points),
    )

    with pytest.raises(ValueError, match="target turnover is required"):
        evaluate_early_warning(
            target=target_without_turnover,
            benchmark=flat("csi-300", 300),
            current_breadth=BreadthSnapshot(
                DECISION_DATE, Decimal("0.70"), Decimal("0.95"), 95, 100
            ),
            prior_breadth=BreadthSnapshot(
                target.points[-11].trading_date,
                Decimal("0.40"),
                Decimal("0.95"),
                95,
                100,
            ),
            sectors=(
                rising("semiconductor", 300),
                rising("software", 300),
                flat("equipment", 300),
            ),
        )


def test_confirmation_takes_phase_precedence() -> None:
    assert classify_phase(warning=warning(), confirmation=confirmation(active=True)) is RiskPhase.ON
    assert classify_phase(warning=warning(), confirmation=confirmation(active=False)) is RiskPhase.WATCH
    assert classify_phase(
        warning=warning(active=False), confirmation=confirmation(active=False)
    ) is RiskPhase.OFF


def test_precomputed_breadth_uses_the_same_confirmation_rules() -> None:
    signal = evaluate_risk_state_from_breadth(
        target=rising("kstar-growth"),
        benchmark=flat("csi-300"),
        breadth=BreadthSnapshot(
            DECISION_DATE,
            Decimal("0.60"),
            Decimal("0.90"),
            90,
            100,
        ),
        config=EARLY_CONFIRMATION_CONFIG,
    )

    assert signal.risk_on is True
    assert signal.eligible_constituents == 90
    assert signal.expected_constituents == 100
