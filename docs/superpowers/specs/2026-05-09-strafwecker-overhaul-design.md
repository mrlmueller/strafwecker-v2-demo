# Strafwecker System Overhaul — Design Spec

**Date:** 2026-05-09  
**Status:** Approved

---

## Overview

Full overhaul of the Strafwecker alarm system: a two-part hardware+software system consisting of a Raspberry Pi (alarm player, Flask API, Tuya light control) and an ESP32 (5-minute button press countdown, RGB LED, penalty trigger). The current implementation has no git-based deployment, hardcoded secrets, a critical multi-worker alarm state bug, and code scattered across SSH-edited files. This spec describes the replacement architecture.

---

## System Context

```
[Browser / Vercel Frontend]
        │  HTTPS
        ▼
[Next.js API route proxy]  ← injects API key server-side
        │  HTTP + X-API-KEY
        ▼
[Cloudflared Tunnel]
        │
        ▼
[Raspberry Pi: FastAPI + uvicorn]
        │  GPIO / pygame
        ├── Speaker (alarm sound)
        ├── Button (local stop)
        ├── Tuya Bulb (light fade)
        │
        │  HTTP POST /trigger
        ▼
[ESP32: MicroPython HTTP server]
        │  Button press detection
        │  RGB LED status
        │  HTTP POST /api/v1/esp/callback → Pi
        └─ HTTPS POST → Cloud Function (penalty if no press)

[systemd wecker.timer] ── fires wecker.py every minute ──► [FastAPI services layer]
```

---

## Repository Structure

New GitHub repository: `strafwecker` (fresh, no migrated history).

```
strafwecker/
├── frontend/               # Next.js app (moved from current repo)
├── backend/
│   ├── app/
│   │   ├── main.py                   # FastAPI app factory
│   │   ├── config.py                 # pydantic-settings: all config from .env
│   │   ├── dependencies.py           # FastAPI DI: get_db(), verify_api_key()
│   │   ├── api/                      # LAYER 1: Presentation
│   │   │   ├── middleware.py         # API key auth, request logging
│   │   │   └── v1/
│   │   │       ├── router.py
│   │   │       ├── alarms.py
│   │   │       ├── logs.py
│   │   │       ├── esp.py
│   │   │       ├── light.py
│   │   │       └── network.py
│   │   ├── schemas/                  # Pydantic request/response models
│   │   │   ├── alarm.py
│   │   │   ├── log.py
│   │   │   ├── esp.py
│   │   │   └── light.py
│   │   ├── services/                 # LAYER 2: Business Logic
│   │   │   ├── alarm_service.py      # Next-alarm calc, scheduling logic
│   │   │   ├── esp_service.py        # Button press handling, penalty logic
│   │   │   ├── light_service.py      # Fade phase calculation, color interpolation
│   │   │   ├── player_service.py     # pygame audio + GPIO (run_in_executor)
│   │   │   └── log_service.py        # Log state machine
│   │   └── repositories/             # LAYER 3: Data Access
│   │       ├── base.py               # SQLite context manager, WAL mode
│   │       ├── alarm_repository.py
│   │       ├── log_repository.py
│   │       └── network_repository.py
│   ├── wecker.py                     # One-shot alarm checker (systemd timer)
│   ├── migrations/                   # Alembic migration files
│   ├── systemd/                      # Authoritative systemd unit files
│   │   ├── strafwecker-api.service
│   │   ├── wecker.service
│   │   ├── wecker.timer
│   │   └── cleanup_logs.timer
│   ├── pyproject.toml                # Poetry: ~10 real deps only
│   ├── .env.example                  # Template, no real values
│   └── tests/
│       ├── unit/
│       └── integration/
├── esp32/
│   ├── main.py
│   ├── config.py.example             # Template, no credentials
│   └── tests/                        # Syntax + logic checks (CI)
├── docs/
│   └── superpowers/specs/
├── .github/
│   └── workflows/
│       ├── backend-deploy.yml
│       ├── frontend.yml
│       └── esp32-check.yml
└── README.md
```

---

## Backend Architecture (3-Layer FastAPI)

### Layer 1: Presentation (api/)

- All routes are thin: parse schema → call service → return response.
- No business logic, no SQL.
- `middleware.py` handles API key auth for all routes using `hmac.compare_digest()` (timing-safe). OPTIONS requests bypass auth for CORS preflight.
- All routes mounted under `/api/v1/`.
- `local_only` protection on `/api/v1/esp/callback` and `/api/v1/light` uses `CF-Connecting-IP` header (set by Cloudflare, not spoofable by clients) instead of `X-Forwarded-For`.

