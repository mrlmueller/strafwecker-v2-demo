import pytest
from app.repositories import alarm_repository as repo


def test_create_and_get_alarm(test_db_path):
    alarm_id = repo.create(
        time="07:30",
        days_of_week=[0, 1, 2, 3, 4],
        enabled=True,
        repeat_type="weekly",
        label="Weekday",
        light=True,
    )
    alarm = repo.get_by_id(alarm_id)
    assert alarm is not None
    assert alarm.time == "07:30"
    assert alarm.days_of_week == [0, 1, 2, 3, 4]
    assert alarm.enabled is True
    assert alarm.light is True


def test_get_all_returns_all(test_db_path):
    repo.create("06:00", [], True, "once", None, False)
    repo.create("08:00", [], True, "once", None, False)
    assert len(repo.get_all()) == 2


def test_get_enabled_filters_disabled(test_db_path):
    repo.create("06:00", [], True, "once", None, False)
    repo.create("08:00", [], False, "once", None, False)
    enabled = repo.get_enabled()
    assert len(enabled) == 1
    assert enabled[0].time == "06:00"


def test_update_alarm(test_db_path):
    alarm_id = repo.create("07:00", [], True, "once", None, False)
    repo.update(alarm_id, "09:00", [5, 6], False, "weekly", "Weekend", True)
    alarm = repo.get_by_id(alarm_id)
    assert alarm.time == "09:00"
    assert alarm.days_of_week == [5, 6]
    assert alarm.enabled is False


def test_delete_alarm(test_db_path):
    alarm_id = repo.create("07:00", [], True, "once", None, False)
    assert repo.delete(alarm_id) is True
    assert repo.get_by_id(alarm_id) is None


def test_get_by_id_not_found(test_db_path):
    assert repo.get_by_id(9999) is None


def test_create_nap_persists_kind_and_nap_fields(test_db_path):
    alarm_id = repo.create(
        time="14:30", days_of_week=[], enabled=True, repeat_type="once",
        label="Power nap", light=True, light_fade_minutes=0,
        kind="nap", nap_target_at="2026-05-10T14:30:00",
        nap_duration_minutes=20, esp32_button=False,
    )
    alarm = repo.get_by_id(alarm_id)
    assert alarm.kind == "nap"
    assert alarm.nap_target_at == "2026-05-10T14:30:00"
    assert alarm.nap_duration_minutes == 20
    assert alarm.esp32_button is False


def test_create_alarm_defaults_kind_to_alarm(test_db_path):
    alarm_id = repo.create(
        time="07:00", days_of_week=[0, 1], enabled=True, repeat_type="weekly",
        label=None, light=False, light_fade_minutes=0,
    )
    alarm = repo.get_by_id(alarm_id)
    assert alarm.kind == "alarm"
    assert alarm.nap_target_at is None
    assert alarm.nap_duration_minutes is None
    assert alarm.esp32_button is True


def test_update_round_trips_new_fields(test_db_path):
    alarm_id = repo.create(
        time="07:00", days_of_week=[], enabled=True, repeat_type="once",
        label=None, light=False, light_fade_minutes=0,
    )
    repo.update(
        alarm_id, time="14:00", days_of_week=[], enabled=True,
        repeat_type="once", label="Edit", light=True, light_fade_minutes=0,
        kind="nap", nap_target_at="2026-05-10T14:00:00",
        nap_duration_minutes=15, esp32_button=False,
    )
    alarm = repo.get_by_id(alarm_id)
    assert alarm.kind == "nap"
    assert alarm.nap_target_at == "2026-05-10T14:00:00"
    assert alarm.nap_duration_minutes == 15
    assert alarm.esp32_button is False
