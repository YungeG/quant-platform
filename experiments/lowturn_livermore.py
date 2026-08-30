"""Small event-driven simulator for low-turnover Livermore research."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import floor
from typing import Callable, Sequence


@dataclass(frozen=True)
class Bar:
    adj_open: float
    adj_close: float
    raw_open: float
    raw_high: float
    raw_low: float
    raw_close: float
    volume: float
    pct_change: float


@dataclass(frozen=True)
class Candidate:
    symbol: str
    score: float
    risk_pct: float = 0.08
    max_entry_price: float | None = None


@dataclass
class Order:
    symbol: str
    side: str
    reason: str
    due_index: int
    fraction: float = 0.0
    risk_pct: float = 0.08
    max_entry_price: float | None = None
    retries: int = 0


@dataclass
class Position:
    symbol: str
    shares: float
    units: int
    first_entry_price: float
    average_cost: float
    highest_close: float
    last_close: float
    entry_index: int
    risk_pct: float
    hard_stop_price: float


@dataclass(frozen=True)
class StrategyConfig:
    name: str
    max_positions: int = 4
    initial_fraction: float = 1.0 / 12.0
    add_fraction: float = 1.0 / 12.0
    pyramid: bool = True
    max_units: int = 3
    add_thresholds: tuple[float, ...] = (0.05, 0.10)
    risk_sized: bool = False
    risk_per_unit: float = 0.005
    trailing_r_multiple: float = 1.5
    stop_enabled: bool = True
    stop_loss: float = 0.08
    trailing_stop: float = 0.12
    fixed_hold_days: int | None = None
    buy_cost: float = 0.0013
    sell_cost: float = 0.0018
    buy_retry_days: int = 3
    lot_size: int = 100
    initial_nav: float = 400_000.0


@dataclass
class SimulationResult:
    dates: list[str]
    nav: list[float]
    gross_exposure: list[float]
    benchmark_returns: list[float]
    trades: list[dict] = field(default_factory=list)
    blocked_buys: int = 0
    blocked_sells: int = 0
    expired_buys: int = 0
    gap_skips: int = 0
    missing_valuation_days: int = 0
    position_days: int = 0
    final_cash: float = 0.0
    final_positions: dict[str, Position] = field(default_factory=dict)


def one_price_limit_up(bar: Bar) -> bool:
    return (
        bar.raw_open == bar.raw_high == bar.raw_low == bar.raw_close
        and bar.pct_change >= 4.5
    )


def one_price_limit_down(bar: Bar) -> bool:
    return (
        bar.raw_open == bar.raw_high == bar.raw_low == bar.raw_close
        and bar.pct_change <= -4.5
    )


def simulate(
    dates: Sequence[str],
    bar_lookup: Callable[[str, str], Bar | None],
    candidates: dict[str, list[Candidate]],
    benchmark_returns: dict[str, float],
    config: StrategyConfig,
    add_allowed: dict[str, bool] | None = None,
) -> SimulationResult:
    cash = float(config.initial_nav)
    positions: dict[str, Position] = {}
    pending: list[Order] = []
    last_nav = float(config.initial_nav)
    result = SimulationResult(dates=[], nav=[], gross_exposure=[], benchmark_returns=[])

    def valuation(price_field: str, date: str) -> float:
        total = cash
        for position in positions.values():
            bar = bar_lookup(date, position.symbol)
            price = getattr(bar, price_field) if bar is not None else position.last_close
            total += position.shares * price
        return total

    def has_pending(symbol: str, side: str | None = None) -> bool:
        return any(
            order.symbol == symbol and (side is None or order.side == side)
            for order in pending
        )

    def schedule_sell(symbol: str, reason: str, due_index: int) -> None:
        nonlocal pending
        if has_pending(symbol, "SELL"):
            return
        pending = [order for order in pending if not (order.symbol == symbol and order.side == "BUY")]
        pending.append(Order(symbol=symbol, side="SELL", reason=reason, due_index=due_index))

    for index, date in enumerate(dates):
        due = [order for order in pending if order.due_index == index]
        pending = [order for order in pending if order.due_index != index]
        due.sort(key=lambda order: 0 if order.side == "SELL" else 1)

        for order in due:
            bar = bar_lookup(date, order.symbol)
            if order.side == "SELL":
                position = positions.get(order.symbol)
                if position is None:
                    continue
                if bar is None or bar.volume <= 0 or one_price_limit_down(bar):
                    result.blocked_sells += 1
                    if index + 1 < len(dates):
                        order.due_index = index + 1
                        pending.append(order)
                    continue
                notional = position.shares * bar.adj_open
                fee = notional * config.sell_cost
                cash += notional - fee
                result.trades.append(
                    {
                        "date": date,
                        "symbol": order.symbol,
                        "side": "SELL",
                        "reason": order.reason,
                        "units": position.units,
                        "adj_price": bar.adj_open,
                        "raw_price": bar.raw_open,
                        "notional": notional,
                        "fee": fee,
                        "holding_days": index - position.entry_index,
                        "return_from_average_cost": bar.adj_open / position.average_cost - 1.0,
                    }
                )
                del positions[order.symbol]
                continue

            if order.reason == "entry" and order.symbol in positions:
                continue
            if order.reason == "entry" and len(positions) >= config.max_positions:
                continue
            if order.reason == "add" and order.symbol not in positions:
                continue
            if has_pending(order.symbol, "SELL"):
                continue
            if bar is not None and order.max_entry_price is not None and bar.adj_open > order.max_entry_price:
                result.gap_skips += 1
                result.expired_buys += 1
                continue
            if bar is None or bar.volume <= 0 or one_price_limit_up(bar):
                result.blocked_buys += 1
                order.retries += 1
                if order.retries < config.buy_retry_days and index + 1 < len(dates):
                    order.due_index = index + 1
                    pending.append(order)
                else:
                    result.expired_buys += 1
                continue

            nav_at_open = valuation("adj_open", date)
            target_notional = (
                nav_at_open * config.risk_per_unit / order.risk_pct
                if config.risk_sized
                else nav_at_open * order.fraction
            )
            affordable = cash / (1.0 + config.buy_cost)
            raw_lots = floor(min(target_notional, affordable) / bar.raw_open / config.lot_size)
            raw_shares = raw_lots * config.lot_size
            if raw_shares <= 0:
                result.expired_buys += 1
                continue
            notional = raw_shares * bar.raw_open
            fee = notional * config.buy_cost
            adjusted_shares = notional / bar.adj_open
            cash -= notional + fee
            existing = positions.get(order.symbol)
            if existing is None:
                positions[order.symbol] = Position(
                    symbol=order.symbol,
                    shares=adjusted_shares,
                    units=1,
                    first_entry_price=bar.adj_open,
                    average_cost=bar.adj_open,
                    highest_close=bar.adj_open,
                    last_close=bar.adj_open,
                    entry_index=index,
                    risk_pct=order.risk_pct,
                    hard_stop_price=bar.adj_open * (1.0 - order.risk_pct),
                )
                units = 1
            else:
                total_shares = existing.shares + adjusted_shares
                existing.average_cost = (
                    existing.average_cost * existing.shares + bar.adj_open * adjusted_shares
                ) / total_shares
                existing.shares = total_shares
                existing.units += 1
                existing.hard_stop_price = max(
                    existing.hard_stop_price,
                    existing.average_cost * (1.0 - existing.risk_pct),
                )
                units = existing.units
            result.trades.append(
                {
                    "date": date,
                    "symbol": order.symbol,
                    "side": "BUY",
                    "reason": order.reason,
                    "units": units,
                    "adj_price": bar.adj_open,
                    "raw_price": bar.raw_open,
                    "raw_shares": raw_shares,
                    "notional": notional,
                    "fee": fee,
                }
            )

        for position in positions.values():
            bar = bar_lookup(date, position.symbol)
            result.position_days += 1
            if bar is None:
                result.missing_valuation_days += 1
                continue
            position.last_close = bar.adj_close
            position.highest_close = max(position.highest_close, bar.adj_close)

        close_nav = valuation("adj_close", date)
        gross = close_nav - cash
        result.dates.append(date)
        result.nav.append(close_nav)
        result.gross_exposure.append(gross / close_nav if close_nav > 0 else 0.0)
        result.benchmark_returns.append(float(benchmark_returns.get(date, 0.0)))
        last_nav = close_nav

        if index + 1 >= len(dates):
            continue

        for symbol, position in list(positions.items()):
            if has_pending(symbol, "SELL"):
                continue
            bar = bar_lookup(date, symbol)
            if bar is None:
                continue
            if config.fixed_hold_days is not None:
                if index - position.entry_index + 1 >= config.fixed_hold_days:
                    schedule_sell(symbol, "fixed_hold", index + 1)
                continue
            if config.stop_enabled:
                if config.risk_sized:
                    hard_line = position.hard_stop_price
                    trailing_active = position.highest_close >= position.first_entry_price * (1.0 + position.risk_pct)
                    trailing_line = (
                        position.highest_close
                        - config.trailing_r_multiple * position.first_entry_price * position.risk_pct
                        if trailing_active
                        else float("-inf")
                    )
                else:
                    hard_line = position.average_cost * (1.0 - config.stop_loss)
                    trailing_line = position.highest_close * (1.0 - config.trailing_stop)
                stop_line = max(hard_line, trailing_line)
                if bar.adj_close <= stop_line:
                    reason = "trailing_stop" if trailing_line > hard_line else "hard_stop"
                    schedule_sell(symbol, reason, index + 1)
                    continue
            can_add = add_allowed is None or bool(add_allowed.get(date, False))
            if (
                config.pyramid
                and can_add
                and position.units < config.max_units
                and not has_pending(symbol, "BUY")
            ):
                threshold = (
                    position.risk_pct * position.units
                    if config.risk_sized
                    else config.add_thresholds[position.units - 1]
                )
                if bar.adj_close >= position.first_entry_price * (1.0 + threshold):
                    pending.append(
                        Order(
                            symbol=symbol,
                            side="BUY",
                            reason="add",
                            due_index=index + 1,
                            fraction=config.add_fraction,
                            risk_pct=position.risk_pct,
                            max_entry_price=(
                                bar.adj_close + 0.5 * position.first_entry_price * position.risk_pct
                                if config.risk_sized
                                else None
                            ),
                        )
                    )

        occupied = len(positions) + sum(
            1 for order in pending if order.side == "BUY" and order.reason == "entry"
        )
        for candidate in candidates.get(date, []):
            if occupied >= config.max_positions:
                break
            if candidate.symbol in positions or has_pending(candidate.symbol):
                continue
            pending.append(
                Order(
                    symbol=candidate.symbol,
                    side="BUY",
                    reason="entry",
                    due_index=index + 1,
                    fraction=config.initial_fraction,
                    risk_pct=candidate.risk_pct,
                    max_entry_price=candidate.max_entry_price,
                )
            )
            occupied += 1

    result.final_cash = cash
    result.final_positions = positions
    return result
