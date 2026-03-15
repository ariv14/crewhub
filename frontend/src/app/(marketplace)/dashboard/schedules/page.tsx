// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  Clock,
  Plus,
  Trash2,
  Pause,
  Play,
  AlertTriangle,
} from "lucide-react";
import {
  useMySchedules,
  useDeleteSchedule,
  usePauseSchedule,
  useResumeSchedule,
  useCreateSchedule,
} from "@/lib/hooks/use-schedules";
import { ROUTES } from "@/lib/constants";
import { formatRelativeTime } from "@/lib/utils";
import { EmptyState } from "@/components/shared/empty-state";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import type { Schedule, ScheduleCreate } from "@/types/schedule";

const CRON_PRESETS = [
  { label: "Every hour", value: "0 * * * *" },
  { label: "Daily at 9am", value: "0 9 * * *" },
  { label: "Weekly (Mon 9am)", value: "0 9 * * 1" },
  { label: "Monthly (1st, 9am)", value: "0 9 1 * *" },
];

function describeCron(expr: string): string {
  const presetMatch = CRON_PRESETS.find((p) => p.value === expr);
  if (presetMatch) return presetMatch.label;
  const parts = expr.split(" ");
  if (parts.length !== 5) return "";
  const [min, hour, dom, , dow] = parts;
  const time = hour !== "*" && min !== "*" ? `at ${hour}:${min.padStart(2, "0")}` : "";
  if (dow !== "*" && dom === "*") {
    const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    const dayName = days[parseInt(dow)] ?? `day ${dow}`;
    return `Every ${dayName} ${time}`.trim();
  }
  if (dom !== "*") return `Monthly on day ${dom} ${time}`.trim();
  if (hour !== "*" && min !== "*") return `Daily ${time}`;
  if (min === "0" && hour === "*") return "Every hour";
  return "";
}

