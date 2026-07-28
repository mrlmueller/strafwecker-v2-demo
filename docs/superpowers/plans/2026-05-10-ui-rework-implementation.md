# UI Rework — Charcoal × Sage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the existing dark-blue shadcn-default frontend with a deliberate "Charcoal × Sage" palette, introduce a Hero-Card add-alarm sheet that uses an iOS-style wheel time picker, add a live seconds indicator and a friendly empty state to the home page.

**Architecture:** Pure frontend changes inside `frontend/`. No backend changes, no schema changes, no new endpoints. We extract three new presentational components (`HomeClock`, `AlarmCard`, `EmptyAlarmsState`), a wheel-picker primitive (`TimeWheelPicker`), and a small utility (`lib/nextAlarm.ts`). The CSS-variable-driven shadcn theme system stays — we only swap the variable values and add two new ones (`--sage`, `--cream`) for direct access.

**Tech Stack:** Next.js 16 (app router), React 18, Tailwind CSS, shadcn/ui (existing), `vaul` (existing for sheet primitive), `lucide-react` (existing for icons).

---

## File Structure

**New files:**
- `frontend/lib/nextAlarm.ts` — pure function computing the next firing of an alarm given the current time
- `frontend/app/components/HomeClock.tsx` — greeting + HH:MM clock + pulsing seconds + conditional next-alarm-in line
- `frontend/app/components/AlarmCard.tsx` — single alarm row with toggle, label, badges, tap-to-edit
- `frontend/app/components/EmptyAlarmsState.tsx` — moon glyph card shown when no alarms exist
- `frontend/app/components/TimeWheelPicker.tsx` — two scrolling columns for hour / minute, scroll-snap-based

**Modified files:**
- `frontend/app/globals.css` — replace dark-mode CSS variables, keep the structure
- `frontend/tailwind.config.ts` — add `sage` and `cream` color tokens
- `frontend/app/manifest.ts` — update `theme_color` and `background_color` to `#161616`
- `frontend/app/layout.tsx` — update viewport `themeColor` to `#161616`
- `frontend/app/page.tsx` — refactor to use new components, replace the centered title + full-width Add button with the new layout
- `frontend/app/components/AlarmDrawer.tsx` — replace `<input type="time">` with `<TimeWheelPicker>`, drop the explicit Repeat/Light/Enabled toggles

**Untouched:**
- `frontend/app/components/Navbar.tsx` (already has the bottom tab bar; new theme vars apply automatically)
- `frontend/app/components/AlarmForm.tsx` (legacy, unused — leave it alone)
- `frontend/app/components/DevTokenManager.tsx`, `TimePicker.tsx` (not used in the new flow)
- All shadcn primitives in `frontend/components/ui/*`
- All backend, ESP32, docs

**Test strategy:** The project has no test framework set up. Each task ends with `npm run lint` and `npm run build` for static verification, plus a manual dev-server check noted in the step. Adding Jest/Vitest is out of scope.

---

## Task 1: Theme tokens — palette swap

Replace the dark-mode CSS variables in `globals.css` with the Charcoal × Sage palette. Add two custom tokens (`--sage`, `--cream`) for direct use, then expose them as Tailwind colors.

**Files:**
- Modify: `frontend/app/globals.css`
- Modify: `frontend/tailwind.config.ts`
- Modify: `frontend/app/manifest.ts`
- Modify: `frontend/app/layout.tsx`

- [ ] **Step 1: Update dark-mode CSS variables**

Replace lines 39–64 (the `.dark { … }` block) of `frontend/app/globals.css` with:

```css
.dark {
    --background: 0 0% 9%;            /* #161616 */
    --foreground: 40 34% 86%;         /* #E8E0D0 cream body */
    --card: 0 0% 14%;                 /* #232323 */
    --card-foreground: 40 34% 86%;
    --popover: 0 0% 14%;
    --popover-foreground: 40 34% 86%;
    --primary: 145 39% 73%;           /* #9FD4B5 sage */
    --primary-foreground: 0 0% 9%;    /* dark text on sage */
    --secondary: 0 0% 14%;
    --secondary-foreground: 40 34% 86%;
    --muted: 0 0% 14%;
    --muted-foreground: 40 7% 60%;    /* desaturated cream */
    --accent: 145 39% 18%;            /* very dark sage for hover */
    --accent-foreground: 145 39% 73%;
    --destructive: 0 65% 55%;
    --destructive-foreground: 40 34% 86%;
    --border: 145 39% 73% / 0.08;
    --input: 0 0% 14%;
    --ring: 145 39% 73%;
    --chart-1: 145 39% 73%;
    --chart-2: 145 39% 53%;
    --chart-3: 40 34% 86%;
    --chart-4: 40 34% 60%;
    --chart-5: 40 34% 40%;

    /* New custom tokens (Charcoal × Sage) */
    --sage: 145 39% 73%;
    --cream: 40 44% 89%;              /* #F0E8D8 brighter cream for numerals */
}
```

Note: HSL values are space-separated (no commas) without the `hsl()` wrapper — that's the shadcn convention. The `--border` token uses `/ 0.08` for native CSS alpha.

