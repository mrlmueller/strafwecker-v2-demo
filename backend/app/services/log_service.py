from typing import Optional
from app.repositories import log_repository as repo


def create_triggered(alarm_id: int, notes: str = "") -> int:
    return repo.insert(alarm_id, state="triggered", notes=notes)


def mark_alarm_received(log_id: int, alarm_id: int) -> None:
    repo.update(log_id, alarm_id, state="alarm_received")


def mark_alarm_playing(log_id: int, alarm_id: int) -> None:
    repo.update(log_id, alarm_id, state="alarm_playing", notes="Sound playing.")


def mark_esp32_notified(log_id: int, alarm_id: int) -> None:
    repo.update(log_id, alarm_id, state="esp32_notified")


def mark_esp32_unreachable(log_id: int, alarm_id: int) -> None:
    repo.update(log_id, alarm_id, state="esp32_unreachable")


def mark_timer_started(log_id: int, alarm_id: int) -> None:
    repo.update(log_id, alarm_id, state="esp32_timer_started")


def mark_button_pressed(
    log_id: int, alarm_id: int, time_to_button_sec: Optional[int], source: str
) -> None:
    repo.update(
        log_id, alarm_id,
        state=f"button_pressed_{source}",
        time_to_button_sec=time_to_button_sec,
        pressed_in_time=True,
    )


def mark_no_press(log_id: int, alarm_id: int) -> None:
    repo.update(log_id, alarm_id, state="no_button_press_esp32", pressed_in_time=False)


def mark_error(log_id: int, alarm_id: int, error: str) -> None:
    repo.update(log_id, alarm_id, state="error", error_details=error)
