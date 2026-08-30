"""Frozen sector-confirmation rule for breakout-retest events."""

from __future__ import annotations


def sector_confirmed(
    strength_percentile: float,
    above_ma60: bool,
    breadth_ma20: float,
    stock_excess_60: float,
) -> bool:
    return (
        strength_percentile >= 0.70
        and above_ma60
        and breadth_ma20 >= 0.55
        and stock_excess_60 > 0
    )