- [ ] **Step 2: Add `sage` and `cream` to Tailwind colors**

In `frontend/tailwind.config.ts`, add inside `theme.extend.colors`:

```ts
sage: 'hsl(var(--sage))',
cream: 'hsl(var(--cream))',
```

The full `colors:` block after this change:

```ts
colors: {
    background: 'hsl(var(--background))',
    foreground: 'hsl(var(--foreground))',
    sage: 'hsl(var(--sage))',
    cream: 'hsl(var(--cream))',
    card: { DEFAULT: 'hsl(var(--card))', foreground: 'hsl(var(--card-foreground))' },
    popover: { DEFAULT: 'hsl(var(--popover))', foreground: 'hsl(var(--popover-foreground))' },
    primary: { DEFAULT: 'hsl(var(--primary))', foreground: 'hsl(var(--primary-foreground))' },
    secondary: { DEFAULT: 'hsl(var(--secondary))', foreground: 'hsl(var(--secondary-foreground))' },
    muted: { DEFAULT: 'hsl(var(--muted))', foreground: 'hsl(var(--muted-foreground))' },
    accent: { DEFAULT: 'hsl(var(--accent))', foreground: 'hsl(var(--accent-foreground))' },
    destructive: { DEFAULT: 'hsl(var(--destructive))', foreground: 'hsl(var(--destructive-foreground))' },
    border: 'hsl(var(--border))',
    input: 'hsl(var(--input))',
    ring: 'hsl(var(--ring))',
    chart: {
        '1': 'hsl(var(--chart-1))',
        '2': 'hsl(var(--chart-2))',
        '3': 'hsl(var(--chart-3))',
        '4': 'hsl(var(--chart-4))',
        '5': 'hsl(var(--chart-5))',
    },
},
```

- [ ] **Step 3: Update manifest theme color**

In `frontend/app/manifest.ts`, change both `background_color` and `theme_color` from `"#0D1929"` to `"#161616"`.

```ts
background_color: "#161616",
theme_color: "#161616",
```

- [ ] **Step 4: Update viewport theme color**

In `frontend/app/layout.tsx` line 28, change `themeColor: "#0D1929"` to `themeColor: "#161616"`.

- [ ] **Step 5: Verify lint + build**

```powershell
cd frontend; npm run lint
```
Expected: passes.

```powershell
cd frontend; npm run build
```
Expected: build succeeds.

- [ ] **Step 6: Commit**

```powershell
git add frontend/app/globals.css frontend/tailwind.config.ts frontend/app/manifest.ts frontend/app/layout.tsx
git commit -m "feat(theme): swap to Charcoal x Sage palette"
```

---

## Task 2: `lib/nextAlarm.ts` — utility for next-firing computation

Pure function that takes the current alarm list and current `Date` and returns `{ alarm, firesAt }` for the soonest upcoming firing, or `null` if no alarm is enabled.

**Files:**
- Create: `frontend/lib/nextAlarm.ts`

- [ ] **Step 1: Create the file**

```ts
// frontend/lib/nextAlarm.ts
import type { Alarm } from "@/utils/api";

export interface NextAlarm {
  alarm: Alarm;
  firesAt: Date;
}

/**
 * Days of week in our Alarm shape: 0 = Mon, 1 = Tue, ..., 6 = Sun.
 * JavaScript Date.getDay() returns 0 = Sun, 1 = Mon, ..., 6 = Sat — convert.
 */
function jsDayToOurDay(jsDay: number): number {
  return (jsDay + 6) % 7;
}

function nextFiringForAlarm(alarm: Alarm, now: Date): Date | null {
  if (!alarm.enabled) return null;
  const [hh, mm] = alarm.time.split(":").map(Number);
  if (Number.isNaN(hh) || Number.isNaN(mm)) return null;

  const todayOurDay = jsDayToOurDay(now.getDay());
  const days = alarm.days_of_week.length > 0 ? alarm.days_of_week : [todayOurDay];

  // Try today and the next 7 days; return the earliest firing strictly in the future.
  for (let offset = 0; offset < 8; offset++) {
    const check = new Date(now);
    check.setDate(check.getDate() + offset);
    check.setHours(hh, mm, 0, 0);
    const ourDay = jsDayToOurDay(check.getDay());
    if (!days.includes(ourDay)) continue;
    if (check.getTime() > now.getTime()) return check;
  }
  return null;
}

export function getNextAlarm(alarms: Alarm[], now: Date = new Date()): NextAlarm | null {
  let best: NextAlarm | null = null;
  for (const alarm of alarms) {
    const firesAt = nextFiringForAlarm(alarm, now);
    if (!firesAt) continue;
    if (!best || firesAt.getTime() < best.firesAt.getTime()) {
      best = { alarm, firesAt };
    }
  }
  return best;
}

/**
 * Format a duration as "Xh Ym" or "Xm" or "Xs" depending on size.
 * Used for the "next alarm in …" line.
 */
export function formatDurationUntil(target: Date, now: Date = new Date()): string {
  const ms = Math.max(0, target.getTime() - now.getTime());
  const totalMin = Math.floor(ms / 60000);
  const hours = Math.floor(totalMin / 60);
  const minutes = totalMin % 60;
  if (hours >= 24) {
    const days = Math.floor(hours / 24);
    const remH = hours % 24;
    return remH > 0 ? `${days}d ${remH}h` : `${days}d`;
  }
  if (hours > 0) return `${hours}h ${minutes}m`;
  if (totalMin > 0) return `${totalMin}m`;
  const seconds = Math.ceil(ms / 1000);
  return `${seconds}s`;
}
```

