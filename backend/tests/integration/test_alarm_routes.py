def test_create_alarm(client):
    res = client.post("/api/v1/alarms/", json={
        "time": "07:30",
        "days_of_week": [0, 1, 2, 3, 4],
        "enabled": True,
        "repeat_type": "weekly",
        "label": "Weekday",
        "light": True,
    })
    assert res.status_code == 201
    assert "alarm_id" in res.json()


def test_list_alarms(client):
    client.post("/api/v1/alarms/", json={"time": "06:00", "days_of_week": [], "enabled": True, "light": False})
    res = client.get("/api/v1/alarms/")
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_get_alarm_by_id(client):
    r = client.post("/api/v1/alarms/", json={"time": "07:00", "days_of_week": [], "enabled": True, "light": False})
    alarm_id = r.json()["alarm_id"]
    res = client.get(f"/api/v1/alarms/{alarm_id}")
    assert res.status_code == 200
    assert res.json()["time"] == "07:00"


def test_get_alarm_not_found(client):
    res = client.get("/api/v1/alarms/9999")
    assert res.status_code == 404


def test_update_alarm(client):
    r = client.post("/api/v1/alarms/", json={"time": "07:00", "days_of_week": [], "enabled": True, "light": False})
    alarm_id = r.json()["alarm_id"]
    res = client.put(f"/api/v1/alarms/{alarm_id}", json={
        "time": "08:00", "days_of_week": [5, 6], "enabled": False,
        "repeat_type": "weekly", "label": "Weekend", "light": True,
    })
    assert res.status_code == 200
    updated = client.get(f"/api/v1/alarms/{alarm_id}").json()
    assert updated["time"] == "08:00"
    assert updated["enabled"] is False


def test_delete_alarm(client):
    r = client.post("/api/v1/alarms/", json={"time": "07:00", "days_of_week": [], "enabled": True, "light": False})
    alarm_id = r.json()["alarm_id"]
    assert client.delete(f"/api/v1/alarms/{alarm_id}").status_code == 200
    assert client.get(f"/api/v1/alarms/{alarm_id}").status_code == 404


def test_invalid_time_format_rejected(client):
    res = client.post("/api/v1/alarms/", json={"time": "7:30", "days_of_week": [], "enabled": True, "light": False})
    assert res.status_code == 422


def test_unauthorized_request_rejected(client):
    from fastapi.testclient import TestClient
    from app.main import app
    unauthed = TestClient(app)
    res = unauthed.get("/api/v1/alarms/")
    assert res.status_code == 401


from datetime import datetime, timedelta


def test_create_nap_fills_target_when_omitted(client):
    res = client.post("/api/v1/alarms/", json={
        "time": "14:30", "days_of_week": [], "enabled": True,
        "repeat_type": "once", "label": "Power nap", "light": True,
        "kind": "nap", "nap_duration_minutes": 20, "esp32_button": False,
    })
    assert res.status_code == 201
    alarm_id = res.json()["alarm_id"]
    fetched = client.get(f"/api/v1/alarms/{alarm_id}").json()
    assert fetched["kind"] == "nap"
    assert fetched["nap_duration_minutes"] == 20
    assert fetched["esp32_button"] is False
    assert fetched["nap_target_at"] is not None
    target = datetime.fromisoformat(fetched["nap_target_at"])
    # Target is snapped to the next *:*:01 wecker firing, so it lies in
    # [now + duration_min, now + duration_min + 60s).
    elapsed = (target - datetime.now()).total_seconds()
    assert 20 * 60 - 5 <= elapsed <= 21 * 60 + 5
    assert target.second == 1


def test_create_nap_keeps_explicit_target(client):
    explicit = (datetime.now() + timedelta(minutes=45)).isoformat(timespec="seconds")
    res = client.post("/api/v1/alarms/", json={
        "time": "15:00", "days_of_week": [], "enabled": True,
        "repeat_type": "once", "label": "Nap", "light": False,
        "kind": "nap", "nap_duration_minutes": 45,
        "nap_target_at": explicit,
    })
    assert res.status_code == 201
    fetched = client.get(f"/api/v1/alarms/{res.json()['alarm_id']}").json()
    assert fetched["nap_target_at"] == explicit


def test_get_alarm_response_includes_new_fields(client):
    r = client.post("/api/v1/alarms/", json={
        "time": "07:00", "days_of_week": [], "enabled": True, "light": False,
    })
    alarm_id = r.json()["alarm_id"]
    fetched = client.get(f"/api/v1/alarms/{alarm_id}").json()
    assert fetched["kind"] == "alarm"
    assert fetched["esp32_button"] is True
    assert fetched["nap_target_at"] is None
    assert fetched["nap_duration_minutes"] is None


def test_restart_nap_resets_target_and_enables(client):
    r = client.post("/api/v1/alarms/", json={
        "time": "14:00", "days_of_week": [], "enabled": True,
        "repeat_type": "once", "label": "Nap", "light": False,
        "kind": "nap", "nap_duration_minutes": 15, "esp32_button": False,
    })
    alarm_id = r.json()["alarm_id"]
    fetched = client.get(f"/api/v1/alarms/{alarm_id}").json()
    fetched["enabled"] = False
    client.put(f"/api/v1/alarms/{alarm_id}", json=fetched)

    res = client.post(f"/api/v1/alarms/{alarm_id}/restart")
    assert res.status_code == 200
    body = res.json()
    assert "target_at" in body

    after = client.get(f"/api/v1/alarms/{alarm_id}").json()
    assert after["enabled"] is True
    new_target = datetime.fromisoformat(after["nap_target_at"])
    elapsed = (new_target - datetime.now()).total_seconds()
    assert 15 * 60 - 5 <= elapsed <= 16 * 60 + 5
    assert new_target.second == 1


def test_restart_rejects_non_nap_kind(client):
    r = client.post("/api/v1/alarms/", json={
        "time": "07:00", "days_of_week": [], "enabled": True, "light": False,
    })
    alarm_id = r.json()["alarm_id"]
    res = client.post(f"/api/v1/alarms/{alarm_id}/restart")
    assert res.status_code == 400


def test_restart_returns_404_when_missing(client):
    res = client.post("/api/v1/alarms/9999/restart")
    assert res.status_code == 404
