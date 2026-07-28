"use client";

import { useState, useEffect, useCallback } from "react";
import { Log, fetchLogs } from "@/utils/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Loader2, RefreshCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { Toaster } from "@/components/ui/toaster";
import { cn } from "@/lib/utils";

export default function LogsPage() {
  const [logs, setLogs] = useState<Log[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const { toast } = useToast();

  const loadLogs = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchLogs();
      setLogs(data);
    } catch (error) {
      console.error("Failed to load logs:", error);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to load logs.",
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  const getStateColor = (state: string) => {
    const lowerState = state.toLowerCase();

    if (
      ["success", "button_pressed_local", "button_pressed_esp32", "button_pressed_auto_stop", "esp32_timer_started"].includes(lowerState)
    ) {
      return "bg-green-500/15 text-green-300 border-green-500/30";
    }

    if (
      ["alarm_started", "alarm_received", "alarm_playing", "esp32_notified"].includes(lowerState)
    ) {
      return "bg-yellow-500/15 text-yellow-300 border-yellow-500/30";
    }

    if (
      ["error", "esp32_unreachable", "no_button_press_esp32"].includes(lowerState)
    ) {
      return "bg-red-500/15 text-red-300 border-red-500/30";
    }

    if (
      ["ignored", "button_pressed_esp32_after_local_stop"].includes(lowerState)
    ) {
      return "bg-blue-500/15 text-blue-300 border-blue-500/30";
    }

    return "bg-foreground/[0.06] text-foreground/70 border-foreground/10";
  };

  return (
    <div className="container mx-auto p-4 pb-24 max-w-md md:max-w-2xl overflow-x-hidden">
      <Toaster />
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold md:text-3xl">Alarm Logs</h1>
        <Button onClick={loadLogs} variant="outline" size="icon">
          <RefreshCcw className="h-4 w-4" />
        </Button>
      </div>
      {loading ? (
        <div className="flex justify-center items-center mt-16">
          <Loader2 className="animate-spin h-8 w-8 text-sage/70" />
        </div>
      ) : (
        <div className="space-y-3">
          {logs.map((log) => (
            <Card key={log.id} className="overflow-hidden">
              <CardHeader className="pb-2 pt-3 px-4">
                <CardTitle className="flex justify-between items-center gap-2 text-base">
                  <Badge
                    variant="outline"
                    className={cn(
                      "max-w-full font-medium text-[10px] tracking-wide truncate",
                      getStateColor(log.state)
                    )}
                    title={log.state}
                  >
                    {log.state}
                  </Badge>
                  <span className="text-xs font-normal text-foreground/50 shrink-0">
                    #{log.id}
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-4 text-sm">
                <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
                  <Field label="Alarm" value={`#${log.alarm_id}`} />
                  <Field
                    label="Triggered"
                    value={new Date(log.timestamp).toLocaleString()}
                  />
                  <Field
                    label="Updated"
                    value={new Date(log.last_update).toLocaleString()}
                  />
                  <Field
                    label="Time to button"
                    value={
                      log.time_to_button_sec !== null
                        ? `${log.time_to_button_sec} s`
                        : "—"
                    }
                  />
                  <Field
                    label="Pressed in time"
                    value={
                      log.pressed_in_time === null
                        ? "—"
                        : log.pressed_in_time
                        ? "Yes"
                        : "No"
                    }
                  />
                </div>
                {log.error_details && (
                  <div className="mt-3 rounded-lg border border-red-500/20 bg-red-500/[0.06] p-2">
                    <div className="text-[10px] tracking-wide font-semibold text-red-300/80 uppercase mb-1">
                      Error
                    </div>
                    <p className="text-xs text-red-200/85 break-words whitespace-pre-wrap font-mono">
                      {log.error_details}
                    </p>
                  </div>
                )}
                {log.notes && (
                  <div className="mt-3">
                    <div className="text-[10px] tracking-wide font-semibold opacity-60 uppercase mb-1">
                      Notes
                    </div>
                    <p className="text-xs whitespace-pre-line break-words">
                      {log.notes}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <div className="text-[9px] tracking-wide font-semibold opacity-50 uppercase">
        {label}
      </div>
      <div className="text-xs break-words">{value}</div>
    </div>
  );
}
