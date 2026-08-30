"""Deterministic growth/inflation cycle classification."""

from __future__ import annotations

from statistics import mean
from typing import Sequence


CYCLE_WEIGHTS = {
    "recovery": {"equity": 0.50, "bond": 0.40, "gold": 0.10},
    "expansion": {"equity": 0.50, "bond": 0.20, "gold": 0.30},
    "stagflation": {"equity": 0.20, "bond": 0.50, "gold": 0.30},
    "contraction": {"equity": 0.20, "bond": 0.70, "gold": 0.10},
}


def _label(growth_impulse: float, inflation_impulse: float) -> str:
    growth_up = growth_impulse > 0
    inflation_up = inflation_impulse > 0
    if growth_up and not inflation_up:
        return "recovery"
    if growth_up and inflation_up:
        return "expansion"
    if not growth_up and inflation_up:
        return "stagflation"
    return "contraction"


def classify_cycle_fast(
    growth: Sequence[float], inflation: Sequence[float]
) -> tuple[str, float, float]:
    if len(growth) != 4 or len(inflation) != 4:
        raise ValueError("fast cycle classification requires exactly four monthly observations")
    growth_impulse = float(growth[-1]) - mean(growth[:3])
    inflation_impulse = float(inflation[-1]) - mean(inflation[:3])
    return _label(growth_impulse, inflation_impulse), growth_impulse, inflation_impulse


def classify_cycle_slow(
    growth: Sequence[float], inflation: Sequence[float]
) -> tuple[str, float, float]:
    if len(growth) != 6 or len(inflation) != 6:
        raise ValueError("slow cycle classification requires exactly six monthly observations")
    growth_impulse = mean(growth[-3:]) - mean(growth[:3])
    inflation_impulse = mean(inflation[-3:]) - mean(inflation[:3])
    return _label(growth_impulse, inflation_impulse), growth_impulse, inflation_impulse