function ScheduleCard({
  schedule,
  onDelete,
  onPause,
  onResume,
}: {
  schedule: Schedule;
  onDelete: (id: string) => void;
  onPause: (id: string) => void;
  onResume: (id: string) => void;
}) {
  const isPaused = !schedule.is_active;
  const hasFailures = schedule.consecutive_failures > 0;

  return (
    <div className="group relative rounded-xl border bg-card p-5 transition-all hover:border-primary/30 hover:shadow-sm">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div
            className={`flex h-10 w-10 items-center justify-center rounded-lg text-lg ${
              isPaused ? "bg-zinc-500/10" : "bg-primary/10"
            }`}
          >
            <Clock className={`h-5 w-5 ${isPaused ? "text-zinc-400" : ""}`} />
          </div>
          <div>
            <h3 className="font-semibold">{schedule.name}</h3>
            <p className="text-xs text-muted-foreground">
              {schedule.schedule_type} · {schedule.cron_expression}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <Badge
            variant="outline"
            className={`text-[10px] ${isPaused ? "text-zinc-400" : "text-green-400"}`}
          >
            {isPaused ? "Paused" : "Active"}
          </Badge>
          {hasFailures && (
            <Badge variant="outline" className="text-[10px] text-amber-400">
              <AlertTriangle className="mr-1 h-3 w-3" />
              {schedule.consecutive_failures} failures
            </Badge>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() =>
              isPaused ? onResume(schedule.id) : onPause(schedule.id)
            }
          >
            {isPaused ? (
              <Play className="h-3.5 w-3.5" />
            ) : (
              <Pause className="h-3.5 w-3.5" />
            )}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 opacity-0 group-hover:opacity-100"
            onClick={() => onDelete(schedule.id)}
          >
            <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
          </Button>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
        <span>{schedule.run_count} runs</span>
        {schedule.next_run_at && (
          <span>Next: {formatRelativeTime(schedule.next_run_at)}</span>
        )}
        {schedule.last_run_at && (
          <span>Last: {formatRelativeTime(schedule.last_run_at)}</span>
        )}
        {schedule.max_runs && (
          <span>
            Limit: {schedule.run_count}/{schedule.max_runs}
          </span>
        )}
      </div>
    </div>
  );
}

function CreateScheduleForm({
  onClose,
  prefill,
}: {
  onClose: () => void;
  prefill?: { type?: string; targetId?: string; name?: string };
}) {
  const createSchedule = useCreateSchedule();
  const [name, setName] = useState(
    prefill?.name ? `Schedule: ${prefill.name}` : ""
  );
  const [scheduleType, setScheduleType] = useState<string>(
    prefill?.type || "workflow"
  );
  const [targetId, setTargetId] = useState(prefill?.targetId || "");
  const [cronExpression, setCronExpression] = useState("0 9 * * *");
  const [inputMessage, setInputMessage] = useState("");
  const [creditMinimum, setCreditMinimum] = useState(0);

  async function handleCreate() {
    if (!name.trim()) return;

    const data: ScheduleCreate = {
      name: name.trim(),
      schedule_type: scheduleType as ScheduleCreate["schedule_type"],
      target_id: targetId || undefined,
      cron_expression: cronExpression,
      input_message: inputMessage || undefined,
      credit_minimum: creditMinimum,
    };

    await createSchedule.mutateAsync(data);
    onClose();
  }

  return (
    <div className="space-y-3">
        <div>
          <Label htmlFor="sched-name">Name</Label>
          <Input
            id="sched-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Daily Translation"
            className="mt-1"
          />
        </div>

        <div>
          <Label htmlFor="sched-type">Type</Label>
          <select
            id="sched-type"
            value={scheduleType}
            onChange={(e) => setScheduleType(e.target.value)}
            className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
          >
            <option value="workflow">Workflow</option>
            <option value="crew">Crew</option>
            <option value="single_task">Single Task</option>
          </select>
        </div>

        {(scheduleType === "workflow" || scheduleType === "crew") && (
          <div>
            <Label htmlFor="sched-target">Target ID</Label>
            <Input
              id="sched-target"
              value={targetId}
              onChange={(e) => setTargetId(e.target.value)}
              placeholder="Workflow or Crew UUID"
              className="mt-1"
            />
          </div>
        )}

        <div>
          <Label>Recurrence</Label>
          <div className="mt-1 flex flex-wrap gap-2">
            {CRON_PRESETS.map((p) => (
              <button
                key={p.value}
                onClick={() => setCronExpression(p.value)}
                className={`rounded-lg border px-3 py-1.5 text-xs transition-all ${
                  cronExpression === p.value
                    ? "border-primary bg-primary/5"
                    : "hover:border-primary/50"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
          <Input
            value={cronExpression}
            onChange={(e) => setCronExpression(e.target.value)}
            placeholder="Custom cron expression"
            className="mt-2"
          />
          {cronExpression && describeCron(cronExpression) && (
            <p className="text-xs text-muted-foreground">
              Runs: <span className="font-medium text-foreground">{describeCron(cronExpression)}</span>
            </p>
          )}
        </div>

        <div>
          <Label htmlFor="sched-input">Input Message</Label>
          <Textarea
            id="sched-input"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="Message to send each run"
            className="mt-1"
            rows={2}
          />
        </div>

        <div>
          <Label htmlFor="sched-credit">
            Credit minimum (skip if balance below)
          </Label>
          <Input
            id="sched-credit"
            type="number"
            min={0}
            value={creditMinimum}
            onChange={(e) => setCreditMinimum(Number(e.target.value))}
            className="mt-1 w-32"
          />
        </div>

        <div className="flex items-center gap-2">
          <Button
            onClick={handleCreate}
            disabled={!name.trim() || createSchedule.isPending}
          >
            {createSchedule.isPending ? "Creating..." : "Create Schedule"}
          </Button>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
        </div>
    </div>
  );
}

export default function SchedulesPage() {
  const searchParams = useSearchParams();
  const { data, isLoading } = useMySchedules();
  const deleteSchedule = useDeleteSchedule();
  const pauseSchedule = usePauseSchedule();
  const resumeSchedule = useResumeSchedule();
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const schedules = data?.schedules ?? [];

  // Check for prefill params from "Schedule This" button
  const prefillType = searchParams.get("type") || undefined;
  const prefillTarget = searchParams.get("target") || undefined;
  const prefillName = searchParams.get("name") || undefined;
  const hasPrefill = !!prefillType;

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Schedules</h1>
          <p className="mt-1 text-muted-foreground">
            Run agents, workflows, or crews on a recurring basis
          </p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="mr-2 h-4 w-4" />
          New Schedule
        </Button>
      </div>

      <Sheet open={showCreate || (hasPrefill && schedules.length === 0 && !deleteTarget)} onOpenChange={(open) => !open && setShowCreate(false)}>
        <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
          <SheetHeader>
            <SheetTitle>New Schedule</SheetTitle>
          </SheetHeader>
          <div className="mt-6">
            <CreateScheduleForm
              onClose={() => setShowCreate(false)}
              prefill={
                hasPrefill
                  ? {
                      type: prefillType,
                      targetId: prefillTarget,
                      name: prefillName,
                    }
                  : undefined
              }
            />
          </div>
        </SheetContent>
      </Sheet>

      <div className="mt-6">
        {!isLoading && schedules.length === 0 && !showCreate ? (
          <EmptyState
            icon={Clock}
            title="No schedules yet"
            description="Schedule workflows, crews, or individual tasks to run automatically on a recurring basis."
            action={
              <Button onClick={() => setShowCreate(true)}>
                Create Schedule
              </Button>
            }
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {schedules.map((schedule) => (
              <ScheduleCard
                key={schedule.id}
                schedule={schedule}
                onDelete={setDeleteTarget}
                onPause={(id) => pauseSchedule.mutate(id)}
                onResume={(id) => resumeSchedule.mutate(id)}
              />
            ))}
          </div>
        )}
      </div>

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="Delete Schedule"
        description="This will permanently delete this schedule. Future runs will not execute."
        confirmLabel="Delete"
        variant="destructive"
        loading={deleteSchedule.isPending}
        onConfirm={() => {
          if (deleteTarget) {
            deleteSchedule.mutate(deleteTarget, {
              onSuccess: () => setDeleteTarget(null),
              onError: () => setDeleteTarget(null),
            });
          }
        }}
      />
    </div>
  );
}
