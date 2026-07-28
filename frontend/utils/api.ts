// utils/api.ts
import { mockApi, isMockApiActive } from "./mockApi";

export interface Alarm {
  id: string;
  time: string;
  days_of_week: number[];
  enabled: boolean;
  repeat_type?: string;
  label?: string;
  light: boolean;
  light_fade_minutes: number;
  kind: "alarm" | "nap";
  nap_target_at: string | null;
  nap_duration_minutes: number | null;
  esp32_button: boolean;
}

// New Log interface based on your DB table
export interface Log {
  id: number;
  timestamp: string;
  last_update: string;
  alarm_id: number;
  state: string;
  time_to_button_sec?: number | null;
  pressed_in_time?: boolean | null;
  error_details?: string | null;
  notes?: string | null;
}

export interface NetworkLog {
  id: number;
  timestamp: string;
  connected: number; // 1 if connected, 0 if not; you can also convert this to a boolean if preferred
  wifi_signal_dBm: string;
  ping_external_ms: string;
  ping_router_ms: string;
  temperature_C: string;
}

export interface MonitorLog {
  id: number;
  timestamp: string;
  event_type: string;
  details: string;
}

export interface RebootHistory {
  id: number;
  timestamp: string;
  success: number;
  notes: string;
}

export const API_BASE_URL = "/api";

