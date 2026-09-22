"""Point-in-time sector/high-volatility watchlist; no orders or return simulation."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Context, Decimal, localcontext
from enum import Enum
from statistics import stdev

from experiments.a_share_market_regime import (
    CHINA_TZ,
    MarketPhase,
    MarketRegime,
    PublishedIndexClose,
    evaluate_market_regime,
)
from experiments.a_share_risk_state import PricePoint


@dataclass(frozen=True, slots=True)
class PublishedStockClose:
    instrument: str
    sector: str
    point: PricePoint  # close is an adjusted, consistently based signal price, NOT a fill price.
    amount_cny: Decimal
    is_st: bool
    is_suspended: bool
    available_at: datetime  # Visibility of the entire row, including membership/status/adjustment.

    def __post_init__(self) -> None:
        if type(self.instrument) is not str or not re.fullmatch(
            r"(?:6[0-9]{5}\.SH|(?:00|30)[0-9]{4}\.SZ|[489][0-9]{5}\.BJ)", self.instrument
        ):
            raise ValueError("stock instrument must use an A-share code format, not an index, ETF or B-share")
        if type(self.sector) is not str or not self.sector.strip() or self.sector != self.sector.strip():
            raise ValueError("sector must be a nonempty, trimmed string")
        if type(self.point) is not PricePoint:
            raise TypeError("point must be PricePoint")
        if type(self.amount_cny) is not Decimal or not self.amount_cny.is_finite() or self.amount_cny < 0:
            raise ValueError("amount_cny must be a finite nonnegative Decimal in yuan")
        if type(self.is_st) is not bool or type(self.is_suspended) is not bool:
            raise TypeError("is_st and is_suspended must be booleans")
        if not isinstance(self.available_at, datetime) or self.available_at.utcoffset() is None:
            raise ValueError("available_at must be a timezone-aware datetime")
        available_at = self.available_at.astimezone(CHINA_TZ)
        if available_at < datetime.combine(self.point.trading_date, time(15), CHINA_TZ):
            raise ValueError("daily stock close cannot be available before the 15:00 session close")
        object.__setattr__(self, "available_at", available_at)


@dataclass(frozen=True, slots=True)
class StockScreenConfig:
    lookback: int = 20
    trend_window: int = 60
    min_annualized_volatility: Decimal = Decimal("0.30")
    max_annualized_volatility: Decimal = Decimal("0.80")
    min_average_amount_cny: Decimal = Decimal("100000000")

    def __post_init__(self) -> None:
        if type(self.lookback) is not int or self.lookback < 2:
            raise ValueError("lookback must be an integer >= 2")
        if type(self.trend_window) is not int or self.trend_window < 1:
            raise ValueError("trend_window must be a positive integer")
        for name in ("min_annualized_volatility", "max_annualized_volatility", "min_average_amount_cny"):
            value = getattr(self, name)
            if type(value) is not Decimal or not value.is_finite() or value < 0:
                raise ValueError(f"{name} must be a finite nonnegative Decimal")
        if not 0 <= self.min_annualized_volatility <= self.max_annualized_volatility or self.max_annualized_volatility == 0:
            raise ValueError("volatility bounds must satisfy 0 <= min <= max and max > 0")

    @property
    def required_sessions(self) -> int:
        return max(self.trend_window, self.lookback + 1)


DEFAULT_SCREEN_CONFIG = StockScreenConfig()


class StockScreenStatus(str, Enum):
    WATCH = "watch"
    REJECTED = "rejected"
    BLOCKED = "blocked"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class StockMetrics:
    adjusted_close: Decimal
    moving_average: Decimal
    momentum: Decimal
    annualized_volatility: Decimal
    average_amount_cny: Decimal
    previous_high: Decimal
    available_at: datetime


@dataclass(frozen=True, slots=True)
class StockDecision:
    instrument: str
    sector: str | None
    status: StockScreenStatus
    reasons: tuple[str, ...]
    metrics: StockMetrics | None = None


@dataclass(frozen=True, slots=True)
class SectorOpportunities:
    market: MarketRegime
    selected_sectors: tuple[str, ...]
    required_sessions: int
    watchlist: tuple[str, ...]
    stocks: tuple[StockDecision, ...]
    unresolved_sectors: tuple[str, ...]
    complete: bool  # Available input-pool checks only; never proof of sector-wide membership coverage.


def _metrics(points: tuple[PublishedStockClose, ...], config: StockScreenConfig) -> StockMetrics:
    with localcontext(Context(prec=28)):
        closes = [item.point.close for item in points]
        recent = closes[-config.lookback - 1 :]
        returns = [right / left - 1 for left, right in zip(recent, recent[1:])]
        # ponytail: fixed 252-session annualization is a diagnostic convention, not a forecast.
        volatility = stdev(returns) * Decimal(252).sqrt()
        return StockMetrics(
            closes[-1],
            sum(closes[-config.trend_window :], Decimal(0)) / config.trend_window,
            closes[-1] / closes[-config.lookback - 1] - 1,
            volatility,
            sum((item.amount_cny for item in points[-config.lookback :]), Decimal(0)) / config.lookback,
            max(closes[-config.lookback - 1 : -1]),
            max(item.available_at for item in points),
        )


def _screen_one(
    latest: PublishedStockClose,
    by_date: Mapping[date, PublishedStockClose],
    sessions: list[date],
    market: MarketRegime,
    config: StockScreenConfig,
) -> StockDecision:
    def decision(status: StockScreenStatus, *reasons: str, metrics: StockMetrics | None = None) -> StockDecision:
        return StockDecision(latest.instrument, latest.sector, status, reasons, metrics)

    if latest.point.trading_date != market.decision_date:
        return decision(StockScreenStatus.UNRESOLVED, "current_close_missing_or_unavailable")
    if latest.is_st or latest.is_suspended:
        status_reasons = tuple(name for name, flag in (("st_stock", latest.is_st), ("suspended", latest.is_suspended)) if flag)
        return decision(StockScreenStatus.REJECTED, *status_reasons)
    if len(sessions) < config.required_sessions:
        return decision(StockScreenStatus.UNRESOLVED, "insufficient_calendar_history")
    window = sessions[-config.required_sessions :]
    missing = next((day for day in window if day not in by_date), None)
    if missing is not None:
        return decision(StockScreenStatus.UNRESOLVED, f"missing_close: {missing}")
    points = tuple(by_date[day] for day in window)
    if any(item.available_at > market.as_of for item in points):
        return decision(StockScreenStatus.UNRESOLVED, "history_not_available")
    if any(item.is_suspended or item.amount_cny == 0 for item in points):
        return decision(StockScreenStatus.UNRESOLVED, "nontrading_session_in_history")

    metrics = _metrics(points, config)
    reasons: list[str] = []
    if metrics.annualized_volatility < config.min_annualized_volatility:
        reasons.append("volatility_too_low")
    if metrics.annualized_volatility > config.max_annualized_volatility:
        reasons.append("volatility_too_high")
    if metrics.average_amount_cny < config.min_average_amount_cny:
        reasons.append("insufficient_liquidity")
    if metrics.adjusted_close <= metrics.moving_average or metrics.momentum <= 0:
        reasons.append("uptrend_not_confirmed")
    if reasons:
        return decision(StockScreenStatus.REJECTED, *reasons, metrics=metrics)
    if market.phase is MarketPhase.UNKNOWN:
        return decision(StockScreenStatus.UNRESOLVED, "market_unknown", metrics=metrics)
    if market.phase is MarketPhase.BEAR:
        return decision(StockScreenStatus.BLOCKED, "bear_market", metrics=metrics)
    if market.phase is MarketPhase.TRANSITION:
        if metrics.adjusted_close <= metrics.previous_high:
            return decision(StockScreenStatus.REJECTED, "transition_requires_breakout", metrics=metrics)
        return decision(StockScreenStatus.WATCH, "transition_breakout_watch_only", metrics=metrics)
    return decision(StockScreenStatus.WATCH, "bull_trend_watch_only", metrics=metrics)


def evaluate_sector_opportunities(
    *,
    index_observations: tuple[PublishedIndexClose, ...],
    stock_observations: tuple[PublishedStockClose, ...],
    calendar: Mapping[date, bool],
    as_of: datetime,
    selected_sectors: tuple[str, ...],
    config: StockScreenConfig = DEFAULT_SCREEN_CONFIG,
) -> SectorOpportunities:
    """Compute the market gate and stock watchlist at the SAME explicit cutoff.

    Sector/status come from each stock's latest visible row, never a future row.
    Each scoped stock needs the latest completed session and uninterrupted history.
    Missing members cannot be inferred from prices: this screens only the supplied
    pool and makes no claim of sector-wide or provider-complete coverage.
    """
    if type(config) is not StockScreenConfig:
        raise TypeError("config must be StockScreenConfig")
    if type(selected_sectors) is not tuple or not selected_sectors or any(
        type(sector) is not str or not sector.strip() or sector != sector.strip()
        for sector in selected_sectors
    ):
        raise ValueError("selected_sectors must be a nonempty tuple of trimmed sector names")
    if len(set(selected_sectors)) != len(selected_sectors):
        raise ValueError("selected_sectors must be unique")
    sectors = tuple(sorted(selected_sectors))
    if type(stock_observations) is not tuple or any(type(item) is not PublishedStockClose for item in stock_observations):
        raise TypeError("stock_observations must be a tuple of PublishedStockClose values")
    market = evaluate_market_regime(observations=index_observations, calendar=calendar, as_of=as_of)
    by_instrument: dict[str, dict[date, PublishedStockClose]] = {}
    for item in stock_observations:
        day = item.point.trading_date
        by_date = by_instrument.setdefault(item.instrument, {})
        if day in by_date:
            raise ValueError(f"duplicate stock/date: {item.instrument} {day}; supply one frozen revision")
        if day in calendar and not calendar[day]:
            raise ValueError(f"stock close on a closed session: {item.instrument} {day}")
        by_date[day] = item

    if market.decision_date is None:
        return SectorOpportunities(market, sectors, config.required_sessions, (), (), sectors, False)
    sessions = sorted(day for day, is_open in calendar.items() if is_open and day <= market.decision_date)
    decisions: list[StockDecision] = []
    seen_sectors: set[str] = set()
    for instrument in sorted(by_instrument):
        by_date = by_instrument[instrument]
        visible = [item for day, item in by_date.items() if day <= market.decision_date and item.available_at <= market.as_of]
        if not visible:
            if any(day <= market.decision_date for day in by_date):
                decisions.append(StockDecision(
                    instrument, None, StockScreenStatus.UNRESOLVED, ("sector_and_price_not_available",),
                ))
            continue
        latest = max(visible, key=lambda item: item.point.trading_date)
        if latest.sector not in sectors:
            continue
        seen_sectors.add(latest.sector)
        decisions.append(_screen_one(latest, by_date, sessions, market, config))
    unresolved_sectors = tuple(sector for sector in sectors if sector not in seen_sectors)
    # Momentum orders inspection priority; it is NOT a predicted return or position size.
    ranked = sorted(
        ((item.metrics.momentum, item.instrument) for item in decisions
         if item.status is StockScreenStatus.WATCH and item.metrics is not None),
        key=lambda pair: pair[0], reverse=True,
    )
    complete = market.phase is not MarketPhase.UNKNOWN and not unresolved_sectors and all(
        item.status is not StockScreenStatus.UNRESOLVED for item in decisions
    )
    return SectorOpportunities(
        market, sectors, config.required_sessions, tuple(instrument for _, instrument in ranked),
        tuple(decisions), unresolved_sectors, complete,
    )
