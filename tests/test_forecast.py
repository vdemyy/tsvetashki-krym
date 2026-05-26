"""Тесты для services.forecast."""

from datetime import date

from services.forecast import forecast_from_history, marker_status, PhaseForecast


class TestMarkerStatus:
    def test_active_event(self):
        today = date(2026, 6, 15)
        assert marker_status(today, date(2026, 6, 10), date(2026, 6, 20)) == "active"

    def test_soon_event(self):
        today = date(2026, 6, 1)
        assert marker_status(today, date(2026, 6, 5), date(2026, 6, 20)) == "soon"

    def test_future_event(self):
        today = date(2026, 1, 1)
        assert marker_status(today, date(2026, 6, 10), date(2026, 6, 20)) == "future"

    def test_ended_event(self):
        today = date(2026, 7, 1)
        assert marker_status(today, date(2026, 6, 10), date(2026, 6, 20)) == "ended"

    def test_start_day_is_active(self):
        today = date(2026, 6, 10)
        assert marker_status(today, date(2026, 6, 10), date(2026, 6, 20)) == "active"

    def test_end_day_is_active(self):
        today = date(2026, 6, 20)
        assert marker_status(today, date(2026, 6, 10), date(2026, 6, 20)) == "active"


class TestForecastFromHistory:
    def test_returns_none_for_empty(self):
        assert forecast_from_history(None) is None
        assert forecast_from_history([]) is None

    def test_single_year(self):
        history = [
            {"year": 2024, "start": "2024-06-10", "peak": "2024-06-20", "end": "2024-07-01"}
        ]
        fc = forecast_from_history(history, 2026)
        assert fc is not None
        assert isinstance(fc, PhaseForecast)
        assert fc.years_used == 1
        assert fc.start is not None
        assert fc.start.year == 2026

    def test_multiple_years(self):
        history = [
            {"year": 2022, "start": "2022-06-10", "peak": "2022-06-22", "end": "2022-07-04"},
            {"year": 2023, "start": "2023-06-12", "peak": "2023-06-24", "end": "2023-07-06"},
            {"year": 2024, "start": "2024-06-08", "peak": "2024-06-20", "end": "2024-07-02"},
        ]
        fc = forecast_from_history(history, 2026)
        assert fc is not None
        assert fc.years_used == 3
        # Start should be around June 10
        assert fc.start.month == 6
        assert 8 <= fc.start.day <= 12

    def test_handles_invalid_data(self):
        history = [{"invalid": "data"}, "not a dict"]
        fc = forecast_from_history(history)
        assert fc is None
