from datetime import datetime, timedelta
from app.services.alarm_service import get_due_alarms, get_next_alarm, _next_occurrence
from app.repositories.alarm_repository import Alarm


def _weekly_alarm(days: list[int], time: str = "07:00") -> Alarm:
    return Alarm(id=1, time=time, days_of_week=days, enabled=True,
                 repeat_type="weekly", label=None, light=False)


def _once_alarm(time: str) -> Alarm:
    return Alarm(id=2, time=time, days_of_week=[], enabled=True,
                 repeat_type="once", label=None, light=False)


def test_next_occurrence_weekly_same_day_future():
    now = datetime(2026, 5, 11, 6, 0)  # Monday 06:00
    alarm = _weekly_alarm([0])  # Monday 07:00
    result = _next_occurrence(alarm, now)
    assert result == datetime(2026, 5, 11, 7, 0)


def test_next_occurrence_weekly_same_day_past_wraps_to_next_week():
    now = datetime(2026, 5, 11, 8, 0)  # Monday 08:00 (alarm at 07:00 already passed)
    alarm = _weekly_alarm([0])
    result = _next_occurrence(alarm, now)
    assert result == datetime(2026, 5, 18, 7, 0)


def test_next_occurrence_weekly_different_day():
    now = datetime(2026, 5, 11, 8, 0)  # Monday
    alarm = _weekly_alarm([2])  # Wednesday
    result = _next_occurrence(alarm, now)
    assert result == datetime(2026, 5, 13, 7, 0)


def test_next_occurrence_once_future():
    now = datetime(2026, 5, 11, 6, 0)
    alarm = _once_alarm("07:30")
    result = _next_occurrence(alarm, now)
    assert result == datetime(2026, 5, 11, 7, 30)


def test_next_occurrence_once_past_returns_none():
    now = datetime(2026, 5, 11, 8, 0)
    alarm = _once_alarm("07:30")
    result = _next_occurrence(alarm, now)
    assert result is None


def test_get_due_alarms_returns_alarm_in_window(test_db_path, monkeypatch):
    from app.repositories import alarm_repository as alarm_repo
    alarm_repo.create("07:00", [0], True, "weekly", None, False)
    # Simulate "now" = 07:00:30 on a Monday
    fake_now = datetime(2026, 5, 11, 7, 0, 30)
    monkeypatch.setattr("app.services.alarm_service.datetime", _FakeDatetime(fake_now))
    due = get_due_alarms()
    assert len(due) == 1


def test_get_due_alarms_misses_alarm_older_than_2_minutes(test_db_path, monkeypatch):
    from app.repositories import alarm_repository as alarm_repo
    alarm_repo.create("07:00", [0], True, "weekly", None, False)
    fake_now = datetime(2026, 5, 11, 7, 3, 0)  # 3 minutes after alarm
    monkeypatch.setattr("app.services.alarm_service.datetime", _FakeDatetime(fake_now))
    due = get_due_alarms()
    assert len(due) == 0


class _FakeDatetime:
    """Minimal datetime mock that returns a fixed 'now'."""
    def __init__(self, now: datetime):
        self._now = now
    def now(self):
        return self._now
    def combine(self, *args, **kwargs):
        return datetime.combine(*args, **kwargs)
    def strptime(self, *args, **kwargs):
        return datetime.strptime(*args, **kwargs)
    def fromisoformat(self, *args, **kwargs):
        return datetime.fromisoformat(*args, **kwargs)


from app.services.alarm_service import pick_active_sunrise


def test_pick_sunrise_no_alarms(test_db_path):
    now = datetime(2026, 5, 11, 6, 30)
    assert pick_active_sunrise(now) is None


def test_pick_sunrise_ignores_alarm_with_light_off(test_db_path):
    from app.repositories import alarm_repository as repo
    repo.create("07:00", [0], True, "weekly", None, light=False, light_fade_minutes=30)
    now = datetime(2026, 5, 11, 6, 45)
    assert pick_active_sunrise(now) is None


def test_pick_sunrise_ignores_alarm_with_zero_fade(test_db_path):
    from app.repositories import alarm_repository as repo
    repo.create("07:00", [0], True, "weekly", None, light=True, light_fade_minutes=0)
    now = datetime(2026, 5, 11, 6, 45)
    assert pick_active_sunrise(now) is None


def test_pick_sunrise_returns_alarm_inside_window(test_db_path):
    from app.repositories import alarm_repository as repo
    repo.create("07:00", [0], True, "weekly", None, light=True, light_fade_minutes=30)
    now = datetime(2026, 5, 11, 6, 45)  # Monday, 15 min before alarm
    result = pick_active_sunrise(now)
    assert result is not None
    alarm, remaining_s, total_s = result
    assert alarm.time == "07:00"
    assert total_s == 30 * 60
    assert remaining_s == 15 * 60


