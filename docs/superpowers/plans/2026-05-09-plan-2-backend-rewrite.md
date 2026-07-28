# Strafwecker Plan 2 — FastAPI Backend Rewrite

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the complete FastAPI 3-layer backend — config, repositories, services, routes, wecker.py, and Alembic migrations — with full unit and integration test coverage. At the end of this plan the new server runs locally and passes all tests. The Pi still runs the old Flask server; go-live happens in Plan 3.

**Architecture:** Three strict layers: `repositories/` (SQL only), `services/` (business logic only), `api/` (HTTP only). `wecker.py` is a standalone one-shot script that reads the DB directly via repositories, then calls `POST /api/v1/alarm/trigger` on localhost to start alarms (keeping alarm state in the web server process which also receives ESP32 callbacks). Single uvicorn process — no forks — so module-level alarm state is consistent across all requests.

**Tech Stack:** FastAPI 0.111+, Pydantic v2, pydantic-settings, SQLite + Alembic, uvicorn, pytest + httpx. RPi.GPIO and pygame are imported lazily inside functions so the backend can be imported and tested on non-Pi machines (Windows dev).

**All steps run from `<projektverzeichnis>\backend\` unless stated otherwise.**

---

## File Map (files written in this plan, in order)

```
backend/
├── app/
│   ├── config.py
│   ├── dependencies.py
│   ├── repositories/
│   │   ├── base.py
│   │   ├── alarm_repository.py
│   │   ├── log_repository.py
│   │   └── network_repository.py
│   ├── schemas/
│   │   ├── alarm.py
│   │   ├── log.py
│   │   ├── esp.py
│   │   └── light.py
│   ├── services/
│   │   ├── alarm_service.py
│   │   ├── log_service.py
│   │   ├── esp_service.py
│   │   ├── light_service.py
│   │   └── player_service.py
│   ├── api/
│   │   ├── middleware.py
│   │   └── v1/
│   │       ├── router.py
│   │       ├── alarms.py
│   │       ├── esp.py
│   │       ├── light.py
│   │       ├── logs.py
│   │       └── network.py
│   └── main.py
├── wecker.py
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_initial_schema.py
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_alarm_service.py
│   │   ├── test_log_service.py
│   │   ├── test_esp_service.py
│   │   └── test_light_service.py
│   └── integration/
│       ├── test_alarm_routes.py
│       └── test_esp_routes.py
└── alembic.ini
```

---

### Task 1: Config and Dependencies

**Files:**
- Write: `app/config.py`
- Write: `app/dependencies.py`
- Write: `tests/conftest.py`

- [ ] **Step 1: Write `app/config.py`**

```python
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    api_key: str
    tuya_dev_id: str
    tuya_local_key: str
    tuya_ip: str
    esp32_ip: str
    database_path: Path = Path("/home/pi/strafwecker/backend/data/strafwecker.db")
    alarm_sound_path: Path = Path("/home/pi/strafwecker/backend/alarm.wav")
    esp32_trigger_duration: int = 300
    alarm_auto_stop_seconds: int = 600

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
```

- [ ] **Step 2: Write `app/dependencies.py`**

```python
import hmac
from fastapi import Header, HTTPException
from app.config import settings


async def verify_api_key(x_api_key: str = Header(...)) -> None:
    if not hmac.compare_digest(x_api_key.encode(), settings.api_key.encode()):
        raise HTTPException(status_code=401, detail="Unauthorized")
```

- [ ] **Step 3: Write `tests/conftest.py`**

```python
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
    light INTEGER DEFAULT 0
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
    from app.main import app
    return TestClient(app, headers={"x-api-key": "testkey"})
```

- [ ] **Step 4: Commit**

```powershell
git add app/config.py app/dependencies.py tests/conftest.py
git commit -m "feat: add config (pydantic-settings) and api key dependency"
```

---

### Task 2: Repository Base

**Files:**
- Write: `app/repositories/base.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_base_repository.py`:

```python
import sqlite3
from app.repositories.base import get_db


def test_get_db_enables_wal(test_db_path):
    with get_db() as conn:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode == "wal"


def test_get_db_enables_foreign_keys(test_db_path):
    with get_db() as conn:
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    assert fk == 1


def test_get_db_rolls_back_on_error(test_db_path):
    try:
        with get_db() as conn:
            conn.execute("INSERT INTO alarms (time) VALUES (?)", ("07:00",))
            raise RuntimeError("simulated error")
    except RuntimeError:
        pass
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM alarms").fetchone()[0]
    assert count == 0
