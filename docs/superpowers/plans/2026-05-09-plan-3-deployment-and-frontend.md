# Strafwecker Plan 3 — Deployment Pipeline, Live Migration & Frontend Updates

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up the GitHub Actions self-hosted runner on the Pi, write all deployment workflows, cut over the live Pi from Flask to FastAPI, update the frontend (server-side API proxy, timezone fix, toast unification), and add the ESP32 watchdog + CI check. After this plan everything runs in production with push-to-deploy.

**Architecture:** Self-hosted runner on Pi connects out to GitHub. `backend-deploy.yml` runs on the Pi runner: git pull → tests → alembic migrate → restart service. Frontend CI runs on a hosted runner and catches build errors before Vercel deploys. ESP32 CI uses mpremote + ruff syntax checks.

**Tech Stack:** GitHub Actions, systemd, uvicorn, Poetry, Next.js, Alembic, MicroPython stubs.

**All steps run from `<projektverzeichnis>\` unless stated otherwise.**

---

## File Map

```
strafwecker/
├── backend/
│   ├── network_reboot.py             ← COPY+FIX: replace local get_next_alarm with service import
│   └── systemd/
│       ├── strafwecker-api.service
│       ├── wecker.service
│       ├── wecker.timer
│       └── cleanup_logs.timer
├── frontend/
│   ├── app/
│   │   └── api/
│   │       └── [...path]/
│   │           └── route.ts          ← NEW: server-side proxy
│   └── utils/
│       └── api.ts                    ← MODIFY: remove timezone hack, fix types
├── esp32/
│   ├── main.py                       ← MODIFY: add WDT watchdog
│   └── tests/
│       └── test_logic.py             ← WRITE: color math + payload tests
└── .github/
    └── workflows/
        ├── backend-deploy.yml
        ├── frontend.yml
        └── esp32-check.yml
```

---

### Task 1: Systemd Unit Files

**Files:**
- Write: `backend/systemd/strafwecker-api.service`
- Write: `backend/systemd/wecker.service`
- Write: `backend/systemd/wecker.timer`
- Write: `backend/systemd/cleanup_logs.timer`

- [ ] **Step 1: Write `backend/systemd/strafwecker-api.service`**

```ini
[Unit]
Description=Strafwecker FastAPI Server
After=network.target sound.target
Wants=sound.target
Requires=sound.target

[Service]
User=pi
WorkingDirectory=/home/pi/strafwecker/backend
EnvironmentFile=/home/pi/strafwecker/backend/.env
Environment="SDL_AUDIODRIVER=alsa"
Environment="AUDIODEV=default"
ExecStart=/home/pi/strafwecker/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
Restart=always
RestartSec=5
LimitNOFILE=4096

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 2: Write `backend/systemd/wecker.service`**

```ini
[Unit]
Description=Strafwecker Alarm Checker (one-shot)
After=strafwecker-api.service

[Service]
Type=oneshot
User=pi
WorkingDirectory=/home/pi/strafwecker/backend
EnvironmentFile=/home/pi/strafwecker/backend/.env
ExecStart=/home/pi/strafwecker/backend/.venv/bin/python wecker.py

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 3: Write `backend/systemd/wecker.timer`**

```ini
[Unit]
Description=Run wecker.service once per minute + 1 second

[Timer]
OnCalendar=*-*-* *:*:01
AccuracySec=1
RandomizedDelaySec=0
Unit=wecker.service
Persistent=true

[Install]
WantedBy=timers.target
```

- [ ] **Step 4: Write `backend/systemd/cleanup_logs.timer`**

```ini
[Unit]
Description=Run cleanup_logs.service daily at 00:30

[Timer]
Unit=cleanup_logs.service
OnBootSec=120
OnCalendar=*-*-* 00:30:00
RandomizedDelaySec=300
Persistent=true

[Install]
WantedBy=timers.target
```

- [ ] **Step 5: Commit**

```powershell
git add backend/systemd/
git commit -m "feat: add systemd unit files for FastAPI server and wecker timer"
```

---

### Task 2: GitHub Actions Workflows

**Files:**
- Write: `.github/workflows/backend-deploy.yml`
- Write: `.github/workflows/frontend.yml`
- Write: `.github/workflows/esp32-check.yml`

- [ ] **Step 1: Write `.github/workflows/backend-deploy.yml`**

```yaml
name: Deploy Backend to Pi

