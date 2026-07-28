from datetime import datetime
from app.api.v1.alarms import _next_wecker_fire_at_or_after


def test_snap_at_zero_seconds_advances_to_one_second():
    dt = datetime(2026, 5, 10, 14, 23, 0)
    assert _next_wecker_fire_at_or_after(dt) == datetime(2026, 5, 10, 14, 23, 1)


def test_snap_already_at_one_second_unchanged():
    dt = datetime(2026, 5, 10, 14, 23, 1)
    assert _next_wecker_fire_at_or_after(dt) == dt


def test_snap_past_one_second_advances_to_next_minute():
    dt = datetime(2026, 5, 10, 14, 23, 2)
    assert _next_wecker_fire_at_or_after(dt) == datetime(2026, 5, 10, 14, 24, 1)


def test_snap_at_thirty_seconds_advances_to_next_minute():
    dt = datetime(2026, 5, 10, 14, 23, 30)
    assert _next_wecker_fire_at_or_after(dt) == datetime(2026, 5, 10, 14, 24, 1)


def test_snap_microsecond_above_zero_at_one_second_advances():
    dt = datetime(2026, 5, 10, 14, 23, 1, 1)
    assert _next_wecker_fire_at_or_after(dt) == datetime(2026, 5, 10, 14, 24, 1)


def test_snap_at_minute_boundary_with_microsecond_advances():
    dt = datetime(2026, 5, 10, 14, 23, 0, 500_000)
    assert _next_wecker_fire_at_or_after(dt) == datetime(2026, 5, 10, 14, 23, 1)
