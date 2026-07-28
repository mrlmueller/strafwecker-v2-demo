from unittest.mock import MagicMock
from app.services.esp_service import handle_callback
from app.schemas.esp import EspCallback
from app.repositories import alarm_repository as alarm_repo
from app.repositories import log_repository as log_repo
from app.services import log_service


def _setup(test_db_path):
    alarm_id = alarm_repo.create("07:00", [], True, "once", None, False)
    log_id = log_service.create_triggered(alarm_id)
    return alarm_id, log_id


def test_handle_timer_started(test_db_path):
    alarm_id, log_id = _setup(test_db_path)
    stop_fn = MagicMock()
    handle_callback(
        EspCallback(status="timer_started", alarm_id=alarm_id, log_id=log_id),
        alarm_is_active=True, stop_alarm_fn=stop_fn,
    )
    assert log_repo.get_recent(1)[0].state == "esp32_timer_started"
    stop_fn.assert_not_called()


def test_handle_button_pressed_stops_active_alarm(test_db_path):
    alarm_id, log_id = _setup(test_db_path)
    stop_fn = MagicMock()
    handle_callback(
        EspCallback(status="button_pressed", alarm_id=alarm_id, log_id=log_id,
                    time_to_button_sec=120),
        alarm_is_active=True, stop_alarm_fn=stop_fn,
    )
    stop_fn.assert_called_once()
    log = log_repo.get_recent(1)[0]
    assert log.state == "button_pressed_esp32"
    assert log.time_to_button_sec == 120


def test_handle_button_pressed_does_not_stop_inactive_alarm(test_db_path):
    alarm_id, log_id = _setup(test_db_path)
    stop_fn = MagicMock()
    handle_callback(
        EspCallback(status="button_pressed", alarm_id=alarm_id, log_id=log_id),
        alarm_is_active=False, stop_alarm_fn=stop_fn,
    )
    stop_fn.assert_not_called()


def test_handle_no_press(test_db_path):
    alarm_id, log_id = _setup(test_db_path)
    stop_fn = MagicMock()
    handle_callback(
        EspCallback(status="no_press", alarm_id=alarm_id, log_id=log_id),
        alarm_is_active=True, stop_alarm_fn=stop_fn,
    )
    assert log_repo.get_recent(1)[0].state == "no_button_press_esp32"
    stop_fn.assert_not_called()
