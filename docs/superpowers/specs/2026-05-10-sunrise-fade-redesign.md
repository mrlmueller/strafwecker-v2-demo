# Sunrise Fade Redesign — Design Spec

**Date:** 2026-05-10
**Status:** Approved

---

## Problem

The v2 sunrise fade is broken. The current implementation lives in
`backend/app/api/v1/esp.py` as `_fade_light_task`: a long-running asyncio
task spawned inside the FastAPI process when `wecker.py` decides the
fade should start (`alarm_service.get_alarms_with_fade_due`). It sleeps
between brightness steps and uses a global `_fade_active` lock in
`light_service.py` to prevent overlap.

Failure modes:

- API restart during the fade kills the in-flight asyncio task; the fade is lost.
- An alarm set 10 minutes before it rings with a 30-minute fade is silently dropped — the start condition (`fade_start ∈ [now-2min, now]`) never fires.
- The single global `_fade_active` lock prevents two alarms with overlapping fade windows from sharing the bulb sensibly.
- Two separate code paths must be reasoned about (`get_alarms_with_fade_due` vs. the asyncio loop), and they can disagree.

The old Flask code on the Pi (`/home/pi/Documents/wecker.py`,
`adjust_light_brightness()`) avoided all of these: every minute it
re-derived the current bulb state from `(now, next_alarm)` and POSTed
a single light command. We are porting that idea back, in v2's 3-layer
shape.

---

## Approach

`wecker.py` already runs once per minute via `wecker.timer`
(`OnCalendar=*-*-* *:*:01`). Each tick does, in order:

1. Trigger any due alarms (existing — unchanged).
2. **(new)** Compute the current sunrise tick and apply it via `POST /api/v1/light`.

Each tick re-derives state from scratch. There is no persistent fade
state, no background task, no lock.

```
wecker.py (every minute)
   │
   ├─ alarm_service.pick_active_sunrise(now)
   │      → Optional[(Alarm, remaining_s, total_s)]
   │
   ├─ GET /api/v1/esp/alarm/status  → if active=True, skip
   │
   ├─ light_service.compute_sunrise_payload(remaining_s, total_s)
   │      → {"hex": "#...", "brightness": 10}             # color phase
   │       or {"brightness": 10..1000, "color_temp": 350} # white phase
   │
   └─ POST /api/v1/light  (x-api-key)
            └─ light_service.apply_light → tinytuya
```

---

## Components

### Layer 3 — repositories

No changes. `alarm_repository.get_enabled()` already returns what we
need.

### Layer 2 — services

**`alarm_service.pick_active_sunrise(now: datetime) -> Optional[tuple[Alarm, int, int]]`**

- Iterates enabled alarms with `light=True` and `light_fade_minutes > 0`.
- For each, finds `next_occurrence > now` using the existing
  `_next_occurrence` helper.
- A candidate is included when `0 < remaining_seconds ≤ light_fade_minutes * 60`.
- Returns the candidate with the **smallest `remaining_seconds`**
  (closest alarm wins). Ties broken by `alarm.id` ascending for
  determinism.
- Returns `None` if there is no candidate.
- Tuple return is `(alarm, remaining_seconds, total_seconds)`. Both
  values are integers.

**Removed:** `alarm_service.get_alarms_with_fade_due`.

**`light_service.compute_sunrise_payload(remaining_seconds: int, total_seconds: int) -> dict`**

Pure function. No I/O. Constants (matching the old Flask behaviour):

```python
COLOR_RATIO = 15 / 35       # ≈ 0.4286
WHITE_RATIO = 20 / 35       # ≈ 0.5714
START_HEX = "#050501"       # near-black warm
END_HEX   = "#fff1a6"       # pale yellow-white
WHITE_COLOR_TEMP = 350
MIN_BRIGHTNESS = 10         # /light schema requires ≥ 10
```

Behaviour:

- `total_color_seconds = total_seconds * COLOR_RATIO`
- `total_white_seconds = total_seconds * WHITE_RATIO`
- **Color phase** when `remaining_seconds > total_white_seconds`:
  - `elapsed_in_color = (total_seconds - remaining_seconds)`
  - `fraction = elapsed_in_color / total_color_seconds`, clamped to `[0, 1]`
  - `hex_val = interpolate_hex(START_HEX, END_HEX, fraction)`
  - return `{"hex": hex_val, "brightness": MIN_BRIGHTNESS}`
- **White phase** when `remaining_seconds ≤ total_white_seconds`:
  - `fraction = (total_white_seconds - remaining_seconds) / total_white_seconds`, clamped to `[0, 1]`
  - `brightness = max(MIN_BRIGHTNESS, int(1000 * fraction))`
  - return `{"brightness": brightness, "color_temp": WHITE_COLOR_TEMP}`

The function never returns `None`. Callers are expected to only invoke
it when they have a candidate from `pick_active_sunrise`.

**Removed:** `_fade_active`, `_fade_lock`, `is_fade_active`,
`mark_fade_started`, `mark_fade_stopped` from `light_service.py`.
`hex_to_rgb` and `interpolate_hex` stay (used by the new function and
the existing `apply_light`).

### Layer 1 — api

**Removed:**
- `POST /api/v1/esp/light/fade-start` route in `app/api/v1/esp.py`.
- `_fade_light_task` async helper in `app/api/v1/esp.py`.

**Reused as-is:**
- `POST /api/v1/light` (existing). Accepts the same payload shapes that
  `compute_sunrise_payload` produces.
