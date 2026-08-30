"""Small allocation helpers and a next-open multi-asset simulator."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from typing import Mapping, Sequence


@dataclass(frozen=True)
class AssetBar:
    adj_open: float
    adj_close: float
    raw_open: float


@dataclass
class AllocationResult:
    dates: list[str]
    nav: list[float]
    turnover: list[float]
    costs: list[float]
    financing_costs: list[float]
    leverage: list[float]
    weights: list[dict[str, float]] = field(default_factory=list)


def normalize_weights(weights: Mapping[str, float]) -> dict[str, float]:
    positive = {asset: max(float(weight), 0.0) for asset, weight in weights.items()}
    total = sum(positive.values())
    if total <= 0:
        raise ValueError("weights must contain positive mass")
    return {asset: weight / total for asset, weight in positive.items()}


def inverse_vol_weights(volatility: Mapping[str, float]) -> dict[str, float]:
    inverse = {
        asset: 1.0 / float(value)
        for asset, value in volatility.items()
        if float(value) > 0
    }
    if len(inverse) != len(volatility):
        raise ValueError("volatility must be positive for every asset")
    return normalize_weights(inverse)


def equal_risk_contribution_weights(
    assets: Sequence[str],
    covariance: Sequence[Sequence[float]],
    *,
    iterations: int = 10_000,
    tolerance: float = 1e-12,
) -> dict[str, float]:
    """Long-only equal-risk weights via cyclical coordinate descent."""
    size = len(assets)
    if size == 0 or len(covariance) != size or any(len(row) != size for row in covariance):
        raise ValueError("covariance shape must match assets")
    if any(float(covariance[i][i]) <= 0 for i in range(size)):
        raise ValueError("covariance diagonal must be positive")
    weights = [1.0 / size] * size
    budget = 1.0 / size
    for _ in range(iterations):
        previous = list(weights)
        for i in range(size):
            diagonal = float(covariance[i][i])
            cross = sum(float(covariance[i][j]) * weights[j] for j in range(size) if j != i)
            weights[i] = (-cross + sqrt(cross * cross + 4.0 * diagonal * budget)) / (2.0 * diagonal)
        if max(abs(weights[i] - previous[i]) for i in range(size)) <= tolerance:
            break
    total = sum(weights)
    return {asset: weights[index] / total for index, asset in enumerate(assets)}


def simulate_allocation(
    dates: Sequence[str],
    bars: Mapping[str, Mapping[str, AssetBar]],
    target_weights: Mapping[str, Mapping[str, float]],
    *,
    initial_nav: float = 400_000.0,
    cost_rate: float = 0.0008,
    financing_rate: float = 0.0,
    normalize_targets: bool = True,
) -> AllocationResult:
    assets = tuple(bars)
    cash = float(initial_nav)
    shares = {asset: 0.0 for asset in assets}
    pending: dict[str, float] | None = None
    result = AllocationResult(
        dates=[], nav=[], turnover=[], costs=[], financing_costs=[], leverage=[]
    )
    for date in dates:
        open_prices = {asset: bars[asset][date].adj_open for asset in assets}
        close_prices = {asset: bars[asset][date].adj_close for asset in assets}
        nav_open = cash + sum(shares[asset] * open_prices[asset] for asset in assets)
        turnover = 0.0
        cost = 0.0
        if pending is not None:
            target = (
                normalize_weights(pending)
                if normalize_targets
                else {asset: max(float(pending.get(asset, 0.0)), 0.0) for asset in assets}
            )
            if sum(target.values()) <= 0:
                raise ValueError("target weights must contain positive mass")
            current_values = {asset: shares[asset] * open_prices[asset] for asset in assets}
            desired_values = {asset: nav_open * target.get(asset, 0.0) for asset in assets}
            traded_notional = sum(
                abs(desired_values[asset] - current_values[asset]) for asset in assets
            )
            turnover = 0.5 * traded_notional / nav_open if nav_open > 0 else 0.0
            cost = traded_notional * cost_rate
            investable = nav_open - cost
            shares = {
                asset: investable * target.get(asset, 0.0) / open_prices[asset]
                for asset in assets
            }
            cash = investable * (1.0 - sum(target.values()))
            pending = None
        financing_cost = max(-cash, 0.0) * financing_rate / 252.0
        cash -= financing_cost
        nav_close = cash + sum(shares[asset] * close_prices[asset] for asset in assets)
        weights_close = {
            asset: shares[asset] * close_prices[asset] / nav_close if nav_close > 0 else 0.0
            for asset in assets
        }
        result.dates.append(date)
        result.nav.append(nav_close)
        result.turnover.append(turnover)
        result.costs.append(cost)
        result.financing_costs.append(financing_cost)
        result.leverage.append(sum(weights_close.values()))
        result.weights.append(weights_close)
        if date in target_weights:
            pending = dict(target_weights[date])
    return result