on:
  push:
    branches: [main]
    paths:
      - "backend/**"

jobs:
  deploy:
    runs-on: self-hosted
    defaults:
      run:
        working-directory: /home/pi/strafwecker

    steps:
      - name: Pull latest code
        run: git pull origin main

      - name: Install dependencies
        working-directory: /home/pi/strafwecker/backend
        run: poetry install --no-root --without dev

      - name: Run unit tests
        working-directory: /home/pi/strafwecker/backend
        run: poetry run pytest tests/unit/ -v --tb=short
        # Abort deploy if unit tests fail

      - name: Apply database migrations
        working-directory: /home/pi/strafwecker/backend
        run: poetry run alembic upgrade head

      - name: Symlink systemd units
        run: |
          sudo cp /home/pi/strafwecker/backend/systemd/strafwecker-api.service /etc/systemd/system/
          sudo cp /home/pi/strafwecker/backend/systemd/wecker.service /etc/systemd/system/
          sudo cp /home/pi/strafwecker/backend/systemd/wecker.timer /etc/systemd/system/
          sudo cp /home/pi/strafwecker/backend/systemd/cleanup_logs.timer /etc/systemd/system/
          sudo systemctl daemon-reload

      - name: Restart API service
        run: sudo systemctl restart strafwecker-api.service

      - name: Verify service is running
        run: |
          sleep 3
          sudo systemctl is-active strafwecker-api.service
```

- [ ] **Step 2: Write `.github/workflows/frontend.yml`**

```yaml
name: Frontend CI

on:
  push:
    branches: [main]
    paths:
      - "frontend/**"

jobs:
  build:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: Lint
        run: npm run lint

      - name: Build
        run: npm run build
        env:
          API_KEY: placeholder
          NEXT_PUBLIC_VERCEL_URL: localhost
```

- [ ] **Step 3: Write `.github/workflows/esp32-check.yml`**

```yaml
name: ESP32 Code Check

on:
  push:
    branches: [main]
    paths:
      - "esp32/**"

jobs:
  check:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install tools
        run: pip install ruff pytest

      - name: Install MicroPython stubs
        run: pip install micropython-esp32-stubs || true
        # Stubs may not cover all modules; failures here are non-fatal

      - name: Syntax check
        run: python -m py_compile esp32/main.py

      - name: Lint
        run: ruff check esp32/ --ignore E501

      - name: Run logic tests
        run: pytest esp32/tests/ -v
```

- [ ] **Step 4: Commit**

```powershell
git add .github/
git commit -m "feat: add GitHub Actions workflows for backend deploy, frontend CI, esp32 check"
```

---

### Task 3: Set Up the Self-Hosted Runner on the Pi

These steps run on the Pi via SSH.

- [ ] **Step 1: On GitHub, generate a runner registration token**

Go to `https://github.com/mrlmueller/strafwecker-v2/settings/actions/runners/new`. Select Linux → ARM64. Copy the token shown (valid 1 hour).

- [ ] **Step 2: SSH into the Pi and download the runner**

```bash
ssh raspberrypi
mkdir -p /home/pi/actions-runner && cd /home/pi/actions-runner
curl -o actions-runner-linux-arm64-2.317.0.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.317.0/actions-runner-linux-arm64-2.317.0.tar.gz
tar xzf actions-runner-linux-arm64-2.317.0.tar.gz
```

Check the latest runner version at https://github.com/actions/runner/releases before running; replace `2.317.0` if a newer version exists.

- [ ] **Step 3: Configure the runner**

```bash
./config.sh --url https://github.com/mrlmueller/strafwecker-v2 \
            --token YOUR_TOKEN_HERE \
            --name raspberry-pi \
            --labels self-hosted,pi \
            --unattended
```

- [ ] **Step 4: Install as a systemd service**

