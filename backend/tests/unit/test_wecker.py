from dataclasses import dataclass
from datetime import datetime
from wecker import _build_recently_handled_ids


@dataclass
class _FakeLog:
    alarm_id: int
    state: str
    timestamp: str


def test_dedup_picks_up_log_within_window():
    now_utc = datetime(2026, 5, 10, 17, 14, 0)
    logs = [_FakeLog(alarm_id=42, state="alarm_received",
                     timestamp="2026-05-10 17:13:30")]
    assert _build_recently_handled_ids(now_utc, logs, 150) == {42}


def test_dedup_excludes_log_outside_window():
    now_utc = datetime(2026, 5, 10, 17, 14, 0)
    logs = [_FakeLog(alarm_id=42, state="alarm_received",
                     timestamp="2026-05-10 17:00:00")]
    assert _build_recently_handled_ids(now_utc, logs, 150) == set()


def test_dedup_excludes_state_not_in_handled_set():
    now_utc = datetime(2026, 5, 10, 17, 14, 0)
    logs = [_FakeLog(alarm_id=42, state="error",
                     timestamp="2026-05-10 17:13:30")]
    assert _build_recently_handled_ids(now_utc, logs, 150) == set()


def test_dedup_returns_multiple_alarm_ids():
    now_utc = datetime(2026, 5, 10, 17, 14, 0)
    logs = [
        _FakeLog(alarm_id=42, state="alarm_received",
                 timestamp="2026-05-10 17:13:30"),
        _FakeLog(alarm_id=43, state="button_pressed_local",
                 timestamp="2026-05-10 17:13:00"),
    ]
    assert _build_recently_handled_ids(now_utc, logs, 150) == {42, 43}


def test_dedup_handles_local_vs_utc_correctly():
    # Regression: with the previous code, comparing local datetime.now() against a
    # UTC timestamp produced a delta of one timezone offset (~7200s for Berlin DST),
    # so logs outside the dedup window were always seen as outside, breaking dedup.
    # Here we simulate the WORKING case: both sides are UTC, log is 30s old, so it
    # IS in window. (The bug would have rejected it.)
    now_utc = datetime(2026, 5, 10, 17, 14, 0)
    logs = [_FakeLog(alarm_id=42, state="alarm_received",
                     timestamp="2026-05-10 17:13:30")]
    assert _build_recently_handled_ids(now_utc, logs, 150) == {42}
