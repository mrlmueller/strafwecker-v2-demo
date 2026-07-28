// app/components/AlarmForm.tsx
import { useState, FormEvent, ChangeEvent } from "react";
import { createAlarm, updateAlarm, Alarm } from "@/utils/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { TimePicker } from "./TimePicker";
import { Loader2, Lightbulb } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface AlarmFormProps {
  alarm: Partial<Alarm>; // new or existing alarm
  onClose: () => void;
}

const daysOfWeekLabels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function AlarmForm({ alarm, onClose }: AlarmFormProps) {
  const { toast } = useToast();
  const [formData, setFormData] = useState({
    time: alarm.time || "07:00",
    days_of_week: alarm.days_of_week || [],
    enabled: alarm.enabled ?? true,
    label: alarm.label || "",
    repeat: (alarm.days_of_week && alarm.days_of_week.length > 0) || false,
    light: alarm.light ?? false, // new field
  });
  const [submitting, setSubmitting] = useState(false);

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  }

  function handleTimeChange(newTime: string) {
    setFormData((prev) => ({ ...prev, time: newTime }));
  }

  function handleDayToggle(index: number) {
    setFormData((prev) => {
      const includesDay = prev.days_of_week.includes(index);
      let updatedDays;
      if (includesDay) {
        updatedDays = prev.days_of_week.filter((d) => d !== index);
      } else {
        updatedDays = [...prev.days_of_week, index].sort((a, b) => a - b);
      }
      return { ...prev, days_of_week: updatedDays };
    });
  }

  function handleRepeatToggle(checked: boolean) {
    setFormData((prev) => ({
      ...prev,
      repeat: checked,
      days_of_week: checked ? prev.days_of_week : [],
    }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const dataToSubmit = {
        time: formData.time,
        days_of_week: formData.days_of_week,
        enabled: true, // Force enabled to true on form submission
        label: formData.label,
        repeat_type: formData.repeat ? "weekly" : "once",
        light: formData.light,
      };

      if (alarm.id) {
        await updateAlarm(alarm.id, dataToSubmit);
        toast({ title: "Success", description: "Alarm updated successfully" });
      } else {
        await createAlarm(dataToSubmit);
        toast({ title: "Success", description: "Alarm created successfully" });
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
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{alarm.id ? "Edit Alarm" : "Add New Alarm"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="time">Time</Label>
            <TimePicker
              id="time"
              value={formData.time}
              onChange={handleTimeChange}
            />
          </div>
          <div>
            <Label htmlFor="label">Label</Label>
            <Input
              id="label"
              name="label"
              value={formData.label}
              onChange={handleChange}
              placeholder="Alarm label"
            />
          </div>
          <div className="flex items-center space-x-2">
            <Switch
              id="repeat"
              checked={formData.repeat}
              onCheckedChange={handleRepeatToggle}
            />
            <Label htmlFor="repeat">Repeat</Label>
          </div>
          {formData.repeat && (
            <div>
              <Label>Days of Week</Label>
              <div className="flex flex-wrap gap-2 mt-2">
                {daysOfWeekLabels.map((day, index) => (
                  <div key={day} className="flex items-center space-x-2">
                    <Checkbox
                      id={day}
                      checked={formData.days_of_week.includes(index)}
                      onCheckedChange={() => handleDayToggle(index)}
                    />
                    <label
                      htmlFor={day}
                      className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                    >
                      {day}
                    </label>
                  </div>
                ))}
              </div>
            </div>
          )}
          <div className="flex items-center space-x-2 mt-4">
            <Label htmlFor="enabled">Enabled:</Label>
            <Switch
              id="enabled"
              checked={formData.enabled}
              onCheckedChange={(checked) =>
                setFormData((prev) => ({ ...prev, enabled: checked }))
              }
            />
          </div>
          <div className="flex items-center space-x-2 mt-4">
            <Lightbulb className="h-5 w-5 text-yellow-400" />
            <Label htmlFor="light">Activate Light</Label>
            <Switch
              id="light"
              checked={formData.light}
              onCheckedChange={(checked) =>
                setFormData((prev) => ({ ...prev, light: checked }))
              }
            />
          </div>
          <div className="flex justify-end space-x-2 mt-6">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={submitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? (
                <Loader2 className="animate-spin h-4 w-4" />
              ) : alarm.id ? (
                "Update"
              ) : (
                "Create"
              )}{" "}
              Alarm
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