- `GET /api/v1/esp/alarm/status` (existing). Returns `{"active": bool}`.

No new endpoints.

### wecker.py

The block at lines 100–122 (the `for alarm, remaining_seconds in get_alarms_with_fade_due()` loop and its POST to `/esp/light/fade-start`) is replaced with:

```python
# (after the existing due-alarm trigger loop)

picked = alarm_service.pick_active_sunrise(datetime.now())
if picked is None:
    return

alarm, remaining_s, total_s = picked

try:
    res = requests.get(f"{API_BASE}/esp/alarm/status", headers=headers, timeout=5)
    if res.ok and res.json().get("active"):
        logger.debug("Alarm currently active; skipping sunrise tick.")
        return
except requests.RequestException as e:
    logger.warning("Could not check alarm status, skipping fade tick: %s", e)
    return

payload = light_service.compute_sunrise_payload(remaining_s, total_s)
try:
    res = requests.post(f"{API_BASE}/light/", json=payload, headers=headers, timeout=5)
    if res.ok:
        logger.info("Sunrise tick for alarm %d (remaining=%ds): %s",
                    alarm.id, remaining_s, payload)
    else:
        logger.warning("Sunrise tick rejected: %s %s", res.status_code, res.text[:200])
except requests.RequestException as e:
    logger.warning("Sunrise tick request failed: %s", e)
```

Imports adjusted: `from app.services import alarm_service, light_service`.

---

## Conflict and edge handling

| Situation | Behaviour |
|---|---|
| Two enabled alarms in fade window | The one with smaller `remaining_seconds` wins. Ties broken by `alarm.id` ascending. |
| `light_fade_minutes = 0` | Alarm is skipped entirely by `pick_active_sunrise`. Existing `_light_on()` at trigger time still flips bulb on full white. |
| `light = False` | Alarm is skipped entirely. |
| Alarm just fired (`once`) | Trigger loop sets `enabled=False`; alarm drops out of `get_enabled()`; no fade tick afterwards. |
| Alarm just fired (`weekly`) | `_next_occurrence` jumps 7 days, far outside fade window. No fade tick. |
| Another alarm currently active | wecker GETs `/esp/alarm/status`; if `active=True`, skip. Prevents a 07:30 alarm's fade tick from overwriting the bright-white state of a 07:00 alarm currently ringing. |
| `/light` POST fails (Tuya offline) | Log warning, return. Next minute retries naturally. |
| API restart mid-fade | No impact. Next minute re-derives from `now` + alarms table. |
| DST jump | Self-corrects within a minute. |
| Alarm set with fade-window already underway | `pick_active_sunrise` finds it on the very next tick and starts mid-curve. No need for a separate "start condition." |

---

## Authentication

Confirmed during design: `APIKeyMiddleware` (`app/api/middleware.py`)
runs on every route mounted under `/api/v1`. `OPTIONS` bypasses for
CORS preflight only. `/api/v1/light` and `/api/v1/esp/callback` add a
loopback / private-IP `_assert_local()` check on top.

`wecker.py` already sends `x-api-key` (line 44) and runs on localhost,
so it satisfies both checks. No auth changes required for this work.

---

## Testing

Unit tests only — all logic is in pure functions. No new integration
tests; the `/light` route already has coverage.

**`tests/unit/test_light_service.py`** (new cases):

- `compute_sunrise_payload(remaining=total, total=1800)` → color phase, `hex == START_HEX`, `brightness == 10`.
- `compute_sunrise_payload(remaining=total*0.6, total=1800)` → mid color phase, valid hex, `brightness == 10`.
- `compute_sunrise_payload(remaining=total_white_seconds + 1, total=1800)` → still color phase, `hex ≈ END_HEX`.
- `compute_sunrise_payload(remaining=total_white_seconds, total=1800)` → white phase begins, `brightness == MIN_BRIGHTNESS`, `color_temp == 350`.
- `compute_sunrise_payload(remaining=0, total=1800)` → white phase end, `brightness == 1000`, `color_temp == 350`.
- `compute_sunrise_payload(remaining=-30, total=1800)` → clamped to white-phase end (`brightness == 1000`).
- `compute_sunrise_payload(remaining=99999, total=1800)` → clamped to color-phase start (`hex == START_HEX`, `brightness == 10`).

**`tests/unit/test_alarm_service.py`** (new cases for `pick_active_sunrise`):

- No alarms enabled → `None`.
- One alarm with `light=False` → `None`.
- One alarm with `light=True, light_fade_minutes=0` → `None`.
- One alarm scheduled 15 min from now, `light=True, light_fade_minutes=30` → returns `(alarm, ~900, 1800)`.
- One alarm scheduled 60 min from now, `light_fade_minutes=30` → `None` (outside window).
- Two alarms in fade window (15 min remaining, 25 min remaining), both `light_fade_minutes=30` → returns the 15-min one.
- Two alarms with identical `remaining_seconds` → returns smaller `alarm.id`.
- Once-type alarm in the past → `None` (no future occurrence today).
- Weekly Mon–Fri alarm at 07:00, `now=Saturday 06:50` → next occurrence is Monday, > 30 min remaining → `None`.

---

## Out of scope

- Frontend (the `light_fade_minutes` field is already exposed in the alarm form).
- Schema migration (no DB changes).
- Auth model changes.
- `_light_on()` behaviour at alarm trigger (kept as-is).
- Sub-minute-resolution fade (a 1-minute step is fine for sunrise; matches old behaviour).