- [ ] **Step 2: Verify lint**

```powershell
cd frontend; npm run lint
```
Expected: passes (no warnings about the new file).

- [ ] **Step 3: Commit**

```powershell
git add frontend/lib/nextAlarm.ts
git commit -m "feat: add lib/nextAlarm.ts utility"
```

---

## Task 3: `HomeClock` component — greeting + clock + seconds + next-in

Replaces lines 150–156 of the current `page.tsx`. Renders the greeting, large `HH:MM` clock, an inline pulsing-dot seconds pill, and the conditional "Next alarm in …" line.

**Files:**
- Create: `frontend/app/components/HomeClock.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/app/components/HomeClock.tsx
"use client";

import { useEffect, useState } from "react";
import type { Alarm } from "@/utils/api";
import { getNextAlarm, formatDurationUntil } from "@/lib/nextAlarm";

interface Props {
  alarms: Alarm[];
}

function getGreeting(hour: number): string {
  if (hour < 5) return "Good night";
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

export function HomeClock({ alarms }: Props) {
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    const tick = () => setNow(new Date());
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  // Render skeleton on first render (SSR / before useEffect runs) to avoid hydration mismatch.
  if (!now) {
    return (
      <div>
        <div className="text-[11px] opacity-55 tracking-wide">&nbsp;</div>
        <div className="text-5xl font-bold tabular-nums tracking-tight text-cream leading-none">
          --<span className="text-sage">:</span>--
        </div>
      </div>
    );
  }

  const hh = now.getHours().toString().padStart(2, "0");
  const mm = now.getMinutes().toString().padStart(2, "0");
  const ss = now.getSeconds().toString().padStart(2, "0");
  const greeting = getGreeting(now.getHours());

  const next = getNextAlarm(alarms, now);

  return (
    <div>
      <div className="text-[11px] opacity-55 tracking-wide mb-0.5">{greeting}</div>
      <div className="flex items-baseline gap-2">
        <div className="text-5xl font-bold tabular-nums tracking-tight text-cream leading-none">
          {hh}<span className="text-sage">:</span>{mm}
        </div>
        <div className="inline-flex items-center gap-1.5 text-[11px] font-medium opacity-70">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-sage animate-pulse-soft shadow-[0_0_8px_hsl(var(--sage))]" />
          {ss}s
        </div>
      </div>
      {next && (
        <div className="text-[9px] opacity-50 mt-2 tracking-[0.1em] uppercase">
          Next alarm in {formatDurationUntil(next.firesAt, now)}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Add the `pulse-soft` animation in globals.css**

Append to `frontend/app/globals.css` (after the existing `@media` block):

```css
@keyframes pulseSoft {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.animate-pulse-soft {
  animation: pulseSoft 1s ease-in-out infinite;
}
```

- [ ] **Step 3: Verify lint + build**

```powershell
cd frontend; npm run lint; npm run build
```
Expected: both pass.

- [ ] **Step 4: Commit**

```powershell
git add frontend/app/components/HomeClock.tsx frontend/app/globals.css
git commit -m "feat: add HomeClock component with live seconds indicator"
```

---

## Task 4: `EmptyAlarmsState` component

A small soft card shown when no alarms exist. Moon glyph + "No alarms set" + helper text.

**Files:**
- Create: `frontend/app/components/EmptyAlarmsState.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/app/components/EmptyAlarmsState.tsx
"use client";

import { Moon } from "lucide-react";

export function EmptyAlarmsState() {
  return (
    <div className="mt-10 rounded-3xl border border-dashed border-sage/25 bg-sage/[0.04] py-10 px-6 text-center">
      <Moon className="mx-auto mb-2 h-7 w-7 text-sage/70" />
      <div className="text-sm font-semibold text-cream">No alarms set</div>
      <div className="mt-1 text-[11px] opacity-55 leading-relaxed">
        Tap + to add your first one.
        <br />
        Sleep tight.
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify lint**

```powershell
cd frontend; npm run lint
```
Expected: passes.

- [ ] **Step 3: Commit**

```powershell
git add frontend/app/components/EmptyAlarmsState.tsx
git commit -m "feat: add EmptyAlarmsState component"
```

---

## Task 5: `AlarmCard` component

Replaces the inline `<Card>` markup at lines 169–211 of `page.tsx`. Shows time, days, badges (sunrise / fade), enable toggle, tap-to-edit. The featured/tinted variant is used for the next-upcoming alarm.

**Files:**
- Create: `frontend/app/components/AlarmCard.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/app/components/AlarmCard.tsx
"use client";

import { Sunrise, Lightbulb } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import type { Alarm } from "@/utils/api";
import { cn } from "@/lib/utils";

interface Props {
  alarm: Alarm;
  featured?: boolean;
  onToggleEnabled: (alarm: Alarm) => void;
  onEdit: (alarm: Alarm) => void;
}

const dayShort = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function formatDays(days: number[]): string {
  if (days.length === 0) return "Once";
  if (days.length === 7) return "Daily";
  // Mon–Fri shortcut
  const isWeekdays = days.length === 5 && [0, 1, 2, 3, 4].every((d) => days.includes(d));
  if (isWeekdays) return "Weekdays";
  // Sat–Sun shortcut
  const isWeekends = days.length === 2 && [5, 6].every((d) => days.includes(d));
  if (isWeekends) return "Weekends";
  return [...days].sort((a, b) => a - b).map((d) => dayShort[d]).join(" · ");
}

export function AlarmCard({ alarm, featured, onToggleEnabled, onEdit }: Props) {
  const enabled = alarm.enabled;
  const showSunrise = alarm.light && alarm.light_fade_minutes > 0;
  const showLight = alarm.light && !showSunrise;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onEdit(alarm)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onEdit(alarm);
        }
      }}
      className={cn(
        "rounded-3xl p-4 mt-3 cursor-pointer transition-all border",
        featured
          ? "bg-sage/[0.07] border-sage/20"
          : "bg-card border-sage/[0.08]",
        !enabled && "opacity-55"
      )}
    >
      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0">
          <div className="text-2xl font-bold tabular-nums tracking-tight text-cream">
            {alarm.time}
          </div>
          <div className="text-[10px] opacity-60 mt-0.5">{formatDays(alarm.days_of_week)}</div>
          {(showSunrise || showLight || alarm.label) && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {showSunrise && (
                <span className="inline-flex items-center gap-1 text-[9px] font-semibold bg-sage/15 text-sage px-2 py-0.5 rounded-md">
                  <Sunrise className="h-2.5 w-2.5" />
                  Sunrise · {alarm.light_fade_minutes} min
                </span>
              )}
              {showLight && (
                <span className="inline-flex items-center gap-1 text-[9px] font-semibold bg-sage/15 text-sage px-2 py-0.5 rounded-md">
                  <Lightbulb className="h-2.5 w-2.5" />
                  Light
                </span>
              )}
              {alarm.label && (
                <span className="text-[9px] font-medium opacity-65 px-1 py-0.5">
                  {alarm.label}
                </span>
              )}
            </div>
          )}
        </div>
        <div onClick={(e) => e.stopPropagation()}>
          <Switch
            checked={enabled}
            onCheckedChange={() => onToggleEnabled(alarm)}
            aria-label={enabled ? "Disable alarm" : "Enable alarm"}
          />
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify lint + build**

```powershell
cd frontend; npm run lint; npm run build
```
Expected: both pass.

- [ ] **Step 3: Commit**

```powershell
git add frontend/app/components/AlarmCard.tsx
git commit -m "feat: add AlarmCard component"
```

---

## Task 6: Refactor `page.tsx` to use the new components

Wire HomeClock + AlarmCard + EmptyAlarmsState. Replace the centered title and full-width Add button with the new layout: clock at the top, list of cards, FAB at bottom-right.

**Files:**
- Modify: `frontend/app/page.tsx`

- [ ] **Step 1: Replace `page.tsx` contents**

Overwrite `frontend/app/page.tsx` with:

```tsx
"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import {
  Alarm,
  fetchAlarms,
  deleteAlarm,
  updateAlarm,
} from "@/utils/api";
import { Plus, Loader2 } from "lucide-react";
import { useTheme } from "next-themes";
import { useToast } from "@/hooks/use-toast";
import { Toaster } from "@/components/ui/toaster";
import AlarmDrawer from "./components/AlarmDrawer";
import { HomeClock } from "./components/HomeClock";
import { AlarmCard } from "./components/AlarmCard";
import { EmptyAlarmsState } from "./components/EmptyAlarmsState";
import { getNextAlarm } from "@/lib/nextAlarm";

export default function Home() {
  const [alarms, setAlarms] = useState<Alarm[]>([]);
  const [editingAlarm, setEditingAlarm] = useState<Alarm | null>(null);
  const [showDrawer, setShowDrawer] = useState(false);
  const [loading, setLoading] = useState<boolean>(false);
  const { setTheme } = useTheme();
  const { toast } = useToast();

  const loadAlarms = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchAlarms();
      setAlarms(data);
    } catch (error) {
      console.error("Failed to load alarms:", error);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to load alarms.",
        duration: 3000,
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    setTheme("dark");
    loadAlarms();
  }, [loadAlarms, setTheme]);

  async function handleDelete(id: string) {
    setLoading(true);
    try {
      await deleteAlarm(id);
      await loadAlarms();
      toast({ title: "Success", description: "Alarm deleted" });
    } catch (error) {
      console.error("Failed to delete alarm:", error);
      toast({ variant: "destructive", title: "Error", description: "Failed to delete alarm" });
    } finally {
      setLoading(false);
    }
  }

  function handleEdit(alarm: Alarm) {
    setEditingAlarm(alarm);
    setShowDrawer(true);
  }

  function handleFormClose() {
    setEditingAlarm(null);
    setShowDrawer(false);
    loadAlarms();
  }

  async function handleToggleEnabled(alarm: Alarm) {
    try {
      await updateAlarm(alarm.id, {
        ...alarm,
        days_of_week: alarm.days_of_week,
        enabled: !alarm.enabled,
        light: alarm.light,
        light_fade_minutes: alarm.light_fade_minutes,
      });
      await loadAlarms();
    } catch (error) {
      console.error("Failed to toggle alarm:", error);
      toast({ variant: "destructive", title: "Error", description: "Failed to update alarm" });
    }
  }

  function handleAddNew() {
    setEditingAlarm({} as Alarm);
    setShowDrawer(true);
  }

  // Sort alarms by upcoming firing so the soonest one is first.
  const sortedAlarms = useMemo(() => {
    const featuredId = getNextAlarm(alarms)?.alarm.id;
    return {
      list: [...alarms].sort((a, b) => {
        if (a.id === featuredId) return -1;
        if (b.id === featuredId) return 1;
        return a.time.localeCompare(b.time);
      }),
      featuredId,
    };
  }, [alarms]);

  return (
    <div className="container mx-auto p-4 pb-24 max-w-md">
      <Toaster />
      <HomeClock alarms={alarms} />

      <div className="mt-6">
        {loading && alarms.length === 0 ? (
          <div className="flex justify-center items-center mt-16">
            <Loader2 className="animate-spin h-7 w-7 text-sage/70" />
          </div>
        ) : alarms.length === 0 ? (
          <EmptyAlarmsState />
        ) : (
          <div>
            {sortedAlarms.list.map((alarm) => (
              <AlarmCard
                key={alarm.id}
                alarm={alarm}
                featured={alarm.id === sortedAlarms.featuredId && alarm.enabled}
                onToggleEnabled={handleToggleEnabled}
                onEdit={handleEdit}
              />
            ))}
          </div>
        )}
      </div>

      {/* FAB */}
      <button
        onClick={handleAddNew}
        aria-label="Add new alarm"
        className="fixed right-5 z-40 grid place-items-center w-14 h-14 rounded-full bg-sage text-background shadow-[0_8px_22px_hsl(var(--sage)/0.3)] active:scale-95 transition-transform"
        style={{ bottom: "calc(5rem + env(safe-area-inset-bottom, 0px))" }}
      >
        <Plus className="h-6 w-6" strokeWidth={2.5} />
      </button>

      {/* Drawer for create/edit */}
      {editingAlarm && (
        <AlarmDrawer
          alarm={editingAlarm}
          open={showDrawer}
          onClose={handleFormClose}
          onDelete={editingAlarm.id ? () => handleDelete(editingAlarm.id) : undefined}
        />
      )}
    </div>
  );
}
```

Note: `AlarmDrawer` now takes an optional `onDelete` prop — we'll wire it in the next task.

- [ ] **Step 2: Verify lint + build**

```powershell
cd frontend; npm run lint; npm run build
```
Expected: both pass. (May error temporarily because AlarmDrawer doesn't accept `onDelete` yet — if so, that's OK; Task 8 will fix it. But it should still build because TS allows extra props on components when they're spread or ignored. If TS errors here, comment out the `onDelete` prop temporarily and re-enable in Task 8.)

If build fails on the `onDelete` prop, drop that prop from this step and re-add in Task 8 step 1 instead.

- [ ] **Step 3: Manual dev-server check**

```powershell
cd frontend; npm run dev
```

Open `http://localhost:3000` in a browser. Verify:
- New charcoal background, sage colon in clock, pulsing dot
- "Next alarm in …" only shows when an alarm is enabled
- Empty state appears when no alarms exist (toggle all off via API or temporarily delete)
- FAB sits bottom-right above the tab bar; tapping opens the (still-old) drawer

