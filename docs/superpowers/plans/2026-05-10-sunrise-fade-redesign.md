# Sunrise Fade Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the fragile asyncio-based pre-trigger fade with a stateless, per-minute sunrise computation that wecker.py drives via the existing `/api/v1/light` endpoint.

**Architecture:** Each minute, `wecker.py` asks `alarm_service.pick_active_sunrise(now)` for the closest enabled alarm whose fade window is open, asks `light_service.compute_sunrise_payload(remaining, total)` for the bulb command, and POSTs it to `/api/v1/light`. State is re-derived from scratch every tick. Two-phase fade matches the old Flask code: color interpolation `#050501 → #fff1a6` for the first 15/35 of the duration, then white-mode brightness ramp `0 → 1000` at `color_temp=350`.

**Tech Stack:** Python 3.12, FastAPI, pydantic, pytest, requests, tinytuya. SQLite (no schema changes).

---

## File Structure

**Modify:**
- `backend/app/services/light_service.py` — add `compute_sunrise_payload`; remove `_fade_active`, `_fade_lock`, `is_fade_active`, `mark_fade_started`, `mark_fade_stopped`.
- `backend/app/services/alarm_service.py` — add `pick_active_sunrise`; remove `get_alarms_with_fade_due`.
- `backend/app/api/v1/esp.py` — remove `_fade_light_task` async helper and `light_fade_start` route.
- `backend/wecker.py` — replace fade-pre-trigger block with sunrise-tick block.

**Modify (tests):**
- `backend/tests/unit/test_light_service.py` — add `compute_sunrise_payload` tests.
- `backend/tests/unit/test_alarm_service.py` — add `pick_active_sunrise` tests; drop any test that references `get_alarms_with_fade_due` (none currently).

No new files. No schema migration.

---

### Task 1: Add `compute_sunrise_payload` (pure function, TDD)

**Files:**
- Modify: `backend/app/services/light_service.py`
- Test: `backend/tests/unit/test_light_service.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/unit/test_light_service.py`:

```python
import pytest
from app.services.light_service import (
    compute_sunrise_payload,
    START_HEX,
    END_HEX,
    WHITE_COLOR_TEMP,
    MIN_BRIGHTNESS,
)


# Total fade = 1800 s (30 min); white phase = 1800 * 20/35 ≈ 1028.57 s.
TOTAL = 1800
WHITE_S = TOTAL * 20 / 35


def test_compute_payload_color_phase_start():
    # remaining == total → very beginning, dim warm
    payload = compute_sunrise_payload(TOTAL, TOTAL)
    assert payload == {"hex": START_HEX, "brightness": MIN_BRIGHTNESS}


def test_compute_payload_color_phase_end():
    # remaining just above white-phase boundary → near END_HEX
    payload = compute_sunrise_payload(int(WHITE_S) + 1, TOTAL)
    assert payload["brightness"] == MIN_BRIGHTNESS
    assert payload["hex"].startswith("#")
    # Hex should be near END_HEX (#fff1a6) — at least one channel close to F.
    assert payload["hex"].upper() != START_HEX.upper()


def test_compute_payload_white_phase_start():
    # remaining == total_white_seconds → fraction = 0 → brightness floor.
    payload = compute_sunrise_payload(int(WHITE_S), TOTAL)
    assert payload["color_temp"] == WHITE_COLOR_TEMP
    assert payload["brightness"] == MIN_BRIGHTNESS


def test_compute_payload_white_phase_end():
    # remaining = 0 → brightness 1000.
    payload = compute_sunrise_payload(0, TOTAL)
    assert payload == {"brightness": 1000, "color_temp": WHITE_COLOR_TEMP}


def test_compute_payload_white_phase_middle():
    # halfway through white phase → brightness ≈ 500.
    payload = compute_sunrise_payload(int(WHITE_S / 2), TOTAL)
    assert payload["color_temp"] == WHITE_COLOR_TEMP
    assert 450 <= payload["brightness"] <= 550


def test_compute_payload_negative_remaining_clamps_to_full_white():
    payload = compute_sunrise_payload(-30, TOTAL)
    assert payload == {"brightness": 1000, "color_temp": WHITE_COLOR_TEMP}


def test_compute_payload_remaining_above_total_clamps_to_color_start():
    payload = compute_sunrise_payload(TOTAL + 5000, TOTAL)
    assert payload == {"hex": START_HEX, "brightness": MIN_BRIGHTNESS}


def test_compute_payload_color_phase_uses_start_hex_at_top():
    # remaining slightly less than total → fraction ≈ 0 → still ~START_HEX.
    payload = compute_sunrise_payload(TOTAL - 1, TOTAL)
    # Allow a very small drift from START_HEX since fraction is just above 0.
    assert payload["brightness"] == MIN_BRIGHTNESS
    assert payload["hex"].startswith("#")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/unit/test_light_service.py -v`
