from app.services import log_service
from app.repositories import alarm_repository as alarm_repo
from app.repositories import log_repository as log_repo


def _setup(test_db_path):
    alarm_id = alarm_repo.create("07:00", [], True, "once", None, False)
    log_id = log_service.create_triggered(alarm_id, notes="initial")
    return alarm_id, log_id


def test_create_triggered(test_db_path):
    alarm_id, log_id = _setup(test_db_path)
    logs = log_repo.get_recent(1)
    assert logs[0].state == "triggered"


def test_mark_alarm_playing(test_db_path):
    alarm_id, log_id = _setup(test_db_path)
    log_service.mark_alarm_playing(log_id, alarm_id)
    assert log_repo.get_recent(1)[0].state == "alarm_playing"


def test_mark_button_pressed_esp32(test_db_path):
    alarm_id, log_id = _setup(test_db_path)
    log_service.mark_button_pressed(log_id, alarm_id, time_to_button_sec=90, source="esp32")
    log = log_repo.get_recent(1)[0]
    assert log.state == "button_pressed_esp32"
    assert log.time_to_button_sec == 90
    assert log.pressed_in_time is True


def test_mark_no_press(test_db_path):
    alarm_id, log_id = _setup(test_db_path)
    log_service.mark_no_press(log_id, alarm_id)
    log = log_repo.get_recent(1)[0]
    assert log.state == "no_button_press_esp32"
    assert log.pressed_in_time is False
