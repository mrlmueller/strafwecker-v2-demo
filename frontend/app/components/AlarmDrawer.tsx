"use client";

import { useState, FormEvent, useMemo } from "react";
import { createAlarm, updateAlarm, Alarm } from "@/utils/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Loader2, Trash2, Sunrise } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { TimeWheelPicker } from "./TimeWheelPicker";
import { cn } from "@/lib/utils";

interface AlarmDrawerProps {
  alarm: Partial<Alarm>;
  open: boolean;
  onClose: () => void;
  onDelete?: () => void;
}

const dayShort = ["M", "T", "W", "T", "F", "S", "S"];

export default function AlarmDrawer({ alarm, open, onClose, onDelete }: AlarmDrawerProps) {
  const defaultTime = useMemo(() => {
    if (alarm.time) return alarm.time;
    const oneMinuteLater = new Date(Date.now() + 60_000);
    const hh = String(oneMinuteLater.getHours()).padStart(2, "0");
    const mm = String(oneMinuteLater.getMinutes()).padStart(2, "0");
    return `${hh}:${mm}`;
  }, [alarm.time]);

  const [initialHour, initialMinute] = useMemo(() => {
    const [h, m] = defaultTime.split(":").map(Number);
    return [h ?? 7, m ?? 0];
  }, [defaultTime]);

  const { toast } = useToast();
  const [formData, setFormData] = useState({
    hour: initialHour,
    minute: initialMinute,
    days_of_week: alarm.days_of_week || [],
    label: alarm.label || "Wake up",
    light_fade_minutes: alarm.light_fade_minutes ?? 0,
  });

  const [submitting, setSubmitting] = useState(false);

  function handleTimeChange(h: number, m: number) {
    setFormData((prev) => ({ ...prev, hour: h, minute: m }));
  }

  function handleDayToggle(index: number) {
    setFormData((prev) => {
      const has = prev.days_of_week.includes(index);
      const updated = has
        ? prev.days_of_week.filter((d) => d !== index)
        : [...prev.days_of_week, index].sort((a, b) => a - b);
      return { ...prev, days_of_week: updated };
    });
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const time = `${String(formData.hour).padStart(2, "0")}:${String(formData.minute).padStart(2, "0")}`;
      const lightOn = formData.light_fade_minutes > 0;
      const dataToSubmit = {
        time,
        days_of_week: formData.days_of_week,
        enabled: alarm.id ? alarm.enabled ?? true : true,
        label: formData.label,
        repeat_type: formData.days_of_week.length > 0 ? "weekly" : "once",
        light: lightOn,
        light_fade_minutes: formData.light_fade_minutes,
      };

      if (alarm.id) {
        await updateAlarm(alarm.id, dataToSubmit);
        toast({ title: "Saved", description: "Alarm updated" });
      } else {
        await createAlarm(dataToSubmit);
        toast({ title: "Saved", description: "Alarm created" });
      }
      onClose();
    } catch (error) {
      console.error("Failed to save alarm:", error);
      toast({ variant: "destructive", title: "Error", description: "Failed to save alarm" });
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
            {alarm.id ? "Edit alarm" : "New alarm"}
          </SheetTitle>
        </SheetHeader>

        <form onSubmit={handleSubmit} className="space-y-4 mt-4">
          <TimeWheelPicker
            hour={formData.hour}
            minute={formData.minute}
            onChange={handleTimeChange}
          />

          <div>
            <div className="text-[9px] opacity-55 tracking-[0.12em] uppercase font-semibold mt-3 mb-2">
              Repeat
            </div>
            <div className="flex justify-between gap-1">
              {dayShort.map((d, i) => {
                const on = formData.days_of_week.includes(i);
                return (
                  <button
                    key={i}
                    type="button"
                    onClick={() => handleDayToggle(i)}
                    className={cn(
                      "w-9 h-9 rounded-full text-[11px] font-semibold transition-colors",
                      on
                        ? "bg-sage text-background"
                        : "bg-card border border-sage/[0.08] text-foreground/80"
                    )}
                  >
                    {d}
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <Label htmlFor="label" className="text-[9px] opacity-55 tracking-[0.12em] uppercase font-semibold">
              Label
            </Label>
            <Input
              id="label"
              value={formData.label}
              onChange={(e) => setFormData((p) => ({ ...p, label: e.target.value }))}
              placeholder="Wake up"
              className="mt-1.5 bg-card border-sage/[0.08]"
            />
          </div>

          <div>
            <Label htmlFor="light_fade_minutes" className="text-[9px] opacity-55 tracking-[0.12em] uppercase font-semibold flex items-center gap-1.5">
              <Sunrise className="h-3 w-3" />
              Sunrise fade
            </Label>
            <Select
              value={String(formData.light_fade_minutes)}
              onValueChange={(val) =>
                setFormData((p) => ({ ...p, light_fade_minutes: Number(val) }))
              }
            >
              <SelectTrigger id="light_fade_minutes" className="mt-1.5 bg-card border-sage/[0.08]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="0">Off</SelectItem>
                <SelectItem value="5">5 min</SelectItem>
                <SelectItem value="10">10 min</SelectItem>
                <SelectItem value="15">15 min</SelectItem>
                <SelectItem value="20">20 min</SelectItem>
                <SelectItem value="30">30 min</SelectItem>
              </SelectContent>
            </Select>
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
              "Create alarm"
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
              Delete alarm
            </Button>
          )}
        </form>
      </SheetContent>
    </Sheet>
  );
}
