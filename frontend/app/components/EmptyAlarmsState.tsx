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