def test_pick_sunrise_skips_alarm_outside_window(test_db_path):
    from app.repositories import alarm_repository as repo
    repo.create("07:00", [0], True, "weekly", None, light=True, light_fade_minutes=30)
    now = datetime(2026, 5, 11, 6, 0)  # Monday, 60 min before alarm
    assert pick_active_sunrise(now) is None


def test_pick_sunrise_picks_closer_when_two_in_window(test_db_path):
    from app.repositories import alarm_repository as repo
    a1 = repo.create("07:00", [0], True, "weekly", None, light=True, light_fade_minutes=30)
    a2 = repo.create("07:30", [0], True, "weekly", None, light=True, light_fade_minutes=60)
    now = datetime(2026, 5, 11, 6, 45)
    # a1: remaining 15 min; a2: remaining 45 min — a1 wins (smaller remaining).
    result = pick_active_sunrise(now)
    assert result is not None
    alarm, remaining_s, _ = result
    assert alarm.id == a1
    assert remaining_s == 15 * 60


def test_pick_sunrise_tie_broken_by_lower_id(test_db_path):
    from app.repositories import alarm_repository as repo
    a1 = repo.create("07:00", [0], True, "weekly", None, light=True, light_fade_minutes=30)
    a2 = repo.create("07:00", [0], True, "weekly", None, light=True, light_fade_minutes=30)
    now = datetime(2026, 5, 11, 6, 45)
    result = pick_active_sunrise(now)
    assert result is not None
    alarm, _, _ = result
    assert alarm.id == min(a1, a2)


def test_pick_sunrise_once_alarm_in_past_skipped(test_db_path):
    from app.repositories import alarm_repository as repo
    repo.create("07:00", [], True, "once", None, light=True, light_fade_minutes=30)
    now = datetime(2026, 5, 11, 8, 0)  # past 07:00
    assert pick_active_sunrise(now) is None


def test_pick_sunrise_weekly_other_day_outside_window(test_db_path):
    from app.repositories import alarm_repository as repo
    # Alarm on Monday only, now is Saturday — next occurrence is in 2 days.
    repo.create("07:00", [0], True, "weekly", None, light=True, light_fade_minutes=30)
    now = datetime(2026, 5, 16, 6, 45)  # Saturday
    assert pick_active_sunrise(now) is None


def _nap_alarm(alarm_id: int, target_at: str, duration_min: int = 20) -> Alarm:
    return Alarm(
        id=alarm_id, time=target_at[11:16], days_of_week=[],
        enabled=True, repeat_type="once", label="Nap",
        light=False, light_fade_minutes=0,
        kind="nap", nap_target_at=target_at,
        nap_duration_minutes=duration_min, esp32_button=False,
    )


def test_next_occurrence_nap_future_target():
    now = datetime(2026, 5, 11, 14, 0)
    alarm = _nap_alarm(99, "2026-05-11T14:20:00")
    assert _next_occurrence(alarm, now) == datetime(2026, 5, 11, 14, 20)


def test_next_occurrence_nap_past_target_returns_none():
    now = datetime(2026, 5, 11, 14, 30)
    alarm = _nap_alarm(99, "2026-05-11T14:20:00")
    assert _next_occurrence(alarm, now) is None


def test_next_occurrence_nap_missing_target_returns_none():
    alarm = Alarm(
        id=99, time="14:00", days_of_week=[], enabled=True,
        repeat_type="once", label=None, light=False, light_fade_minutes=0,
        kind="nap", nap_target_at=None, nap_duration_minutes=20,
        esp32_button=False,
    )
    now = datetime(2026, 5, 11, 14, 0)
    assert _next_occurrence(alarm, now) is None


def test_get_due_alarms_picks_up_nap_in_window(test_db_path, monkeypatch):
    from app.repositories import alarm_repository as alarm_repo
    target_at = "2026-05-11T14:00:00"
    alarm_repo.create(
        time="14:00", days_of_week=[], enabled=True, repeat_type="once",
        label="Nap", light=False, light_fade_minutes=0,
        kind="nap", nap_target_at=target_at,
        nap_duration_minutes=20, esp32_button=False,
    )
    fake_now = datetime(2026, 5, 11, 14, 0, 30)  # 30 s after nap target
    monkeypatch.setattr("app.services.alarm_service.datetime", _FakeDatetime(fake_now))
    due = get_due_alarms()
    assert len(due) == 1
    assert due[0][0].kind == "nap"


def test_pick_active_sunrise_skips_naps(test_db_path):
    # A nap should never be picked. Naps imply light_fade_minutes=0
    # so the existing filter excludes them; this test asserts that explicitly.
    from app.repositories import alarm_repository as alarm_repo
    alarm_repo.create(
        time="14:00", days_of_week=[], enabled=True, repeat_type="once",
        label="Nap", light=True, light_fade_minutes=0,
        kind="nap", nap_target_at="2026-05-11T14:30:00",
        nap_duration_minutes=30, esp32_button=False,
    )
    now = datetime(2026, 5, 11, 14, 15)
    assert pick_active_sunrise(now) is None