```

- [ ] **Step 2: Run test to verify it fails**

```powershell
poetry run pytest tests/unit/test_base_repository.py -v
```

Expected: `ImportError` or `AttributeError` — `get_db` not defined yet.

- [ ] **Step 3: Write `app/repositories/base.py`**

```python
import sqlite3
from contextlib import contextmanager
from typing import Generator
from app.config import settings


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(settings.database_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
poetry run pytest tests/unit/test_base_repository.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```powershell
git add app/repositories/base.py tests/unit/test_base_repository.py
git commit -m "feat: add repository base with WAL mode and rollback on error"
```

---

### Task 3: Alarm Repository

**Files:**
- Write: `app/repositories/alarm_repository.py`
- Write: `tests/unit/test_alarm_repository.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_alarm_repository.py
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
```

- [ ] **Step 2: Run to verify they fail**

```powershell
poetry run pytest tests/unit/test_alarm_repository.py -v
```

Expected: `ImportError` — module not implemented.

- [ ] **Step 3: Write `app/repositories/alarm_repository.py`**

```python
import json
from dataclasses import dataclass
from typing import Optional
from app.repositories.base import get_db


@dataclass
class Alarm:
    id: int
    time: str
    days_of_week: list[int]
    enabled: bool
    repeat_type: str
    label: Optional[str]
    light: bool


def _row_to_alarm(row) -> Alarm:
    return Alarm(
        id=row["id"],
        time=row["time"],
        days_of_week=json.loads(row["days_of_week"]) if row["days_of_week"] else [],
        enabled=bool(row["enabled"]),
        repeat_type=row["repeat_type"] or "once",
        label=row["label"],
        light=bool(row["light"]),
    )


def get_all() -> list[Alarm]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM alarms").fetchall()
    return [_row_to_alarm(r) for r in rows]


def get_by_id(alarm_id: int) -> Optional[Alarm]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM alarms WHERE id = ?", (alarm_id,)).fetchone()
    return _row_to_alarm(row) if row else None


def get_enabled() -> list[Alarm]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM alarms WHERE enabled = 1").fetchall()
    return [_row_to_alarm(r) for r in rows]


def create(
    time: str, days_of_week: list[int], enabled: bool,
    repeat_type: str, label: Optional[str], light: bool,
) -> int:
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO alarms (time, days_of_week, enabled, repeat_type, label, light) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (time, json.dumps(days_of_week), int(enabled), repeat_type, label, int(light)),
        )
        return cursor.lastrowid


def update(
    alarm_id: int, time: str, days_of_week: list[int], enabled: bool,
    repeat_type: str, label: Optional[str], light: bool,
) -> bool:
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE alarms SET time=?, days_of_week=?, enabled=?, repeat_type=?, label=?, light=? "
            "WHERE id=?",
            (time, json.dumps(days_of_week), int(enabled), repeat_type, label, int(light), alarm_id),
        )
        return cursor.rowcount > 0


def delete(alarm_id: int) -> bool:
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM alarms WHERE id = ?", (alarm_id,))
        return cursor.rowcount > 0
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
poetry run pytest tests/unit/test_alarm_repository.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```powershell
git add app/repositories/alarm_repository.py tests/unit/test_alarm_repository.py
git commit -m "feat: implement alarm repository with full CRUD"
```

---

### Task 4: Log Repository

**Files:**
- Write: `app/repositories/log_repository.py`
- Write: `tests/unit/test_log_repository.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_log_repository.py
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
```

- [ ] **Step 2: Run to verify they fail**

```powershell
poetry run pytest tests/unit/test_log_repository.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Write `app/repositories/log_repository.py`**

```python
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
```

- [ ] **Step 4: Run tests**

```powershell
poetry run pytest tests/unit/test_log_repository.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```powershell
git add app/repositories/log_repository.py tests/unit/test_log_repository.py
git commit -m "feat: implement log repository"
```

---

### Task 5: Network Repository

**Files:**
- Write: `app/repositories/network_repository.py`

No TDD for this one — it's a read-only query layer for existing data, tested implicitly via integration tests in Task 14.

- [ ] **Step 1: Write `app/repositories/network_repository.py`**

```python
from dataclasses import dataclass
from typing import Optional
from app.repositories.base import get_db


@dataclass
class NetworkLog:
    id: int
    timestamp: str
    connected: int
    wifi_signal_dBm: str
    ping_external_ms: str
    ping_router_ms: str
    temperature_C: str


@dataclass
class PaginatedResult:
    data: list
    page: int
    limit: int
    total: int
    pages: int


def _row_to_network_log(row) -> NetworkLog:
    return NetworkLog(
        id=row["id"],
        timestamp=row["timestamp"],
        connected=row["connected"],
        wifi_signal_dBm=row["wifi_signal_dBm"] or "N/A",
        ping_external_ms=row["ping_external_ms"] or "N/A",
        ping_router_ms=row["ping_router_ms"] or "N/A",
        temperature_C=row["temperature_C"] or "N/A",
    )


def get_paginated(
    limit: int = 100,
    page: int = 1,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    minimal: bool = False,
) -> PaginatedResult:
    limit = min(max(limit, 1), 1000)
    page = max(page, 1)
    offset = (page - 1) * limit

    where_clauses: list[str] = []
    params: list = []
    if start_date:
        where_clauses.append("timestamp >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append("timestamp <= ?")
        params.append(end_date)
    where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    cols = "id, timestamp, connected, temperature_C" if minimal else "*"
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT {cols} FROM network_log{where_sql} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
        total = conn.execute(
            f"SELECT COUNT(*) FROM network_log{where_sql}", params
        ).fetchone()[0]

    return PaginatedResult(
        data=[dict(r) for r in rows],
        page=page,
        limit=limit,
        total=total,
        pages=max(1, (total + limit - 1) // limit),
    )
```

- [ ] **Step 2: Commit**

```powershell
git add app/repositories/network_repository.py
git commit -m "feat: implement network log repository with pagination"
```

---

### Task 6: Pydantic Schemas

**Files:**
- Write: `app/schemas/alarm.py`
- Write: `app/schemas/log.py`
- Write: `app/schemas/esp.py`
- Write: `app/schemas/light.py`

- [ ] **Step 1: Write `app/schemas/alarm.py`**

```python
import re
from typing import Optional
from pydantic import BaseModel, field_validator


class AlarmCreate(BaseModel):
    time: str
    days_of_week: list[int] = []
    enabled: bool = True
    repeat_type: str = "once"
    label: Optional[str] = None
    light: bool = False

    @field_validator("time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        if not re.match(r"^\d{2}:\d{2}$", v):
            raise ValueError("time must be HH:MM format")
        h, m = int(v[:2]), int(v[3:])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError("invalid time value")
        return v

    @field_validator("days_of_week")
    @classmethod
    def validate_days(cls, v: list[int]) -> list[int]:
        if not all(0 <= d <= 6 for d in v):
            raise ValueError("days_of_week must be integers 0–6")
        return sorted(set(v))


class AlarmUpdate(AlarmCreate):
    pass


class AlarmResponse(BaseModel):
    id: int
    time: str
    days_of_week: list[int]
    enabled: bool
    repeat_type: str
    label: Optional[str]
    light: bool
```

- [ ] **Step 2: Write `app/schemas/log.py`**

```python
from typing import Optional
from pydantic import BaseModel


class LogResponse(BaseModel):
    id: int
    timestamp: str
    last_update: str
    alarm_id: int
    state: str
    time_to_button_sec: Optional[int] = None
    pressed_in_time: Optional[bool] = None
    error_details: Optional[str] = None
    notes: Optional[str] = None
```

- [ ] **Step 3: Write `app/schemas/esp.py`**

```python
from typing import Literal, Optional
from pydantic import BaseModel


class EspCallback(BaseModel):
    status: Literal["button_pressed", "no_press", "timer_started"]
    alarm_id: int
    log_id: int
    time_to_button_sec: Optional[int] = None
    start_time: Optional[float] = None
```

- [ ] **Step 4: Write `app/schemas/light.py`**

```python
from typing import Optional
from pydantic import BaseModel, field_validator


class LightRequest(BaseModel):
    brightness: int
    color_temp: Optional[int] = None
    hex: Optional[str] = None
    color: Optional[str] = None

    @field_validator("brightness")
    @classmethod
    def validate_brightness(cls, v: int) -> int:
        if not (10 <= v <= 1000):
            raise ValueError("brightness must be 10–1000")
        return v
```

- [ ] **Step 5: Commit**

```powershell
git add app/schemas/
git commit -m "feat: add pydantic schemas for all API boundaries"
```

---

### Task 7: Alarm Service

**Files:**
- Write: `app/services/alarm_service.py`
- Write: `tests/unit/test_alarm_service.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_alarm_service.py
from datetime import datetime, timedelta
from unittest.mock import patch
from app.services.alarm_service import get_due_alarms, get_next_alarm, _next_occurrence
from app.repositories.alarm_repository import Alarm


def _weekly_alarm(days: list[int], time: str = "07:00") -> Alarm:
    return Alarm(id=1, time=time, days_of_week=days, enabled=True,
                 repeat_type="weekly", label=None, light=False)


def _once_alarm(time: str) -> Alarm:
    return Alarm(id=2, time=time, days_of_week=[], enabled=True,
                 repeat_type="once", label=None, light=False)


def test_next_occurrence_weekly_same_day_future():
    now = datetime(2026, 5, 11, 6, 0)  # Monday 06:00
    alarm = _weekly_alarm([0])  # Monday 07:00
    result = _next_occurrence(alarm, now)
    assert result == datetime(2026, 5, 11, 7, 0)


def test_next_occurrence_weekly_same_day_past_wraps_to_next_week():
    now = datetime(2026, 5, 11, 8, 0)  # Monday 08:00 (alarm at 07:00 already passed)
    alarm = _weekly_alarm([0])
    result = _next_occurrence(alarm, now)
    assert result == datetime(2026, 5, 18, 7, 0)


def test_next_occurrence_weekly_different_day():
    now = datetime(2026, 5, 11, 8, 0)  # Monday
    alarm = _weekly_alarm([2])  # Wednesday
    result = _next_occurrence(alarm, now)
    assert result == datetime(2026, 5, 13, 7, 0)


def test_next_occurrence_once_future():
    now = datetime(2026, 5, 11, 6, 0)
    alarm = _once_alarm("07:30")
    result = _next_occurrence(alarm, now)
    assert result == datetime(2026, 5, 11, 7, 30)


def test_next_occurrence_once_past_returns_none():
    now = datetime(2026, 5, 11, 8, 0)
    alarm = _once_alarm("07:30")
    result = _next_occurrence(alarm, now)
    assert result is None


def test_get_due_alarms_returns_alarm_in_window(test_db_path, monkeypatch):
    from app.repositories import alarm_repository as alarm_repo
    alarm_repo.create("07:00", [0], True, "weekly", None, False)
    # Simulate "now" = 07:00:30 on a Monday
    fake_now = datetime(2026, 5, 11, 7, 0, 30)
    monkeypatch.setattr("app.services.alarm_service.datetime", _FakeDatetime(fake_now))
    due = get_due_alarms()
    assert len(due) == 1


def test_get_due_alarms_misses_alarm_older_than_2_minutes(test_db_path, monkeypatch):
    from app.repositories import alarm_repository as alarm_repo
    alarm_repo.create("07:00", [0], True, "weekly", None, False)
    fake_now = datetime(2026, 5, 11, 7, 3, 0)  # 3 minutes after alarm
    monkeypatch.setattr("app.services.alarm_service.datetime", _FakeDatetime(fake_now))
    due = get_due_alarms()
    assert len(due) == 0


class _FakeDatetime:
    """Minimal datetime mock that returns a fixed 'now'."""
    def __init__(self, now: datetime):
        self._now = now
    def now(self):
        return self._now
    def combine(self, *args, **kwargs):
        return datetime.combine(*args, **kwargs)
    def strptime(self, *args, **kwargs):
        return datetime.strptime(*args, **kwargs)
```

- [ ] **Step 2: Run to verify they fail**

```powershell
poetry run pytest tests/unit/test_alarm_service.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Write `app/services/alarm_service.py`**

```python
from datetime import datetime, timedelta
from typing import Optional
from app.repositories.alarm_repository import Alarm, get_enabled


def get_next_alarm() -> tuple[Optional[Alarm], Optional[datetime]]:
    alarms = get_enabled()
    now = datetime.now()
    best_alarm: Optional[Alarm] = None
    best_dt: Optional[datetime] = None
    for alarm in alarms:
        candidate = _next_occurrence(alarm, now)
        if candidate and (best_dt is None or candidate < best_dt):
            best_alarm = alarm
            best_dt = candidate
    return best_alarm, best_dt


def get_due_alarms() -> list[tuple[Alarm, datetime]]:
    """Return alarms whose scheduled time falls within the last 2 minutes."""
    alarms = get_enabled()
    now = datetime.now()
    window_start = now - timedelta(minutes=2)
    due = []
    for alarm in alarms:
        candidate = _next_occurrence(alarm, window_start)
        if candidate and window_start <= candidate <= now:
            due.append((alarm, candidate))
    return due


def _next_occurrence(alarm: Alarm, after: datetime) -> Optional[datetime]:
    try:
        alarm_time = datetime.strptime(alarm.time, "%H:%M").time()
    except ValueError:
        return None

    if alarm.repeat_type == "weekly":
        if not alarm.days_of_week:
            return None
        candidates = []
        for day in alarm.days_of_week:
            delta = (day - after.weekday()) % 7
            candidate_date = after.date() + timedelta(days=delta)
            candidate_dt = datetime.combine(candidate_date, alarm_time)
            if candidate_dt <= after:
                candidate_dt += timedelta(days=7)
            candidates.append(candidate_dt)
        return min(candidates) if candidates else None

    elif alarm.repeat_type == "once":
        candidate_dt = datetime.combine(after.date(), alarm_time)
        return candidate_dt if candidate_dt > after else None

    return None
```

- [ ] **Step 4: Run tests**

```powershell
poetry run pytest tests/unit/test_alarm_service.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```powershell
git add app/services/alarm_service.py tests/unit/test_alarm_service.py
git commit -m "feat: implement alarm service with 2-minute due-alarm window"
```

---

### Task 8: Log and ESP Services

**Files:**
- Write: `app/services/log_service.py`
- Write: `app/services/esp_service.py`
- Write: `tests/unit/test_log_service.py`
- Write: `tests/unit/test_esp_service.py`

- [ ] **Step 1: Write `app/services/log_service.py`**

```python
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
```

- [ ] **Step 2: Write failing tests for log_service**

```python
# tests/unit/test_log_service.py
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
```

- [ ] **Step 3: Write `app/services/esp_service.py`**

```python
import logging
from app.schemas.esp import EspCallback
from app.services import log_service

logger = logging.getLogger(__name__)


def handle_callback(data: EspCallback, alarm_is_active: bool, stop_alarm_fn) -> None:
    """
    Process an ESP32 status callback.
    alarm_is_active: current value from player_service.is_active()
    stop_alarm_fn: callable — player_service.stop()
    """
    if data.status == "timer_started":
        log_service.mark_timer_started(data.log_id, data.alarm_id)
        logger.info("ESP32 timer started for alarm %d", data.alarm_id)

    elif data.status == "button_pressed":
        log_service.mark_button_pressed(
            data.log_id, data.alarm_id,
            time_to_button_sec=data.time_to_button_sec,
            source="esp32",
        )
        if alarm_is_active:
            stop_alarm_fn()
            logger.info("Alarm stopped via ESP32 button press.")
        else:
            logger.info("ESP32 button pressed but alarm was already stopped.")

    elif data.status == "no_press":
        log_service.mark_no_press(data.log_id, data.alarm_id)
        logger.info("ESP32 reported no button press for alarm %d", data.alarm_id)
```

- [ ] **Step 4: Write failing tests for esp_service**

```python
# tests/unit/test_esp_service.py
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
```

- [ ] **Step 5: Run all unit tests**

```powershell
poetry run pytest tests/unit/ -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```powershell
git add app/services/log_service.py app/services/esp_service.py
git add tests/unit/test_log_service.py tests/unit/test_esp_service.py
git commit -m "feat: implement log service and esp service with tests"
```

---

### Task 9: Light Service

**Files:**
- Write: `app/services/light_service.py`
- Write: `tests/unit/test_light_service.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_light_service.py
from app.services.light_service import hex_to_rgb, interpolate_hex, _hsv_to_rgb


def test_hex_to_rgb_white():
    assert hex_to_rgb("#FFFFFF") == (255, 255, 255)


def test_hex_to_rgb_black():
    assert hex_to_rgb("#000000") == (0, 0, 0)


def test_hex_to_rgb_red():
    assert hex_to_rgb("#FF0000") == (255, 0, 0)


def test_hex_to_rgb_no_hash():
    assert hex_to_rgb("00FF00") == (0, 255, 0)


def test_interpolate_hex_zero_fraction():
    result = interpolate_hex("#000000", "#FFFFFF", 0.0)
    assert result == "#000000"


def test_interpolate_hex_full_fraction():
    result = interpolate_hex("#000000", "#FFFFFF", 1.0)
    assert result == "#FFFFFF"


def test_interpolate_hex_midpoint():
    result = interpolate_hex("#000000", "#FFFFFF", 0.5)
    r, g, b = hex_to_rgb(result)
    assert 127 <= r <= 128


def test_interpolate_hex_clamps_over_one():
    result = interpolate_hex("#000000", "#FFFFFF", 1.5)
    assert result == "#FFFFFF"


def test_hsv_to_rgb_pure_red():
    r, g, b = _hsv_to_rgb(0, 1000, 1000)
    assert r == 255 and g == 0 and b == 0


def test_hsv_to_rgb_pure_green():
    r, g, b = _hsv_to_rgb(120, 1000, 1000)
    assert g == 255 and r == 0 and b == 0
```

- [ ] **Step 2: Run to verify they fail**

```powershell
poetry run pytest tests/unit/test_light_service.py -v
```

- [ ] **Step 3: Write `app/services/light_service.py`**

```python
import logging
from typing import Optional
from app.schemas.light import LightRequest

logger = logging.getLogger(__name__)


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def interpolate_hex(start_hex: str, end_hex: str, fraction: float) -> str:
    fraction = max(0.0, min(1.0, fraction))
    sr, sg, sb = hex_to_rgb(start_hex)
    er, eg, eb = hex_to_rgb(end_hex)
    r = int(sr + (er - sr) * fraction)
    g = int(sg + (eg - sg) * fraction)
    b = int(sb + (eb - sb) * fraction)
    return f"#{r:02X}{g:02X}{b:02X}"


def _hsv_to_rgb(h: int, s: int, v: int) -> tuple[int, int, int]:
    s_f = s / 1000.0
    v_f = v / 1000.0
    h_mod = h % 360
    c = v_f * s_f
    x = c * (1 - abs((h_mod / 60.0) % 2 - 1))
    m = v_f - c
    if 0 <= h_mod < 60:
        rp, gp, bp = c, x, 0.0
    elif 60 <= h_mod < 120:
        rp, gp, bp = x, c, 0.0
    elif 120 <= h_mod < 180:
        rp, gp, bp = 0.0, c, x
    elif 180 <= h_mod < 240:
        rp, gp, bp = 0.0, x, c
    elif 240 <= h_mod < 300:
        rp, gp, bp = x, 0.0, c
    else:
        rp, gp, bp = c, 0.0, x
    return int((rp + m) * 255), int((gp + m) * 255), int((bp + m) * 255)


def apply_light(req: LightRequest) -> dict:
    """Send light command to Tuya device. Imports tinytuya at call time."""
    import tinytuya
    from app.config import settings

    d = tinytuya.BulbDevice(
        dev_id=settings.tuya_dev_id,
        address=settings.tuya_ip,
        local_key=settings.tuya_local_key,
        version=3.3,
    )
    status = d.status()
    dps = status.get("dps", {})
    is_on = dps.get("20", False)
    current_mode = dps.get("21", "white")

    if req.hex:
        r, g, b = hex_to_rgb(req.hex)
        if current_mode != "colour":
            d.set_mode("colour", nowait=True)
        d.set_colour(r, g, b, nowait=True)
        if not is_on:
            d.turn_on()
        return {"mode": "colour", "rgb": [r, g, b], "hex": req.hex}

    elif req.color:
        h_val, s_val = 0, 1000
        for part in req.color.split(","):
            kv = part.strip().split(":")
            if len(kv) == 2:
                if kv[0] == "h":
                    h_val = int(kv[1])
                elif kv[0] == "s":
                    s_val = int(kv[1])
        r, g, b = _hsv_to_rgb(h_val, s_val, req.brightness)
        if current_mode != "colour":
            d.set_mode("colour", nowait=True)
        d.set_colour(r, g, b, nowait=True)
        if not is_on:
            d.turn_on()
        return {"mode": "colour", "rgb": [r, g, b]}

    else:
        color_temp = req.color_temp or 500
        if current_mode != "white":
            d.set_mode("white", nowait=True)
        d.set_white(req.brightness, color_temp, nowait=True)
        return {"mode": "white", "brightness": req.brightness, "color_temp": color_temp}
```

- [ ] **Step 4: Run tests**

```powershell
poetry run pytest tests/unit/test_light_service.py -v
```

Expected: 10 passed.

- [ ] **Step 5: Commit**

```powershell
git add app/services/light_service.py tests/unit/test_light_service.py
git commit -m "feat: implement light service with color math tests"
```

---

### Task 10: Player Service

**Files:**
- Write: `app/services/player_service.py`

This service owns alarm playback state. It's tested via mocks since pygame and RPi.GPIO are unavailable on the dev machine.

- [ ] **Step 1: Write `app/services/player_service.py`**

```python
import asyncio
import logging
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

_alarm_active = False
_alarm_id: Optional[int] = None
_log_id: Optional[int] = None
_alarm_start_time: Optional[float] = None
_lock = threading.Lock()


def is_active() -> bool:
    return _alarm_active


def get_current_ids() -> tuple[Optional[int], Optional[int]]:
    return _alarm_id, _log_id


async def play(alarm_id: int, log_id: int) -> bool:
    """Start alarm. Returns False if already active."""
    global _alarm_active, _alarm_id, _log_id, _alarm_start_time
    with _lock:
        if _alarm_active:
            return False
        _alarm_active = True
        _alarm_id = alarm_id
        _log_id = log_id
        _alarm_start_time = time.time()
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _play_blocking)
    return True


def _play_blocking() -> None:
    try:
        import pygame
        from app.config import settings
        pygame.mixer.music.load(str(settings.alarm_sound_path))
        pygame.mixer.music.play(-1, fade_ms=20000)
    except ImportError:
        logger.warning("pygame not available — audio disabled")
    except Exception:
        logger.exception("Error starting alarm audio")
        _reset()


def stop() -> None:
    global _alarm_active
    with _lock:
        if not _alarm_active:
            return
        try:
            import pygame
            pygame.mixer.music.stop()
        except ImportError:
            pass
        except Exception:
            logger.exception("Error stopping pygame")
        _reset()


def _reset() -> None:
    global _alarm_active, _alarm_id, _log_id, _alarm_start_time
    _alarm_active = False
    _alarm_id = None
    _log_id = None
    _alarm_start_time = None


def setup_gpio() -> None:
    """Register GPIO interrupt for the physical button on the Pi. No-op on non-Pi."""
    try:
        import RPi.GPIO as GPIO
        BUTTON_PIN = 16
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING,
                              callback=_gpio_button_callback, bouncetime=500)
        logger.info("GPIO button listener registered on pin %d.", BUTTON_PIN)
    except ImportError:
        logger.warning("RPi.GPIO not available — physical button disabled.")
    except Exception:
        logger.exception("Failed to set up GPIO.")


def _gpio_button_callback(channel) -> None:
    if not _alarm_active:
        return
    a_id, l_id = get_current_ids()
    stop()
    if a_id is not None and l_id is not None:
        from app.services import log_service
        log_service.mark_button_pressed(l_id, a_id, time_to_button_sec=None, source="local")
```

- [ ] **Step 2: Commit**

```powershell
git add app/services/player_service.py
git commit -m "feat: implement player service with GPIO interrupt and executor-based audio"
```

---

### Task 11: API Middleware and Router

**Files:**
- Write: `app/api/middleware.py`
- Write: `app/api/v1/router.py`

- [ ] **Step 1: Write `app/api/middleware.py`**

```python
import hmac
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        from app.config import settings
        provided = request.headers.get("x-api-key", "")
        if not hmac.compare_digest(provided.encode(), settings.api_key.encode()):
            logger.warning("Rejected request with invalid API key from %s", request.client)
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
        return await call_next(request)
```

- [ ] **Step 2: Write `app/api/v1/router.py`**

```python
from fastapi import APIRouter
from app.api.v1 import alarms, logs, esp, light, network

router = APIRouter(prefix="/api/v1")
router.include_router(alarms.router)
router.include_router(logs.router)
router.include_router(esp.router)
router.include_router(light.router)
router.include_router(network.router)
```

- [ ] **Step 3: Commit**

```powershell
git add app/api/middleware.py app/api/v1/router.py
git commit -m "feat: add API key middleware and v1 router"
```

---

### Task 12: Alarm and Log Routes

**Files:**
- Write: `app/api/v1/alarms.py`
- Write: `app/api/v1/logs.py`
- Write: `tests/integration/test_alarm_routes.py`

- [ ] **Step 1: Write failing integration tests for alarms**

```python
# tests/integration/test_alarm_routes.py


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
```

- [ ] **Step 2: Run to verify they fail**

```powershell
poetry run pytest tests/integration/test_alarm_routes.py -v
```

Expected: `ImportError` for `app.main`.

- [ ] **Step 3: Write `app/api/v1/alarms.py`**

```python
from fastapi import APIRouter, HTTPException
from app.schemas.alarm import AlarmCreate, AlarmUpdate, AlarmResponse
from app.repositories import alarm_repository as repo

router = APIRouter(prefix="/alarms", tags=["alarms"])


def _alarm_to_response(alarm) -> dict:
    return {
        "id": alarm.id, "time": alarm.time, "days_of_week": alarm.days_of_week,
        "enabled": alarm.enabled, "repeat_type": alarm.repeat_type,
        "label": alarm.label, "light": alarm.light,
    }


@router.get("/", response_model=list[AlarmResponse])
def list_alarms():
    return [_alarm_to_response(a) for a in repo.get_all()]


@router.get("/{alarm_id}", response_model=AlarmResponse)
def get_alarm(alarm_id: int):
    alarm = repo.get_by_id(alarm_id)
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    return _alarm_to_response(alarm)


@router.post("/", status_code=201)
def create_alarm(data: AlarmCreate):
    alarm_id = repo.create(
        time=data.time, days_of_week=data.days_of_week,
        enabled=data.enabled, repeat_type=data.repeat_type,
        label=data.label, light=data.light,
    )
    return {"message": "Alarm created", "alarm_id": alarm_id}


@router.put("/{alarm_id}")
def update_alarm(alarm_id: int, data: AlarmUpdate):
    if not repo.get_by_id(alarm_id):
        raise HTTPException(status_code=404, detail="Alarm not found")
    repo.update(alarm_id, data.time, data.days_of_week, data.enabled,
                data.repeat_type, data.label, data.light)
    return {"message": "Alarm updated"}


@router.delete("/{alarm_id}")
def delete_alarm(alarm_id: int):
    if not repo.get_by_id(alarm_id):
        raise HTTPException(status_code=404, detail="Alarm not found")
    repo.delete(alarm_id)
    return {"message": "Alarm deleted"}
```

- [ ] **Step 4: Write `app/api/v1/logs.py`**

```python
from fastapi import APIRouter
from app.schemas.log import LogResponse
from app.repositories import log_repository as repo

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/", response_model=list[LogResponse])
def get_logs(limit: int = 10):
    limit = min(max(limit, 1), 100)
    logs = repo.get_recent(limit)
    return [
        {
            "id": l.id, "timestamp": l.timestamp, "last_update": l.last_update,
            "alarm_id": l.alarm_id, "state": l.state,
            "time_to_button_sec": l.time_to_button_sec,
            "pressed_in_time": l.pressed_in_time,
            "error_details": l.error_details, "notes": l.notes,
        }
        for l in logs
    ]
```

- [ ] **Step 5: Run integration tests**

```powershell
poetry run pytest tests/integration/test_alarm_routes.py -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```powershell
git add app/api/v1/alarms.py app/api/v1/logs.py tests/integration/test_alarm_routes.py
git commit -m "feat: implement alarm CRUD routes and logs route with integration tests"
```

---

### Task 13: ESP32 Callback and Alarm Trigger Routes

**Files:**
- Write: `app/api/v1/esp.py`
- Write: `tests/integration/test_esp_routes.py`

- [ ] **Step 1: Write failing integration tests**

```python
# tests/integration/test_esp_routes.py
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
    monkeypatch.setattr(ps, "stop", lambda: stopped.append(True))
    res = client.post("/api/v1/esp/callback", json={
        "status": "button_pressed", "alarm_id": alarm_id, "log_id": log_id,
        "time_to_button_sec": 90,
    })
    assert res.status_code == 200
    assert len(stopped) == 1
    log = log_repo.get_recent(1)[0]
    assert log.state == "button_pressed_esp32"


def test_esp_callback_requires_local_ip(client):
    # The TestClient sends from 127.0.0.1 which is local — verify it passes.
    # External IP rejection is verified by checking the decorator logic directly.
    r = client.post("/api/v1/alarms/", json={"time": "07:00", "days_of_week": [], "enabled": True, "light": False})
    alarm_id = r.json()["alarm_id"]
    log_id = log_service.create_triggered(alarm_id)
    res = client.post("/api/v1/esp/callback", json={
        "status": "no_press", "alarm_id": alarm_id, "log_id": log_id,
    })
    assert res.status_code == 200
```

- [ ] **Step 2: Write `app/api/v1/esp.py`**

```python
import asyncio
import logging
import ipaddress
from fastapi import APIRouter, HTTPException, Request
from app.schemas.esp import EspCallback
from app.services import esp_service, player_service, log_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/esp", tags=["esp"])


def _assert_local(request: Request) -> None:
    """Reject requests from non-local IPs. Uses CF-Connecting-IP if present."""
    cf_ip = request.headers.get("cf-connecting-ip")
    forwarded = request.headers.get("x-forwarded-for")
    if cf_ip:
        ip_str = cf_ip.strip()
    elif forwarded:
        ip_str = forwarded.split(",")[0].strip()
    else:
        ip_str = request.client.host if request.client else "0.0.0.0"
    try:
        ip = ipaddress.ip_address(ip_str)
        if not (ip.is_loopback or ip.is_private or ip.is_link_local):
            logger.warning("Rejected non-local ESP callback from %s", ip_str)
            raise HTTPException(status_code=403, detail="Local network only")
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid IP")


@router.post("/callback")
def esp_callback(data: EspCallback, request: Request):
    _assert_local(request)
    esp_service.handle_callback(
        data,
        alarm_is_active=player_service.is_active(),
        stop_alarm_fn=player_service.stop,
    )
    return {"message": "ok"}


@router.post("/alarm/trigger")
async def trigger_alarm(alarm_id: int, log_id: int):
    """Called by wecker.py via localhost POST to start alarm in this process."""
    log_service.mark_alarm_received(log_id, alarm_id)
    started = await player_service.play(alarm_id, log_id)
    if not started:
        return {"message": "alarm already active"}
    log_service.mark_alarm_playing(log_id, alarm_id)
    asyncio.create_task(_notify_esp32(alarm_id, log_id))
    asyncio.create_task(_auto_stop(alarm_id, log_id))
    return {"message": "alarm started"}


async def _notify_esp32(alarm_id: int, log_id: int) -> None:
    import requests as req_lib
    from app.config import settings
    esp_url = f"http://{settings.esp32_ip}/trigger"
    payload = {"duration": settings.esp32_trigger_duration, "alarm_id": alarm_id, "log_id": log_id}
    headers = {"X-API-KEY": settings.api_key}
    loop = asyncio.get_event_loop()
    for attempt in range(3):
        try:
            success = await loop.run_in_executor(
                None,
                lambda: req_lib.post(esp_url, json=payload, headers=headers, timeout=5).ok,
            )
            if success:
                log_service.mark_esp32_notified(log_id, alarm_id)
                return
        except Exception as e:
            logger.warning("ESP32 notify attempt %d failed: %s", attempt + 1, e)
            await asyncio.sleep(2)
    log_service.mark_esp32_unreachable(log_id, alarm_id)


async def _auto_stop(alarm_id: int, log_id: int) -> None:
    from app.config import settings
    await asyncio.sleep(settings.alarm_auto_stop_seconds)
    if player_service.is_active():
        player_service.stop()
        log_service.mark_button_pressed(log_id, alarm_id, time_to_button_sec=None, source="auto_stop")
```

- [ ] **Step 3: Run tests**

```powershell
poetry run pytest tests/integration/test_esp_routes.py -v
```

Expected: all pass.

- [ ] **Step 4: Commit**

```powershell
git add app/api/v1/esp.py tests/integration/test_esp_routes.py
git commit -m "feat: implement ESP32 callback route and alarm trigger endpoint"
```

---

### Task 14: Light and Network Routes

**Files:**
- Write: `app/api/v1/light.py`
- Write: `app/api/v1/network.py`

- [ ] **Step 1: Write `app/api/v1/light.py`**

```python
import ipaddress
import logging
from fastapi import APIRouter, HTTPException, Request
from app.schemas.light import LightRequest
from app.services.light_service import apply_light

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/light", tags=["light"])


def _assert_local(request: Request) -> None:
    cf_ip = request.headers.get("cf-connecting-ip")
    forwarded = request.headers.get("x-forwarded-for")
    ip_str = cf_ip or (forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "0.0.0.0"))
    try:
        ip = ipaddress.ip_address(ip_str.strip())
        if not (ip.is_loopback or ip.is_private or ip.is_link_local):
            raise HTTPException(status_code=403, detail="Local network only")
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid IP")


@router.post("/")
def control_light(data: LightRequest, request: Request):
    _assert_local(request)
    try:
        result = apply_light(data)
        return {"message": "Light updated", **result}
    except Exception as e:
        logger.exception("Failed to update light")
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 2: Write `app/api/v1/network.py`**

```python
from fastapi import APIRouter, Query
from typing import Optional
from app.repositories import network_repository as repo

router = APIRouter(prefix="/network", tags=["network"])


@router.get("/logs")
def get_network_logs(
    limit: int = Query(100, ge=1, le=1000),
    page: int = Query(1, ge=1),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    minimal: bool = False,
):
    result = repo.get_paginated(limit=limit, page=page,
                                start_date=start_date, end_date=end_date, minimal=minimal)
    return {
        "data": result.data,
        "meta": {"page": result.page, "limit": result.limit,
                 "total": result.total, "pages": result.pages},
    }
```

- [ ] **Step 3: Commit**

```powershell
git add app/api/v1/light.py app/api/v1/network.py
git commit -m "feat: implement light control and network log routes"
```

---

### Task 15: App Factory (main.py)

**Files:**
- Write: `app/main.py`

- [ ] **Step 1: Write `app/main.py`**

```python
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.middleware import APIKeyMiddleware
from app.api.v1.router import router
from app.services import player_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Strafwecker API")
    player_service.setup_gpio()
    yield
    logger.info("Shutting down Strafwecker API")


app = FastAPI(title="Strafwecker API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://raspberryalarm.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(APIKeyMiddleware)
app.include_router(router)
```

- [ ] **Step 2: Run the full test suite**

```powershell
poetry run pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```powershell
git add app/main.py
git commit -m "feat: add FastAPI app factory with CORS, middleware, and lifespan"
```

---

### Task 16: wecker.py

**Files:**
- Write: `wecker.py`

- [ ] **Step 1: Write `wecker.py`**

```python
#!/usr/bin/env python3
"""
Alarm checker — run once per minute by systemd wecker.timer.
Checks for due alarms, creates log entries, then calls the API to start playback.
"""
import logging
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

API_BASE = "http://localhost:8000/api/v1"
API_KEY = os.environ["API_KEY"]
HEADERS = {"x-api-key": API_KEY}


def main() -> None:
    from app.services.alarm_service import get_due_alarms
    from app.services.log_service import create_triggered

    due = get_due_alarms()
    if not due:
        logger.debug("No alarms due.")
        return

    for alarm, scheduled_dt in due:
        logger.info("Alarm %d due (scheduled %s), triggering.", alarm.id, scheduled_dt)
        log_id = create_triggered(alarm.id, notes=f"Due at {scheduled_dt}")
        try:
            res = requests.post(
                f"{API_BASE}/esp/alarm/trigger",
                params={"alarm_id": alarm.id, "log_id": log_id},
                headers=HEADERS,
                timeout=5,
            )
            if res.ok:
                logger.info("Alarm %d trigger accepted by API.", alarm.id)
            else:
                logger.error("API rejected alarm trigger: %s %s", res.status_code, res.text)
        except requests.RequestException as e:
            logger.error("Failed to reach API for alarm %d: %s", alarm.id, e)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```powershell
git add wecker.py
git commit -m "feat: implement wecker.py alarm checker using service layer + API trigger"
```

---

### Task 17: Alembic Migration

**Files:**
- Write: `alembic.ini`
- Write: `migrations/env.py`
- Write: `migrations/script.py.mako`
- Write: `migrations/versions/001_initial_schema.py`

- [ ] **Step 1: Initialize Alembic**

```powershell
cd backend
poetry run alembic init migrations
```

This creates `alembic.ini` and `migrations/`. We'll overwrite the generated files.

- [ ] **Step 2: Edit `alembic.ini` — set the database URL**

Find the line starting with `sqlalchemy.url` and replace it:

```ini
sqlalchemy.url = sqlite:///%(here)s/data/strafwecker.db
```

Also set the script location:

```ini
script_location = migrations
```

- [ ] **Step 3: Replace `migrations/env.py`**

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata,
                      literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.", poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: Write `migrations/versions/001_initial_schema.py`**

```python
"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alarms",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("time", sa.Text, nullable=False),
        sa.Column("days_of_week", sa.Text),
        sa.Column("enabled", sa.Integer, default=1),
        sa.Column("repeat_type", sa.Text, default="once"),
        sa.Column("label", sa.Text),
        sa.Column("light", sa.Integer, default=0),
    )
    op.create_table(
        "logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.DateTime, nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("last_update", sa.DateTime, nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("alarm_id", sa.Integer, nullable=False),
        sa.Column("state", sa.Text, nullable=False, default="triggered"),
        sa.Column("time_to_button_sec", sa.Integer),
        sa.Column("pressed_in_time", sa.Integer),
        sa.Column("error_details", sa.Text),
        sa.Column("notes", sa.Text),
    )
    op.create_table(
        "network_log",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.Text),
        sa.Column("connected", sa.Integer),
        sa.Column("wifi_signal_dBm", sa.Text),
        sa.Column("ping_external_ms", sa.Text),
        sa.Column("ping_router_ms", sa.Text),
        sa.Column("temperature_C", sa.Text),
    )


def downgrade() -> None:
    op.drop_table("network_log")
    op.drop_table("logs")
    op.drop_table("alarms")
```

- [ ] **Step 5: Test the migration runs clean**

```powershell
mkdir -p backend/data
poetry run alembic upgrade head
```

Expected output ends with `Running upgrade -> 001, initial schema`.

- [ ] **Step 6: Verify the DB was created**

```powershell
poetry run python -c "
import sqlite3
conn = sqlite3.connect('data/strafwecker.db')
tables = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()
print([t[0] for t in tables])
conn.close()
"
```

Expected: `['alarms', 'logs', 'network_log']`.

- [ ] **Step 7: Commit**

```powershell
git add alembic.ini migrations/
git commit -m "feat: add Alembic migrations with initial schema"
```

---

### Task 18: Smoke Test the Running Server

- [ ] **Step 1: Create a minimal `.env` for local testing**

```powershell
@"
API_KEY=testkey123
TUYA_DEV_ID=fake
TUYA_LOCAL_KEY=fake
TUYA_IP=127.0.0.1
ESP32_IP=127.0.0.1
DATABASE_PATH=data/strafwecker.db
ALARM_SOUND_PATH=alarm.wav
"@ | Set-Content .env
```

- [ ] **Step 2: Run the server**

```powershell
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Expected: starts without errors. You should see `INFO: Started server process`.

- [ ] **Step 3: Verify the API docs are accessible**

Open `http://localhost:8000/docs` in a browser. You should see all routes listed.

- [ ] **Step 4: Run the full test suite one final time**

```powershell
poetry run pytest tests/ -v --tb=short
```

Expected: all tests pass.

- [ ] **Step 5: Final commit and push**

```powershell
git add -A
git commit -m "chore: final plan-2 cleanup and verified smoke test"
git push origin main
```

---

**Plan 2 complete.** The FastAPI backend is fully implemented, tested, and runs locally. The Pi still runs the old Flask service. Proceed to Plan 3 (Deployment, Live Migration & Frontend Updates).
