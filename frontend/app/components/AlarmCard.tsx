"use client";

import { Sunrise, Lightbulb, Loader2 } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import type { Alarm } from "@/utils/api";
import { cn } from "@/lib/utils";

interface Props {
  alarm: Alarm;
  featured?: boolean;
  busy?: boolean;
  onToggleEnabled: (alarm: Alarm) => void;
  onEdit: (alarm: Alarm) => void;
}

const dayShort = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function formatDays(days: number[]): string {
  if (days.length === 0) return "Once";
  if (days.length === 7) return "Daily";
  const isWeekdays = days.length === 5 && [0, 1, 2, 3, 4].every((d) => days.includes(d));
  if (isWeekdays) return "Weekdays";
  const isWeekends = days.length === 2 && [5, 6].every((d) => days.includes(d));
  if (isWeekends) return "Weekends";
  return [...days].sort((a, b) => a - b).map((d) => dayShort[d]).join(" · ");
}

export function AlarmCard({ alarm, featured, busy, onToggleEnabled, onEdit }: Props) {
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
        <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
          {busy && <Loader2 className="h-4 w-4 animate-spin text-sage/70" />}
          <Switch
            checked={enabled}
            disabled={busy}
            onCheckedChange={() => onToggleEnabled(alarm)}
            aria-label={enabled ? "Disable alarm" : "Enable alarm"}
          />
        </div>
      </div>
    </div>
  );
}
