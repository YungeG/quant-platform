"""Tests for experiments.l2_risers_phase_v9 pure helpers."""
from __future__ import annotations

import math
from decimal import Decimal

import pytest

from experiments.l2_risers_phase_v9 import anchor_views, observed_up_leg

# ---------------------------------------------------------------------------
# observed_up_leg
# ---------------------------------------------------------------------------


class TestObservedUpLegBasic:
    def test_simple_increasing(self):
        pts = [
            {"day": "20260901", "close": "10"},
            {"day": "20260902", "close": "20"},
            {"day": "20260903", "close": "30"},
        ]
        r = observed_up_leg(pts)
        assert r["trough_day"] == "20260901"
        assert r["peak_day"] == "20260903"
        assert r["trough_raw_close"] == "10"
        assert r["peak_raw_close"] == "30"

    def test_simple_decreasing_returns_none(self):
        pts = [
            {"day": "20260901", "close": "30"},
            {"day": "20260902", "close": "20"},
            {"day": "20260903", "close": "10"},
        ]
        assert observed_up_leg(pts) is None

    def test_flat_returns_none(self):
        pts = [
            {"day": "20260901", "close": "10"},
            {"day": "20260902", "close": "10"},
        ]
        assert observed_up_leg(pts) is None

    def test_later_global_low_before_peak(self):
        # Global min is at day 3, but peak is at day 4 -> max ratio
        pts = [
            {"day": "20260901", "close": "15"},
            {"day": "20260902", "close": "20"},
            {"day": "20260903", "close": "5"},
            {"day": "20260904", "close": "25"},
        ]
        r = observed_up_leg(pts)
        # ratio 25/5=5 > 20/15=1.33
        assert r["trough_day"] == "20260903"
        assert r["peak_day"] == "20260904"

    def test_ratio_vs_absolute_change(self):
        # Absolute: 100->110 = +10; 1->5 = +4
        # Ratio: 110/100=1.1 vs 5/1=5 -> ratio wins
        pts = [
            {"day": "20260901", "close": "100"},
            {"day": "20260902", "close": "110"},
            {"day": "20260903", "close": "1"},
            {"day": "20260904", "close": "5"},
        ]
        r = observed_up_leg(pts)
        assert r["trough_day"] == "20260903"
        assert r["peak_day"] == "20260904"


class TestObservedUpLegTieBreaks:
    def test_earliest_peak_day(self):
        # Two pairs with same ratio: (day1,day2)=20/10=2 and (day3,day4)=10/5=2
        # Earliest peak is day2
        pts = [
            {"day": "20260901", "close": "10"},
            {"day": "20260902", "close": "20"},
            {"day": "20260903", "close": "5"},
            {"day": "20260904", "close": "10"},
        ]
        r = observed_up_leg(pts)
        assert r["peak_day"] == "20260902"
        assert r["trough_day"] == "20260901"

    def test_latest_trough_day_for_same_peak(self):
        # Same peak day, two trough candidates with same close
        # day1=5, day2=5, day3=10 -> ratio 10/5=2 for both troughs
        # Latest trough for peak day3 is day2
        pts = [
            {"day": "20260901", "close": "5"},
            {"day": "20260902", "close": "5"},
            {"day": "20260903", "close": "10"},
        ]
        r = observed_up_leg(pts)
        assert r["peak_day"] == "20260903"
        assert r["trough_day"] == "20260902"  # latest trough

    def test_earliest_peak_overrides_later_trough(self):
        # (day1,day2) ratio=2, (day3,day4) ratio=2
        # Earliest peak=day2 wins even though day3 is a later lower trough
        pts = [
            {"day": "20260901", "close": "5"},
            {"day": "20260902", "close": "10"},
            {"day": "20260903", "close": "1"},
            {"day": "20260904", "close": "2"},
        ]
        r = observed_up_leg(pts)
        assert r["peak_day"] == "20260902"
        assert r["trough_day"] == "20260901"


