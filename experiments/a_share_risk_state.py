"""Research-only KSTAR relative-risk state signal."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_CEILING, Decimal
from enum import Enum


@dataclass(frozen=True, slots=True)
class PricePoint:
    trading_date: date
    close: Decimal
    turnover: Decimal | None = None

    def __post_init__(self) -> None:
        if type(self.trading_date) is not date:
            raise TypeError("trading_date must be a date")
        if type(self.close) is not Decimal or not self.close.is_finite():
            raise TypeError("close must be a finite Decimal")
        if self.close <= 0:
            raise ValueError("close must be positive")
        if self.turnover is not None:
            if type(self.turnover) is not Decimal or not self.turnover.is_finite():
                raise TypeError("turnover must be a finite Decimal or None")
            if self.turnover < 0:
                raise ValueError("turnover must be nonnegative")


@dataclass(frozen=True, slots=True)
class CloseSeries:
    instrument: str
    points: tuple[PricePoint, ...]

    def __post_init__(self) -> None:
        if type(self.instrument) is not str or not self.instrument.strip():
            raise ValueError("instrument must be a nonempty string")
        if type(self.points) is not tuple or not self.points:
            raise ValueError("points must be a nonempty tuple")
        if any(type(point) is not PricePoint for point in self.points):
            raise TypeError("points must contain PricePoint values")
        dates = tuple(point.trading_date for point in self.points)
        if dates != tuple(sorted(set(dates))):
            raise ValueError("point dates must be strictly increasing and unique")


@dataclass(frozen=True, slots=True)
class RiskStateConfig:
    trend_window: int = 120
    relative_window: int = 60
    breadth_window: int = 60
    breadth_threshold: Decimal = Decimal("0.55")
    minimum_coverage: Decimal = Decimal("0.80")

    def __post_init__(self) -> None:
        for name in ("trend_window", "relative_window", "breadth_window"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        for name in ("breadth_threshold", "minimum_coverage"):
            value = getattr(self, name)
            if type(value) is not Decimal or not value.is_finite():
                raise TypeError(f"{name} must be a finite Decimal")
            if not Decimal("0") <= value <= Decimal("1"):
                raise ValueError(f"{name} must be between zero and one")


@dataclass(frozen=True, slots=True)
class RiskStateSignal:
    decision_date: date
    risk_on: bool
    trend_ok: bool
    relative_strength_ok: bool
    breadth_ok: bool
    coverage_ok: bool
    target_above_moving_average: Decimal
    relative_excess_return: Decimal
    breadth: Decimal
    coverage: Decimal
    eligible_constituents: int
    expected_constituents: int


@dataclass(frozen=True, slots=True)
class BreadthSnapshot:
    trading_date: date
    breadth: Decimal
    coverage: Decimal
    eligible_count: int
    expected_count: int

    def __post_init__(self) -> None:
        if type(self.trading_date) is not date:
            raise TypeError("trading_date must be a date")
        for name in ("breadth", "coverage"):
            value = getattr(self, name)
            if type(value) is not Decimal or not value.is_finite():
                raise TypeError(f"{name} must be a finite Decimal")
            if not Decimal("0") <= value <= Decimal("1"):
                raise ValueError(f"{name} must be between zero and one")
        if type(self.expected_count) is not int or self.expected_count <= 0:
            raise ValueError("expected_count must be a positive integer")
        if (
            type(self.eligible_count) is not int
            or not 0 <= self.eligible_count <= self.expected_count
        ):
            raise ValueError("eligible_count must be between zero and expected_count")
        if self.coverage != Decimal(self.eligible_count) / Decimal(self.expected_count):
            raise ValueError("coverage must match eligible and expected counts")


@dataclass(frozen=True, slots=True)
class EarlyWarningSignal:
    decision_date: date
    watch: bool
    conditions_met: int
    breadth_acceleration_ok: bool
    relative_strength_turn_ok: bool
    volatility_compression_ok: bool
    turnover_expansion_ok: bool
    sector_diffusion_ok: bool
    breadth_acceleration: Decimal
    relative_strength_spread: Decimal
    relative_strength_ma_slope: Decimal
    current_bandwidth: Decimal
    bandwidth_cutoff: Decimal
    turnover_ratio: Decimal
    sector_diffusion: Decimal


class RiskPhase(str, Enum):
    OFF = "off"
    WATCH = "watch"
    ON = "on"


DEFAULT_CONFIG = RiskStateConfig()
EARLY_CONFIRMATION_CONFIG = RiskStateConfig(
    trend_window=60,
    relative_window=20,
    breadth_window=60,
)

_BREADTH_ACCELERATION_THRESHOLD = Decimal("0.20")
_MINIMUM_BREADTH_COVERAGE = Decimal("0.80")
_RELATIVE_MA_WINDOW = 20
_RELATIVE_SLOPE_LOOKBACK = 5
_VOLATILITY_WINDOW = 20
_VOLATILITY_HISTORY = 252
_VOLATILITY_PERCENTILE = Decimal("0.30")
_TURNOVER_SHORT_WINDOW = 5
_TURNOVER_LONG_WINDOW = 20
_TURNOVER_RATIO_THRESHOLD = Decimal("1.30")
_SECTOR_RETURN_WINDOW = 20
_SECTOR_DIFFUSION_THRESHOLD = Decimal("2") / Decimal("3")
_MINIMUM_SECTOR_COUNT = 3
_MINIMUM_WARNING_CONDITIONS = 3


def evaluate_risk_state(
    *,
    target: CloseSeries,
    benchmark: CloseSeries,
    constituents: tuple[CloseSeries, ...],
    expected_constituent_count: int,
    config: RiskStateConfig = DEFAULT_CONFIG,
) -> RiskStateSignal:
    """Evaluate the frozen weekly risk-on conditions using only visible closes."""
    if type(target) is not CloseSeries or type(benchmark) is not CloseSeries:
        raise TypeError("target and benchmark must be CloseSeries values")
    if type(constituents) is not tuple or any(
        type(series) is not CloseSeries for series in constituents
    ):
        raise TypeError("constituents must be a tuple of CloseSeries values")
    if type(expected_constituent_count) is not int or expected_constituent_count <= 0:
        raise ValueError("expected_constituent_count must be a positive integer")
    if type(config) is not RiskStateConfig:
        raise TypeError("config must be RiskStateConfig")
    if len(constituents) > expected_constituent_count:
        raise ValueError("constituents cannot exceed expected_constituent_count")
    instruments = tuple(series.instrument for series in constituents)
    if len(instruments) != len(set(instruments)):
        raise ValueError("constituent instruments must be unique")

    (
        decision_date,
        target_above_moving_average,
        trend_ok,
        relative_excess_return,
        relative_strength_ok,
    ) = _trend_and_relative(target, benchmark, config)

    eligible = tuple(
        series
        for series in constituents
        if len(series.points) >= config.breadth_window
        and series.points[-1].trading_date == decision_date
    )
    coverage = Decimal(len(eligible)) / Decimal(expected_constituent_count)
    breadth = (
        Decimal(
            sum(
                series.points[-1].close
                > _mean(
                    tuple(
                        point.close
                        for point in series.points[-config.breadth_window :]
                    )
                )
                for series in eligible
            )
        )
        / Decimal(len(eligible))
        if eligible
        else Decimal("0")
    )
    breadth_ok = breadth >= config.breadth_threshold
    coverage_ok = coverage >= config.minimum_coverage
    risk_on = trend_ok and relative_strength_ok and breadth_ok and coverage_ok

    return RiskStateSignal(
        decision_date=decision_date,
        risk_on=risk_on,
        trend_ok=trend_ok,
        relative_strength_ok=relative_strength_ok,
        breadth_ok=breadth_ok,
        coverage_ok=coverage_ok,
        target_above_moving_average=target_above_moving_average,
        relative_excess_return=relative_excess_return,
        breadth=breadth,
        coverage=coverage,
        eligible_constituents=len(eligible),
        expected_constituents=expected_constituent_count,
    )


def evaluate_risk_state_from_breadth(
    *,
    target: CloseSeries,
    benchmark: CloseSeries,
    breadth: BreadthSnapshot,
    config: RiskStateConfig = DEFAULT_CONFIG,
) -> RiskStateSignal:
    """Evaluate confirmation from a point-in-time precomputed breadth snapshot."""
    if type(target) is not CloseSeries or type(benchmark) is not CloseSeries:
        raise TypeError("target and benchmark must be CloseSeries values")
    if type(breadth) is not BreadthSnapshot:
        raise TypeError("breadth must be BreadthSnapshot")
    if type(config) is not RiskStateConfig:
        raise TypeError("config must be RiskStateConfig")
    (
        decision_date,
        target_above_moving_average,
        trend_ok,
        relative_excess_return,
        relative_strength_ok,
    ) = _trend_and_relative(target, benchmark, config)
    if breadth.trading_date != decision_date:
        raise ValueError("breadth must match the decision date")
    breadth_ok = breadth.breadth >= config.breadth_threshold
    coverage_ok = breadth.coverage >= config.minimum_coverage
    return RiskStateSignal(
        decision_date=decision_date,
        risk_on=trend_ok and relative_strength_ok and breadth_ok and coverage_ok,
        trend_ok=trend_ok,
        relative_strength_ok=relative_strength_ok,
        breadth_ok=breadth_ok,
        coverage_ok=coverage_ok,
        target_above_moving_average=target_above_moving_average,
        relative_excess_return=relative_excess_return,
        breadth=breadth.breadth,
        coverage=breadth.coverage,
        eligible_constituents=breadth.eligible_count,
        expected_constituents=breadth.expected_count,
    )


def evaluate_early_warning(
    *,
    target: CloseSeries,
    benchmark: CloseSeries,
    current_breadth: BreadthSnapshot,
    prior_breadth: BreadthSnapshot,
    sectors: tuple[CloseSeries, ...],
) -> EarlyWarningSignal:
    """Evaluate five frozen leading conditions without making a trade decision."""
    if type(target) is not CloseSeries or type(benchmark) is not CloseSeries:
        raise TypeError("target and benchmark must be CloseSeries values")
    if type(current_breadth) is not BreadthSnapshot or type(
        prior_breadth
    ) is not BreadthSnapshot:
        raise TypeError("breadth inputs must be BreadthSnapshot values")
    if type(sectors) is not tuple or any(
        type(sector) is not CloseSeries for sector in sectors
    ):
        raise TypeError("sectors must be a tuple of CloseSeries values")
    if len(sectors) < _MINIMUM_SECTOR_COUNT:
        raise ValueError(f"at least {_MINIMUM_SECTOR_COUNT} sectors are required")
    if len({sector.instrument for sector in sectors}) != len(sectors):
        raise ValueError("sector instruments must be unique")

    decision_date = target.points[-1].trading_date
    if current_breadth.trading_date != decision_date:
        raise ValueError("current breadth must match the decision date")
    _require_history(target, _VOLATILITY_HISTORY + _VOLATILITY_WINDOW - 1)
    expected_prior_date = target.points[-11].trading_date
    if prior_breadth.trading_date != expected_prior_date:
        raise ValueError("prior breadth must be exactly ten target observations earlier")

    breadth_acceleration = current_breadth.breadth - prior_breadth.breadth
    breadth_acceleration_ok = (
        current_breadth.coverage >= _MINIMUM_BREADTH_COVERAGE
        and prior_breadth.coverage >= _MINIMUM_BREADTH_COVERAGE
        and breadth_acceleration >= _BREADTH_ACCELERATION_THRESHOLD
    )

    target_closes, benchmark_closes = _aligned_closes(
        target,
        benchmark,
        _RELATIVE_MA_WINDOW + _RELATIVE_SLOPE_LOOKBACK,
    )
    relative_values = tuple(
        target_close / benchmark_close
        for target_close, benchmark_close in zip(
            target_closes, benchmark_closes, strict=True
        )
    )
    current_relative_ma = _mean(relative_values[-_RELATIVE_MA_WINDOW:])
    prior_relative_ma = _mean(
        relative_values[
            -_RELATIVE_MA_WINDOW - _RELATIVE_SLOPE_LOOKBACK :
            -_RELATIVE_SLOPE_LOOKBACK
        ]
    )
    relative_strength_spread = (
        relative_values[-1] / current_relative_ma - Decimal("1")
    )
    relative_strength_ma_slope = (
        current_relative_ma / prior_relative_ma - Decimal("1")
    )
    relative_strength_turn_ok = (
        relative_strength_spread > 0 and relative_strength_ma_slope > 0
    )

    bandwidths = _bandwidth_history(target)
    current_bandwidth = bandwidths[-1]
    bandwidth_cutoff = _nearest_rank(
        bandwidths,
        _VOLATILITY_PERCENTILE,
    )
    volatility_compression_ok = current_bandwidth <= bandwidth_cutoff

    turnover_points = target.points[-_TURNOVER_LONG_WINDOW:]
    if any(point.turnover is None for point in turnover_points):
        raise ValueError("target turnover is required for the last 20 observations")
    turnovers = tuple(
        point.turnover for point in turnover_points if point.turnover is not None
    )
    long_turnover = _mean(turnovers)
    if long_turnover == 0:
        raise ValueError("long-window turnover must be positive")
    turnover_ratio = _mean(turnovers[-_TURNOVER_SHORT_WINDOW:]) / long_turnover
    turnover_expansion_ok = turnover_ratio >= _TURNOVER_RATIO_THRESHOLD

    sector_outperformance = tuple(
        _relative_return(sector, benchmark, _SECTOR_RETURN_WINDOW) > 0
        for sector in sectors
    )
    sector_diffusion = Decimal(sum(sector_outperformance)) / Decimal(len(sectors))
    sector_diffusion_ok = sector_diffusion >= _SECTOR_DIFFUSION_THRESHOLD

    conditions_met = sum(
        (
            breadth_acceleration_ok,
            relative_strength_turn_ok,
            volatility_compression_ok,
            turnover_expansion_ok,
            sector_diffusion_ok,
        )
    )
    return EarlyWarningSignal(
        decision_date=decision_date,
        watch=conditions_met >= _MINIMUM_WARNING_CONDITIONS,
        conditions_met=conditions_met,
        breadth_acceleration_ok=breadth_acceleration_ok,
        relative_strength_turn_ok=relative_strength_turn_ok,
        volatility_compression_ok=volatility_compression_ok,
        turnover_expansion_ok=turnover_expansion_ok,
        sector_diffusion_ok=sector_diffusion_ok,
        breadth_acceleration=breadth_acceleration,
        relative_strength_spread=relative_strength_spread,
        relative_strength_ma_slope=relative_strength_ma_slope,
        current_bandwidth=current_bandwidth,
        bandwidth_cutoff=bandwidth_cutoff,
        turnover_ratio=turnover_ratio,
        sector_diffusion=sector_diffusion,
    )


def classify_phase(
    *, warning: EarlyWarningSignal, confirmation: RiskStateSignal
) -> RiskPhase:
    """Classify the current state; confirmation takes precedence over warning."""
    if type(warning) is not EarlyWarningSignal:
        raise TypeError("warning must be EarlyWarningSignal")
    if type(confirmation) is not RiskStateSignal:
        raise TypeError("confirmation must be RiskStateSignal")
    if warning.decision_date != confirmation.decision_date:
        raise ValueError("warning and confirmation dates must match")
    if confirmation.risk_on:
        return RiskPhase.ON
    if warning.watch:
        return RiskPhase.WATCH
    return RiskPhase.OFF


def _trend_and_relative(
    target: CloseSeries,
    benchmark: CloseSeries,
    config: RiskStateConfig,
) -> tuple[date, Decimal, bool, Decimal, bool]:
    decision_date = target.points[-1].trading_date
    if benchmark.points[-1].trading_date != decision_date:
        raise ValueError("target and benchmark must end on the same decision date")
    _require_history(target, max(config.trend_window, config.relative_window + 1))
    _require_history(benchmark, config.relative_window + 1)
    target_start = target.points[-config.relative_window - 1]
    benchmark_start = benchmark.points[-config.relative_window - 1]
    if target_start.trading_date != benchmark_start.trading_date:
        raise ValueError("target and benchmark relative windows must align")
    target_close = target.points[-1].close
    trend_average = _mean(
        tuple(point.close for point in target.points[-config.trend_window :])
    )
    target_above_moving_average = target_close / trend_average - Decimal("1")
    relative_excess_return = (
        target_close / target_start.close
        - benchmark.points[-1].close / benchmark_start.close
    )
    return (
        decision_date,
        target_above_moving_average,
        target_above_moving_average > 0,
        relative_excess_return,
        relative_excess_return > 0,
    )


def _require_history(series: CloseSeries, minimum: int) -> None:
    if len(series.points) < minimum:
        raise ValueError(f"{series.instrument} requires at least {minimum} closes")


def _aligned_closes(
    left: CloseSeries,
    right: CloseSeries,
    count: int,
) -> tuple[tuple[Decimal, ...], tuple[Decimal, ...]]:
    _require_history(left, count)
    _require_history(right, count)
    left_points = left.points[-count:]
    right_points = right.points[-count:]
    if tuple(point.trading_date for point in left_points) != tuple(
        point.trading_date for point in right_points
    ):
        raise ValueError(f"{left.instrument} and {right.instrument} dates must align")
    return (
        tuple(point.close for point in left_points),
        tuple(point.close for point in right_points),
    )


def _relative_return(
    target: CloseSeries,
    benchmark: CloseSeries,
    window: int,
) -> Decimal:
    target_by_date = {point.trading_date: point.close for point in target.points}
    benchmark_by_date = {
        point.trading_date: point.close for point in benchmark.points
    }
    dates = sorted(set(target_by_date) & set(benchmark_by_date))
    if len(dates) < window + 1:
        raise ValueError(
            f"{target.instrument} and {benchmark.instrument} require "
            f"{window + 1} common observations"
        )
    start, end = dates[-window - 1], dates[-1]
    return (
        target_by_date[end] / target_by_date[start]
        - benchmark_by_date[end] / benchmark_by_date[start]
    )


def _bandwidth_history(series: CloseSeries) -> tuple[Decimal, ...]:
    closes = tuple(
        point.close
        for point in series.points[
            -(_VOLATILITY_HISTORY + _VOLATILITY_WINDOW - 1) :
        ]
    )
    return tuple(
        _bollinger_bandwidth(closes[end - _VOLATILITY_WINDOW : end])
        for end in range(_VOLATILITY_WINDOW, len(closes) + 1)
    )


def _bollinger_bandwidth(values: tuple[Decimal, ...]) -> Decimal:
    average = _mean(values)
    variance = _mean(tuple((value - average) ** 2 for value in values))
    return Decimal("4") * variance.sqrt() / average


def _nearest_rank(values: tuple[Decimal, ...], percentile: Decimal) -> Decimal:
    rank = int(
        (Decimal(len(values)) * percentile).to_integral_value(
            rounding=ROUND_CEILING
        )
    )
    return sorted(values)[max(rank - 1, 0)]


def _mean(values: tuple[Decimal, ...]) -> Decimal:
    return sum(values, Decimal("0")) / Decimal(len(values))
