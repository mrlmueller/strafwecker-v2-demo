"use client";

import { useState, FormEvent, useMemo } from "react";
import { createAlarm, updateAlarm, Alarm } from "@/utils/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Sheet, SheetContent, SheetHeader, SheetTitle,
} from "@/components/ui/sheet";
import { Loader2, Trash2, Lightbulb, BellRing } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { MinuteWheelPicker } from "./MinuteWheelPicker";

interface Props {
  alarm: Partial<Alarm>;
  open: boolean;
  onClose: () => void;
  onDelete?: () => void;
}

export default function NapDrawer({ alarm, open, onClose, onDelete }: Props) {
  const { toast } = useToast();

  const initialMinutes = useMemo(
    () => alarm.nap_duration_minutes ?? 15,
    [alarm.nap_duration_minutes],
  );

  const [formData, setFormData] = useState({
    minutes: initialMinutes,
    label: alarm.label || "Nap",
    // New timers default both switches ON; editing keeps the stored values
    // (a stored `false` stays false, since `false ?? true === false`).
    light: alarm.light ?? true,
    esp32_button: alarm.esp32_button ?? true,
  });
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const now = new Date();
      const target = new Date(now.getTime() + formData.minutes * 60_000);
      const hh = String(target.getHours()).padStart(2, "0");
      const mm = String(target.getMinutes()).padStart(2, "0");
      const dataToSubmit = {
        time: `${hh}:${mm}`,
        days_of_week: [],
        enabled: true,
        repeat_type: "once",
        label: formData.label,
        light: formData.light,
        light_fade_minutes: 0,
        kind: "nap" as const,
        nap_target_at: null,
        nap_duration_minutes: formData.minutes,
        esp32_button: formData.esp32_button,
      };

      if (alarm.id) {
        await updateAlarm(alarm.id, dataToSubmit);
        toast({ title: "Saved", description: "Nap updated" });
      } else {
        await createAlarm(dataToSubmit);
        toast({ title: "Saved", description: "Nap started" });
      }
      onClose();
    } catch (error) {
      console.error("Failed to save nap:", error);
      toast({ variant: "destructive", title: "Error", description: "Failed to save nap" });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent
        side="bottom"
        className="h-auto max-h-[92vh] overflow-auto rounded-t-3xl border-t border-sage/10"
        style={{ paddingBottom: "calc(1rem + env(safe-area-inset-bottom, 0px))" }}
      >
        <SheetHeader>
          <SheetTitle className="text-center">
            {alarm.id ? "Edit timer" : "New timer"}
          </SheetTitle>
        </SheetHeader>

        <form onSubmit={handleSubmit} className="space-y-4 mt-4">
          <MinuteWheelPicker
            minutes={formData.minutes}
            onChange={(m) => setFormData((p) => ({ ...p, minutes: m }))}
          />

          <div>
            <Label htmlFor="label" className="text-[9px] opacity-55 tracking-[0.12em] uppercase font-semibold">
              Label
            </Label>
            <Input
              id="label"
              value={formData.label}
              onChange={(e) => setFormData((p) => ({ ...p, label: e.target.value }))}
              placeholder="Nap"
              className="mt-1.5 bg-card border-sage/[0.08]"
            />
          </div>

          <div className="flex items-center justify-between bg-card border border-sage/[0.08] rounded-2xl px-4 py-3">
            <div className="flex items-center gap-2">
              <Lightbulb className="h-4 w-4 text-yellow-400/80" />
              <span className="text-sm">Light at end</span>
            </div>
            <Switch
              checked={formData.light}
              onCheckedChange={(v) => setFormData((p) => ({ ...p, light: v }))}
            />
          </div>

          <div className="flex items-center justify-between bg-card border border-sage/[0.08] rounded-2xl px-4 py-3">
            <div className="flex items-center gap-2">
              <BellRing className="h-4 w-4 text-foreground/70" />
              <span className="text-sm">ESP32 button</span>
            </div>
            <Switch
              checked={formData.esp32_button}
              onCheckedChange={(v) => setFormData((p) => ({ ...p, esp32_button: v }))}
            />
          </div>

          <Button
            type="submit"
            disabled={submitting}
            className="w-full mt-2 bg-sage text-background hover:bg-sage/90 font-bold rounded-2xl py-6"
          >
            {submitting ? (
              <Loader2 className="animate-spin h-4 w-4" />
            ) : alarm.id ? (
              "Save changes"
            ) : (
              "Start timer"
            )}
          </Button>

          {alarm.id && onDelete && (
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                onDelete();
                onClose();
              }}
              className="w-full text-destructive/80 hover:text-destructive hover:bg-destructive/10 font-medium"
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Delete timer
            </Button>
          )}
        </form>
      </SheetContent>
    </Sheet>
  );
}
