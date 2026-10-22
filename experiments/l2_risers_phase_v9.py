"""Pure helpers for L2 risers phase v9 retrospective price-stage alignment.

Two pure functions, stdlib Decimal only, no I/O, no pandas, no network.
"""
from __future__ import annotations

import datetime
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from typing import Sequence


def _parse_day(day: str) -> datetime.date:
    """Validate YYYYMMDD string and return a datetime.date."""
    if not isinstance(day, str):
        raise ValueError(f"day must be str, got {type(day).__name__}")
    if len(day) != 8 or not day.isdigit():
        raise ValueError(f"day must be YYYYMMDD, got {day!r}")
    try:
        return datetime.date(int(day[:4]), int(day[4:6]), int(day[6:8]))
    except ValueError as e:
        raise ValueError(f"invalid date {day!r}: {e}") from None


def _to_decimal(close) -> Decimal:
    """Convert close to Decimal; accept Decimal or exact-decimal string."""
    if isinstance(close, Decimal):
        d = close
    elif isinstance(close, str):
        try:
            d = Decimal(close)
        except InvalidOperation as e:
            raise ValueError(f"close string not decimal: {close!r}") from None
    else:
        raise ValueError(
            f"close must be Decimal or str, got {type(close).__name__}"
        )
    if d.is_nan() or d.is_infinite():
        raise ValueError(f"close must be finite, got {close!r}")
    if d <= 0:
        raise ValueError(f"close must be positive, got {close!r}")
    return d


def observed_up_leg(points: Sequence[dict]) -> dict | None:
    """Find the maximum close[j]/close[i] up-leg over i<j.

    Parameters
    ----------
    points : sequence of {'day': 'YYYYMMDD', 'close': Decimal|str}
        Must be nonempty, sorted by strictly increasing valid dates,
        with finite positive closes, and contain >=2 points.

    Returns
    -------
    dict with keys trough_day, peak_day, trough_raw_close, peak_raw_close
        (raw closes are exact Decimal strings), or None if no up-leg
        (i.e., no pair with close[j] > close[i]) exists.

    Tie-breaking (when multiple pairs share the max ratio):
        1. EARLIEST peak_day
        2. LATEST trough_day for that peak

    Uses exact Decimal cross-products for ratio comparison (no rounding).
    """
    if not isinstance(points, Sequence):
        raise TypeError("points must be a sequence")
    n = len(points)
    if n < 2:
        raise ValueError("need >=2 points")

    # Parse and validate
    parsed: list[tuple[str, Decimal]] = []
    seen_dates: set[str] = set()
    for idx, p in enumerate(points):
        if not isinstance(p, dict):
            raise TypeError(f"point {idx} must be dict")
        day = _parse_day(p["day"])
        day_str = p["day"]
        if day_str in seen_dates:
            raise ValueError(f"duplicate date {day_str!r}")
        seen_dates.add(day_str)
        close = _to_decimal(p["close"])
        parsed.append((day_str, close))

    # Check strictly increasing
    for k in range(1, n):
        if parsed[k][0] <= parsed[k - 1][0]:
            raise ValueError(
                f"dates not strictly increasing at index {k}: "
                f"{parsed[k - 1][0]} >= {parsed[k][0]}"
            )

    # Find max-ratio pair using running minimum.
    # For each j, the best trough is the index with minimum close among i<j;
    # ties in close -> latest index (latest trough day).
    # Across j, ties in ratio -> earliest j (earliest peak day).
    best_num: Decimal | None = None  # close[j] of best ratio
    best_den: Decimal | None = None  # close[i] of best ratio
    best_i: int | None = None
    best_j: int | None = None

    min_close = parsed[0][1]
    min_close_idx = 0

    for j in range(1, n):
        cj = parsed[j][1]
        trough_close = min_close
        trough_idx = min_close_idx

        if best_num is None:
            best_num = cj
            best_den = trough_close
            best_i = trough_idx
            best_j = j
        else:
            # Compare cj/trough_close vs best_num/best_den
            # cj * best_den  vs  best_num * trough_close
            lhs = Fraction(cj) * Fraction(best_den)
            rhs = Fraction(best_num) * Fraction(trough_close)
            if lhs > rhs:
                best_num = cj
                best_den = trough_close
                best_i = trough_idx
                best_j = j
            # On tie (lhs == rhs): keep earlier peak (don't update),
            # which is already best_j since j increases monotonically.

        # Update running minimum for next j
        if cj < min_close:
            min_close = cj
            min_close_idx = j
        elif cj == min_close:
            # Same close -> latest index (latest trough day)
            min_close_idx = j

    # No up-leg if max ratio <= 1 (i.e., best_num <= best_den)
    assert best_num is not None and best_den is not None
    if best_num <= best_den:
        return None

    return {
        "trough_day": parsed[best_i][0],
        "peak_day": parsed[best_j][0],
        "trough_raw_close": str(parsed[best_i][1]),
        "peak_raw_close": str(parsed[best_j][1]),
    }


