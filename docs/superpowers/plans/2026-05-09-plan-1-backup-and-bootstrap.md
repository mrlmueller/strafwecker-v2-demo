# Strafwecker Plan 1 — Pre-Migration Backup & Monorepo Bootstrap

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Take a full backup of the Raspberry Pi, create the new `strafwecker` GitHub monorepo, and scaffold all directories with existing code moved into place — ready for the backend rewrite in Plan 2.

**Architecture:** Fresh GitHub repo with `frontend/`, `backend/`, and `esp32/` directories. No code is written yet; this plan only moves existing code and creates the project skeleton. The old Pi setup remains untouched until Plan 3.

**Tech Stack:** Git, GitHub CLI (`gh`), Poetry (Python), PowerShell / WSL for backup commands.

---

## File Map

```
strafwecker/                        ← new repo (cloned fresh from GitHub)
├── frontend/                       ← copy of current <projektverzeichnis> (src files only)
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 ← empty stub
│   │   ├── config.py               ← empty stub
│   │   ├── dependencies.py         ← empty stub
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── middleware.py       ← empty stub
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py       ← empty stub
│   │   │       ├── alarms.py       ← empty stub
│   │   │       ├── logs.py         ← empty stub
│   │   │       ├── esp.py          ← empty stub
│   │   │       ├── light.py        ← empty stub
│   │   │       └── network.py      ← empty stub
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── alarm.py            ← empty stub
│   │   │   ├── log.py              ← empty stub
│   │   │   ├── esp.py              ← empty stub
│   │   │   └── light.py            ← empty stub
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── alarm_service.py    ← empty stub
│   │   │   ├── esp_service.py      ← empty stub
│   │   │   ├── light_service.py    ← empty stub
│   │   │   ├── player_service.py   ← empty stub
│   │   │   └── log_service.py      ← empty stub
│   │   └── repositories/
│   │       ├── __init__.py
│   │       ├── base.py             ← empty stub
│   │       ├── alarm_repository.py ← empty stub
│   │       ├── log_repository.py   ← empty stub
│   │       └── network_repository.py ← empty stub
│   ├── migrations/
│   │   └── versions/               ← empty, Alembic fills this in Plan 2
│   ├── systemd/                    ← empty, filled in Plan 3
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py             ← empty stub
│   │   ├── unit/
│   │   │   └── __init__.py
│   │   └── integration/
│   │       └── __init__.py
│   ├── alarm.wav                   ← copied from Pi
│   ├── pyproject.toml
│   ├── alembic.ini                 ← empty stub (Alembic fills in Plan 2)
│   └── .env.example
├── esp32/
│   ├── main.py                     ← copied from Pi + watchdog stub added
│   ├── config.py.example
│   └── tests/
│       ├── __init__.py
│       └── test_logic.py           ← empty stub
├── .github/
│   └── workflows/                  ← empty, filled in Plan 3
├── .gitignore
└── README.md
```

---

### Task 1: Back Up the Pi

**Files:** None — backup files stay local, never committed.

- [ ] **Step 1: Take the SD card image (run from WSL or Git Bash — NOT PowerShell)**

```bash
ssh raspberrypi "sudo dd if=/dev/mmcblk0 bs=4M status=progress | gzip" > ~/pi-backup-20260509.img.gz
```

This streams a compressed image of the full SD card to your Windows home directory via WSL. Takes 10–20 minutes. File will be ~4–8 GB compressed. If anything goes wrong later, flash this back with Raspberry Pi Imager and you're fully restored.

- [ ] **Step 2: Dump the database**

```bash
ssh raspberrypi "sqlite3 /home/pi/Documents/flask_app/database.db '.dump'" > ~/pi-db-backup-20260509.sql
```

- [ ] **Step 3: Verify the image exists and is non-zero**

```bash
ls -lh ~/pi-backup-20260509.img.gz
ls -lh ~/pi-db-backup-20260509.sql
```

Expected: both files exist, image is several GB, SQL dump is tens of MB.

- [ ] **Step 4: Copy alarm.wav from Pi to your Windows machine (for use in Plan 2)**

```bash
scp raspberrypi:/home/pi/Documents/flask_app/alarm.wav ~/alarm.wav
```

---

### Task 2: Create the GitHub Repository

**Files:** None — manual GitHub step.

- [ ] **Step 1: Create the repo on GitHub using the gh CLI**

```powershell
gh repo create mrlmueller/strafwecker-v2 --private --description "Strafwecker monorepo: FastAPI backend, Next.js frontend, ESP32 firmware"
```

- [ ] **Step 2: Initialize the local folder as a git repo**

The folder `<projektverzeichnis>` already exists as an empty directory. Initialize git in it and link to the new remote:

