#!/usr/bin/env python3
"""
Alarm checker — run once per minute by systemd wecker.timer.
Checks for due alarms, creates log entries, then calls the API to start playback.
"""
import logging
import os
import sys
from datetime import datetime, timezone

import requests

sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

API_BASE = "http://localhost:8000/api/v1"

# States that confirm the alarm was successfully handed off to the API.
# "triggered" (log created but API not reached) and "error" are NOT in this set,
# so failed triggers are retried on the next minute.
_HANDLED_STATES = {
    "alarm_received", "alarm_playing", "esp32_notified", "esp32_unreachable",
    "button_pressed_esp32", "button_pressed_local", "button_pressed_auto_stop",
    "no_button_press_esp32", "esp32_timer_started",
}
_DEDUP_WINDOW_SECONDS = 150  # 2.5 min — covers two consecutive wecker.py runs


def _build_recently_handled_ids(
    now_utc: datetime, recent_logs: list, window_seconds: int,
) -> set[int]:
    """Return alarm IDs whose recent log row is within window_seconds of now_utc.

    log.timestamp comes from SQLite CURRENT_TIMESTAMP (UTC), so callers must pass
    a UTC-naive `now_utc`. Comparing UTC timestamps against a local `datetime.now()`
    breaks the dedup window by the timezone offset and causes duplicate fires.
    """
    return {
        log.alarm_id for log in recent_logs
        if log.state in _HANDLED_STATES
        and (now_utc - datetime.fromisoformat(log.timestamp)).total_seconds() < window_seconds
    }


def main() -> None:
    from app.services.alarm_service import get_due_alarms, pick_active_sunrise
    from app.services.light_service import compute_sunrise_payload
    from app.services.log_service import create_triggered, mark_error
    from app.repositories import log_repository as log_repo
    from app.repositories import alarm_repository

    api_key = os.environ.get("API_KEY")
    if not api_key:
        logger.critical("API_KEY environment variable not set.")
        return
    headers = {"x-api-key": api_key}

    due = get_due_alarms()
    if not due:
        logger.debug("No alarms due.")
    else:
        # Build set of alarm IDs already successfully handled within the dedup window.
        # Prevents double-firing when a user presses the button between two consecutive
        # wecker.py runs while the alarm is still within the 2-minute due window.
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        recent_logs = log_repo.get_recent(limit=50)
        recently_handled_ids = _build_recently_handled_ids(
            now_utc, recent_logs, _DEDUP_WINDOW_SECONDS,
        )

        for alarm, scheduled_dt in due:
            if alarm.id in recently_handled_ids:
                logger.info(
                    "Alarm %d already handled within the last %.0fs, skipping.",
                    alarm.id, _DEDUP_WINDOW_SECONDS,
                )
                continue

            logger.info("Alarm %d due (scheduled %s), triggering.", alarm.id, scheduled_dt)
            try:
                log_id = create_triggered(alarm.id, notes=f"Due at {scheduled_dt}")
            except Exception as e:
                logger.error("Failed to create log for alarm %d: %s", alarm.id, e)
                continue

            try:
                res = requests.post(
                    f"{API_BASE}/esp/alarm/trigger",
                    params={"alarm_id": alarm.id, "log_id": log_id},
                    headers=headers,
                    timeout=5,
                )
                if res.ok:
                    logger.info("Alarm %d trigger accepted by API.", alarm.id)
                    # Disable once alarms after firing so they don't re-fire the next day.
                    if alarm.repeat_type == "once":
                        alarm_repository.update(
                            alarm.id, alarm.time, alarm.days_of_week, False,
                            alarm.repeat_type, alarm.label, alarm.light, alarm.light_fade_minutes,
                            kind=alarm.kind, nap_target_at=alarm.nap_target_at,
                            nap_duration_minutes=alarm.nap_duration_minutes,
                            esp32_button=alarm.esp32_button,
                        )
                        logger.info("Once alarm %d disabled after triggering.", alarm.id)
                else:
                    logger.error("API rejected alarm trigger: %s %s", res.status_code, res.text)
                    mark_error(log_id, alarm.id, f"API rejected: {res.status_code} {res.text[:200]}")
            except requests.RequestException as e:
                logger.error("Failed to reach API for alarm %d: %s", alarm.id, e)
                mark_error(log_id, alarm.id, f"API unreachable: {e}")

    # Sunrise tick: re-derive bulb state from now+alarms each minute.
    picked = pick_active_sunrise(datetime.now())
    if picked is None:
        return

    alarm, remaining_s, total_s = picked

    try:
        status_res = requests.get(
            f"{API_BASE}/esp/alarm/status", headers=headers, timeout=5,
        )
        if status_res.ok and status_res.json().get("active"):
            logger.debug("Alarm currently active; skipping sunrise tick.")
            return
    except requests.RequestException as e:
        logger.warning("Could not check alarm status, skipping sunrise tick: %s", e)
        return

    payload = compute_sunrise_payload(remaining_s, total_s)
    try:
        res = requests.post(
            f"{API_BASE}/light/", json=payload, headers=headers, timeout=5,
        )
        if res.ok:
            logger.info(
                "Sunrise tick for alarm %d (remaining=%ds total=%ds): %s",
                alarm.id, remaining_s, total_s, payload,
            )
        else:
            logger.warning(
                "Sunrise tick rejected for alarm %d: %s %s",
                alarm.id, res.status_code, res.text[:200],
            )
    except requests.RequestException as e:
        logger.warning("Sunrise tick request failed for alarm %d: %s", alarm.id, e)


if __name__ == "__main__":
    main()