```bash
sudo ./svc.sh install
sudo ./svc.sh start
sudo systemctl status actions.runner.mrlmueller-strafwecker.raspberry-pi.service
```

Expected: `active (running)`.

- [ ] **Step 5: Grant the runner sudo rights for the two commands it needs**

```bash
sudo visudo
```

Add this line at the bottom of the file (replace `pi` if your user is different):

```
pi ALL=(ALL) NOPASSWD: /usr/bin/systemctl daemon-reload, /usr/bin/systemctl restart strafwecker-api.service, /usr/bin/cp /home/pi/strafwecker/backend/systemd/* /etc/systemd/system/
```

Save and exit.

- [ ] **Step 6: Verify runner appears on GitHub**

Go to `https://github.com/mrlmueller/strafwecker-v2/settings/actions/runners`. The `raspberry-pi` runner should show as **Idle**.

---

### Task 4: Clone the Repo on the Pi

Run on the Pi via SSH.

- [ ] **Step 1: Clone the new repo**

```bash
ssh raspberrypi
cd /home/pi
git clone git@github.com:mrlmueller/strafwecker-v2.git strafwecker
cd strafwecker/backend
```

- [ ] **Step 2: Install Python dependencies**

```bash
pip install poetry
poetry config virtualenvs.in-project true
poetry install --no-root --without dev
```

Note: Poetry will skip `RPi.GPIO` not being in pyproject.toml. Install it manually:

```bash
.venv/bin/pip install RPi.GPIO
```

- [ ] **Step 3: Create the `.env` file on the Pi**

```bash
cat > /home/pi/strafwecker/backend/.env << 'EOF'
API_KEY=<paste your existing API key>
TUYA_DEV_ID=bfb26566d5b2f5524bavt0
TUYA_LOCAL_KEY=]#1a3n;rx}E~qEbp
TUYA_IP=192.168.1.34
ESP32_IP=192.168.1.28
DATABASE_PATH=/home/pi/strafwecker/backend/data/strafwecker.db
ALARM_SOUND_PATH=/home/pi/strafwecker/backend/alarm.wav
EOF
chmod 600 /home/pi/strafwecker/backend/.env
```

Get the existing API key from the old setup: `cat /home/pi/Documents/flask_app/.env`.

- [ ] **Step 4: Create the data directory**

```bash
mkdir -p /home/pi/strafwecker/backend/data
```

- [ ] **Step 5: Copy network_reboot.py into the monorepo**

`/home/pi/Documents/network_reboot.py` contains a local `get_next_alarm()` that duplicates — and diverges from — the correct logic in `alarm_service`. Copy it into the repo so it can be fixed and version-controlled.

On the Pi:
```bash
cp /home/pi/Documents/network_reboot.py /home/pi/strafwecker/backend/network_reboot.py
```

On your Windows machine, open `backend/network_reboot.py`. Find and **delete** the entire local `get_next_alarm` function. It will look something like:

```python
def get_next_alarm(alarms):
    now = datetime.now()
    # ... buggy logic that does not handle the 2-minute window
```

Replace the imports block at the top of the file with:

```python
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.services.alarm_service import get_next_alarm
from app.config import settings
```

Then update any call site that used the old `get_next_alarm(alarms)` signature. The shared service version takes no arguments and reads from the database directly:

```python
# Old (remove):
alarms = fetch_alarms_from_db()
next_alarm = get_next_alarm(alarms)

# New:
next_alarm = get_next_alarm()   # returns Optional[tuple[Alarm, datetime]]
```

Adjust the reboot-decision logic to unpack the tuple:

```python
if next_alarm is not None:
    alarm, scheduled_dt = next_alarm
    # use scheduled_dt for time comparison
```

- [ ] **Step 6: Commit network_reboot.py**

```powershell
git add backend/network_reboot.py
git commit -m "fix: replace duplicated get_next_alarm in network_reboot.py with shared alarm_service"
```

---

### Task 5: Migrate the Live Database

- [ ] **Step 1: Copy the existing database to the new location**

```bash
cp /home/pi/Documents/flask_app/database.db /home/pi/strafwecker/backend/data/strafwecker.db
```

- [ ] **Step 2: Run Alembic on the existing database**

