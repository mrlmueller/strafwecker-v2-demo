# Nap Timer — Design Spec

**Date:** 2026-05-10
**Status:** Approved

---

## Problem

The Strafwecker today only supports recurring or one-off time-of-day
alarms. Short naps (15–20 minutes) are awkward: they require setting
an arbitrary clock time, the ESP32 button countdown and cloud-function
penalty path always fire, and if you want a light cue you only get the
sunrise fade — which doesn't make sense over a 15-minute window.

We want an iOS-Clock-style nap timer:

- Choose a duration between 1 and 60 minutes.
- Optional ESP32 button. When off, the whole no-press penalty path is
  skipped.
- Light, when enabled, snaps to full brightness at trigger time — no
  fade.
- One-time use, but the row is not auto-deleted; the UI shows ended
  naps with a Restart action.

---

## Schema (migration 003)

One Alembic migration on the existing `alarms` table:

| Column | Type | Default | Notes |
|---|---|---|---|
| `kind` | TEXT NOT NULL | `'alarm'` | `'alarm'` or `'nap'`. |
| `nap_target_at` | TEXT | NULL | ISO-8601 datetime, naps only. |
| `nap_duration_minutes` | INTEGER | NULL | 1..60, naps only. |
| `esp32_button` | INTEGER NOT NULL | `1` | Boolean; applies to both kinds. Default `1` keeps existing alarm behaviour unchanged. |

Existing alarms keep `kind='alarm'`, `nap_*` null, `esp32_button=1`.
For naps, `time` is filled with the `HH:MM` portion of `nap_target_at`
on create / restart so the existing display, sort, and "next alarm"
code keeps working without conditionals; `repeat_type='once'`;
`light_fade_minutes=0`.

---

## Backend changes

### `alarm_service._next_occurrence(alarm, after)`

Add a kind-branch at the top:

```python
if alarm.kind == "nap":
    if not alarm.nap_target_at:
        return None
    target = datetime.fromisoformat(alarm.nap_target_at)
    return target if target > after else None
# existing weekly/once logic untouched
```

Naps now fire through the same `get_due_alarms()` loop as alarms. No
changes to `wecker.py`. `pick_active_sunrise` already filters on
`light_fade_minutes > 0`, so naps are naturally excluded from sunrise
tick computation.

### `api/v1/esp.py::trigger_alarm`

Wrap the existing ESP32 notify in a conditional:

```python
if alarm.esp32_button:
    asyncio.create_task(_notify_esp32(alarm_id, log_id))
asyncio.create_task(_auto_stop(alarm_id, log_id))   # unchanged
```

When `esp32_button=False`: the ESP32 firmware never receives `/trigger`,
so it never starts its no-press countdown, so the cloud-function
penalty never fires. The Pi's `_auto_stop` still terminates the sound
after `alarm_auto_stop_seconds`.

The existing `_light_on()` (full brightness at trigger when `light=True`)
already gives the "no fade, full brightness at end" behaviour we want
for naps. No changes to that path.

### `wecker.py` `once`-disable logic

Already handles naps via `repeat_type='once'`. No code change.

---

## API surface

Existing endpoints `/api/v1/alarms` (CRUD) absorb naps. Schemas grow:

```python
class AlarmCreate(BaseModel):
    time: str                       # HH:MM (set to HH:MM of nap_target_at for naps)
    days_of_week: list[int] = []
    enabled: bool = True
    repeat_type: str = "once"
    label: Optional[str] = None
    light: bool = False
    light_fade_minutes: int = 0
    # NEW
    kind: str = "alarm"             # "alarm" | "nap"
    nap_target_at: Optional[str] = None   # ISO datetime; if None and kind=='nap', server fills with now+duration
    nap_duration_minutes: Optional[int] = None
    esp32_button: bool = True
```

Validation rules (in the schema validators):

- `kind` ∈ {`'alarm'`, `'nap'`}.
- When `kind == 'nap'`: `nap_duration_minutes` required and in `[1, 60]`.
- When `kind == 'nap'` and `nap_target_at` is None: server fills it
  with `(datetime.now() + nap_duration_minutes minutes).isoformat()`
  in the route (not the schema, since schemas should not own clock).
- When `kind == 'alarm'`: `nap_*` fields ignored / null.

`AlarmResponse` exposes the same new fields.

### One new route

```
POST /api/v1/alarms/{id}/restart
```

Behaviour:
- 404 if not found.
- 400 if `alarm.kind != 'nap'` or `nap_duration_minutes is None`.
- Otherwise: set `nap_target_at = now + nap_duration_minutes`,
  `enabled=True`, persist, return `200 { message, target_at }`.

Lives in `api/v1/alarms.py`. The same auth middleware protects it.

---

## Frontend

### Home page split

`frontend/app/page.tsx` splits the alarm list into two groups:

- **Alarms** (`alarm.kind !== 'nap'`) — existing `AlarmCard` rendering.
- **Timers** (`alarm.kind === 'nap'`) — new `NapCard` rendering. Section
  only rendered when at least one nap exists.

The featured / "next alarm" logic (`lib/nextAlarm.ts`) is extended:
when `alarm.kind === 'nap'` and `nap_target_at` is set and in the
future, the candidate is `new Date(nap_target_at)` (instead of going
through the HH:MM/days-of-week computation). Otherwise the existing
logic runs. Naps and alarms compete; whichever fires first is featured.

### FAB chooser

The home FAB no longer opens `AlarmDrawer` directly. Instead it opens
a small bottom sheet with two large buttons — *Alarm* and *Timer* —
that route to `AlarmDrawer` or new `NapDrawer` respectively.

### `NapDrawer` (new component)