- [ ] **Step 4: Commit**

```powershell
git add frontend/app/page.tsx
git commit -m "feat: refactor home page to new card-based layout with FAB"
```

---

## Task 7: `TimeWheelPicker` component

Two scrolling columns (hours / minutes) with scroll-snap. Center selection visualized with two faint sage horizontal lines. Items dim by distance from center. ~120 LOC, no new deps.

**Files:**
- Create: `frontend/app/components/TimeWheelPicker.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/app/components/TimeWheelPicker.tsx
"use client";

import { useEffect, useRef, useState, forwardRef } from "react";

const ITEM_HEIGHT = 36;
const VISIBLE_ITEMS = 5;
const COLUMN_HEIGHT = ITEM_HEIGHT * VISIBLE_ITEMS; // 180
const PADDING = (COLUMN_HEIGHT - ITEM_HEIGHT) / 2; // 72

interface Props {
  hour: number;
  minute: number;
  onChange: (hour: number, minute: number) => void;
}

export function TimeWheelPicker({ hour, minute, onChange }: Props) {
  return (
    <div
      className="relative bg-card rounded-2xl border border-sage/10 px-4"
      style={{ height: COLUMN_HEIGHT }}
    >
      {/* center selection lines */}
      <div
        className="pointer-events-none absolute left-4 right-4 h-px bg-sage/25"
        style={{ top: "calc(50% - 18px)" }}
      />
      <div
        className="pointer-events-none absolute left-4 right-4 h-px bg-sage/25"
        style={{ top: "calc(50% + 18px)" }}
      />

      <div className="flex items-center justify-center h-full gap-3">
        <WheelColumn
          count={24}
          value={hour}
          onValueChange={(h) => onChange(h, minute)}
        />
        <div
          className="text-3xl text-sage font-semibold pb-1 select-none"
          aria-hidden
        >
          :
        </div>
        <WheelColumn
          count={60}
          value={minute}
          onValueChange={(m) => onChange(hour, m)}
        />
      </div>
    </div>
  );
}

interface ColumnProps {
  count: number;
  value: number;
  onValueChange: (n: number) => void;
}

function WheelColumn({ count, value, onValueChange }: ColumnProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [centerIndex, setCenterIndex] = useState(value);
  const programmaticScrollUntil = useRef(0);

  // Set initial scroll position; suppress scroll handler briefly so we don't fire a redundant onChange.
  useEffect(() => {
    if (!ref.current) return;
    programmaticScrollUntil.current = Date.now() + 300;
    ref.current.scrollTop = value * ITEM_HEIGHT;
    setCenterIndex(value);
    // We intentionally only run when `value` changes from outside; tracked via ref to avoid loops.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  function handleScroll() {
    if (!ref.current) return;
    const idx = Math.round(ref.current.scrollTop / ITEM_HEIGHT);
    const clamped = Math.max(0, Math.min(count - 1, idx));
    setCenterIndex(clamped);
    if (Date.now() < programmaticScrollUntil.current) return;
    if (clamped !== value) onValueChange(clamped);
  }

  return (
    <div
      ref={ref}
      onScroll={handleScroll}
      className="overflow-y-scroll snap-y snap-mandatory no-scrollbar"
      style={{
        height: COLUMN_HEIGHT,
        width: 56,
        scrollbarWidth: "none",
      }}
    >
      <div style={{ paddingTop: PADDING, paddingBottom: PADDING }}>
        {Array.from({ length: count }, (_, i) => {
          const distance = Math.abs(i - centerIndex);
          let opacity = 1;
          if (distance === 1) opacity = 0.5;
          else if (distance === 2) opacity = 0.25;
          else if (distance > 2) opacity = 0.1;
          return (
            <div
              key={i}
              className="snap-center flex items-center justify-center text-2xl font-medium tabular-nums select-none"
              style={{
                height: ITEM_HEIGHT,
                opacity,
                color: distance === 0 ? "hsl(var(--cream))" : undefined,
              }}
            >
              {i.toString().padStart(2, "0")}
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add `no-scrollbar` utility**

Append to `frontend/app/globals.css`:

```css
.no-scrollbar::-webkit-scrollbar { display: none; }
.no-scrollbar { -ms-overflow-style: none; }
```

- [ ] **Step 3: Verify lint + build**

```powershell
cd frontend; npm run lint; npm run build
```
Expected: both pass.

- [ ] **Step 4: Commit**

```powershell
git add frontend/app/components/TimeWheelPicker.tsx frontend/app/globals.css
git commit -m "feat: add TimeWheelPicker component"
```

---

## Task 8: Rework `AlarmDrawer.tsx`

Replace the time input with `TimeWheelPicker`. Remove the explicit Repeat / Light / Enabled toggles per the spec — selecting days enables repeat; sunrise minutes > 0 implies light is on. Add a Delete button (only visible in edit mode).

**Files:**
- Modify: `frontend/app/components/AlarmDrawer.tsx`

- [ ] **Step 1: Replace `AlarmDrawer.tsx` contents**

Overwrite `frontend/app/components/AlarmDrawer.tsx` with:

```tsx
"use client";

