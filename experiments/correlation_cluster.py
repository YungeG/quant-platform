"""Frozen dynamic correlation-cluster confirmation rule."""

from __future__ import annotations


def correlation_cluster_confirmed(peer_count: int, median_correlation: float) -> bool:
    return peer_count >= 2 and median_correlation >= 0.65