_VALID_W = frozenset({5, 10, 20})

_VIEW_DEFS = (
    # (name, start_offset_from_anchor, end_offset_from_anchor, anchor_key)
    # Ranges are inclusive on both ends, relative to anchor index.
    # before_trough_exclusive: [trough_idx - W, trough_idx - 1]
    # after_trough_exclusive:  [trough_idx + 1, trough_idx + W]
    # into_peak_inclusive:     [peak_idx - W + 1, peak_idx]
    # after_peak_exclusive:    [peak_idx + 1, peak_idx + W]
)


def anchor_views(
    calendar: Sequence[str],
    trough_day: str,
    peak_day: str,
    W: int,
) -> list[dict]:
    """Compute four anchored market-index views around trough and peak.

    Parameters
    ----------
    calendar : sorted sequence of unique valid YYYYMMDD strings
    trough_day, peak_day : both present in calendar, trough_day < peak_day
    W : exactly 5, 10, or 20

    Returns
    -------
    list of 4 dicts, each with keys:
        view : str (view name)
        lookback : int (== W)
        days : list[str] (intersection with calendar, in calendar order)
        status : 'complete' | 'left_censored' | 'right_censored'
        expected_days : int (== W)
    """
    if not isinstance(calendar, Sequence):
        raise TypeError("calendar must be a sequence")
    if type(W) is not int or W not in _VALID_W:
        raise ValueError(f"W must be one of {sorted(_VALID_W)}, got {W!r}")

    # Validate calendar
    cal: list[str] = []
    cal_set: set[str] = set()
    prev_date: datetime.date | None = None
    for idx, d in enumerate(calendar):
        dt = _parse_day(d)
        if d in cal_set:
            raise ValueError(f"duplicate calendar date {d!r}")
        if prev_date is not None and dt <= prev_date:
            raise ValueError(
                f"calendar not strictly increasing at index {idx}"
            )
        cal.append(d)
        cal_set.add(d)
        prev_date = dt

    n = len(cal)
    cal_index = {d: i for i, d in enumerate(cal)}

    # Validate anchors
    if trough_day not in cal_set:
        raise ValueError(f"trough_day {trough_day!r} not in calendar")
    if peak_day not in cal_set:
        raise ValueError(f"peak_day {peak_day!r} not in calendar")

    trough_idx = cal_index[trough_day]
    peak_idx = cal_index[peak_day]

    # Validate trough < peak using date comparison (string compare works for
    # YYYYMMDD but let's be explicit via the parsed dates)
    if not (_parse_day(trough_day) < _parse_day(peak_day)):
        raise ValueError(
            f"trough_day {trough_day!r} must be < peak_day {peak_day!r}"
        )

    # Define the four views as (name, start_idx, end_idx) inclusive ranges
    views_spec = [
        (
            "before_trough_exclusive",
            trough_idx - W,
            trough_idx - 1,
        ),
        (
            "after_trough_exclusive",
            trough_idx + 1,
            trough_idx + W,
        ),
        (
            "into_peak_inclusive",
            peak_idx - W + 1,
            peak_idx,
        ),
        (
            "after_peak_exclusive",
            peak_idx + 1,
            peak_idx + W,
        ),
    ]

    result: list[dict] = []
    for view_name, req_start, req_end in views_spec:
        # Clip to valid calendar index range [0, n-1]
        clip_start = max(0, req_start)
        clip_end = min(n - 1, req_end)

        if clip_start > clip_end:
            days: list[str] = []
        else:
            days = [cal[i] for i in range(clip_start, clip_end + 1)]

        # Determine status
        left_ok = req_start >= 0
        right_ok = req_end < n

        if left_ok and right_ok:
            status = "complete"
        elif not left_ok:
            status = "left_censored"
        else:
            status = "right_censored"

        result.append(
            {
                "view": view_name,
                "lookback": W,
                "days": days,
                "status": status,
                "expected_days": W,
            }
        )

    return result
