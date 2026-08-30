"""Frozen concept-cluster confirmation rule."""

from __future__ import annotations


def concept_cluster_confirmed(shared_peer_counts: list[int]) -> bool:
    return any(count >= 2 for count in shared_peer_counts)