class TestObservedUpLegValidation:
    def test_too_few_points(self):
        with pytest.raises(ValueError, match=">=2"):
            observed_up_leg([{"day": "20260901", "close": "10"}])

    @pytest.mark.parametrize(
        "bad",
        [
            [{"day": "20260902", "close": "10"}, {"day": "20260901", "close": "5"}],
            [{"day": "20260901", "close": "10"}, {"day": "20260901", "close": "5"}],
        ],
        ids=["unsorted", "duplicate"],
    )
    def test_date_ordering(self, bad):
        with pytest.raises(ValueError):
            observed_up_leg(bad)

    @pytest.mark.parametrize(
        "bad_day",
        ["20261301", "20260230", "abc", "2026091", "202609011"],
        ids=["month13", "feb30", "alpha", "short", "long"],
    )
    def test_invalid_date_formats(self, bad_day):
        with pytest.raises(ValueError):
            observed_up_leg(
                [
                    {"day": bad_day, "close": "10"},
                    {"day": "20260902", "close": "20"},
                ]
            )

    @pytest.mark.parametrize(
        "bad_close",
        ["0", "-5", "0.00", "NaN", "Inf", "-Inf", "Infinity"],
        ids=["zero", "neg", "zero_dec", "nan", "inf", "neginf", "infinity"],
    )
    def test_nonpositive_nonfinite(self, bad_close):
        with pytest.raises(ValueError):
            observed_up_leg(
                [
                    {"day": "20260901", "close": bad_close},
                    {"day": "20260902", "close": "10"},
                ]
            )

    def test_close_wrong_type(self):
        with pytest.raises(ValueError, match="Decimal or str"):
            observed_up_leg(
                [
                    {"day": "20260901", "close": 10},
                    {"day": "20260902", "close": "20"},
                ]
            )


class TestObservedUpLegExactDecimal:
    def test_ratio_difference_beyond_decimal_context_precision(self):
        points = [{"day": day, "close": close} for day, close in (
            ("20260901", "1"), ("20260902", "2"),
            ("20260903", "1"), ("20260904", "2.0000000000000000000000000001"),
        )]
        result = observed_up_leg(points)
        assert result["trough_day"] == "20260903"
        assert result["peak_day"] == "20260904"

    def test_no_rounding_cross_product(self):
        # 3/7 vs 30000000000000000001/70000000000000000001
        # The second ratio is slightly less than 3/7
        # Cross product: 30000000000000000001 * 7 = 210000000000000000007
        #                3 * 70000000000000000001 = 210000000000000000003
        # So first pair wins (3/7 > ...)
        pts = [
            {"day": "20260901", "close": "7"},
            {"day": "20260902", "close": "3"},
            {"day": "20260903", "close": "70000000000000000001"},
            {"day": "20260904", "close": "30000000000000000001"},
        ]
        r = observed_up_leg(pts)
        # Best ratio: 3/7 from (day1,day2) -- wait, 3/7 < 1, that's not an up-leg
        # Actually 3/7 < 1 so that pair is not an up-leg.
        # Let me reconsider: we need close[j] > close[i].
        # (day1,day3): 70000000000000000001/7 ≈ 1e19
        # (day1,day4): 30000000000000000001/7 ≈ 4.3e18
        # (day2,day3): 70000000000000000001/3 ≈ 2.3e19
        # (day2,day4): 30000000000000000001/3 ≈ 1e19
        # Max is (day2,day3): 70000000000000000001/3
        assert r["trough_day"] == "20260902"
        assert r["peak_day"] == "20260903"

    def test_exact_decimal_string_preserved(self):
        pts = [
            {"day": "20260901", "close": Decimal("1.23456789012345678901234567890")},
            {"day": "20260902", "close": Decimal("9.87654321098765432109876543210")},
        ]
        r = observed_up_leg(pts)
        assert r["trough_raw_close"] == "1.23456789012345678901234567890"
        assert r["peak_raw_close"] == "9.87654321098765432109876543210"

    def test_decimal_input_accepted(self):
        pts = [
            {"day": "20260901", "close": Decimal("5")},
            {"day": "20260902", "close": Decimal("10")},
        ]
        r = observed_up_leg(pts)
        assert r["trough_raw_close"] == "5"
        assert r["peak_raw_close"] == "10"

    def test_tie_exact_cross_product(self):
        # 6/3 == 4/2 == 2.0 exactly. Earliest peak wins.
        pts = [
            {"day": "20260901", "close": "3"},
            {"day": "20260902", "close": "6"},
            {"day": "20260903", "close": "2"},
            {"day": "20260904", "close": "4"},
        ]
        r = observed_up_leg(pts)
        assert r["peak_day"] == "20260902"
        assert r["trough_day"] == "20260901"