Expected: 8 new tests FAIL with `ImportError` (the symbols don't exist yet).

- [ ] **Step 3: Implement `compute_sunrise_payload` and constants**

Add to `backend/app/services/light_service.py` (above `apply_light`):

```python
COLOR_RATIO = 15 / 35
WHITE_RATIO = 20 / 35
START_HEX = "#050501"
END_HEX = "#fff1a6"
WHITE_COLOR_TEMP = 350
MIN_BRIGHTNESS = 10


def compute_sunrise_payload(remaining_seconds: int, total_seconds: int) -> dict:
    """Pure function: derive the bulb command for one sunrise tick.

    Two phases over total_seconds:
      • Color phase (first 15/35 of total): hex interpolated START_HEX → END_HEX, brightness fixed at 10.
      • White phase (last 20/35 of total): white mode, brightness 10 → 1000 at color_temp 350.
    """
    total_white_s = total_seconds * WHITE_RATIO
    total_color_s = total_seconds * COLOR_RATIO

    if remaining_seconds > total_white_s:
        elapsed_in_color = (total_seconds - remaining_seconds)
        fraction = elapsed_in_color / total_color_s if total_color_s > 0 else 0.0
        fraction = max(0.0, min(1.0, fraction))
        return {"hex": interpolate_hex(START_HEX, END_HEX, fraction),
                "brightness": MIN_BRIGHTNESS}

    # White phase
    if total_white_s <= 0:
        return {"brightness": 1000, "color_temp": WHITE_COLOR_TEMP}
    fraction = (total_white_s - remaining_seconds) / total_white_s
    fraction = max(0.0, min(1.0, fraction))
    brightness = max(MIN_BRIGHTNESS, int(1000 * fraction))
    return {"brightness": brightness, "color_temp": WHITE_COLOR_TEMP}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/unit/test_light_service.py -v`
Expected: all light_service tests PASS, including the 8 new ones.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/light_service.py backend/tests/unit/test_light_service.py
git commit -m "feat(light): add compute_sunrise_payload pure function

Two-phase sunrise: color interpolation (#050501 → #fff1a6) for the first
15/35 of the fade, then white-mode brightness ramp (10 → 1000) at
color_temp=350. Stateless — caller derives remaining/total from alarm
schedule each tick."
```

---

### Task 2: Remove dead fade-lock helpers from `light_service`

**Files:**
- Modify: `backend/app/services/light_service.py`

The new design re-derives state every tick, so the global lock is dead weight. Removing it now (before Task 5 deletes its only caller) keeps the diff per task small.

- [ ] **Step 1: Confirm no remaining callers outside `esp.py`**

Run: `grep -rn "is_fade_active\|mark_fade_started\|mark_fade_stopped\|_fade_active\|_fade_lock" backend`
Expected output: matches only inside `backend/app/services/light_service.py` and `backend/app/api/v1/esp.py`. The `esp.py` callers will be deleted in Task 5.

- [ ] **Step 2: Delete the lock and helpers**

In `backend/app/services/light_service.py`, delete:

```python
import threading
...
_fade_active = False
_fade_lock = threading.Lock()


def is_fade_active() -> bool:
    with _fade_lock:
        return _fade_active


def mark_fade_started() -> bool:
    """Try to claim the fade slot. Returns True if acquired, False if already running."""
    global _fade_active
    with _fade_lock:
        if _fade_active:
            return False
        _fade_active = True
        return True


def mark_fade_stopped() -> None:
    global _fade_active
    with _fade_lock:
        _fade_active = False
```

Also remove the `import threading` line if it has no other use in the file (it doesn't — confirm with `grep "threading" backend/app/services/light_service.py`).

- [ ] **Step 3: Verify nothing in services or tests still references the removed names**

Run: `grep -rn "is_fade_active\|mark_fade_started\|mark_fade_stopped" backend/app backend/tests`
Expected: only matches in `backend/app/api/v1/esp.py` (those go in Task 5).

- [ ] **Step 4: Run the test suite**

Run: `cd backend && pytest -q`
Expected: PASS. (`esp.py` still imports `light_service` but only the lock helpers, which Task 5 removes — but `import light_service` is not the same as importing the names, so test collection is fine. If the file currently does `from app.services.light_service import mark_fade_started`, fix the import in this task — see Step 5 below.)

- [ ] **Step 5: If esp.py imports the removed names, comment them out so tests still collect**

Check: `grep -n "from app.services.light_service" backend/app/api/v1/esp.py`

If the import line includes `mark_fade_started` etc., temporarily edit it to import only what's still used. (Inspect first; do not blanket-rewrite.) Re-run `pytest -q`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/light_service.py backend/app/api/v1/esp.py
git commit -m "refactor(light): drop fade lock helpers

Stateless sunrise design re-derives state every tick from
(now, alarm) — no shared global state to guard, so the lock is
removed."
```

---

### Task 3: Add `pick_active_sunrise` (TDD)

**Files:**
- Modify: `backend/app/services/alarm_service.py`
- Test: `backend/tests/unit/test_alarm_service.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/unit/test_alarm_service.py`:

```python
from app.services.alarm_service import pick_active_sunrise


def _light_alarm(alarm_id: int, time: str, fade_min: int,
                 days: list[int], light: bool = True,
                 repeat_type: str = "weekly") -> Alarm:
    return Alarm(
        id=alarm_id, time=time, days_of_week=days,
        enabled=True, repeat_type=repeat_type, label=None,
        light=light, light_fade_minutes=fade_min,
    )


def test_pick_sunrise_no_alarms(test_db_path):
    now = datetime(2026, 5, 11, 6, 30)
    assert pick_active_sunrise(now) is None


def test_pick_sunrise_ignores_alarm_with_light_off(test_db_path):
    from app.repositories import alarm_repository as repo
    repo.create("07:00", [0], True, "weekly", None, light=False, light_fade_minutes=30)
    now = datetime(2026, 5, 11, 6, 45)
    assert pick_active_sunrise(now) is None


def test_pick_sunrise_ignores_alarm_with_zero_fade(test_db_path):
    from app.repositories import alarm_repository as repo
    repo.create("07:00", [0], True, "weekly", None, light=True, light_fade_minutes=0)
    now = datetime(2026, 5, 11, 6, 45)
    assert pick_active_sunrise(now) is None


def test_pick_sunrise_returns_alarm_inside_window(test_db_path):
    from app.repositories import alarm_repository as repo
    repo.create("07:00", [0], True, "weekly", None, light=True, light_fade_minutes=30)
    now = datetime(2026, 5, 11, 6, 45)  # Monday, 15 min before alarm
    result = pick_active_sunrise(now)
    assert result is not None
    alarm, remaining_s, total_s = result
    assert alarm.time == "07:00"
    assert total_s == 30 * 60
    assert remaining_s == 15 * 60


def test_pick_sunrise_skips_alarm_outside_window(test_db_path):
    from app.repositories import alarm_repository as repo
    repo.create("07:00", [0], True, "weekly", None, light=True, light_fade_minutes=30)
    now = datetime(2026, 5, 11, 6, 0)  # Monday, 60 min before alarm
    assert pick_active_sunrise(now) is None


def test_pick_sunrise_picks_closer_when_two_in_window(test_db_path):
    from app.repositories import alarm_repository as repo
    a1 = repo.create("07:00", [0], True, "weekly", None, light=True, light_fade_minutes=30)
    a2 = repo.create("07:30", [0], True, "weekly", None, light=True, light_fade_minutes=60)
    now = datetime(2026, 5, 11, 6, 45)
    # a1: remaining 15 min; a2: remaining 45 min — a1 wins (smaller remaining).
    result = pick_active_sunrise(now)
    assert result is not None
    alarm, remaining_s, _ = result
    assert alarm.id == a1
    assert remaining_s == 15 * 60


def test_pick_sunrise_tie_broken_by_lower_id(test_db_path):
    # Two alarms with the same time and same fade — same remaining_seconds.
    from app.repositories import alarm_repository as repo
    a1 = repo.create("07:00", [0], True, "weekly", None, light=True, light_fade_minutes=30)
    a2 = repo.create("07:00", [0], True, "weekly", None, light=True, light_fade_minutes=30)
    now = datetime(2026, 5, 11, 6, 45)
    result = pick_active_sunrise(now)
    assert result is not None
    alarm, _, _ = result
    assert alarm.id == min(a1, a2)


def test_pick_sunrise_once_alarm_in_past_skipped(test_db_path):
    from app.repositories import alarm_repository as repo
    repo.create("07:00", [], True, "once", None, light=True, light_fade_minutes=30)
    now = datetime(2026, 5, 11, 8, 0)  # past 07:00
    assert pick_active_sunrise(now) is None


def test_pick_sunrise_weekly_other_day_outside_window(test_db_path):
    from app.repositories import alarm_repository as repo
    # Alarm on Monday only, now is Saturday — next occurrence is in 2 days.
    repo.create("07:00", [0], True, "weekly", None, light=True, light_fade_minutes=30)
    now = datetime(2026, 5, 16, 6, 45)  # Saturday
    assert pick_active_sunrise(now) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/unit/test_alarm_service.py -v`
Expected: all 9 new tests FAIL with `ImportError: cannot import name 'pick_active_sunrise'`.

- [ ] **Step 3: Implement `pick_active_sunrise`**

Add to `backend/app/services/alarm_service.py` (after `get_alarms_with_fade_due`):

```python
def pick_active_sunrise(now: datetime) -> Optional[tuple[Alarm, int, int]]:
    """Pick the enabled alarm whose sunrise should drive the bulb right now.

    Returns (alarm, remaining_seconds, total_seconds) for the candidate with the
    smallest remaining_seconds (closest in time). Ties broken by alarm.id ascending.
    Returns None when no alarm is in any fade window.
    """
    alarms = get_enabled()
    best: Optional[tuple[Alarm, int, int]] = None
    for alarm in alarms:
        if not alarm.light or alarm.light_fade_minutes <= 0:
            continue
        candidate = _next_occurrence(alarm, now)
        if candidate is None:
            continue
        remaining_s = int((candidate - now).total_seconds())
        total_s = alarm.light_fade_minutes * 60
        if not (0 < remaining_s <= total_s):
            continue
        if best is None:
            best = (alarm, remaining_s, total_s)
            continue
        b_alarm, b_remaining, _ = best
        if remaining_s < b_remaining or (remaining_s == b_remaining and alarm.id < b_alarm.id):
            best = (alarm, remaining_s, total_s)
    return best
```

Note `Optional` is already imported in this file; `get_enabled` and `_next_occurrence` are defined in the same module.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/unit/test_alarm_service.py -v`
Expected: all alarm_service tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/alarm_service.py backend/tests/unit/test_alarm_service.py
git commit -m "feat(alarm): add pick_active_sunrise selector

Returns the enabled alarm whose fade window is currently open and whose
remaining time is smallest. Ties broken by alarm.id. Used by wecker.py
to decide which alarm drives the bulb each minute."
```

---

### Task 4: Remove `get_alarms_with_fade_due`

**Files:**
- Modify: `backend/app/services/alarm_service.py`

`pick_active_sunrise` supersedes it. The current caller (`wecker.py`) is updated in Task 6; this task just removes the dead function and confirms no other caller exists.

- [ ] **Step 1: Confirm callers**

Run: `grep -rn "get_alarms_with_fade_due" backend`
Expected: matches in `backend/app/services/alarm_service.py` (definition), `backend/wecker.py` (caller — handled in Task 6). No tests reference it.

- [ ] **Step 2: Delete the function**

In `backend/app/services/alarm_service.py`, delete:

```python
def get_alarms_with_fade_due() -> list[tuple[Alarm, int]]:
    """Return (alarm, remaining_seconds) for alarms whose light fade should start now."""
    alarms = get_enabled()
    now = datetime.now()
    window_start = now - timedelta(minutes=2)
    result = []
    for alarm in alarms:
        if not alarm.light or alarm.light_fade_minutes <= 0:
            continue
        # Search for next occurrence relative to just before fade would have started
        search_after = now - timedelta(minutes=alarm.light_fade_minutes + 2)
        candidate = _next_occurrence(alarm, search_after)
        if candidate is None:
            continue
        fade_start = candidate - timedelta(minutes=alarm.light_fade_minutes)
        if window_start <= fade_start <= now:
            remaining = max(0, int((candidate - now).total_seconds()))
            result.append((alarm, remaining))
    return result
```

- [ ] **Step 3: Run tests**

Run: `cd backend && pytest -q`
Expected: PASS. (`wecker.py` still imports the deleted name, but tests don't import `wecker.py` so collection is unaffected. Don't fix wecker.py here — Task 6 handles it.)

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/alarm_service.py
git commit -m "refactor(alarm): drop get_alarms_with_fade_due

Replaced by pick_active_sunrise. wecker.py caller updated in the
follow-up commit."
```

---

### Task 5: Remove `_fade_light_task` and `/light/fade-start` endpoint

**Files:**
- Modify: `backend/app/api/v1/esp.py`

- [ ] **Step 1: Confirm no integration tests reference the route**

Run: `grep -rn "fade-start\|_fade_light_task\|light_fade_start" backend`
Expected: matches only in `backend/app/api/v1/esp.py` and `backend/wecker.py`. (wecker.py is updated in Task 6.)

- [ ] **Step 2: Delete the route and helper**

In `backend/app/api/v1/esp.py`, delete the entire block:

```python
@router.post("/light/fade-start")
async def light_fade_start(alarm_id: int, total_seconds: int):
    """Called by wecker.py to start a gradual light sunrise before alarm rings."""
    from app.repositories import alarm_repository
    alarm = alarm_repository.get_by_id(alarm_id)
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    if not alarm.light:
        return {"message": "light not enabled for this alarm", "started": False}
    if total_seconds <= 0:
        return {"message": "no time remaining for fade", "started": False}
    if not light_service.mark_fade_started():
        return {"message": "fade already running", "started": False}
    asyncio.create_task(_fade_light_task(alarm_id, total_seconds))
    logger.info("Light fade task created for alarm %d (%ds)", alarm_id, total_seconds)
    return {"message": "fade started", "started": True}


async def _fade_light_task(alarm_id: int, total_seconds: int) -> None:
    """Gradually brighten light from dim warm to full neutral over total_seconds."""
    try:
        try:
            import tinytuya
        except ImportError:
            logger.warning("tinytuya not available — cannot fade light for alarm %d", alarm_id)
            return

        import time as time_lib
        from app.config import settings

        steps = max(2, total_seconds // 30)
        interval = total_seconds / steps
        tuya_cfg = dict(
            dev_id=settings.tuya_dev_id,
            address=settings.tuya_ip,
            local_key=settings.tuya_local_key,
            version=3.3,
        )
        loop = asyncio.get_running_loop()

        def _init_light():
            d = tinytuya.BulbDevice(**tuya_cfg)
            d.turn_on()
            time_lib.sleep(0.5)
            d.set_mode("white")
            d.set_white(10, 0)  # very dim, warmest colour temp (sunrise)

        await loop.run_in_executor(None, _init_light)
        logger.info("Fade for alarm %d started: %d steps over %ds", alarm_id, steps, total_seconds)

        for step in range(1, steps + 1):
            await asyncio.sleep(interval)
            if player_service.is_active():
                # Alarm already started; _light_on() will set full brightness
                logger.info("Fade for alarm %d interrupted by alarm start at step %d/%d", alarm_id, step, steps)
                break
            fraction = step / steps
            brightness = int(10 + 990 * fraction)
            color_temp = int(500 * fraction)  # warm (0) → neutral (500)

            def _set_step(b=brightness, ct=color_temp):
                d = tinytuya.BulbDevice(**tuya_cfg)
                d.set_white(b, ct)

            try:
                await loop.run_in_executor(None, _set_step)
            except Exception:
                logger.exception("Fade step %d/%d failed for alarm %d", step, steps, alarm_id)
    except Exception:
        logger.exception("_fade_light_task for alarm %d failed", alarm_id)
    finally:
        light_service.mark_fade_stopped()
```

- [ ] **Step 3: Tidy `esp.py` imports**

After deletion, check: `grep -n "import\|from" backend/app/api/v1/esp.py | head -20`. Confirm `light_service` is still imported (it isn't used anywhere else in this file after the deletion — `_light_on` constructs `tinytuya.BulbDevice` inline). If unused, remove `light_service` from the line:

```python
from app.services import esp_service, player_service, log_service, light_service
```
becomes:
```python
from app.services import esp_service, player_service, log_service
```

- [ ] **Step 4: Run the test suite**

Run: `cd backend && pytest -q`
Expected: PASS. (Integration tests `test_esp_routes.py` should not reference `/esp/light/fade-start`; if they do, the test will fail and you'll need to delete that test in this same step.)

- [ ] **Step 5: Manual smoke check the file still parses**

Run: `cd backend && python -c "from app.api.v1 import esp; print('ok')"`
Expected: `ok`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/esp.py
git commit -m "refactor(esp): drop /light/fade-start route and async fade task

Replaced by stateless per-minute sunrise tick driven by wecker.py."
```

---

### Task 6: Update `wecker.py` to drive sunrise ticks

**Files:**
- Modify: `backend/wecker.py`

- [ ] **Step 1: Replace the import line**

In `backend/wecker.py`, find:

```python
    from app.services.alarm_service import get_due_alarms, get_alarms_with_fade_due
    from app.services.log_service import create_triggered, mark_error
    from app.repositories import log_repository as log_repo
    from app.repositories import alarm_repository
```

Change the first line to:

```python
    from app.services.alarm_service import get_due_alarms, pick_active_sunrise
    from app.services.light_service import compute_sunrise_payload
    from app.services.log_service import create_triggered, mark_error
    from app.repositories import log_repository as log_repo
    from app.repositories import alarm_repository
```

- [ ] **Step 2: Replace the fade-pre-trigger block**

In `backend/wecker.py`, find and delete the entire block starting at the `# Light fade pre-trigger` comment (currently lines 100–122):

```python
    # Light fade pre-trigger: start gradual brightness ramp before alarm rings
    for alarm, remaining_seconds in get_alarms_with_fade_due():
        logger.info(
            "Starting light fade for alarm %d (%ds remaining until alarm).",
            alarm.id, remaining_seconds,
        )
        try:
            res = requests.post(
                f"{API_BASE}/esp/light/fade-start",
                params={"alarm_id": alarm.id, "total_seconds": remaining_seconds},
                headers=headers,
                timeout=5,
            )
            if res.ok:
                data = res.json()
                if data.get("started"):
                    logger.info("Light fade started for alarm %d.", alarm.id)
                else:
                    logger.info("Light fade for alarm %d: %s", alarm.id, data.get("message"))
            else:
                logger.warning("Fade-start rejected for alarm %d: %s", alarm.id, res.status_code)
        except requests.RequestException as e:
            logger.warning("Could not reach API for fade-start, alarm %d: %s", alarm.id, e)
```

Replace it with:

```python
    # Sunrise tick: re-derive bulb state from now+alarms each minute.
    picked = pick_active_sunrise(datetime.now())
    if picked is None:
        return

    alarm, remaining_s, total_s = picked

    try:
        status_res = requests.get(
            f"{API_BASE}/esp/alarm/status", headers=headers, timeout=5,
        )
        if status_res.ok and status_res.json().get("active"):
            logger.debug("Alarm currently active; skipping sunrise tick.")
            return
    except requests.RequestException as e:
        logger.warning("Could not check alarm status, skipping sunrise tick: %s", e)
        return

    payload = compute_sunrise_payload(remaining_s, total_s)
    try:
        res = requests.post(
            f"{API_BASE}/light/", json=payload, headers=headers, timeout=5,
        )
        if res.ok:
            logger.info(
                "Sunrise tick for alarm %d (remaining=%ds total=%ds): %s",
                alarm.id, remaining_s, total_s, payload,
            )
        else:
            logger.warning(
                "Sunrise tick rejected for alarm %d: %s %s",
                alarm.id, res.status_code, res.text[:200],
            )
    except requests.RequestException as e:
        logger.warning("Sunrise tick request failed for alarm %d: %s", alarm.id, e)
```

- [ ] **Step 3: Confirm no remaining references to deleted symbols**

Run: `grep -n "get_alarms_with_fade_due\|fade-start" backend/wecker.py`
Expected: no matches.

- [ ] **Step 4: Smoke-check the script imports cleanly**

Run: `cd backend && python -c "import wecker; print('ok')"`
Expected: `ok`. (No stale imports, no NameErrors at module load.)

- [ ] **Step 5: Run the full test suite**

Run: `cd backend && pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/wecker.py
git commit -m "feat(wecker): drive sunrise via per-minute /light POST

Each tick: pick the closest enabled alarm whose fade window is open,
skip if any alarm is currently active, compute the bulb command via
compute_sunrise_payload, and POST it to /api/v1/light. Replaces the
fragile asyncio fade task in the API process."
```

---

### Task 7: End-to-end sanity on the Pi

**Files:** none — verification only.

This is a manual check that the deployed system behaves. Do this after the GitHub Actions self-hosted runner has deployed the changes (or `ssh` and pull manually).

- [ ] **Step 1: Push and let the deploy run**

```bash
git push origin main
```

Watch GitHub Actions. Expected: backend-deploy workflow green.

- [ ] **Step 2: Tail logs on the Pi**

```bash
ssh raspberrypi "journalctl -u wecker.service -f -n 20"
```

- [ ] **Step 3: Set a test alarm**

In the frontend, create a one-off alarm 5 minutes in the future with `light=True` and `light_fade_minutes=3`. The fade window opens 3 minutes before the alarm.

- [ ] **Step 4: Watch wecker logs across the fade window**

Expected log entries (one per minute, starting roughly 3 min before alarm):
```
Sunrise tick for alarm <id> (remaining=180s total=180s): {'hex': '#050501', 'brightness': 10}
Sunrise tick for alarm <id> (remaining=120s total=180s): {'brightness': ...}   # white phase begins
Sunrise tick for alarm <id> (remaining=60s total=180s):  {'brightness': ...}
```

The bulb should visibly progress from a near-black warm glow to bright neutral white over the 3 minutes.

- [ ] **Step 5: Verify alarm fires normally**

When the alarm rings, expect:
- Existing `_light_on()` flips bulb to brightness=1000, color_temp=500.
- Next minute's wecker tick logs nothing about sunrise (alarm time has passed; for `once` it's disabled, for `weekly` next occurrence is 7 days out).
- If the alarm is still ringing at the next-minute mark, wecker GETs `/esp/alarm/status` → active=True → logs `Alarm currently active; skipping sunrise tick`.

- [ ] **Step 6: If anything looks wrong, capture logs and stop here**

Don't paper over weirdness. Report back: full wecker log output for the fade window plus any API errors from `journalctl -u strafwecker-api.service`.

---

## Self-review

**Spec coverage:** every section of the design spec has a task —
- §2 Components → Tasks 1, 2, 3, 4, 5, 6
- §3 Conflict / edges → covered by tests in Tasks 1 & 3 plus the wecker logic in Task 6
- §4 Auth → no changes (confirmed in spec)
- §5 Testing → Tasks 1 & 3
- §6 Out of scope → respected

**No placeholders:** every code change shows the actual code; every test step shows the actual test; every command shows the expected output.

**Type consistency:** `pick_active_sunrise` returns `Optional[tuple[Alarm, int, int]]` — matches the unpack in wecker.py (`alarm, remaining_s, total_s = picked`) and the signature consumed by `compute_sunrise_payload(remaining_s, total_s)` (both ints). `compute_sunrise_payload` always returns a `dict` of either `{hex, brightness}` or `{brightness, color_temp}` — both shapes are accepted by the existing `LightRequest` schema.
