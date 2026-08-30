from datetime import date, timedelta

from experiments.run_ground_volume_validation import (
    _spread,
    month_end_indices,
    rolling_volume_scores,
    timing_returns,
)


def test_ground_volume_maps_to_high_score() -> None:
    low = rolling_volume_scores([100.0] * 9 + [10.0], window=10)
    high = rolling_volume_scores([10.0] * 9 + [100.0], window=10)

    assert low[-1] == 1.0
    assert high[-1] == 0.0


def test_month_end_and_spread_are_explicit() -> None:
    dates = [date(2024, 1, 30), date(2024, 1, 31), date(2024, 2, 1), date(2024, 2, 29)]
    assert month_end_indices(dates) == [1, 3]

    result = _spread(
        [
            {"score": 0.90, "forward_return": 0.10},
            {"score": 0.85, "forward_return": 0.20},
            {"score": 0.10, "forward_return": -0.10},
            {"score": 0.15, "forward_return": 0.00},
        ]
    )
    assert abs(result["spread"] - 0.20) < 1e-12


def test_monthly_ground_tilt_is_low_frequency() -> None:
    dates = [date(2020, 1, 1) + timedelta(days=index) for index in range(500)]
    closes = [100.0 * (1.001**index) for index in range(500)]
    turnovers = [100.0] * 249 + [10.0] * 251
    scores = rolling_volume_scores(turnovers)

    result = timing_returns(dates, closes, scores)

    assert 0.50 <= result["average_exposure"] <= 1.00
    assert result["annual_turnover"] < 12.0
    assert result["timing"]["cagr"] > 0
