# UI rework — Charcoal × Sage with Hero Card + Wheel Picker

**Date:** 2026-05-10
**Branch:** `feat/ui-rework-charcoal-sage`
**Scope:** Visual + interaction overhaul of the Strafwecker frontend (Next.js / Tailwind / shadcn). Mobile-first, optimized for the iOS PWA experience already wired up.

## Goals

1. Replace the generic shadcn-default look with a deliberate, calm "bedside" aesthetic.
2. Mobile-first; works equally well in the browser and as an installed iOS PWA.
3. Always-visible **seconds** indicator on the home page.
4. Friendly **empty state** when no alarms exist.
5. Refined **Add Alarm** sheet using a wheel-style time picker.

Out of scope: backend changes, alarm logic, network logic, the Logs/Network pages' content (they inherit the new theme but no layout changes).

## Visual language — "Charcoal × Sage"

| Token         | Value      | Used for                                          |
| ------------- | ---------- | ------------------------------------------------- |
| `--bg`        | `#161616`  | App background (solid, OLED-friendly)             |
| `--card`      | `#232323`  | Default alarm cards, fields                       |
| `--card-hi`   | `#2A2A2A`  | Tinted/featured card (next-up alarm)              |
| `--accent`    | `#9FD4B5`  | Sage accent (toggles, FAB, day pills, save btn)   |
| `--accent-soft` | `rgba(159,212,181,0.18)` | Subtle accent fills (pills, borders) |
| `--text`      | `#E8E0D0`  | Primary cream body text                           |
| `--cream`     | `#F0E8D8`  | Brighter cream — clock numerals, time displays    |
| `--text-muted` | `rgba(232,224,208,0.55)` | Secondary text, labels             |

- Cards: `border-radius: 22px` (alarm cards), `16px` (fields), `12px` (toggles, day pills are circular).
- Card border: `1px solid rgba(159,212,181,0.08)` for default cards, `0.18` for the featured/tinted card.
- Typography: native system stack (already in use). Numerals use `font-feature-settings: "tnum"` for stable widths.
- The day-of-week selector is a row of 7 circular pills (28px), filled sage when selected.

Light mode: not in scope for this pass. Dark mode is forced (existing behavior preserved).

## Home page (`app/page.tsx`)

```
┌─────────────────────────────────────┐
│ Good morning                        │  ← greeting
│ 07:42  ●18s ←pulsing sage dot       │  ← clock with seconds indicator
│ NEXT ALARM IN 22H 18M               │  ← only when at least one enabled alarm
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ 06:30                       ●→  │ │  ← featured (tinted) card = next-up
│ │ Weekdays                        │ │
│ │ ☀ Sunrise · 15 min              │ │
│ └─────────────────────────────────┘ │
│ ┌─────────────────────────────────┐ │
│ │ 08:00                       ●   │ │  ← regular card
│ │ Weekends                        │ │
│ └─────────────────────────────────┘ │
│                                ╭─╮  │  ← FAB (sage circle)
│                                │+│  │
│                                ╰─╯  │
└─────────────────────────────────────┘
       [ Home   Logs   Net ]            ← existing bottom tab bar
```

**Components:**

- **Greeting** — "Good morning" / "Good afternoon" / "Good evening" based on local hour.
- **Clock** — `HH:MM` in cream, sage colon. Beside it, an inline pill with a pulsing sage dot and `:SSs` text (animated 1s pulse).
- **Next alarm in** — only shown when there is at least one enabled alarm. Computed from sorted upcoming firings. Hidden in the empty state.
- **Alarm cards** — first enabled card gets `tinted` style (lighter background, sage border tint). Toggling enabled flips the switch and updates the API. Tap card body to edit. Long-press / swipe is not in scope.
- **Pills** — small `accent-soft` chips on each card to indicate "Sunrise", "15 min", "Light only" (when applicable).
- **FAB** — fixed bottom-right (with safe-area inset), sage circle with `+`. Opens the Add Alarm sheet.
- **Empty state** — replaces the whole alarm list with a soft card: moon glyph + "No alarms set" + "Tap + to add your first one."

Edit and delete actions: keep current behavior (edit opens sheet pre-filled; delete still uses the trash button on the card). Move them into the card menu rather than visible icons — a small overflow `⋯` button on each card opens a tiny popover with Edit / Delete. (This declutters the card, which is the main visual win.)

