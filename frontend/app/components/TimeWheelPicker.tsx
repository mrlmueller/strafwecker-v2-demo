"use client";

import { useEffect, useRef, useState } from "react";

const ITEM_HEIGHT = 36;
const VISIBLE_ITEMS = 5;
const COLUMN_HEIGHT = ITEM_HEIGHT * VISIBLE_ITEMS;
const PADDING = (COLUMN_HEIGHT - ITEM_HEIGHT) / 2;

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
  const [scrollIndex, setScrollIndex] = useState(value);
  const programmaticScrollUntil = useRef(0);

  useEffect(() => {
    if (!ref.current) return;
    programmaticScrollUntil.current = Date.now() + 300;
    ref.current.scrollTop = value * ITEM_HEIGHT;
  }, [value]);

  function handleScroll() {
    if (!ref.current) return;
    const idx = Math.round(ref.current.scrollTop / ITEM_HEIGHT);
    const clamped = Math.max(0, Math.min(count - 1, idx));
    setScrollIndex(clamped);
    if (Date.now() < programmaticScrollUntil.current) return;
    if (clamped !== value) onValueChange(clamped);
  }

  const centerIndex = scrollIndex;

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
