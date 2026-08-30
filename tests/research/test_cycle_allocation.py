import pytest

from experiments.cycle_allocation import (
    CYCLE_WEIGHTS,
    classify_cycle_fast,
    classify_cycle_slow,
)


@pytest.mark.parametrize(
    ("growth", "inflation", "expected"),
    [
        ([49, 49, 49, 50], [2, 2, 2, 1], "recovery"),
        ([49, 49, 49, 50], [1, 1, 1, 2], "expansion"),
        ([50, 50, 50, 49], [1, 1, 1, 2], "stagflation"),
        ([50, 50, 50, 49], [2, 2, 2, 1], "contraction"),
    ],
)
def test_fast_cycle_quadrants(growth, inflation, expected):
    label, _, _ = classify_cycle_fast(growth, inflation)
    assert label == expected
    assert sum(CYCLE_WEIGHTS[label].values()) == pytest.approx(1.0)


def test_slow_cycle_uses_three_month_blocks():
    label, growth_impulse, inflation_impulse = classify_cycle_slow(
        [49, 49, 49, 50, 50, 50],
        [2, 2, 2, 1, 1, 1],
    )
    assert label == "recovery"
    assert growth_impulse == pytest.approx(1.0)
    assert inflation_impulse == pytest.approx(-1.0)