```powershell
cd <projektverzeichnis>
git init
git branch -M main
git remote add origin git@github.com:mrlmueller/strafwecker-v2.git
```

All subsequent Plan 1 steps run from `<projektverzeichnis>`.

---

### Task 3: Root-Level Files

**Files:**
- Create: `.gitignore`
- Create: `README.md`

- [ ] **Step 1: Write `.gitignore`**

```
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.egg-info/
dist/
build/
.venv/
venv/

# Environment & secrets
.env
backend/.env
esp32/config.py

# Database
*.db
*.db-shm
*.db-wal

# Logs
*.log

# Node / Next.js
frontend/node_modules/
frontend/.next/
frontend/.env.local

# Pi backup files
*.img.gz
*.sql

# OS
.DS_Store
Thumbs.db
```

- [ ] **Step 2: Write `README.md`**

```markdown
# Strafwecker

Alarm system: Raspberry Pi (FastAPI backend, audio, Tuya light) + ESP32 (button press countdown).

## Structure

- `frontend/` — Next.js app (deployed on Vercel)
- `backend/` — FastAPI 3-layer backend (runs on Raspberry Pi)
- `esp32/` — MicroPython firmware (flashed manually via USB)

## Setup

See `docs/superpowers/specs/2026-05-09-strafwecker-overhaul-design.md` for full architecture.
```

- [ ] **Step 3: Commit**

```powershell
git add .gitignore README.md
git commit -m "chore: initialize monorepo with gitignore and readme"
```

---

### Task 4: Copy the Frontend

**Files:** All `frontend/**` files copied from the old repo.

- [ ] **Step 1: Create the frontend directory and copy all source files**

Run from `<projektverzeichnis>` in PowerShell:

```powershell
New-Item -ItemType Directory -Path frontend
$src = "<projektverzeichnis>"
$dst = "<projektverzeichnis>\frontend"

# Copy source files (exclude node_modules, .next, .git, docs)
$exclude = @("node_modules", ".next", ".git", "docs")
Get-ChildItem -Path $src | Where-Object { $_.Name -notin $exclude } | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination $dst -Recurse -Force
}
```

- [ ] **Step 2: Verify the copy**

```powershell
Get-ChildItem frontend/app
```

Expected output: `components`, `logs`, `network`, `globals.css`, `layout.tsx`, `page.tsx`.

- [ ] **Step 3: Create `frontend/.env.local.example`**

```
# Copy this to .env.local and fill in values
API_KEY=your_api_key_here
```

This replaces `NEXT_PUBLIC_API_KEY`. The real `.env.local` is never committed (already in .gitignore).

- [ ] **Step 4: Commit**

```powershell
git add frontend/
git commit -m "chore: move Next.js frontend into frontend/ subdirectory"
```

---

### Task 5: Set Up the ESP32 Directory

**Files:**
- Create: `esp32/main.py` (from Pi)
- Create: `esp32/config.py.example`
- Create: `esp32/tests/__init__.py`
- Create: `esp32/tests/test_logic.py`

- [ ] **Step 1: Copy ESP32 files from Pi**

```powershell
New-Item -ItemType Directory -Path esp32/tests -Force
```

```bash
# Run from WSL/Git Bash
scp raspberrypi:/home/pi/Documents/ESP32/main.py <projektverzeichnis>/esp32/main.py
```

- [ ] **Step 2: Create `esp32/config.py.example`**

```python
# Copy this to config.py and fill in real values.
# config.py is in .gitignore and must never be committed.
PI_URL = "http://192.168.x.x:8000/api/v1/esp/callback"
CLOUD_RUN_URL = "https://us-central1-your-project.cloudfunctions.net/send_money"
API_KEY = "your_api_key_here"
SECRET_KEY = "your_secret_key_here"
SSID = "your_wifi_ssid"
WLAN_PASSWORD = "your_wifi_password"
```

- [ ] **Step 3: Create `esp32/tests/__init__.py`** (empty file)

- [ ] **Step 4: Create `esp32/tests/test_logic.py`** (empty stub)

```python
# Tests for pure ESP32 logic (color math, payload building).
# These run in CI using standard CPython — no MicroPython or hardware needed.
```

- [ ] **Step 5: Commit**

```powershell
git add esp32/
git commit -m "chore: add ESP32 firmware and test scaffold"
```

---