### Layer 2: Services (services/)

- All business logic lives here. No HTTP, no SQL.
- `alarm_service.py`: single source of truth for next-alarm calculation. Used by both the FastAPI app and `wecker.py`. Checks within last 2 minutes to handle late systemd fires.
- `player_service.py`: wraps `pygame.mixer` and `RPi.GPIO`. All blocking calls wrapped in `asyncio.get_event_loop().run_in_executor()` so they do not stall the async event loop.
- `esp_service.py`: handles the state machine for ESP32 callbacks (`timer_started` → `button_pressed` | `no_press`). Owns the penalty-trigger logic.
- `light_service.py`: fade phase calculation (color phase → white phase) and hex color interpolation. Pure functions, no I/O.
- `log_service.py`: manages log row state transitions. Owns the `insert_log_row` / `update_log_row` logic.
- Alarm state (`alarm_active`, `alarm_id_in_play`, etc.) is managed inside `player_service.py` as module-level state. This is safe because FastAPI + uvicorn runs as a **single process** (no Gunicorn multi-worker fork), eliminating the critical multi-worker state bug from the current implementation.

### Layer 3: Repositories (repositories/)

- All SQL lives here. Returns plain dataclasses or dicts — never raw `sqlite3.Row` objects.
- `base.py` provides a context manager that opens a connection with `PRAGMA journal_mode=WAL` and `PRAGMA foreign_keys=ON`, commits on success, rolls back on exception.
- Absolute database path read from `config.py` (never a relative path).
- `alarm_repository.py`: CRUD for alarms table.
- `log_repository.py`: insert and update for logs table.
- `network_repository.py`: insert for network_log, paginated reads.

### wecker.py

- Standalone script imported into the same virtualenv.
- Imports `alarm_service` and `log_service` directly — no HTTP call to itself.
- Checks whether any alarm's scheduled time falls within the last 2 minutes (handles late systemd fires).
- Logs a `missed_alarm` warning if an alarm was due more than 2 minutes ago and has no log entry.
- Called by `wecker.timer` at `*:*:01` (1 second past each minute).

### Configuration

`config.py` uses `pydantic-settings.BaseSettings`. All fields are typed. App refuses to start with a clear error if a required secret is missing.

Required `.env` fields on the Pi:
```
API_KEY=
TUYA_DEV_ID=
TUYA_LOCAL_KEY=
TUYA_IP=
ESP32_IP=
DATABASE_PATH=/home/pi/strafwecker/backend/data/strafwecker.db
```

### Dependencies (pyproject.toml)

Replaces the current 200-entry `requirements.txt` (which includes all Raspberry Pi OS system packages):
```
fastapi, uvicorn[standard], pydantic-settings, python-dotenv,
pygame, RPi.GPIO, tinytuya, orjson, requests, alembic
```

### Database

- SQLite, WAL mode, foreign keys enabled.
- Schema managed by Alembic. All `CREATE TABLE IF NOT EXISTS` calls removed from application code.
- All timestamps stored as UTC ISO strings.
- Existing database migrated in place — no data loss.

---

## Deployment Pipeline

### Self-hosted GitHub Actions runner on Pi

The Pi runs the GitHub Actions runner as a systemd service. It connects outbound to GitHub — no inbound SSH port needed, no new firewall rules.

**`.github/workflows/backend-deploy.yml`** (triggers on `backend/**` changes):
1. Runs on self-hosted runner (the Pi itself).
2. `git pull origin main`
3. `poetry install --no-dev`
4. `poetry run pytest tests/unit/` — aborts deploy if tests fail.
5. `poetry run alembic upgrade head` — applies any pending migrations.
6. `sudo systemctl daemon-reload`
7. Symlinks `backend/systemd/*.service` and `*.timer` into `/etc/systemd/system/`.
8. `sudo systemctl restart strafwecker-api.service`
9. Keeps previous app directory as `/home/pi/strafwecker-backup/` for fast rollback.

**`.github/workflows/frontend.yml`** (triggers on `frontend/**` changes):
1. Runs on hosted GitHub runner.
2. `npm ci && npm run lint && npm run build` — catches errors before Vercel deploys.
3. Vercel deploys automatically via its own GitHub integration.

