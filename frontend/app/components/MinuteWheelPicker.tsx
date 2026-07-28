"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

interface Props {
  minutes: number;
  onChange: (m: number) => void;
}

const ITEM_HEIGHT = 44;
const VALUES = Array.from({ length: 60 }, (_, i) => i + 1); // 1..60

export function MinuteWheelPicker({ minutes, onChange }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const scrollTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const idx = VALUES.indexOf(minutes);
    if (idx >= 0) ref.current.scrollTop = idx * ITEM_HEIGHT;
  }, [minutes]);

  function handleScroll() {
    if (!ref.current) return;
    if (scrollTimeout.current) clearTimeout(scrollTimeout.current);
    scrollTimeout.current = setTimeout(() => {
      if (!ref.current) return;
      const idx = Math.round(ref.current.scrollTop / ITEM_HEIGHT);
      const clamped = Math.max(0, Math.min(VALUES.length - 1, idx));
      ref.current.scrollTo({ top: clamped * ITEM_HEIGHT, behavior: "smooth" });
      onChange(VALUES[clamped]);
    }, 120);
  }

  return (
    <div className="relative h-[132px] overflow-hidden rounded-2xl bg-card/40 border border-sage/[0.08]">
      <div
        ref={ref}
        onScroll={handleScroll}
        className="h-full overflow-y-scroll snap-y snap-mandatory scroll-pt-[44px] no-scrollbar"
        style={{ paddingTop: ITEM_HEIGHT, paddingBottom: ITEM_HEIGHT }}
      >
        {VALUES.map((v) => (
          <div
            key={v}
            className={cn(
              "h-[44px] flex items-center justify-center text-2xl leading-none tabular-nums snap-center",
              v === minutes ? "text-cream font-semibold" : "text-foreground/40"
            )}
          >
            {v}
            <span className="text-sm ml-1.5 opacity-60">min</span>
          </div>
        ))}
      </div>
      <div className="pointer-events-none absolute inset-x-0 top-[44px] h-[44px] border-y border-sage/15" />
    </div>
  );
}