## Add Alarm sheet (`AlarmDrawer.tsx`)

A bottom sheet (`vaul` is already a dep) using the Hero-Card-with-Wheel-Picker pattern.

```
┌─────────────────────────────────────┐
│            ─────                    │  ← grabber
│            New alarm                │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │                                 │ │
│ │       06    :    30             │ │  ← wheel picker (3 visible)
│ │     center   with  scroll       │ │     hour wheel + minute wheel
│ │                                 │ │
│ └─────────────────────────────────┘ │
│                                     │
│ REPEAT                              │
│  M  T  W  T  F  S  S                │  ← circle pills, sage when on
│                                     │
│ ┌─ Label ─────────── Wake up   ›─┐ │
│ ┌─ ☀ Sunrise fade ── 15 min    ›─┐ │
│                                     │
│ ┌─────── Save alarm ─────────────┐ │  ← sage button
└─────────────────────────────────────┘
```

**Components:**

- **Grabber + title** — standard sheet affordances.
- **Hero wheel card** — replaces the current `<input type="time">`. Two scroll columns (hours 00–23, minutes 00–59), with the center selection highlighted by two faint sage horizontal lines and the center number drawn larger and brighter than its neighbors. Snap-on-scroll (CSS `scroll-snap-type: y mandatory`). Touch + wheel scrolling on desktop.
- **Repeat row** — kept compact. 7 day pills inline. The "Repeat" toggle from the current form is removed — selecting at least one day implicitly enables repeat; selecting none means "Once".
- **Label field** — single-line input on a separate line below.
- **Sunrise fade field** — kept as a select trigger (uses existing shadcn Select). Light on/off is implicit: if Sunrise > 0 minutes, light is enabled. The redundant "Activate Light" toggle from the current form is removed.
- **Save** — sage primary button. Loading state uses spinner.

The "Enabled" switch in the current form is removed entirely — newly created alarms are always enabled, and you toggle existing alarms on the home card.

## Wheel picker — implementation notes

A standalone `<TimeWheelPicker>` component (`app/components/TimeWheelPicker.tsx`):

- Two scrollable columns rendered as `<div>` lists.
- Each column has top/bottom padding equal to (column-height − item-height) / 2 so the first/last item can sit in the center slot.
- `scroll-snap-type: y mandatory; scroll-snap-align: center` on each item.
- On scroll, debounce ~80ms then read `scrollTop`, divide by item-height to get the index, call `onChange(hour, minute)`.
- Items more than 1 step away from center are dimmed via opacity (0.25 → 0.5 → 1 → 0.5 → 0.25).
- The two faint sage selection lines are absolutely-positioned siblings of the columns, not part of the items.

No external dep. ~120 LOC.

## Color/theming integration

Replace the dark-mode CSS variables in `frontend/app/globals.css` with the Charcoal × Sage tokens. Light-mode tokens stay (we're not deleting them) but are unused since the layout forces dark mode.

Tailwind utility usage: keep using existing shadcn semantic classes (`bg-card`, `text-foreground`, etc.) so nothing else has to change — they automatically pick up the new HSL values via the `:root.dark` variables.

The PWA manifest's `theme_color` and `background_color` change from `#0D1929` → `#161616` to match.

## Out-of-scope but worth noting

- The clock's "next alarm in" text is computed client-side. We already have `alarm.time` and `alarm.days_of_week` and `alarm.enabled`; the calculation is straightforward and doesn't need new backend endpoints.
- The card overflow menu is implemented with shadcn's existing primitives (`Popover` + `Button`). We'll need to add `@radix-ui/react-popover` if it's not present (it isn't — see package.json — so add it).

## Acceptance criteria

1. Home page shows a sage-tinted live seconds indicator that pulses every second.
2. "Next alarm in …" is hidden when no alarms are enabled; an empty-state card replaces the alarm list.
3. Featured/tinted card visually highlights the next-upcoming-firing alarm; others are default-style.
4. The Add Alarm sheet uses the wheel picker; scrolling each column updates the time live.
5. The Repeat-toggle and Light-on toggle are removed; behavior is implicit from day selection and sunrise minutes.
6. Charcoal × Sage palette applies app-wide; no leftover blue/`primary` from the previous theme is visible.
7. iOS PWA still respects the safe-area insets (existing behavior preserved).
8. `npm run build` and `npm run lint` both pass.