// Handle days_of_week as either a JSON string (old Flask) or a real array (new FastAPI)
function parseDaysOfWeek(days: string | number[]): number[] {
  if (!days) return [];
  if (Array.isArray(days)) return days;
  try {
    const parsed = JSON.parse(days);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

interface RawAlarm {
  id: string;
  time: string;
  days_of_week: string | number[];
  enabled: number | boolean;
  repeat_type?: string;
  label?: string;
  light: number | boolean;
  light_fade_minutes?: number;
  kind?: "alarm" | "nap";
  nap_target_at?: string | null;
  nap_duration_minutes?: number | null;
  esp32_button?: number | boolean;
}

export async function fetchAlarms(): Promise<Alarm[]> {
  if (isMockApiActive()) return mockApi.fetchAlarms();
  const res = await fetch(`${API_BASE_URL}/alarms`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch alarms: ${res.statusText}`);
  }

  const data = await res.json();

  return data.map((alarm: RawAlarm) => ({
    ...alarm,
    days_of_week: parseDaysOfWeek(alarm.days_of_week),
    enabled: Boolean(alarm.enabled),
    light: Boolean(alarm.light),
    light_fade_minutes: alarm.light_fade_minutes ?? 0,
    kind: alarm.kind ?? "alarm",
    nap_target_at: alarm.nap_target_at ?? null,
    nap_duration_minutes: alarm.nap_duration_minutes ?? null,
    esp32_button: alarm.esp32_button == null ? true : Boolean(alarm.esp32_button),
  }));
}

export async function fetchAlarm(id: string): Promise<Alarm> {
  if (isMockApiActive()) return mockApi.fetchAlarm(id);
  const res = await fetch(`${API_BASE_URL}/alarms/${id}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch alarm: ${res.statusText}`);
  }

  const alarm = await res.json();
  return {
    ...alarm,
    days_of_week: parseDaysOfWeek(alarm.days_of_week),
    enabled: Boolean(alarm.enabled),
    light: Boolean(alarm.light),
    light_fade_minutes: alarm.light_fade_minutes ?? 0,
    kind: alarm.kind ?? "alarm",
    nap_target_at: alarm.nap_target_at ?? null,
    nap_duration_minutes: alarm.nap_duration_minutes ?? null,
    esp32_button: alarm.esp32_button == null ? true : Boolean(alarm.esp32_button),
  };
}

interface AlarmCreateOrUpdateData {
  time: string;
  days_of_week: number[];
  enabled: boolean;
  repeat_type?: string;
  label?: string;
  light: boolean;
  light_fade_minutes?: number;
  kind?: "alarm" | "nap";
  nap_target_at?: string | null;
  nap_duration_minutes?: number | null;
  esp32_button?: boolean;
}

export async function createAlarm(
  data: AlarmCreateOrUpdateData
): Promise<{ message: string; id: string }> {
  if (isMockApiActive()) {
    return mockApi.createAlarm({
      time: data.time,
      days_of_week: data.days_of_week,
      enabled: true,
      repeat_type: data.repeat_type,
      label: data.label,
      light: Boolean(data.light),
      light_fade_minutes: data.light_fade_minutes ?? 0,
      kind: data.kind ?? "alarm",
      nap_target_at: data.nap_target_at ?? null,
      nap_duration_minutes: data.nap_duration_minutes ?? null,
      esp32_button: data.esp32_button ?? true,
    });
  }
  const payload = {
    ...data,
    days_of_week: data.days_of_week,
    enabled: true,
    light: Boolean(data.light),
    light_fade_minutes: data.light_fade_minutes ?? 0,
  };

  const res = await fetch(`${API_BASE_URL}/alarms`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(`Failed to create alarm: ${res.statusText}`);
  }

  return res.json();
}

export async function updateAlarm(
  id: string,
  data: AlarmCreateOrUpdateData
): Promise<{ message: string }> {
  if (isMockApiActive()) {
    return mockApi.updateAlarm(id, {
      time: data.time,
      days_of_week: data.days_of_week,
      enabled: Boolean(data.enabled),
      repeat_type: data.repeat_type,
      label: data.label,
      light: Boolean(data.light),
      light_fade_minutes: data.light_fade_minutes ?? 0,
    });
  }
  const payload = {
    ...data,
    days_of_week: data.days_of_week,
    enabled: Boolean(data.enabled),
    light: Boolean(data.light),
    light_fade_minutes: data.light_fade_minutes ?? 0,
  };

  const res = await fetch(`${API_BASE_URL}/alarms/${id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(`Failed to update alarm: ${res.statusText}`);
  }

  return res.json();
}

export async function deleteAlarm(id: string): Promise<{ message: string }> {
  if (isMockApiActive()) return mockApi.deleteAlarm(id);
  const res = await fetch(`${API_BASE_URL}/alarms/${id}`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    throw new Error(`Failed to delete alarm: ${res.statusText}`);
  }

  return res.json();
}

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

// New: Fetch logs from the Flask server
export async function fetchLogs(): Promise<Log[]> {
  if (isMockApiActive()) return mockApi.fetchLogs();
  const res = await fetch(`${API_BASE_URL}/logs`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch logs: ${res.statusText}`);
  }

  const data = await res.json();

  return data.map((log: RawLog) => ({
    ...log,
    pressed_in_time:
      log.pressed_in_time === null ? null : Number(log.pressed_in_time) === 1,
  }));
}

export async function fetchNetworkLogs(
  limit: number = 100,
  startDate?: string,
  endDate?: string,
  page: number = 1,
  minimal: boolean = true
): Promise<{
  data: NetworkLog[];
  meta: {
    page: number;
    limit: number;
    total: number;
    pages: number;
    minimal: boolean;
  };
}> {
  if (isMockApiActive()) return mockApi.fetchNetworkLogs();
  // Build URL with parameters
  let url = `${API_BASE_URL}/network_logs?limit=${limit}&page=${page}&minimal=${minimal}`;

  // Add date filters if provided
  if (startDate) {
    url += `&start_date=${encodeURIComponent(startDate)}`;
  }

  if (endDate) {
    url += `&end_date=${encodeURIComponent(endDate)}`;
  }

  const res = await fetch(url, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
    // Disable caching to get fresh data
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch network logs: ${res.statusText}`);
  }

  const data = await res.json();

  // Ensure timestamps are parsed as UTC
  if (data.data && data.data.length > 0) {
    data.data = data.data.map((log: NetworkLog) => ({
      ...log,
      timestamp: log.timestamp.endsWith("Z")
        ? log.timestamp
        : log.timestamp + "Z",
    }));
  }

  return data;
}

export async function fetchMonitorLogs(
  limit: number = 25,
  page: number = 1,
  eventType?: string
): Promise<{
  data: MonitorLog[];
  meta: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
}> {
  if (isMockApiActive()) return mockApi.fetchMonitorLogs();
  // Build URL with parameters
  let url = `${API_BASE_URL}/monitor_logs?limit=${limit}&page=${page}`;

  // Add event_type filter if provided
  if (eventType) {
    url += `&event_type=${encodeURIComponent(eventType)}`;
  }

  const res = await fetch(url, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch monitor logs: ${res.statusText}`);
  }

  return await res.json();
}

export async function fetchRebootHistory(
  limit: number = 10,
  page: number = 1,
  success?: number
): Promise<{
  data: RebootHistory[];
  meta: {
    page: number;
    limit: number;
    total: number;
    pages: number;
  };
}> {
  if (isMockApiActive()) return mockApi.fetchRebootHistory();
  // Build URL with parameters
  let url = `${API_BASE_URL}/reboot_history?limit=${limit}&page=${page}`;

  // Add success filter if provided
  if (success !== undefined) {
    url += `&success=${success}`;
  }

  const res = await fetch(url, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch reboot history: ${res.statusText}`);
  }

  return await res.json();
}

export async function restartNap(id: string): Promise<{ message: string; target_at: string }> {
  if (isMockApiActive()) return { message: "ok", target_at: new Date().toISOString() };
  const res = await fetch(`${API_BASE_URL}/alarms/${id}/restart`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error(`Failed to restart nap: ${res.statusText}`);
  return res.json();
}