# ---------------------------------------------------------------------------
# anchor_views
# ---------------------------------------------------------------------------

# A 15-day calendar spanning weekends (no Sat/Sun)
_CALENDAR_15 = [
    "20260901",  # Tue  idx 0
    "20260902",  # Wed  idx 1
    "20260903",  # Thu  idx 2
    "20260904",  # Fri  idx 3
    "20260907",  # Mon  idx 4
    "20260908",  # Tue  idx 5
    "20260909",  # Wed  idx 6
    "20260910",  # Thu  idx 7
    "20260911",  # Fri  idx 8
    "20260914",  # Mon  idx 9
    "20260915",  # Tue  idx 10
    "20260916",  # Wed  idx 11
    "20260917",  # Thu  idx 12
    "20260918",  # Fri  idx 13
    "20260921",  # Mon  idx 14
]


class TestAnchorViewsBasic:
    def test_full_calendar_w5(self):
        # trough at idx 7, peak at idx 12 -> all views fit within [0,14]
        views = anchor_views(_CALENDAR_15, "20260910", "20260917", 5)
        assert len(views) == 4

        v0 = views[0]  # before_trough_exclusive: idx 2..6
        assert v0["view"] == "before_trough_exclusive"
        assert v0["lookback"] == 5
        assert v0["expected_days"] == 5
        assert v0["status"] == "complete"
        assert v0["days"] == [
            "20260903",
            "20260904",
            "20260907",
            "20260908",
            "20260909",
        ]

        v1 = views[1]  # after_trough_exclusive: idx 8..12
        assert v1["view"] == "after_trough_exclusive"
        assert v1["status"] == "complete"
        assert v1["days"] == [
            "20260911",
            "20260914",
            "20260915",
            "20260916",
            "20260917",
        ]

        v2 = views[2]  # into_peak_inclusive: idx 8..12
        assert v2["view"] == "into_peak_inclusive"
        assert v2["status"] == "complete"
        assert v2["days"] == [
            "20260911",
            "20260914",
            "20260915",
            "20260916",
            "20260917",
        ]

        v3 = views[3]  # after_peak_exclusive: idx 13..14 (only 2 available)
        assert v3["view"] == "after_peak_exclusive"
        assert v3["status"] == "right_censored"
        assert v3["expected_days"] == 5
        assert v3["days"] == ["20260918", "20260921"]

    def test_weekend_spanning_no_compression(self):
        # Calendar skips Sat/Sun; views use calendar indices, not calendar days
        # trough at idx 3 (Fri), W=5 -> before: idx -2..2 -> left_censored
        views = anchor_views(_CALENDAR_15, "20260904", "20260914", 5)
        v0 = views[0]
        assert v0["status"] == "left_censored"
        # Clipped to idx 0..2
        assert v0["days"] == ["20260901", "20260902", "20260903"]
        assert v0["expected_days"] == 5
        assert len(v0["days"]) == 3  # 3 of 5 available


