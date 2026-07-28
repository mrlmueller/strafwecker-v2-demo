from datetime import datetime, timedelta
from typing import Optional
from app.repositories.alarm_repository import Alarm, get_enabled


def get_next_alarm() -> tuple[Optional[Alarm], Optional[datetime]]:
    alarms = get_enabled()
    now = datetime.now()
    best_alarm: Optional[Alarm] = None
    best_dt: Optional[datetime] = None
    for alarm in alarms:
        candidate = _next_occurrence(alarm, now)
        if candidate and (best_dt is None or candidate < best_dt):
            best_alarm = alarm
            best_dt = candidate
    return best_alarm, best_dt


def get_due_alarms() -> list[tuple[Alarm, datetime]]:
    """Return alarms whose scheduled time falls within the last 2 minutes."""
    alarms = get_enabled()
    now = datetime.now()
    window_start = now - timedelta(minutes=2)
    due = []
    for alarm in alarms:
        candidate = _next_occurrence(alarm, window_start)
        if candidate and window_start <= candidate <= now:
            due.append((alarm, candidate))
    return due


def pick_active_sunrise(now: datetime) -> Optional[tuple[Alarm, int, int]]:
    """Pick the enabled alarm whose sunrise should drive the bulb right now.

    Returns (alarm, remaining_seconds, total_seconds) for the candidate with the
    smallest remaining_seconds (closest in time). Ties broken by alarm.id ascending.
    Returns None when no alarm is in any fade window.
    """
    alarms = get_enabled()
    best: Optional[tuple[Alarm, int, int]] = None
    for alarm in alarms:
        if not alarm.light or alarm.light_fade_minutes <= 0:
            continue
        candidate = _next_occurrence(alarm, now)
        if candidate is None:
            continue
        remaining_s = int((candidate - now).total_seconds())
        total_s = alarm.light_fade_minutes * 60
        if not (0 < remaining_s <= total_s):
            continue
        if best is None:
            best = (alarm, remaining_s, total_s)
            continue
        b_alarm, b_remaining, _ = best
        if remaining_s < b_remaining or (remaining_s == b_remaining and alarm.id < b_alarm.id):
            best = (alarm, remaining_s, total_s)
    return best


def _next_occurrence(alarm: Alarm, after: datetime) -> Optional[datetime]:
    if alarm.kind == "nap":
        if not alarm.nap_target_at:
            return None
        try:
            target = datetime.fromisoformat(alarm.nap_target_at)
        except ValueError:
            return None
        return target if target > after else None

    try:
        alarm_time = datetime.strptime(alarm.time, "%H:%M").time()
    except ValueError:
        return None

    if alarm.repeat_type == "weekly":
        if not alarm.days_of_week:
            return None
        candidates = []
        for day in alarm.days_of_week:
            delta = (day - after.weekday()) % 7
            candidate_date = after.date() + timedelta(days=delta)
            candidate_dt = datetime.combine(candidate_date, alarm_time)
            if candidate_dt <= after:
                candidate_dt += timedelta(days=7)
            candidates.append(candidate_dt)
        return min(candidates) if candidates else None

    elif alarm.repeat_type == "once":
        candidate_dt = datetime.combine(after.date(), alarm_time)
        return candidate_dt if candidate_dt > after else None

    return None