### Task 6: Scaffold the Backend Python Project

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/alarm.wav` (copied from Pi)
- Create: all `__init__.py` stubs
- Create: all empty `.py` stubs

- [ ] **Step 1: Copy alarm.wav**

```powershell
New-Item -ItemType Directory -Path backend -Force
Copy-Item "$env:USERPROFILE\alarm.wav" backend\alarm.wav
```

- [ ] **Step 2: Create `backend/pyproject.toml`**

```toml
[tool.poetry]
name = "strafwecker-backend"
version = "0.1.0"
description = "Strafwecker alarm system backend"
authors = ["mrlmueller"]
python = "^3.11"

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.111"
uvicorn = {extras = ["standard"], version = "^0.29"}
pydantic-settings = "^2.2"
python-dotenv = "^1.0"
orjson = "^3.10"
requests = "^2.31"
tinytuya = "^1.15"
alembic = "^1.13"
pygame = "^2.5"

[tool.poetry.group.dev.dependencies]
pytest = "^8.2"
pytest-asyncio = "^0.23"
httpx = "^0.27"
ruff = "^0.4"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
```

Note: `RPi.GPIO` is NOT listed here because it cannot install on Windows. It is installed manually on the Pi during setup. The code handles its absence with a try/except.

- [ ] **Step 3: Create `backend/.env.example`**

```
API_KEY=change_me
TUYA_DEV_ID=change_me
TUYA_LOCAL_KEY=change_me
TUYA_IP=192.168.x.x
ESP32_IP=192.168.x.x
DATABASE_PATH=/home/pi/strafwecker/backend/data/strafwecker.db
ALARM_SOUND_PATH=/home/pi/strafwecker/backend/alarm.wav
```

- [ ] **Step 4: Create all empty stub files**

Run this PowerShell script from `backend/`:

```powershell
$dirs = @(
    "app", "app/api", "app/api/v1",
    "app/schemas", "app/services", "app/repositories",
    "migrations/versions", "systemd", "tests/unit", "tests/integration"
)
foreach ($d in $dirs) {
    New-Item -ItemType Directory -Path $d -Force | Out-Null
}

$stubs = @(
    "app/__init__.py", "app/main.py", "app/config.py", "app/dependencies.py",
    "app/api/__init__.py", "app/api/middleware.py",
    "app/api/v1/__init__.py", "app/api/v1/router.py",
    "app/api/v1/alarms.py", "app/api/v1/logs.py",
    "app/api/v1/esp.py", "app/api/v1/light.py", "app/api/v1/network.py",
    "app/schemas/__init__.py", "app/schemas/alarm.py",
    "app/schemas/log.py", "app/schemas/esp.py", "app/schemas/light.py",
    "app/services/__init__.py", "app/services/alarm_service.py",
    "app/services/esp_service.py", "app/services/light_service.py",
    "app/services/player_service.py", "app/services/log_service.py",
    "app/repositories/__init__.py", "app/repositories/base.py",
    "app/repositories/alarm_repository.py", "app/repositories/log_repository.py",
    "app/repositories/network_repository.py",
    "tests/__init__.py", "tests/conftest.py",
    "tests/unit/__init__.py", "tests/integration/__init__.py",
    "wecker.py", "alembic.ini"
)
foreach ($f in $stubs) {
    if (-not (Test-Path $f)) { New-Item -ItemType File -Path $f -Force | Out-Null }
}
```

- [ ] **Step 5: Commit**

```powershell
cd <projektverzeichnis>
git add backend/
git commit -m "chore: scaffold backend Python project with Poetry and empty stubs"
```

---

### Task 7: Copy Docs and Push

**Files:**
- Create: `docs/superpowers/specs/` (copy from old repo)
- Create: `docs/superpowers/plans/` (copy from old repo)

- [ ] **Step 1: Copy the docs directory**

```powershell
New-Item -ItemType Directory -Path docs/superpowers/specs -Force
New-Item -ItemType Directory -Path docs/superpowers/plans -Force
Copy-Item "<projektverzeichnis>\docs\superpowers\specs\*" docs\superpowers\specs\ -Recurse
Copy-Item "<projektverzeichnis>\docs\superpowers\plans\*" docs\superpowers\plans\ -Recurse
```

- [ ] **Step 2: Create `.github/workflows/` directory (empty placeholder)**

```powershell
New-Item -ItemType Directory -Path .github/workflows -Force
New-Item -ItemType File -Path .github/workflows/.gitkeep -Force
```

- [ ] **Step 3: Final commit and push**

```powershell
git add docs/ .github/
git commit -m "chore: add specs, plans, and github workflows placeholder"
git push -u origin main
```

- [ ] **Step 4: Verify on GitHub**

Open `https://github.com/mrlmueller/strafwecker` in a browser. Confirm you see `frontend/`, `backend/`, `esp32/`, `docs/` directories and no secrets in any committed file.

---

**Plan 1 complete.** The new monorepo exists on GitHub with all code organized. The Pi is still running the old Flask server untouched. Proceed to Plan 2 (Backend Rewrite).