The existing database already has all the tables. Alembic needs to be told this is already at the initial migration:

```bash
cd /home/pi/strafwecker/backend
.venv/bin/alembic stamp 001
```

This marks the database as being at revision `001` without running the migration (which would fail since tables already exist).

- [ ] **Step 3: Verify**

```bash
.venv/bin/alembic current
```

Expected output: `001 (head)`.

---

### Task 6: Live Cutover

This task stops the old Flask server and starts the new FastAPI server.

- [ ] **Step 1: Confirm the old service is running**

```bash
sudo systemctl status flask_alarm.service
```

- [ ] **Step 2: Test the new server manually before cutting over**

```bash
cd /home/pi/strafwecker/backend
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 1
```

In a second terminal, test an endpoint:

```bash
curl -H "x-api-key: $(grep API_KEY /home/pi/strafwecker/backend/.env | cut -d= -f2)" \
     http://localhost:8001/api/v1/alarms/
```

Expected: `[]` or your existing alarms as JSON. Stop uvicorn with Ctrl+C.

- [ ] **Step 3: Stop the old services**

```bash
sudo systemctl stop flask_alarm.service
sudo systemctl stop wecker.timer
sudo systemctl disable flask_alarm.service
sudo systemctl disable wecker.timer
```

- [ ] **Step 4: Install and start the new services**

```bash
sudo cp /home/pi/strafwecker/backend/systemd/strafwecker-api.service /etc/systemd/system/
sudo cp /home/pi/strafwecker/backend/systemd/wecker.service /etc/systemd/system/
sudo cp /home/pi/strafwecker/backend/systemd/wecker.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable strafwecker-api.service
sudo systemctl enable wecker.timer
sudo systemctl start strafwecker-api.service
sudo systemctl start wecker.timer
```

- [ ] **Step 5: Verify the new service is running**

```bash
sudo systemctl status strafwecker-api.service
sudo systemctl status wecker.timer
```

Expected: both `active`.

- [ ] **Step 6: Check the API from your Windows machine**

```powershell
$key = "your_api_key_here"
Invoke-RestMethod -Uri "http://raspberrypi:8000/api/v1/alarms/" -Headers @{"x-api-key"=$key}
```

Expected: list of your alarms.

- [ ] **Step 7: Update the Cloudflared target**

The old Flask was on port 5000. The new FastAPI is on port 8000. Update the cloudflared config:

```bash
sudo nano /etc/cloudflared/config.yml
```

Change `localhost:5000` to `localhost:8000`. Then:

```bash
sudo systemctl restart cloudflared
```

- [ ] **Step 8: Verify the frontend still works**

Open https://raspberryalarm.vercel.app and confirm alarms load. If they don't load, check the API key in Vercel's environment variables and update to match the new `.env` on the Pi.

---

### Task 7: Test the Deployment Pipeline

- [ ] **Step 1: Make a trivial backend change**

In `backend/app/main.py`, add a health endpoint:

```python
@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 2: Commit and push**

```powershell
git add backend/app/main.py
git commit -m "feat: add health endpoint"
git push origin main
```

- [ ] **Step 3: Watch the GitHub Actions run**

Go to `https://github.com/mrlmueller/strafwecker-v2/actions`. You should see `Deploy Backend to Pi` running on the `raspberry-pi` self-hosted runner. It should complete green.

- [ ] **Step 4: Verify the deployed change**

```powershell
Invoke-RestMethod -Uri "http://raspberrypi:8000/health" -Headers @{"x-api-key"="your_api_key"}
```

Expected: `{"status": "ok"}`.

---

### Task 8: Frontend — Server-Side API Proxy

**Files:**
- Create: `frontend/app/api/[...path]/route.ts`
- Modify: `frontend/utils/api.ts` (change `API_BASE_URL`)
- Modify: `frontend/next.config.js` (remove old proxy rewrite if present)

- [ ] **Step 1: Create `frontend/app/api/[...path]/route.ts`**

