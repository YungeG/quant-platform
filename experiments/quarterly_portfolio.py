"""Minimal next-open simulator for quarterly long-only stock baskets."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import floor
from typing import Callable, Sequence

from experiments.lowturn_livermore import Bar, one_price_limit_down, one_price_limit_up


def select_industry_balanced(
    rows: Sequence[tuple[str, str, float, float]],
    count: int,
    industry_cap: int,
) -> list[str]:
    """Select low-vol names ordered by industry percentile, then absolute volatility."""
    selected: list[str] = []
    industry_counts: dict[str, int] = {}
    for symbol, industry, volatility, industry_percentile in sorted(
        rows, key=lambda row: (row[3], row[2], row[0])
    ):
        if industry_counts.get(industry, 0) >= industry_cap:
            continue
        selected.append(symbol)
        industry_counts[industry] = industry_counts.get(industry, 0) + 1
        if len(selected) >= count:
            break
    return selected


@dataclass
class BasketPosition:
    symbol: str
    shares: float
    last_close: float


@dataclass
class BasketOrder:
    symbol: str
    side: str
    due_index: int
    retries: int = 0


@dataclass(frozen=True)
class BasketConfig:
    name: str
    target_count: int
    initial_nav: float = 400_000.0
    lot_size: int = 100
    buy_cost: float = 0.0013
    sell_cost: float = 0.0018
    buy_retry_days: int = 3


@dataclass
class BasketResult:
    dates: list[str]
    nav: list[float]
    cash_fraction: list[float]
    position_count: list[int]
    trades: list[dict] = field(default_factory=list)
    blocked_buys: int = 0
    blocked_sells: int = 0
    expired_buys: int = 0
    lot_failures: int = 0
    missing_valuation_days: int = 0
    position_days: int = 0


def simulate_basket(
    dates: Sequence[str],
    bar_lookup: Callable[[str, str], Bar | None],
    targets: dict[str, list[str]],
    config: BasketConfig,
) -> BasketResult:
    cash = float(config.initial_nav)
    positions: dict[str, BasketPosition] = {}
    pending: list[BasketOrder] = []
    result = BasketResult(dates=[], nav=[], cash_fraction=[], position_count=[])

    def has_pending(symbol: str, side: str | None = None) -> bool:
        return any(
            order.symbol == symbol and (side is None or order.side == side)
            for order in pending
        )

    def open_nav(date: str) -> float:
        total = cash
        for position in positions.values():
            bar = bar_lookup(date, position.symbol)
            total += position.shares * (bar.adj_open if bar is not None else position.last_close)
        return total

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
                        "notional": notional,
                        "fee": fee,
                    }
                )
                del positions[order.symbol]
                continue

            if order.symbol in positions:
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
            target_notional = open_nav(date) / config.target_count
            affordable = cash / (1.0 + config.buy_cost)
            raw_lots = floor(min(target_notional, affordable) / bar.raw_open / config.lot_size)
            raw_shares = raw_lots * config.lot_size
            if raw_shares <= 0:
                result.lot_failures += 1
                result.expired_buys += 1
                continue
            notional = raw_shares * bar.raw_open
            fee = notional * config.buy_cost
            cash -= notional + fee
            positions[order.symbol] = BasketPosition(
                symbol=order.symbol,
                shares=notional / bar.adj_open,
                last_close=bar.adj_open,
            )
            result.trades.append(
                {
                    "date": date,
                    "symbol": order.symbol,
                    "side": "BUY",
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
            else:
                position.last_close = bar.adj_close
        invested = sum(position.shares * position.last_close for position in positions.values())
        nav = cash + invested
        result.dates.append(date)
        result.nav.append(nav)
        result.cash_fraction.append(cash / nav if nav > 0 else 1.0)
        result.position_count.append(len(positions))

        if index + 1 >= len(dates) or date not in targets:
            continue
        target = list(dict.fromkeys(targets[date]))
        target_set = set(target)
        pending = [
            order
            for order in pending
            if not (order.side == "BUY" and order.symbol not in target_set)
        ]
        for symbol in positions:
            if symbol not in target_set and not has_pending(symbol, "SELL"):
                pending.append(BasketOrder(symbol=symbol, side="SELL", due_index=index + 1))
        for symbol in target:
            if symbol not in positions and not has_pending(symbol):
                pending.append(BasketOrder(symbol=symbol, side="BUY", due_index=index + 1))

    return result
