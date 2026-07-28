"use client";

import { useRef, useState, type ReactNode, type PointerEvent } from "react";
import { Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  onDelete: () => void;
  disabled?: boolean;
  children: ReactNode;
}

// Distance (px) the card must be dragged left before release commits a delete.
const THRESHOLD = 96;
// Movement (px) before we decide the gesture is a horizontal swipe vs a vertical
// scroll. Below this we stay neutral so the page can still scroll normally.
const DIR_LOCK = 10;
// Any horizontal travel beyond this marks the gesture as a swipe, so the trailing
// click (which would otherwise open the edit drawer) is suppressed.
const MOVE_SUPPRESS = 8;

/**
 * Wraps a card so it can be swiped right-to-left to delete. Dragging reveals a
 * red delete affordance; releasing past THRESHOLD animates the card off-screen
 * and calls onDelete (the parent shows an Undo toast and defers the real
 * server delete, so an accidental swipe is recoverable).
 */
export function SwipeToDelete({ onDelete, disabled, children }: Props) {
  const [dx, setDx] = useState(0);
  const [animating, setAnimating] = useState(false);
  const [removing, setRemoving] = useState(false);

  const startX = useRef(0);
  const startY = useRef(0);
  const dragging = useRef(false);
  const axis = useRef<"h" | "v" | null>(null);
  const moved = useRef(false);

  function onPointerDown(e: PointerEvent) {
    if (disabled || removing) return;
    if (e.pointerType === "mouse" && e.button !== 0) return;
    startX.current = e.clientX;
    startY.current = e.clientY;
    dragging.current = true;
    axis.current = null;
    moved.current = false;
    setAnimating(false);
  }

  function onPointerMove(e: PointerEvent) {
    if (!dragging.current) return;
    const deltaX = e.clientX - startX.current;
    const deltaY = e.clientY - startY.current;

    if (axis.current === null) {
      if (Math.abs(deltaX) < DIR_LOCK && Math.abs(deltaY) < DIR_LOCK) return;
      axis.current = Math.abs(deltaX) > Math.abs(deltaY) ? "h" : "v";
      if (axis.current === "h") {
        (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
      }
    }
    if (axis.current !== "h") return;

    if (Math.abs(deltaX) > MOVE_SUPPRESS) moved.current = true;
    // Only left swipes translate; a small rightward pull is rubber-banded to 0.
    setDx(Math.min(0, deltaX));
  }

  function endDrag(e: PointerEvent) {
    if (!dragging.current) return;
    dragging.current = false;
    const wasHorizontal = axis.current === "h";
    axis.current = null;
    try {
      (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    } catch {
      /* pointer was never captured */
    }

    setAnimating(true);
    if (wasHorizontal && dx <= -THRESHOLD) {
      setRemoving(true);
      setDx(-window.innerWidth);
      window.setTimeout(onDelete, 180);
    } else {
      setDx(0);
    }
  }

  const revealed = dx < -MOVE_SUPPRESS;

  return (
    // overflow-hidden makes this a block-formatting context so the child card's
    // top margin stays contained (keeping the red background aligned) and clips
    // the card cleanly as it slides off-screen.
    <div className="relative overflow-hidden">
      {/* Delete affordance revealed underneath as the card slides left. */}
      <div
        aria-hidden
        className={cn(
          "absolute inset-x-0 bottom-0 top-3 rounded-3xl bg-destructive/90",
          "flex items-center justify-end pr-6 transition-opacity",
          revealed ? "opacity-100" : "opacity-0",
        )}
      >
        <Trash2 className="h-5 w-5 text-destructive-foreground" />
      </div>

      <div
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onClickCapture={(e) => {
          if (moved.current) {
            e.preventDefault();
            e.stopPropagation();
            moved.current = false;
          }
        }}
        style={{
          transform: `translateX(${dx}px)`,
          transition: animating ? "transform 180ms ease-out" : "none",
          touchAction: "pan-y",
        }}
      >
        {children}
      </div>
    </div>
  );
}
