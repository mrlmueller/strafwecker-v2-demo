import sqlite3
import pytest
from pathlib import Path
from fastapi.testclient import TestClient


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS alarms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    time TEXT NOT NULL,
    days_of_week TEXT,
    enabled INTEGER DEFAULT 1,
    repeat_type TEXT DEFAULT 'once',
    label TEXT,
    light INTEGER DEFAULT 0,
    light_fade_minutes INTEGER NOT NULL DEFAULT 0,
    kind TEXT NOT NULL DEFAULT 'alarm',
    nap_target_at TEXT,
    nap_duration_minutes INTEGER,
    esp32_button INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_update DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    alarm_id INTEGER NOT NULL,
    state TEXT NOT NULL DEFAULT 'triggered',
    time_to_button_sec INTEGER,
    pressed_in_time INTEGER,
    error_details TEXT,
    notes TEXT
);
CREATE TABLE IF NOT EXISTS network_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    connected INTEGER,
    wifi_signal_dBm TEXT,
    ping_external_ms TEXT,
    ping_router_ms TEXT,
    temperature_C TEXT
);
"""


@pytest.fixture
def test_db_path(tmp_path: Path, monkeypatch) -> Path:
    db = tmp_path / "test.db"
    monkeypatch.setattr("app.config.settings.database_path", db)
    conn = sqlite3.connect(str(db))
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()
    return db


@pytest.fixture
def client(test_db_path, monkeypatch):
    monkeypatch.setenv("API_KEY", "testkey")
    monkeypatch.setenv("TUYA_DEV_ID", "fakeid")
    monkeypatch.setenv("TUYA_LOCAL_KEY", "fakekey")
    monkeypatch.setenv("TUYA_IP", "127.0.0.1")
    monkeypatch.setenv("ESP32_IP", "127.0.0.1")
    # Patch the already-instantiated singleton so the middleware sees "testkey".
    import app.config as cfg
    monkeypatch.setattr(cfg.settings, "api_key", "testkey")
    from app.main import app
    return TestClient(app, headers={"x-api-key": "testkey"})
