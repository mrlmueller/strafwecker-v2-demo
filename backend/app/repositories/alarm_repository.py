import json
import logging
from dataclasses import dataclass
from typing import Optional
from app.repositories.base import get_db

logger = logging.getLogger(__name__)


@dataclass
class Alarm:
    id: int
    time: str
    days_of_week: list[int]
    enabled: bool
    repeat_type: str
    label: Optional[str]
    light: bool
    light_fade_minutes: int = 0
    kind: str = "alarm"
    nap_target_at: Optional[str] = None
    nap_duration_minutes: Optional[int] = None
    esp32_button: bool = True


def _row_to_alarm(row) -> Alarm:
    try:
        days = json.loads(row["days_of_week"]) if row["days_of_week"] else []
    except (json.JSONDecodeError, TypeError):
        logger.warning("Corrupted days_of_week for alarm %s, defaulting to []", row["id"])
        days = []
    return Alarm(
        id=row["id"],
        time=row["time"],
        days_of_week=days,
        enabled=bool(row["enabled"]),
        repeat_type=row["repeat_type"] or "once",
        label=row["label"],
        light=bool(row["light"]),
        light_fade_minutes=int(row["light_fade_minutes"] or 0),
        kind=row["kind"] or "alarm",
        nap_target_at=row["nap_target_at"],
        nap_duration_minutes=row["nap_duration_minutes"],
        esp32_button=bool(row["esp32_button"]),
    )


def get_all() -> list[Alarm]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM alarms").fetchall()
    return [_row_to_alarm(r) for r in rows]


def get_by_id(alarm_id: int) -> Optional[Alarm]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM alarms WHERE id = ?", (alarm_id,)).fetchone()
    return _row_to_alarm(row) if row else None


def get_enabled() -> list[Alarm]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM alarms WHERE enabled = 1").fetchall()
    return [_row_to_alarm(r) for r in rows]


def create(
    time: str, days_of_week: list[int], enabled: bool,
    repeat_type: str, label: Optional[str], light: bool,
    light_fade_minutes: int = 0,
    kind: str = "alarm",
    nap_target_at: Optional[str] = None,
    nap_duration_minutes: Optional[int] = None,
    esp32_button: bool = True,
) -> int:
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO alarms (time, days_of_week, enabled, repeat_type, label, "
            "light, light_fade_minutes, kind, nap_target_at, nap_duration_minutes, "
            "esp32_button) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (time, json.dumps(days_of_week), int(enabled), repeat_type, label,
             int(light), light_fade_minutes, kind, nap_target_at,
             nap_duration_minutes, int(esp32_button)),
        )
        return cursor.lastrowid


def update(
    alarm_id: int, time: str, days_of_week: list[int], enabled: bool,
    repeat_type: str, label: Optional[str], light: bool,
    light_fade_minutes: int = 0,
    kind: str = "alarm",
    nap_target_at: Optional[str] = None,
    nap_duration_minutes: Optional[int] = None,
    esp32_button: bool = True,
) -> bool:
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE alarms SET time=?, days_of_week=?, enabled=?, repeat_type=?, "
            "label=?, light=?, light_fade_minutes=?, kind=?, nap_target_at=?, "
            "nap_duration_minutes=?, esp32_button=? WHERE id=?",
            (time, json.dumps(days_of_week), int(enabled), repeat_type, label,
             int(light), light_fade_minutes, kind, nap_target_at,
             nap_duration_minutes, int(esp32_button), alarm_id),
        )
        return cursor.rowcount > 0


def delete(alarm_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM alarms WHERE id = ?", (alarm_id,))
        return cursor.rowcount > 0