import { useState, FormEvent, useMemo } from "react";
import { createAlarm, updateAlarm, Alarm } from "@/utils/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Loader2, Trash2, Sunrise } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { TimeWheelPicker } from "./TimeWheelPicker";
import { cn } from "@/lib/utils";

interface AlarmDrawerProps {
  alarm: Partial<Alarm>;
  open: boolean;
  onClose: () => void;
  onDelete?: () => void;
}

const dayShort = ["M", "T", "W", "T", "F", "S", "S"];

export default function AlarmDrawer({ alarm, open, onClose, onDelete }: AlarmDrawerProps) {
  const defaultTime = useMemo(() => {
    if (alarm.time) return alarm.time;
    const oneMinuteLater = new Date(Date.now() + 60_000);
    const hh = String(oneMinuteLater.getHours()).padStart(2, "0");
    const mm = String(oneMinuteLater.getMinutes()).padStart(2, "0");
    return `${hh}:${mm}`;
  }, [alarm.time]);

  const [hour, minute] = useMemo(() => {
    const [h, m] = defaultTime.split(":").map(Number);
    return [h ?? 7, m ?? 0];
  }, [defaultTime]);

  const { toast } = useToast();
  const [formData, setFormData] = useState({
    hour,
    minute,
    days_of_week: alarm.days_of_week || [],
    label: alarm.label || "Wake up",
    light_fade_minutes: alarm.light_fade_minutes ?? 0,
  });

  const [submitting, setSubmitting] = useState(false);

  function handleTimeChange(h: number, m: number) {
    setFormData((prev) => ({ ...prev, hour: h, minute: m }));
  }

  function handleDayToggle(index: number) {
    setFormData((prev) => {
      const has = prev.days_of_week.includes(index);
      const updated = has
        ? prev.days_of_week.filter((d) => d !== index)
        : [...prev.days_of_week, index].sort((a, b) => a - b);
      return { ...prev, days_of_week: updated };
    });
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const time = `${String(formData.hour).padStart(2, "0")}:${String(formData.minute).padStart(2, "0")}`;
      const lightOn = formData.light_fade_minutes > 0;
      const dataToSubmit = {
        time,
        days_of_week: formData.days_of_week,
        enabled: alarm.id ? alarm.enabled ?? true : true,
        label: formData.label,
        repeat_type: formData.days_of_week.length > 0 ? "weekly" : "once",
        light: lightOn,
        light_fade_minutes: formData.light_fade_minutes,
      };

      if (alarm.id) {
        await updateAlarm(alarm.id, dataToSubmit);
        toast({ title: "Saved", description: "Alarm updated" });
      } else {
        await createAlarm(dataToSubmit);
        toast({ title: "Saved", description: "Alarm created" });
      }
      onClose();
    } catch (error) {
      console.error("Failed to save alarm:", error);
      toast({ variant: "destructive", title: "Error", description: "Failed to save alarm" });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent
        side="bottom"
        className="h-auto max-h-[92vh] overflow-auto rounded-t-3xl border-t border-sage/10"
        style={{ paddingBottom: "calc(1rem + env(safe-area-inset-bottom, 0px))" }}
      >
        <SheetHeader>
          <SheetTitle className="text-center">
            {alarm.id ? "Edit alarm" : "New alarm"}
          </SheetTitle>
        </SheetHeader>

        <form onSubmit={handleSubmit} className="space-y-4 mt-4">
          {/* Hero wheel picker */}
          <TimeWheelPicker
            hour={formData.hour}
            minute={formData.minute}
            onChange={handleTimeChange}
          />

          {/* Repeat (day pills) */}
          <div>
            <div className="text-[9px] opacity-55 tracking-[0.12em] uppercase font-semibold mt-3 mb-2">
              Repeat
            </div>
            <div className="flex justify-between gap-1">
              {dayShort.map((d, i) => {
                const on = formData.days_of_week.includes(i);
                return (
                  <button
                    key={i}
                    type="button"
                    onClick={() => handleDayToggle(i)}
                    className={cn(
                      "w-9 h-9 rounded-full text-[11px] font-semibold transition-colors",
                      on
                        ? "bg-sage text-background"
                        : "bg-card border border-sage/[0.08] text-foreground/80"
                    )}
                  >
                    {d}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Label */}
          <div>
            <Label htmlFor="label" className="text-[9px] opacity-55 tracking-[0.12em] uppercase font-semibold">
              Label
            </Label>
            <Input
              id="label"
              value={formData.label}
              onChange={(e) => setFormData((p) => ({ ...p, label: e.target.value }))}
              placeholder="Wake up"
              className="mt-1.5 bg-card border-sage/[0.08]"
            />
          </div>

          {/* Sunrise fade */}
          <div>
            <Label htmlFor="light_fade_minutes" className="text-[9px] opacity-55 tracking-[0.12em] uppercase font-semibold flex items-center gap-1.5">
              <Sunrise className="h-3 w-3" />
              Sunrise fade
            </Label>
            <Select
              value={String(formData.light_fade_minutes)}
              onValueChange={(val) =>
                setFormData((p) => ({ ...p, light_fade_minutes: Number(val) }))
              }
            >
              <SelectTrigger id="light_fade_minutes" className="mt-1.5 bg-card border-sage/[0.08]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="0">Off</SelectItem>
                <SelectItem value="5">5 min</SelectItem>
                <SelectItem value="10">10 min</SelectItem>
                <SelectItem value="15">15 min</SelectItem>
                <SelectItem value="20">20 min</SelectItem>
                <SelectItem value="30">30 min</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Save */}
          <Button
            type="submit"
            disabled={submitting}
            className="w-full mt-2 bg-sage text-background hover:bg-sage/90 font-bold rounded-2xl py-6"
          >
            {submitting ? (
              <Loader2 className="animate-spin h-4 w-4" />
            ) : alarm.id ? (
              "Save changes"
            ) : (
              "Create alarm"
            )}
          </Button>

          {/* Delete (edit mode only) */}
          {alarm.id && onDelete && (
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                onDelete();
                onClose();
              }}
              className="w-full text-destructive/80 hover:text-destructive hover:bg-destructive/10 font-medium"
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Delete alarm
            </Button>
          )}
        </form>
      </SheetContent>
    </Sheet>
  );
}
```

- [ ] **Step 2: Verify lint + build**

```powershell
cd frontend; npm run lint; npm run build
```
Expected: both pass.

- [ ] **Step 3: Manual dev-server smoke test**

```powershell
cd frontend; npm run dev
```

Open `http://localhost:3000`. Verify:
- Tap FAB → bottom sheet opens with wheel picker showing default time
- Scroll hour column → minute stays put, hour value updates; release snaps to nearest
- Scroll minute column independently
- Tap a day pill → fills sage; tap again → un-fills
- Pick a sunrise fade > 0 from the select
- Tap "Create alarm" → toast appears, sheet closes, new alarm shows on home page
- Tap an existing alarm card → sheet opens in edit mode with values populated; the Delete button appears at the bottom
- Tap Delete → toast, sheet closes, alarm removed

