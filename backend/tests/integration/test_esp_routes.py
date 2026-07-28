from app.repositories import alarm_repository as alarm_repo
from app.repositories import log_repository as log_repo
from app.services import log_service
import app.services.player_service as ps


def _setup_alarm_and_log(client):
    r = client.post("/api/v1/alarms/", json={"time": "07:00", "days_of_week": [], "enabled": True, "light": False})
    alarm_id = r.json()["alarm_id"]
    log_id = log_service.create_triggered(alarm_id)
    return alarm_id, log_id


def test_esp_callback_timer_started(client, test_db_path):
    alarm_id, log_id = _setup_alarm_and_log(client)
    res = client.post("/api/v1/esp/callback", json={
        "status": "timer_started", "alarm_id": alarm_id, "log_id": log_id,
    })
    assert res.status_code == 200
    assert log_repo.get_recent(1)[0].state == "esp32_timer_started"


def test_esp_callback_button_pressed_stops_alarm(client, test_db_path, monkeypatch):
    alarm_id, log_id = _setup_alarm_and_log(client)
    monkeypatch.setattr(ps, "_alarm_active", True)
    monkeypatch.setattr(ps, "_alarm_id", alarm_id)
    monkeypatch.setattr(ps, "_log_id", log_id)
    stopped = []

    def _fake_stop():
        stopped.append(True)
        return True

    monkeypatch.setattr(ps, "stop", _fake_stop)
    res = client.post("/api/v1/esp/callback", json={
        "status": "button_pressed", "alarm_id": alarm_id, "log_id": log_id,
        "time_to_button_sec": 90,
    })
    assert res.status_code == 200
    assert len(stopped) == 1
    log = log_repo.get_recent(1)[0]
    assert log.state == "button_pressed_esp32"


def test_esp_callback_requires_local_ip(client):
    r = client.post("/api/v1/alarms/", json={"time": "07:00", "days_of_week": [], "enabled": True, "light": False})
    alarm_id = r.json()["alarm_id"]
    log_id = log_service.create_triggered(alarm_id)
    res = client.post("/api/v1/esp/callback", json={
        "status": "no_press", "alarm_id": alarm_id, "log_id": log_id,
    })
    assert res.status_code == 200


from app.api.v1 import esp as esp_module


def test_trigger_alarm_skips_esp_notify_when_esp32_button_false(client, test_db_path, monkeypatch):
    notify_calls = []

    async def _fake_notify(alarm_id, log_id):
        notify_calls.append((alarm_id, log_id))

    async def _fake_play(alarm_id, log_id):
        return True

    monkeypatch.setattr(esp_module, "_notify_esp32", _fake_notify)
    monkeypatch.setattr(esp_module.player_service, "play", _fake_play)
    monkeypatch.setattr(esp_module.player_service, "is_active", lambda: False)

    r = client.post("/api/v1/alarms/", json={
        "time": "14:30", "days_of_week": [], "enabled": True,
        "repeat_type": "once", "label": "Nap", "light": False,
        "kind": "nap", "nap_duration_minutes": 20, "esp32_button": False,
    })
    alarm_id = r.json()["alarm_id"]
    log_id = log_service.create_triggered(alarm_id)

    res = client.post(f"/api/v1/esp/alarm/trigger?alarm_id={alarm_id}&log_id={log_id}")
    assert res.status_code == 200
    assert notify_calls == []


def test_trigger_alarm_notifies_esp_when_esp32_button_true(client, test_db_path, monkeypatch):
    notify_calls = []

    async def _fake_notify(alarm_id, log_id):
        notify_calls.append((alarm_id, log_id))

    async def _fake_play(alarm_id, log_id):
        return True

    monkeypatch.setattr(esp_module, "_notify_esp32", _fake_notify)
    monkeypatch.setattr(esp_module.player_service, "play", _fake_play)
    monkeypatch.setattr(esp_module.player_service, "is_active", lambda: False)

    r = client.post("/api/v1/alarms/", json={
        "time": "07:00", "days_of_week": [], "enabled": True,
        "repeat_type": "once", "label": "Wake", "light": False,
        "esp32_button": True,
    })
    alarm_id = r.json()["alarm_id"]
    log_id = log_service.create_triggered(alarm_id)

    res = client.post(f"/api/v1/esp/alarm/trigger?alarm_id={alarm_id}&log_id={log_id}")
    assert res.status_code == 200

    # Give the spawned task a tick to run.
    import time as _t
    _t.sleep(0.05)
    assert len(notify_calls) == 1
    assert notify_calls[0] == (alarm_id, log_id)
