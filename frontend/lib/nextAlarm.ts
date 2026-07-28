import type { Alarm } from "@/utils/api";

export interface NextAlarm {
  alarm: Alarm;
  firesAt: Date;
}

function jsDayToOurDay(jsDay: number): number {
  return (jsDay + 6) % 7;
}

function nextFiringForAlarm(alarm: Alarm, now: Date): Date | null {
  if (!alarm.enabled) return null;

  if (alarm.kind === "nap") {
    if (!alarm.nap_target_at) return null;
    const target = new Date(alarm.nap_target_at);
    if (Number.isNaN(target.getTime())) return null;
    return target.getTime() > now.getTime() ? target : null;
  }

  const [hh, mm] = alarm.time.split(":").map(Number);
  if (Number.isNaN(hh) || Number.isNaN(mm)) return null;

  const todayOurDay = jsDayToOurDay(now.getDay());
  const days = alarm.days_of_week.length > 0 ? alarm.days_of_week : [todayOurDay];

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
