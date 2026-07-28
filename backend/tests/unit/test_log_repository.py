from app.repositories import log_repository as repo
from app.repositories import alarm_repository as alarm_repo


def _make_alarm(test_db_path):
    return alarm_repo.create("07:00", [], True, "once", None, False)


def test_insert_log(test_db_path):
    alarm_id = _make_alarm(test_db_path)
    log_id = repo.insert(alarm_id, state="triggered", notes="test")
    assert log_id is not None
    logs = repo.get_recent(10)
    assert len(logs) == 1
    assert logs[0].state == "triggered"
    assert logs[0].alarm_id == alarm_id


def test_update_log_state(test_db_path):
    alarm_id = _make_alarm(test_db_path)
    log_id = repo.insert(alarm_id)
    repo.update(log_id, alarm_id, state="alarm_playing")
    logs = repo.get_recent(1)
    assert logs[0].state == "alarm_playing"


def test_update_log_button_press(test_db_path):
    alarm_id = _make_alarm(test_db_path)
    log_id = repo.insert(alarm_id)
    repo.update(log_id, alarm_id, time_to_button_sec=42, pressed_in_time=True)
    logs = repo.get_recent(1)
    assert logs[0].time_to_button_sec == 42
    assert logs[0].pressed_in_time is True


def test_update_log_appends_notes(test_db_path):
    alarm_id = _make_alarm(test_db_path)
    log_id = repo.insert(alarm_id, notes="first")
    repo.update(log_id, alarm_id, notes="second")
    logs = repo.get_recent(1)
    assert "first" in logs[0].notes
    assert "second" in logs[0].notes


def test_get_recent_limit(test_db_path):
    alarm_id = _make_alarm(test_db_path)
    for _ in range(15):
        repo.insert(alarm_id)
    assert len(repo.get_recent(10)) == 10
