"""Small helpers for point-in-time earnings-announcement events."""

from __future__ import annotations

from bisect import bisect_left
from datetime import date
from typing import Sequence


POSITIVE_FORECAST_TYPES = frozenset({"预增", "扭亏"})


def is_first_forecast(announcement: str, first_announcement: str | None) -> bool:
    return bool(first_announcement) and announcement == first_announcement


def next_signal_session(announcement: date, sessions: Sequence[date]) -> date | None:
    position = bisect_left(sessions, announcement)
    return sessions[position] if position < len(sessions) else None
