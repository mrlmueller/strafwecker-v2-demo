// app/components/TimePicker.tsx
import { useState, useCallback, ChangeEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ChevronUp, ChevronDown } from "lucide-react";

interface TimePickerProps {
  id: string;
  value: string; // Format "HH:MM"
  onChange: (newTime: string) => void;
}

export function TimePicker({ id, value, onChange }: TimePickerProps) {
  const [time, setTime] = useState(() => {
    const [hours, minutes] = value.split(":").map(Number);
    return { hours, minutes };
  });

  const updateTime = useCallback(
    (newTime: { hours: number; minutes: number }) => {
      setTime(newTime);
      onChange(
        `${newTime.hours.toString().padStart(2, "0")}:${newTime.minutes
          .toString()
          .padStart(2, "0")}`
      );
    },
    [onChange]
  );

  const incrementHours = () =>
    updateTime({ ...time, hours: (time.hours + 1) % 24 });
  const decrementHours = () =>
    updateTime({ ...time, hours: (time.hours - 1 + 24) % 24 });
  const incrementMinutes = () =>
    updateTime({ ...time, minutes: (time.minutes + 1) % 60 });
  const decrementMinutes = () =>
    updateTime({ ...time, minutes: (time.minutes - 1 + 60) % 60 });

  const handleHoursChange = (e: ChangeEvent<HTMLInputElement>) => {
    const newHours = Math.max(0, Math.min(23, Number(e.target.value) || 0));
    updateTime({ ...time, hours: newHours });
  };

  const handleMinutesChange = (e: ChangeEvent<HTMLInputElement>) => {
    const newMinutes = Math.max(0, Math.min(59, Number(e.target.value) || 0));
    updateTime({ ...time, minutes: newMinutes });
  };

  return (
    <div className="flex items-center space-x-2">
      <div className="flex flex-col items-center">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={incrementHours}
        >
          <ChevronUp className="h-4 w-4" />
        </Button>
        <Input
          id={`${id}-hours`}
          type="number"
          min="0"
          max="23"
          value={time.hours}
          onChange={handleHoursChange}
          className="w-16 text-center"
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={decrementHours}
        >
          <ChevronDown className="h-4 w-4" />
        </Button>
      </div>
      <span className="text-2xl">:</span>
      <div className="flex flex-col items-center">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={incrementMinutes}
        >
          <ChevronUp className="h-4 w-4" />
        </Button>
        <Input
          id={`${id}-minutes`}
          type="number"
          min="0"
          max="59"
          value={time.minutes}
          onChange={handleMinutesChange}
          className="w-16 text-center"
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={decrementMinutes}
        >
          <ChevronDown className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