- Title: "New timer" / "Edit timer".
- A single-column wheel picker for minutes 1..60, default 15. Reuses
  the existing `TimeWheelPicker` component (with a thin minute-only
  variant if needed; otherwise a new `MinuteWheelPicker`).
- Label input, default "Nap".
- Switch: *Light* — when on, bulb snaps to full bright at trigger.
  Default off.
- Switch: *ESP32 button* — when on, the no-press penalty path is
  active. **UI default for naps: off** (naps are typically soft
  alarms). The DB column default `1` exists only so existing alarm
  rows keep their hard-alarm behaviour after the migration.
- Submit button: *Start timer* (create) / *Save changes* (edit).
- Delete button: same pattern as `AlarmDrawer`.

### `NapCard` (new component)

Two visual states:

**Active** (`enabled=true` AND `nap_target_at > now`):
- Big tabular label: live countdown, ticking once per second from a
  page-level `useEffect`. Format `MM:SS`.
- Sub-line: "Started 7 min ago" or original duration.
- Chips: `Lightbulb` (if `light`), `Bell-off` (if `!esp32_button`),
  optional label.
- Right-side `Switch` to disable (sets `enabled=false`).

**Ended** (anything not Active — i.e. `enabled=false`, OR
`nap_target_at <= now`, OR `nap_target_at` is null):
- Label "Ended" with relative time.
- **Restart** button (calls `POST /alarms/{id}/restart`).
- Tap card body to edit (opens `NapDrawer`).

The shared page-level `useEffect` ticks once per second only when at
least one nap is in the active state.

### Featured rendering on Home

When a nap is featured (i.e. `getNextAlarm` returned it), it appears
above its section heading with a sage-tinted background — same
treatment alarms get today.

### `utils/api.ts`

`Alarm` interface gains the new fields. `createAlarm` /
`updateAlarm` accept them. New helper `restartNap(id)` calls the new
endpoint.

---

## Conflict and edge handling

| Situation | Behaviour |
|---|---|
| Nap fires | `repeat_type='once'` → existing wecker code disables it; row persists with `nap_target_at` intact. UI flips to *Ended*. |
| User taps Restart on an ended nap | `POST /restart` resets `nap_target_at = now + duration_min`, `enabled=true`. UI flips back to *Active*. |
| User edits an ended nap's duration in the drawer | PUT updates `nap_duration_minutes`; tapping Restart afterwards uses the new duration. |
| User disables an active nap via the Switch | `enabled=false`; `nap_target_at` preserved. UI shows it greyed but visible. Re-enabling without Restart fires only if target is still in the future. |
| Two enabled rows fire on the same minute (alarm+nap, or two naps) | Both go through `get_due_alarms`; both trigger; the second `trigger_alarm` hits the "alarm already active" branch and returns gracefully (existing behaviour). The second `_light_on()` is a no-op (same target state). |
| `esp32_button=False` and ESP32 is reachable | ESP32 never gets `/trigger`. No no-press path. Auto-stop still ends the sound. |
| `esp32_button=True` and ESP32 is unreachable | Existing behaviour: 3 retries, mark `esp32_unreachable`. No regression. |
| Nap created with target already in the past (clock skew, edge case) | `_next_occurrence` returns None (target ≤ after). Nap never fires. User can Restart. |
| Light fade for a nap | Excluded by `pick_active_sunrise` filter (`light_fade_minutes > 0`). No sunrise tick. |
| Migration applied on Pi with existing alarms | All four columns have safe defaults / NULL. Existing rows keep firing identically. |

---

## Authentication

No changes. The new `POST /alarms/{id}/restart` route is mounted under
`/api/v1` and is automatically covered by `APIKeyMiddleware`. The
existing alarm CRUD already requires the API key, no per-route
addition needed.

---

## Testing

### Unit (`backend/tests/unit/`)

`test_alarm_service.py`:
- `_next_occurrence` for `kind='nap'`:
  - Future target → returns target.
  - Past target → returns None.
  - Missing `nap_target_at` → None.
- `pick_active_sunrise` skips a nap-kind alarm even when
  `light_fade_minutes > 0` (defensive — a nap shouldn't have fade
  anyway, but assert the kind-filter logic if added).

`test_alarm_schemas.py` (new file):
- `AlarmCreate` accepts a valid nap payload.
- `AlarmCreate` rejects `nap_duration_minutes=0`, `61`, and `None` when `kind='nap'`.
- `AlarmCreate` accepts a nap with `nap_target_at` omitted (route
  fills it; schema-level test just confirms it's optional).

### Integration (`backend/tests/integration/`)

`test_alarm_routes.py`:
- `POST /alarms` with nap payload: row created, `nap_target_at` set
  appropriately when omitted on the wire.
- `POST /alarms/{id}/restart`: target updates, `enabled=true`.
- `POST /alarms/{id}/restart` on a `kind='alarm'` row: 400.
- `POST /alarms/{id}/restart` on missing row: 404.

`test_esp_routes.py`:
- `trigger_alarm` for `esp32_button=False`: assert `_notify_esp32` is
  not awaited (monkeypatch the helper, count calls).
- `trigger_alarm` for `esp32_button=True`: existing test still passes.

### Frontend

- Light snapshot test on `NapCard` for both Active and Ended states.
- Manual browser smoke: create a 1-min nap, watch it tick, watch it
  fire, confirm Restart works, confirm `esp32_button=False` produces
  no ESP32 traffic in the API logs.

---

## Out of scope

- ESP32 firmware changes (not needed — when not notified, the firmware
  does nothing).
- Sub-minute precision (1-min granularity matches the wecker cadence).
- Per-nap sound/volume customization.
- Recurring naps.
- A separate "Recent durations" list (the `nap_duration_minutes`
  column is already a one-tap restart of the exact nap).
- Pause/resume of an active nap (it's a one-shot timer; you Restart or
  Delete).
