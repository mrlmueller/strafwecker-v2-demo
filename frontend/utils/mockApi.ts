/**
 * In-memory mock data layer for local UI development.
 *
 * Activated when NEXT_PUBLIC_USE_MOCK_API === "true" — see utils/api.ts.
 * Mutations persist in module-level state for the lifetime of the dev server
 * (HMR may reset on certain edits; that's fine, it just reseeds).
 */

import type {
  Alarm,
  Log,
  NetworkLog,
  MonitorLog,
  RebootHistory,
} from "./api";

// Use globalThis to survive Next.js HMR module re-evaluation in dev.
declare global {
  var __mockAlarms: Alarm[] | undefined;
}

function seedAlarms(): Alarm[] {
  return [
    {
      id: "mock-1",
      time: "06:30",
      days_of_week: [0, 1, 2, 3, 4],
      enabled: true,
      repeat_type: "weekly",
      label: "Wake up",
      light: true,
      light_fade_minutes: 15,
      kind: "alarm",
      nap_target_at: null,
      nap_duration_minutes: null,
      esp32_button: true,
    },
    {
      id: "mock-2",
      time: "08:00",
      days_of_week: [5, 6],
      enabled: true,
      repeat_type: "weekly",
      label: "Lazy morning",
      light: false,
      light_fade_minutes: 0,
      kind: "alarm",
      nap_target_at: null,
      nap_duration_minutes: null,
      esp32_button: true,
    },
    {
      id: "mock-3",
      time: "22:30",
      days_of_week: [],
      enabled: false,
      repeat_type: "once",
      label: "Bedtime test",
      light: false,
      light_fade_minutes: 0,
      kind: "alarm",
      nap_target_at: null,
      nap_duration_minutes: null,
      esp32_button: true,
    },
  ];
}

if (!globalThis.__mockAlarms) {
  globalThis.__mockAlarms = seedAlarms();
}

function delay(ms = 120) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms));
}

function nextId(): string {
  return `mock-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
}

export const mockApi = {
  async fetchAlarms(): Promise<Alarm[]> {
    await delay();
    return [...(globalThis.__mockAlarms ?? [])];
  },

  async fetchAlarm(id: string): Promise<Alarm> {
    await delay();
    const found = (globalThis.__mockAlarms ?? []).find((a) => a.id === id);
    if (!found) throw new Error(`Mock alarm ${id} not found`);
    return { ...found };
  },

  async createAlarm(data: Omit<Alarm, "id">): Promise<{ message: string; id: string }> {
    await delay();
    const id = nextId();
    const alarm: Alarm = {
      id,
      time: data.time,
      days_of_week: data.days_of_week,
      enabled: data.enabled ?? true,
      repeat_type: data.repeat_type ?? (data.days_of_week.length > 0 ? "weekly" : "once"),
      label: data.label ?? "",
      light: Boolean(data.light),
      light_fade_minutes: data.light_fade_minutes ?? 0,
      kind: data.kind ?? "alarm",
      nap_target_at: data.nap_target_at ?? null,
      nap_duration_minutes: data.nap_duration_minutes ?? null,
      esp32_button: data.esp32_button ?? true,
    };
    globalThis.__mockAlarms = [...(globalThis.__mockAlarms ?? []), alarm];
    return { message: "ok (mock)", id };
  },

  async updateAlarm(id: string, data: Partial<Alarm>): Promise<{ message: string }> {
    await delay();
    const alarms = globalThis.__mockAlarms ?? [];
    const idx = alarms.findIndex((a) => a.id === id);
    if (idx === -1) throw new Error(`Mock alarm ${id} not found`);
    alarms[idx] = { ...alarms[idx], ...data, id } as Alarm;
    globalThis.__mockAlarms = [...alarms];
    return { message: "ok (mock)" };
  },

  async deleteAlarm(id: string): Promise<{ message: string }> {
    await delay();
    globalThis.__mockAlarms = (globalThis.__mockAlarms ?? []).filter((a) => a.id !== id);
    return { message: "ok (mock)" };
  },

  async fetchLogs(): Promise<Log[]> {
    await delay();
    return [
      {
        id: 1,
        timestamp: new Date(Date.now() - 1000 * 60 * 60 * 8).toISOString(),
        last_update: new Date(Date.now() - 1000 * 60 * 60 * 8).toISOString(),
        alarm_id: 1,
        state: "fired",
        time_to_button_sec: 12,
        pressed_in_time: true,
        error_details: null,
        notes: "mock entry",
      },
    ];
  },

  async fetchNetworkLogs(): Promise<{
    data: NetworkLog[];
    meta: { page: number; limit: number; total: number; pages: number; minimal: boolean };
  }> {
    await delay();
    return {
      data: [],
      meta: { page: 1, limit: 100, total: 0, pages: 0, minimal: true },
    };
  },

  async fetchMonitorLogs(): Promise<{
    data: MonitorLog[];
    meta: { page: number; limit: number; total: number; pages: number };
  }> {
    await delay();
    return { data: [], meta: { page: 1, limit: 25, total: 0, pages: 0 } };
  },

  async fetchRebootHistory(): Promise<{
    data: RebootHistory[];
    meta: { page: number; limit: number; total: number; pages: number };
  }> {
    await delay();
    return { data: [], meta: { page: 1, limit: 10, total: 0, pages: 0 } };
  },
};

/**
 * Two guards must both be true for the mock to activate:
 *   1. NODE_ENV is "development" (Next.js sets this; `next build` always sets it
 *      to "production", so production bundles can never hit the mock path).
 *   2. NEXT_PUBLIC_USE_MOCK_API is "true" (set in .env.development; you can
 *      override locally by setting it to "false" in .env.local).
 *
 * Belt-and-suspenders: even if someone accidentally pushes the flag into a prod
 * env, the NODE_ENV check still blocks it.
 */
export const isMockApiActive = (): boolean =>
  process.env.NODE_ENV === "development" &&
  process.env.NEXT_PUBLIC_USE_MOCK_API === "true";