**`.github/workflows/esp32-check.yml`** (triggers on `esp32/**` changes):
1. Runs on hosted GitHub runner.
2. `python -m py_compile esp32/main.py` — syntax check.
3. `ruff check esp32/` — linting.
4. `pytest esp32/tests/` — unit tests using MicroPython stubs (pure logic: color math, payload building, timer arithmetic).

### Systemd services on Pi after migration

| Service | Replaces | Notes |
|---|---|---|
| `strafwecker-api.service` | `flask_alarm.service` | `uvicorn app.main:app`, single worker |
| `wecker.service` + `wecker.timer` | same | Unchanged pattern |
| `cloudflared.service` | same | Unchanged |
| `cleanup_logs.timer` | same | Unchanged |

Unit files live in `backend/systemd/` as the authoritative source. Deploy script symlinks them — editing in git and pushing is all that's needed to change service config.

---

## Pi Backup Strategy

Taken before any migration work begins.

**Layer 1 — Full SD card image:**
```bash
ssh raspberrypi "sudo dd if=/dev/mmcblk0 bs=4M status=progress | gzip" > pi-backup-20260509.img.gz
```
Byte-for-byte copy of the SD card to the Windows machine. Run from WSL or Git Bash (PowerShell does not support `$()` subshell in this context). Full recovery path: flash with Raspberry Pi Imager.

**Layer 2 — Database + code snapshot:**
```bash
ssh raspberrypi "sqlite3 /home/pi/Documents/flask_app/database.db '.dump'" > db-backup-$(date +%Y%m%d).sql
```
Committed to `backup/pre-migration/` branch of the new repo.

**Layer 3 — Fast rollback service:**
The deploy script keeps the previous working copy at `/home/pi/strafwecker-backup/`. A `strafwecker-api-backup.service` unit can be started manually to restore the previous version in seconds.

---

## Secrets Management

**On the Pi:** `/home/pi/strafwecker/backend/.env` — created manually once during setup, never committed to git.

**In GitHub:** Only `GH_RUNNER_TOKEN` (runner registration). No application secrets in GitHub.

**ESP32:** `esp32/config.py` in `.gitignore`. `esp32/config.py.example` committed with placeholder values.

**Frontend:** API key moved to a server-side Next.js API route. `NEXT_PUBLIC_API_KEY` removed entirely — key never ships in the browser bundle.

---

## Frontend Changes

Minimal changes — the frontend is largely fine. Targeted fixes only:

1. **API proxy route** (`frontend/app/api/[...path]/route.ts`): server-side proxy that injects `API_KEY` from a non-public env var. Removes `NEXT_PUBLIC_API_KEY`.
2. **Timezone fix removed**: Pi stores UTC, frontend parses with `new Date(timestamp + 'Z')`.
3. **Toast unified**: `react-hot-toast` removed, `AlarmForm.tsx` migrated to shadcn `useToast`.
4. **`any` types replaced** in `api.ts` with proper typed interfaces.

---

## Bug Fixes Summary

| # | Issue | Fix |
|---|---|---|
| 1 | Multi-worker alarm state bug (CRITICAL) | Single uvicorn process — no forks |
| 2 | Relative database path | Absolute path from config |
| 3 | `wecker.py` can miss alarms | Check last-2-minutes window |
| 4 | `network_reboot.py` next-alarm logic wrong | Shared `alarm_service.get_next_alarm()` |
| 5 | Hardcoded credentials in source | All secrets to `.env` / `.gitignore` |
| 6 | Timing-unsafe API key compare | `hmac.compare_digest()` |
| 7 | `local_only` trusts spoofable header | Use `CF-Connecting-IP` |
| 8 | API key in client bundle | Server-side proxy route |
| 9 | SQLite no WAL mode | WAL enabled in `base.py` |
| 10 | No schema migrations | Alembic |
| 11 | `print("DEBUG: ...")` in production | Removed |
| 12 | Two toast libraries | Unified to shadcn |
| 13 | Timezone hack (breaks with DST) | UTC storage + proper parse |
| 14 | Duplicated `get_next_alarm()` | Single shared implementation |
| 15 | Fragile manual JSON chunking | Proper cursor-level streaming |
| 16 | ESP32 no watchdog | `machine.WDT` added |

---

## Out of Scope

- ESP32 OTA / automated flashing — version-controlled only, manual flash via USB.
- Switching away from SQLite (appropriate for this load).
- Replacing Cloudflared tunnel setup.
- Changes to the Cloud Function (penalty deduction) — not owned by this repo.