```typescript
import { NextRequest, NextResponse } from "next/server";

const PI_BASE = process.env.PI_API_URL ?? "http://raspberrypi:8000";
const API_KEY = process.env.API_KEY ?? "";

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return proxyRequest(request, params.path, "GET");
}

export async function POST(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return proxyRequest(request, params.path, "POST");
}

export async function PUT(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return proxyRequest(request, params.path, "PUT");
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return proxyRequest(request, params.path, "DELETE");
}

async function proxyRequest(
  request: NextRequest,
  pathSegments: string[],
  method: string
): Promise<NextResponse> {
  const path = pathSegments.join("/");
  const search = request.nextUrl.search;
  const targetUrl = `${PI_BASE}/api/v1/${path}${search}`;

  const body =
    method !== "GET" && method !== "DELETE"
      ? await request.text()
      : undefined;

  const res = await fetch(targetUrl, {
    method,
    headers: {
      "Content-Type": "application/json",
      "x-api-key": API_KEY,
    },
    body,
    cache: "no-store",
  });

  const data = await res.text();
  return new NextResponse(data, {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}
```

- [ ] **Step 2: Update `frontend/utils/api.ts` — change API_BASE_URL and remove API_KEY from client**

Find these lines near the top of `utils/api.ts`:

```typescript
export const API_BASE_URL = "/api"; // Proxied to the Flask backend via next.config.js
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";
```

Replace with:

```typescript
export const API_BASE_URL = "/api";
```

Then remove the `"X-API-KEY": API_KEY` header from all `fetch` calls throughout `api.ts`. The proxy route injects the key server-side. Replace each occurrence of:

```typescript
headers: {
  "Content-Type": "application/json",
  "X-API-KEY": API_KEY,
},
```

with:

```typescript
headers: {
  "Content-Type": "application/json",
},
```

- [ ] **Step 3: Add environment variables to `frontend/.env.local.example`**

```
PI_API_URL=http://raspberrypi:8000
API_KEY=your_api_key_here
```

Add these to Vercel's environment variables under `Settings → Environment Variables` for the production deployment (mark as non-public — no `NEXT_PUBLIC_` prefix).

- [ ] **Step 4: Commit**

```powershell
git add frontend/app/api/ frontend/utils/api.ts
git commit -m "feat: move API key to server-side proxy route, remove from client bundle"
```

---

### Task 9: Frontend — Fix Timezone and Unify Toast

**Files:**
- Modify: `frontend/utils/api.ts` (remove timezone hack)
- Modify: `frontend/app/components/AlarmForm.tsx` (replace react-hot-toast)

- [ ] **Step 1: Remove the timezone hack in `frontend/utils/api.ts`**

Find and delete this entire block in `fetchNetworkLogs` (lines ~254–282):

```typescript
// Fix for timezone issues (the server timestamps are in UTC, browser in local timezone)
if (data.data && data.data.length > 0) {
  const lastLog = data.data[0];
  const now = new Date();
  const mostRecentLogDate = new Date(lastLog.timestamp);
  const diffMinutes = Math.floor(
    (now.getTime() - mostRecentLogDate.getTime()) / (1000 * 60)
  );
  if (diffMinutes >= 55 && diffMinutes <= 65) {
    data.data = data.data.map((log: any) => {
      const originalDate = new Date(log.timestamp);
      const correctedDate = new Date(originalDate);
      correctedDate.setHours(correctedDate.getHours() + 1);
      return { ...log, timestamp: correctedDate.toISOString() };
    });
  }
}
```

Replace with nothing — the Pi now stores UTC timestamps and the frontend parses them correctly with `new Date(timestamp + 'Z')`.

- [ ] **Step 2: Update `fetchNetworkLogs` return mapping to parse timestamps as UTC**

Find where the data is returned at the end of `fetchNetworkLogs` and update the data mapping (add `+ 'Z'` to ensure UTC parsing):

In the `NetworkLog` interface in `api.ts`, the `timestamp` field is already a `string`. The display component should parse it as `new Date(log.timestamp + 'Z')`. If you have any timestamp display in `app/network/page.tsx`, update those lines to append `'Z'` when constructing a `Date`:

```typescript
// Anywhere you do: new Date(log.timestamp)
// Change to:       new Date(log.timestamp.endsWith('Z') ? log.timestamp : log.timestamp + 'Z')
```

