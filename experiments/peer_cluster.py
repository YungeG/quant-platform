"""Frozen peer-cluster confirmation rule."""

from __future__ import annotations


def cluster_confirmed(
    peer_breakout_count: int,
    breakout_density: float,
    group_return20: float,
    group_above_ma20: bool,
) -> bool:
    return (
        peer_breakout_count >= 2
        and breakout_density >= 0.10
        and group_return20 > 0
        and group_above_ma20
    )
