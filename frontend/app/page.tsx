"use client";

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import {
  Alarm, fetchAlarms, deleteAlarm, updateAlarm, restartNap,
} from "@/utils/api";
import { Plus, Loader2 } from "lucide-react";
import { useTheme } from "next-themes";
import { useToast } from "@/hooks/use-toast";
import { Toaster } from "@/components/ui/toaster";
import { ToastAction } from "@/components/ui/toast";
import AlarmDrawer from "./components/AlarmDrawer";
import NapDrawer from "./components/NapDrawer";
import { HomeClock } from "./components/HomeClock";
import { AlarmCard } from "./components/AlarmCard";
import { NapCard } from "./components/NapCard";
import { SwipeToDelete } from "./components/SwipeToDelete";
import { CreateChooser } from "./components/CreateChooser";
import { EmptyAlarmsState } from "./components/EmptyAlarmsState";
import { getNextAlarm } from "@/lib/nextAlarm";

// How long the Undo toast stays up before the delete is actually committed.
const UNDO_TOAST_MS = 4000;
const DELETE_COMMIT_MS = 4200;

export default function Home() {
  const [alarms, setAlarms] = useState<Alarm[]>([]);
  const [editing, setEditing] = useState<Alarm | null>(null);
  const [editingKind, setEditingKind] = useState<"alarm" | "nap">("alarm");
  const [chooserOpen, setChooserOpen] = useState(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [now, setNow] = useState(Date.now());
  // Per-item in-flight state so toggles/restarts show activity (never optimistic).
  const [busyIds, setBusyIds] = useState<Set<string>>(new Set());
  // Cards swiped away but not yet committed to the server (undoable).
  const [pendingDeleteIds, setPendingDeleteIds] = useState<Set<string>>(new Set());
  const deleteTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());
  const { setTheme } = useTheme();
  const { toast } = useToast();

  const setBusy = useCallback((id: string, on: boolean) => {
    setBusyIds((prev) => {
      const next = new Set(prev);
      if (on) next.add(id);
      else next.delete(id);
      return next;
    });
  }, []);

  const loadAlarms = useCallback(async () => {
    setLoading(true);
    try {
      setAlarms(await fetchAlarms());
    } catch (error) {
      console.error("Failed to load alarms:", error);
      toast({ variant: "destructive", title: "Error", description: "Failed to load alarms." });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    setTheme("dark");
    loadAlarms();
  }, [loadAlarms, setTheme]);

  // Tick once per second only when at least one nap is active.
  useEffect(() => {
    const hasActiveNap = alarms.some(
      (a) => a.kind === "nap" && a.enabled && a.nap_target_at &&
        new Date(a.nap_target_at).getTime() > Date.now(),
    );
    if (!hasActiveNap) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [alarms]);

  async function handleDelete(id: string) {
    setLoading(true);
    try {
      await deleteAlarm(id);
      await loadAlarms();
      toast({ title: "Deleted" });
    } catch (error) {
      console.error("Failed to delete:", error);
      toast({ variant: "destructive", title: "Error", description: "Failed to delete" });
    } finally {
      setLoading(false);
    }
  }

  function handleEdit(a: Alarm) {
    setEditing(a);
    setEditingKind(a.kind);
  }

  function handleFormClose() {
    setEditing(null);
    loadAlarms();
  }

  async function handleToggleEnabled(a: Alarm) {
    setBusy(a.id, true);
    try {
      await updateAlarm(a.id, { ...a, enabled: !a.enabled });
      await loadAlarms();
    } catch (error) {
      console.error("Failed to toggle:", error);
      toast({ variant: "destructive", title: "Error", description: "Failed to update" });
    } finally {
      setBusy(a.id, false);
    }
  }

  async function handleRestart(a: Alarm) {
    setBusy(a.id, true);
    try {
      await restartNap(a.id);
      await loadAlarms();
      toast({ title: "Timer restarted" });
    } catch (error) {
      console.error("Failed to restart:", error);
      toast({ variant: "destructive", title: "Error", description: "Failed to restart" });
    } finally {
      setBusy(a.id, false);
    }
  }

  // --- swipe-to-delete with undo -------------------------------------------
  // The card is hidden immediately, but the server delete is deferred so it can
  // be undone. If the user leaves the page first, pending deletes are flushed.
  const commitDelete = useCallback(async (id: string) => {
    deleteTimers.current.delete(id);
    try {
      await deleteAlarm(id);
      await loadAlarms();
    } catch (error) {
      console.error("Failed to delete:", error);
      toast({ variant: "destructive", title: "Error", description: "Failed to delete" });
    } finally {
      // Whether it succeeded or failed, stop hiding it (a reload reflects truth).
      setPendingDeleteIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  }, [loadAlarms, toast]);

  function undoDelete(id: string) {
    const timer = deleteTimers.current.get(id);
    if (timer) {
      clearTimeout(timer);
      deleteTimers.current.delete(id);
    }
    setPendingDeleteIds((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  }

  function handleSwipeDelete(a: Alarm) {
    setPendingDeleteIds((prev) => new Set(prev).add(a.id));
    const timer = setTimeout(() => commitDelete(a.id), DELETE_COMMIT_MS);
    deleteTimers.current.set(a.id, timer);
    toast({
      title: a.kind === "nap" ? "Timer deleted" : "Alarm deleted",
      duration: UNDO_TOAST_MS,
      action: (
        <ToastAction altText="Undo delete" onClick={() => undoDelete(a.id)}>
          Undo
        </ToastAction>
      ),
    });
  }

  // Flush any still-pending deletes when the page unmounts so nothing is lost.
  useEffect(() => {
    const timers = deleteTimers.current;
    return () => {
      timers.forEach((timer, id) => {
        clearTimeout(timer);
        deleteAlarm(id).catch((e) => console.error("Failed to flush delete:", e));
      });
      timers.clear();
    };
  }, []);

  function handleAddAlarm() {
    setEditingKind("alarm");
    setEditing({} as Alarm);
  }

  function handleAddNap() {
    setEditingKind("nap");
    setEditing({} as Alarm);
  }

  const groups = useMemo(() => {
    const visible = alarms.filter((a) => !pendingDeleteIds.has(a.id));
    const featuredId = getNextAlarm(visible)?.alarm.id;
    const sortedAlarms = visible
      .filter((a) => a.kind !== "nap")
      .sort((a, b) => {
        if (a.id === featuredId) return -1;
        if (b.id === featuredId) return 1;
        return a.time.localeCompare(b.time);
      });
    const sortedNaps = visible
      .filter((a) => a.kind === "nap")
      .sort((a, b) => {
        const aActive = a.enabled && !!a.nap_target_at && new Date(a.nap_target_at).getTime() > now;
        const bActive = b.enabled && !!b.nap_target_at && new Date(b.nap_target_at).getTime() > now;
        if (aActive && !bActive) return -1;
        if (!aActive && bActive) return 1;
        const aT = a.nap_target_at ? new Date(a.nap_target_at).getTime() : 0;
        const bT = b.nap_target_at ? new Date(b.nap_target_at).getTime() : 0;
        return bT - aT;
      });
    return { sortedAlarms, sortedNaps, featuredId };
  }, [alarms, now, pendingDeleteIds]);

  return (
    <div className="container mx-auto p-4 pb-24 max-w-md">
      <Toaster />
      <HomeClock />

      <div className="mt-6">
        {loading && alarms.length === 0 ? (
          <div className="flex justify-center items-center mt-16">
            <Loader2 className="animate-spin h-7 w-7 text-sage/70" />
          </div>
        ) : alarms.length === 0 ? (
          <EmptyAlarmsState />
        ) : (
          <>
            {groups.sortedAlarms.length > 0 && (
              <div>
                <div className="text-[9px] opacity-55 tracking-[0.12em] uppercase font-semibold mt-2">
                  Alarms
                </div>
                {groups.sortedAlarms.map((a) => (
                  <SwipeToDelete key={a.id} onDelete={() => handleSwipeDelete(a)}>
                    <AlarmCard
                      alarm={a}
                      featured={a.id === groups.featuredId && a.enabled}
                      busy={busyIds.has(a.id)}
                      onToggleEnabled={handleToggleEnabled}
                      onEdit={handleEdit}
                    />
                  </SwipeToDelete>
                ))}
              </div>
            )}
            {groups.sortedNaps.length > 0 && (
              <div className="mt-6">
                <div className="text-[9px] opacity-55 tracking-[0.12em] uppercase font-semibold">
                  Timers
                </div>
                {groups.sortedNaps.map((a) => (
                  <SwipeToDelete key={a.id} onDelete={() => handleSwipeDelete(a)}>
                    <NapCard
                      alarm={a}
                      now={now}
                      featured={a.id === groups.featuredId && a.enabled}
                      busy={busyIds.has(a.id)}
                      onToggleEnabled={handleToggleEnabled}
                      onEdit={handleEdit}
                      onRestart={handleRestart}
                    />
                  </SwipeToDelete>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      <button
        onClick={() => setChooserOpen(true)}
        aria-label="Add new"
        className="fixed right-5 z-40 grid place-items-center w-14 h-14 rounded-full bg-sage text-background shadow-[0_8px_22px_hsl(var(--sage)/0.3)] active:scale-95 transition-transform"
        style={{ bottom: "calc(5rem + env(safe-area-inset-bottom, 0px))" }}
      >
        <Plus className="h-6 w-6" strokeWidth={2.5} />
      </button>

      <CreateChooser
        open={chooserOpen}
        onClose={() => setChooserOpen(false)}
        onPickAlarm={handleAddAlarm}
        onPickNap={handleAddNap}
      />

      {editing && editingKind === "alarm" && (
        <AlarmDrawer
          key={editing.id ?? "new-alarm"}
          alarm={editing}
          open={true}
          onClose={handleFormClose}
          onDelete={editing.id ? () => handleDelete(editing.id) : undefined}
        />
      )}
      {editing && editingKind === "nap" && (
        <NapDrawer
          key={editing.id ?? "new-nap"}
          alarm={editing}
          open={true}
          onClose={handleFormClose}
          onDelete={editing.id ? () => handleDelete(editing.id) : undefined}
        />
      )}
    </div>
  );
}