class TestAnchorViewsCensoring:
    def test_left_censored(self):
        # trough at idx 2, W=5 -> before: idx -3..1 -> left_censored
        views = anchor_views(_CALENDAR_15, "20260903", "20260917", 5)
        v0 = views[0]
        assert v0["status"] == "left_censored"
        assert v0["days"] == ["20260901", "20260902"]

    def test_right_censored(self):
        # peak at idx 13, W=5 -> after_peak: idx 14..18 -> right_censored
        views = anchor_views(_CALENDAR_15, "20260903", "20260918", 5)
        v3 = views[3]
        assert v3["status"] == "right_censored"
        assert v3["days"] == ["20260921"]

    def test_into_peak_left_censored(self):
        # peak at idx 2, W=5 -> into_peak: idx -2..2 -> left_censored
        views = anchor_views(_CALENDAR_15, "20260901", "20260903", 5)
        v2 = views[2]
        assert v2["view"] == "into_peak_inclusive"
        assert v2["status"] == "left_censored"
        assert v2["days"] == ["20260901", "20260902", "20260903"]


class TestAnchorViewsValidation:
    @pytest.mark.parametrize("bad_w", [0, 1, 3, 7, 15, 25, -5, 5.0, "5"])
    def test_unsupported_W(self, bad_w):
        with pytest.raises(ValueError, match="W must be"):
            anchor_views(_CALENDAR_15, "20260903", "20260917", bad_w)

    def test_missing_trough(self):
        with pytest.raises(ValueError, match="not in calendar"):
            anchor_views(_CALENDAR_15, "20260101", "20260917", 5)

    def test_missing_peak(self):
        with pytest.raises(ValueError, match="not in calendar"):
            anchor_views(_CALENDAR_15, "20260903", "20260101", 5)

    def test_trough_not_before_peak(self):
        with pytest.raises(ValueError, match="must be <"):
            anchor_views(_CALENDAR_15, "20260917", "20260903", 5)

    def test_trough_equals_peak(self):
        with pytest.raises(ValueError, match="must be <"):
            anchor_views(_CALENDAR_15, "20260910", "20260910", 5)

    def test_duplicate_calendar(self):
        bad_cal = _CALENDAR_15 + ["20260921"]
        with pytest.raises(ValueError, match="duplicate"):
            anchor_views(bad_cal, "20260903", "20260917", 5)

    def test_unsorted_calendar(self):
        bad_cal = list(reversed(_CALENDAR_15))
        with pytest.raises(ValueError):
            anchor_views(bad_cal, "20260903", "20260917", 5)


class TestAnchorViewsW10and20:
    def test_w10_complete(self):
        # Need >= 21 calendar days for full w10 views around mid points
        # With 15-day calendar, trough at idx 10, peak at idx 12
        # before_trough: idx 0..9 (10 days, complete)
        # after_trough: idx 11..14 (only 4, right_censored... wait, trough=10, +10=20 > 14)
        # Actually after_trough: idx 11..20 -> clipped to 11..14 -> right_censored
        views = anchor_views(_CALENDAR_15, "20260915", "20260917", 10)
        v0 = views[0]
        assert v0["status"] == "complete"
        assert len(v0["days"]) == 10
        assert v0["expected_days"] == 10

        v1 = views[1]
        assert v1["status"] == "right_censored"
        assert v1["expected_days"] == 10
        assert len(v1["days"]) == 4  # idx 11..14

    def test_w20_mostly_censored(self):
        # W=20 on 15-day calendar: everything will be censored
        views = anchor_views(_CALENDAR_15, "20260910", "20260917", 20)
        for v in views:
            assert v["expected_days"] == 20
            assert v["status"] in ("left_censored", "right_censored")


class TestAnchorViewsOverlap:
    def test_views_may_overlap(self):
        # after_trough and into_peak can overlap
        views = anchor_views(_CALENDAR_15, "20260910", "20260917", 5)
        after_trough = views[1]["days"]
        into_peak = views[2]["days"]
        # They share the same range in this case
        assert after_trough == into_peak