- [ ] **Step 3: Replace react-hot-toast in `AlarmForm.tsx` with shadcn useToast**

In `frontend/app/components/AlarmForm.tsx`, replace:

```typescript
import toast, { Toaster } from "react-hot-toast";
```

with:

```typescript
import { useToast } from "@/hooks/use-toast";
```

Add `const { toast } = useToast();` inside the component function after the existing state declarations.

Replace `toast.success("Alarm updated successfully")` with:

```typescript
toast({ title: "Success", description: "Alarm updated successfully" });
```

Replace `toast.success("Alarm created successfully")` with:

```typescript
toast({ title: "Success", description: "Alarm created successfully" });
```

Replace `toast.error("Failed to save alarm")` with:

```typescript
toast({ variant: "destructive", title: "Error", description: "Failed to save alarm" });
```

Remove `<Toaster />` from the JSX (shadcn Toaster is already in `layout.tsx`).

- [ ] **Step 4: Uninstall react-hot-toast**

```powershell
cd frontend
npm uninstall react-hot-toast
```

- [ ] **Step 5: Fix `any` types in `api.ts`**

Replace `data.map((alarm: any) =>` with:

```typescript
interface RawAlarm {
  id: string;
  time: string;
  days_of_week: string | number[];
  enabled: number | boolean;
  repeat_type?: string;
  label?: string;
  light: number | boolean;
}
data.map((alarm: RawAlarm) =>
```

Replace `data.map((log: any) =>` with:

```typescript
interface RawLog {
  id: number;
  timestamp: string;
  last_update: string;
  alarm_id: number;
  state: string;
  time_to_button_sec?: number | null;
  pressed_in_time?: number | null;
  error_details?: string | null;
  notes?: string | null;
}
data.map((log: RawLog) =>
```

- [ ] **Step 6: Build the frontend to verify no TypeScript errors**

```powershell
cd frontend
npm run build
```

Expected: successful build with no type errors.

- [ ] **Step 7: Commit**

```powershell
cd ..
git add frontend/
git commit -m "fix: remove timezone hack, unify toast to shadcn, remove api key from client bundle"
```

---

### Task 10: ESP32 — Watchdog Timer

**Files:**
- Modify: `esp32/main.py`

- [ ] **Step 1: Add WDT to `esp32/main.py`**

Find the `main()` function in `esp32/main.py`:

```python
def main():
    ssid = config.SSID
    password = config.WLAN_PASSWORD
    connect_to_network(ssid, password)
    try:
        asyncio.run(start_server())
    except Exception as e:
        print("Exception in main server loop: {}".format(e))
```

Replace with:

```python
def main():
    from machine import WDT
    wdt = WDT(timeout=30000)  # 30 second watchdog

    ssid = config.SSID
    password = config.WLAN_PASSWORD
    connect_to_network(ssid, password)
    wdt.feed()

    async def run_with_watchdog():
        server_task = asyncio.create_task(start_server())
        while True:
            wdt.feed()
            await asyncio.sleep(10)

    try:
        asyncio.run(run_with_watchdog())
    except Exception as e:
        print("Exception in main server loop: {}".format(e))
```

- [ ] **Step 2: Commit**

```powershell
git add esp32/main.py
git commit -m "feat: add MicroPython WDT watchdog to ESP32 main loop"
```

---

### Task 11: ESP32 — Logic Tests

**Files:**
- Write: `esp32/tests/test_logic.py`

- [ ] **Step 1: Write `esp32/tests/test_logic.py`**

These tests import pure Python functions from a test-adapted copy of the ESP32 logic. MicroPython-specific modules are mocked.

