from datetime import date

from experiments.pead import is_first_forecast, next_signal_session


def test_first_forecast_requires_matching_first_announcement_date():
    assert is_first_forecast("20260115", "20260115")
    assert not is_first_forecast("20260201", "20260115")
    assert not is_first_forecast("20260115", None)


def test_weekend_announcement_maps_to_next_session():
    sessions = [date(2026, 1, 9), date(2026, 1, 12), date(2026, 1, 13)]
    assert next_signal_session(date(2026, 1, 10), sessions) == date(2026, 1, 12)
    assert next_signal_session(date(2026, 1, 12), sessions) == date(2026, 1, 12)
