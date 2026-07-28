"use client";

import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Bell, Timer } from "lucide-react";

interface Props {
  open: boolean;
  onClose: () => void;
  onPickAlarm: () => void;
  onPickNap: () => void;
}

export function CreateChooser({ open, onClose, onPickAlarm, onPickNap }: Props) {
  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent
        side="bottom"
        className="h-auto max-h-[40vh] rounded-t-3xl border-t border-sage/10"
        style={{ paddingBottom: "calc(1.5rem + env(safe-area-inset-bottom, 0px))" }}
      >
        <div className="grid grid-cols-2 gap-3 mt-2">
          <button
            type="button"
            onClick={() => {
              onClose();
              onPickAlarm();
            }}
            className="flex flex-col items-center justify-center gap-3 rounded-2xl bg-card border border-sage/[0.08] py-8 active:scale-95 transition-transform"
          >
            <Bell className="h-7 w-7 text-sage" />
            <span className="text-base font-semibold">Alarm</span>
          </button>
          <button
            type="button"
            onClick={() => {
              onClose();
              onPickNap();
            }}
            className="flex flex-col items-center justify-center gap-3 rounded-2xl bg-card border border-sage/[0.08] py-8 active:scale-95 transition-transform"
          >
            <Timer className="h-7 w-7 text-sage" />
            <span className="text-base font-semibold">Timer</span>
          </button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
