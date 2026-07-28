"use client";

import { Lightbulb, BellOff, RotateCcw, Loader2 } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import type { Alarm } from "@/utils/api";
import { cn } from "@/lib/utils";

interface Props {
  alarm: Alarm;
  now: number;
  featured?: boolean;
  busy?: boolean;
  onToggleEnabled: (alarm: Alarm) => void;
  onEdit: (alarm: Alarm) => void;
  onRestart: (alarm: Alarm) => void;
}

function formatRemaining(ms: number): string {
  if (ms <= 0) return "00:00";
  const totalSec = Math.ceil(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function formatClock(ms: number): string {
  const d = new Date(ms);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function formatEndedAgo(ms: number): string {
  const sec = Math.floor(ms / 1000);
  if (sec < 60) return "just now";
  const m = Math.floor(sec / 60);
  if (m < 60) return `${m} min ago`;
  const h = Math.floor(m / 60);
  return `${h} h ago`;
}

export function NapCard({
  alarm, now, featured, busy, onToggleEnabled, onEdit, onRestart,
}: Props) {
  const targetMs = alarm.nap_target_at ? new Date(alarm.nap_target_at).getTime() : null;
  const isActive = alarm.enabled && targetMs !== null && targetMs > now;
  const remaining = isActive && targetMs ? targetMs - now : 0;
  const endedAgo = !isActive && targetMs ? Math.max(0, now - targetMs) : 0;

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
        !isActive && "opacity-80"
      )}
    >
      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0">
          {isActive ? (
            <>
              <div className="text-2xl font-bold tabular-nums tracking-tight text-cream">
                {formatRemaining(remaining)}
              </div>
              <div className="text-[10px] opacity-60 mt-0.5">
                {alarm.nap_duration_minutes} min nap · rings at{" "}
                <span className="tabular-nums">{targetMs ? formatClock(targetMs) : "--:--"}</span>
              </div>
            </>
          ) : (
            <>
              <div className="text-2xl font-bold tabular-nums tracking-tight text-cream/75">
                {alarm.nap_duration_minutes ?? 0}
                <span className="text-base font-medium opacity-65 ml-1">min</span>
              </div>
              <div className="text-[10px] opacity-60 mt-0.5">
                Ended {formatEndedAgo(endedAgo)}
              </div>
            </>
          )}
          {(alarm.light || !alarm.esp32_button || alarm.label) && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {alarm.light && (
                <span className="inline-flex items-center gap-1 text-[9px] font-semibold bg-sage/15 text-sage px-2 py-0.5 rounded-md">
                  <Lightbulb className="h-2.5 w-2.5" />
                  Light
                </span>
              )}
              {!alarm.esp32_button && (
                <span className="inline-flex items-center gap-1 text-[9px] font-semibold bg-foreground/[0.07] text-foreground/60 px-2 py-0.5 rounded-md">
                  <BellOff className="h-2.5 w-2.5" />
                  No button
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
          {isActive ? (
            <>
              {busy && <Loader2 className="h-4 w-4 animate-spin text-sage/70" />}
              <Switch
                checked={alarm.enabled}
                disabled={busy}
                onCheckedChange={() => onToggleEnabled(alarm)}
                aria-label="Disable timer"
              />
            </>
          ) : (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onRestart(alarm)}
              disabled={busy}
              className="rounded-full px-3"
            >
              {busy ? (
                <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
              ) : (
                <RotateCcw className="h-3.5 w-3.5 mr-1" />
              )}
              Restart
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