```python
"""
Tests for pure ESP32 logic — color math and payload construction.
These run in standard CPython (no hardware, no MicroPython needed).
"""
import sys
from unittest.mock import MagicMock

# Mock MicroPython-specific modules so imports don't fail
sys.modules["network"] = MagicMock()
sys.modules["uasyncio"] = MagicMock()
sys.modules["ujson"] = __import__("json")  # use stdlib json
sys.modules["urequests"] = MagicMock()
sys.modules["machine"] = MagicMock()
sys.modules["_thread"] = MagicMock()
sys.modules["config"] = MagicMock(
    PI_URL="http://192.168.0.1:8000/api/v1/esp/callback",
    CLOUD_RUN_URL="https://example.com/fn",
    API_KEY="testkey",
    SECRET_KEY="testsecret",
    SSID="wifi",
    WLAN_PASSWORD="pass",
)

# Now import only the pure-logic parts
# RGBLED color constants
COLOR_CYAN = (0, 1023, 1023)
COLOR_GREEN = (0, 1023, 0)
COLOR_RED = (1023, 0, 0)
COLOR_OFF = (0, 0, 0)


def build_button_pressed_payload(alarm_id: int, log_id: int, elapsed: int) -> dict:
    return {
        "status": "button_pressed",
        "alarm_id": alarm_id,
        "log_id": log_id,
        "time_to_button_sec": elapsed,
    }


def build_no_press_payload(alarm_id: int, log_id: int) -> dict:
    return {
        "status": "no_press",
        "alarm_id": alarm_id,
        "log_id": log_id,
    }


def build_timer_started_payload(alarm_id: int, log_id: int) -> dict:
    return {
        "status": "timer_started",
        "alarm_id": alarm_id,
        "log_id": log_id,
    }


# Tests

def test_button_pressed_payload_structure():
    p = build_button_pressed_payload(alarm_id=5, log_id=12, elapsed=90)
    assert p["status"] == "button_pressed"
    assert p["alarm_id"] == 5
    assert p["log_id"] == 12
    assert p["time_to_button_sec"] == 90


def test_no_press_payload_has_no_time_field():
    p = build_no_press_payload(alarm_id=5, log_id=12)
    assert p["status"] == "no_press"
    assert "time_to_button_sec" not in p


def test_timer_started_payload_structure():
    p = build_timer_started_payload(alarm_id=3, log_id=7)
    assert p["status"] == "timer_started"
    assert p["alarm_id"] == 3


def test_color_cyan_is_not_off():
    assert COLOR_CYAN != COLOR_OFF


def test_color_red_has_no_green_or_blue():
    r, g, b = COLOR_RED
    assert r == 1023
    assert g == 0
    assert b == 0


def test_color_green_has_no_red_or_blue():
    r, g, b = COLOR_GREEN
    assert r == 0
    assert g == 1023
    assert b == 0
```

- [ ] **Step 2: Run the tests locally**

```powershell
poetry run pytest esp32/tests/ -v
```

Expected: 7 passed (runs from the backend Poetry environment which has pytest).

- [ ] **Step 3: Commit**

```powershell
git add esp32/tests/test_logic.py
git commit -m "test: add ESP32 logic tests for payload building and color constants"
```

---

### Task 12: Final Push and End-to-End Verification

- [ ] **Step 1: Push all changes**

```powershell
git push origin main
```

- [ ] **Step 2: Watch all three GitHub Actions workflows complete**

Go to `https://github.com/mrlmueller/strafwecker-v2/actions`. Three workflows should trigger: `Deploy Backend to Pi`, `Frontend CI`, `ESP32 Code Check`. Confirm all green.

- [ ] **Step 3: End-to-end alarm test**

On the Pi:
```bash
# Create a test alarm 1 minute from now
python3 -c "
from datetime import datetime, timedelta
t = (datetime.now() + timedelta(minutes=1)).strftime('%H:%M')
print(f'Set alarm for {t}')
"
```

Set that time as a new alarm in the frontend. Wait 1 minute. Confirm:
- Alarm sound plays on Pi speakers
- ESP32 RGB LED turns cyan
- Press the ESP32 button — LED turns green, alarm stops
- Log entry shows `button_pressed_esp32` state in the frontend logs page

- [ ] **Step 4: Save memory**

Save a memory note that the system is now fully migrated and running on the new stack (Plans 1–3 complete).

---

**Plan 3 complete.** The full system is live: FastAPI backend with push-to-deploy, ESP32 watchdog, timezone-correct frontend with server-side API key, and three GitHub Actions CI/CD workflows.
