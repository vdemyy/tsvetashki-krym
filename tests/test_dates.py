"""Тесты для utils.dates."""

from datetime import date

from utils.dates import timers_for_phases, event_in_feed


class TestTimersForPhases:
    def test_before_start(self):
        today = date(2026, 5, 1)
        timers = timers_for_phases(today, date(2026, 5, 10), date(2026, 5, 20), date(2026, 5, 30))
        assert len(timers) == 3
        assert timers[0].label == "до начала"
        assert timers[0].days == 9

    def test_between_start_and_peak(self):
        today = date(2026, 5, 15)
        timers = timers_for_phases(today, date(2026, 5, 10), date(2026, 5, 20), date(2026, 5, 30))
        assert len(timers) == 2
        assert timers[0].label == "до пика"

    def test_between_peak_and_end(self):
        today = date(2026, 5, 25)
        timers = timers_for_phases(today, date(2026, 5, 10), date(2026, 5, 20), date(2026, 5, 30))
        assert len(timers) == 2
        assert timers[0].label == "до конца"
        assert timers[1].label == "после пика"

    def test_after_end(self):
        today = date(2026, 6, 5)
        timers = timers_for_phases(today, date(2026, 5, 10), date(2026, 5, 20), date(2026, 5, 30))
        assert len(timers) == 1
        assert timers[0].label == "сезон завершён"
        assert timers[0].days is None


class TestEventInFeed:
    def test_active_event_in_feed(self):
        today = date(2026, 5, 15)
        assert event_in_feed(today, date(2026, 5, 10), date(2026, 5, 20)) is True

    def test_upcoming_event_in_feed(self):
        today = date(2026, 5, 5)
        assert event_in_feed(today, date(2026, 5, 10), date(2026, 5, 20)) is True

    def test_far_future_not_in_feed(self):
        today = date(2026, 1, 1)
        assert event_in_feed(today, date(2026, 5, 10), date(2026, 5, 20)) is False

    def test_past_event_not_in_feed(self):
        today = date(2026, 6, 1)
        assert event_in_feed(today, date(2026, 5, 10), date(2026, 5, 20)) is False