- [ ] **Step 4: Commit**

```powershell
git add frontend/app/components/AlarmDrawer.tsx
git commit -m "feat: rework AlarmDrawer with wheel picker and simplified fields"
```

---

## Task 9: Final polish + verification

A sweep to catch anything missed: full lint, full build, manual PWA-mode check on a phone or simulator if available.

**Files:** none changed unless polish issues appear.

- [ ] **Step 1: Full lint**

```powershell
cd frontend; npm run lint
```
Expected: passes with zero errors and zero warnings.

- [ ] **Step 2: Full build**

```powershell
cd frontend; npm run build
```
Expected: build succeeds, no type errors.

- [ ] **Step 3: Manual smoke test against acceptance criteria**

Run `npm run dev` and verify each acceptance criterion from the spec:

1. Home page shows a sage-tinted live seconds indicator that pulses every second. ✓
2. "Next alarm in …" is hidden when no alarms are enabled; empty-state card replaces the alarm list. ✓ (toggle all alarms off via API or temporarily disable, or seed an empty DB)
3. Featured/tinted card visually highlights the next-upcoming-firing alarm; others are default-style. ✓
4. The Add Alarm sheet uses the wheel picker; scrolling each column updates the time live. ✓
5. The Repeat-toggle and Light-on toggle are removed; behavior is implicit from day selection and sunrise minutes. ✓
6. Charcoal × Sage palette applies app-wide; no leftover blue/`primary` from the previous theme is visible. (Check Logs and Network pages — they should inherit the new theme automatically since they use shadcn primitives.)
7. iOS PWA still respects safe-area insets (existing behavior preserved). ✓
8. `npm run build` and `npm run lint` both pass. ✓

