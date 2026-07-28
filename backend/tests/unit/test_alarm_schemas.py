import pytest
from pydantic import ValidationError
from app.schemas.alarm import AlarmCreate


def _alarm_payload(**overrides):
    base = {"time": "07:00", "days_of_week": [0], "enabled": True,
            "repeat_type": "weekly", "label": "Wake", "light": False,
            "light_fade_minutes": 0}
    base.update(overrides)
    return base


def _nap_payload(**overrides):
    base = {"time": "14:30", "days_of_week": [], "enabled": True,
            "repeat_type": "once", "label": "Nap", "light": False,
            "light_fade_minutes": 0, "kind": "nap",
            "nap_duration_minutes": 20}
    base.update(overrides)
    return base


def test_alarm_payload_defaults_kind_alarm_and_esp32_true():
    a = AlarmCreate(**_alarm_payload())
    assert a.kind == "alarm"
    assert a.esp32_button is True
    assert a.nap_target_at is None
    assert a.nap_duration_minutes is None


def test_nap_payload_accepted_with_minimum_duration():
    a = AlarmCreate(**_nap_payload(nap_duration_minutes=1))
    assert a.kind == "nap"
    assert a.nap_duration_minutes == 1


def test_nap_payload_accepted_with_maximum_duration():
    a = AlarmCreate(**_nap_payload(nap_duration_minutes=60))
    assert a.nap_duration_minutes == 60


def test_nap_payload_rejects_zero_duration():
    with pytest.raises(ValidationError):
        AlarmCreate(**_nap_payload(nap_duration_minutes=0))


def test_nap_payload_rejects_61_duration():
    with pytest.raises(ValidationError):
        AlarmCreate(**_nap_payload(nap_duration_minutes=61))


def test_nap_payload_rejects_missing_duration():
    with pytest.raises(ValidationError):
        AlarmCreate(**_nap_payload(nap_duration_minutes=None))


def test_invalid_kind_rejected():
    with pytest.raises(ValidationError):
        AlarmCreate(**_alarm_payload(kind="snooze"))


def test_alarm_payload_ignores_nap_fields_passed_with_kind_alarm():
    a = AlarmCreate(**_alarm_payload(nap_duration_minutes=20))
    assert a.kind == "alarm"
    assert a.nap_duration_minutes == 20
