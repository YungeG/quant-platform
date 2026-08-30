"""Deterministic breakout-level retest state machine."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Sequence


@dataclass(frozen=True)
class RetestBar:
    high: float
    low: float
    close: float
    previous_close: float
    amount: float
    atr5: float
    one_word_up: bool = False


@dataclass(frozen=True)
class RetestOutcome:
    terminal_reason: str
    retest_index: int | None
    trigger_index: int | None
    pullback_low: float


def evaluate_retest(
    bars: Sequence[RetestBar],
    *,
    breakout_level: float,
    breakout_atr: float,
    breakout_amount: float,
) -> RetestOutcome:
    accepted_retest: int | None = None
    pullback_low = float("inf")
    amounts: list[float] = []
    for index, bar in enumerate(bars[:12], start=1):
        pullback_low = min(pullback_low, bar.low)
        amounts.append(bar.amount)
        if bar.close < breakout_level - breakout_atr:
            return RetestOutcome("support_break", accepted_retest, None, pullback_low)
        if bar.close < bar.previous_close and bar.amount > breakout_amount:
            return RetestOutcome("distribution_selloff", accepted_retest, None, pullback_low)
        if index >= 3 and accepted_retest is None and bar.low <= breakout_level + breakout_atr:
            if bar.close < breakout_level - 0.5 * breakout_atr:
                return RetestOutcome("support_break", index, None, pullback_low)
            if median(amounts) > 0.8 * breakout_amount:
                return RetestOutcome("retest_volume_not_contracted", index, None, pullback_low)
            if bar.atr5 > 1.1 * breakout_atr:
                return RetestOutcome("retest_volatility_expanded", index, None, pullback_low)
            accepted_retest = index
        if accepted_retest is not None:
            prior = bars[max(0, index - 4) : index - 1]
            prior_high = max((item.high for item in prior), default=float("inf"))
            prior_amount = median([item.amount for item in bars[max(0, index - 6) : index - 1]])
            location = (bar.close - bar.low) / (bar.high - bar.low) if bar.high > bar.low else 0.0
            if (
                bar.close > breakout_level
                and bar.close > prior_high
                and location >= 0.60
                and bar.amount > prior_amount
                and not bar.one_word_up
            ):
                return RetestOutcome("triggered", accepted_retest, index, pullback_low)
    reason = "no_retest_timeout" if accepted_retest is None else "no_recovery_timeout"
    return RetestOutcome(reason, accepted_retest, None, pullback_low)