If any criterion fails, fix it inline and commit. Document fixes briefly in commit messages.

- [ ] **Step 4: Final commit if any polish was needed**

```powershell
git add frontend/...
git commit -m "polish: <what was tweaked>"
```

If nothing needed polish, skip this step.

---

## Self-Review

**Spec coverage check:**

| Spec section | Implemented in |
| --- | --- |
| Charcoal × Sage palette | Task 1 |
| Manifest theme color | Task 1 |
| Home — greeting | Task 3 |
| Home — clock with seconds | Task 3 |
| Home — pulsing dot animation | Task 3 |
| Home — conditional "Next alarm in …" | Task 3 (uses `nextAlarm` from Task 2) |
| Home — featured/tinted card | Task 5 + Task 6 (selection logic) |
| Home — alarm cards (toggle, badges) | Task 5 |
| Home — empty state | Task 4 |
| Home — FAB | Task 6 |
| Add Alarm — wheel picker | Tasks 7, 8 |
| Add Alarm — implicit repeat from days | Task 8 |
| Add Alarm — implicit light from sunrise | Task 8 |
| Add Alarm — delete from sheet | Task 8 |
| Sage-color toggle/save styling | Tasks 5, 8 |
| iOS PWA safe area | preserved (existing CSS in globals.css) |
| Lint + build acceptance | Task 9 |

All sections covered.

**Placeholder / red-flag scan:** No "TBD"/"TODO"/"add appropriate handling" placeholders. Every code step shows real code. Type names (`Alarm`, `NextAlarm`, `Props`) and method names (`getNextAlarm`, `handleToggleEnabled`, `onChange`, `onValueChange`) are consistent across tasks.

**One known caveat:** Task 6 step 2 calls out a possible TS error if `AlarmDrawer` doesn't yet accept the `onDelete` prop. The remediation (drop the prop, re-add in Task 8) is explicit. This is the only inter-task ordering hazard.

---

## Execution Handoff

This plan is complete and saved to `docs/superpowers/plans/2026-05-10-ui-rework-implementation.md`. Two execution options:

1. **Subagent-Driven** — fresh subagent per task with review checkpoints
2. **Inline Execution** — execute tasks in this session via executing-plans, batched with checkpoints

The user already authorized direct implementation ("go ahead and implement that") — proceeding with Inline Execution unless directed otherwise.
