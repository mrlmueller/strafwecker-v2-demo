from dataclasses import dataclass
from typing import Optional
from app.repositories.base import get_db


@dataclass
class Log:
    id: int
    timestamp: str
    last_update: str
    alarm_id: int
    state: str
    time_to_button_sec: Optional[int]
    pressed_in_time: Optional[bool]
    error_details: Optional[str]
    notes: Optional[str]


def _row_to_log(row) -> Log:
    pib = row["pressed_in_time"]
    return Log(
        id=row["id"],
        timestamp=row["timestamp"],
        last_update=row["last_update"],
        alarm_id=row["alarm_id"],
        state=row["state"],
        time_to_button_sec=row["time_to_button_sec"],
        pressed_in_time=bool(pib) if pib is not None else None,
        error_details=row["error_details"],
        notes=row["notes"],
    )


def insert(alarm_id: int, state: str = "triggered", notes: str = "") -> int:
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO logs (alarm_id, state, notes) VALUES (?, ?, ?)",
            (alarm_id, state, notes),
        )
        return cursor.lastrowid


def update(
    log_id: int,
    alarm_id: int,
    state: Optional[str] = None,
    time_to_button_sec: Optional[int] = None,
    pressed_in_time: Optional[bool] = None,
    error_details: Optional[str] = None,
    notes: Optional[str] = None,
) -> None:
    fields = ["last_update = CURRENT_TIMESTAMP"]
    values: list = []
    if state is not None:
        fields.append("state = ?")
        values.append(state)
    if time_to_button_sec is not None:
        fields.append("time_to_button_sec = ?")
        values.append(time_to_button_sec)
    if pressed_in_time is not None:
        fields.append("pressed_in_time = ?")
        values.append(int(pressed_in_time))
    if error_details is not None:
        fields.append("error_details = ?")
        values.append(error_details)
    if notes is not None:
        fields.append("notes = COALESCE(notes, '') || char(10) || ?")
        values.append(notes)
    if len(fields) == 1:
        return
    values.extend([log_id, alarm_id])
    with get_db() as conn:
        conn.execute(
            f"UPDATE logs SET {', '.join(fields)} WHERE id = ? AND alarm_id = ?",
            values,
        )


def get_recent(limit: int = 10) -> list[Log]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row_to_log(r) for r in rows]


def delete_older_than(cutoff_iso: str) -> int:
    """Delete alarm log rows with timestamp < cutoff_iso. Returns rows deleted."""
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM logs WHERE timestamp < ?", (cutoff_iso,))
        return cursor.rowcount
