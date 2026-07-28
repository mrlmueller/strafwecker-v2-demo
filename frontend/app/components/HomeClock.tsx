"use client";

import { useEffect, useState } from "react";

function getGreeting(hour: number): string {
  if (hour < 5) return "Good night";
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

export function HomeClock() {
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    const tick = () => setNow(new Date());
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

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
    </div>
  );
}
