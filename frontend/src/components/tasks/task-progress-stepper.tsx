"use client";

import { Check, Circle, Loader2, Pause, X } from "lucide-react";
import { cn, formatRelativeTime } from "@/lib/utils";
import { useElapsedTime } from "@/lib/hooks/use-elapsed-time";
import type { TaskStatus } from "@/types/task";

interface StatusEntry {
  status: string;
  at: string;
}

interface TaskProgressStepperProps {
  status: TaskStatus;
  statusHistory: StatusEntry[] | null;
  createdAt: string;
}

const STEPS = ["submitted", "working", "completed"] as const;
const TERMINAL_FAIL = ["failed", "canceled", "rejected"];

function getStepIndex(status: TaskStatus): number {
  if (status === "submitted" || status === "pending_payment") return 0;
  if (status === "working" || status === "input_required") return 1;
  if (status === "completed") return 2;
  if (TERMINAL_FAIL.includes(status)) return 1;
  return 0;
}

function getTimestampForStep(
  step: string,
  history: StatusEntry[] | null,
  createdAt: string
): string | null {
  if (step === "submitted") return createdAt;
  if (!history) return null;
  const entry = history.find((h) => h.status === step);
  return entry?.at ?? null;
}

export function TaskProgressStepper({
  status,
  statusHistory,
  createdAt,
}: TaskProgressStepperProps) {
  const isActive = !["completed", ...TERMINAL_FAIL].includes(status);
  // For completed/terminal tasks, use the last status history entry as end time
  const endTime = !isActive && statusHistory?.length
    ? statusHistory[statusHistory.length - 1].at
    : null;
  const elapsed = useElapsedTime(createdAt, isActive, endTime);
  const currentIndex = getStepIndex(status);
  const isFailed = TERMINAL_FAIL.includes(status);

  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex items-center justify-between">
        <div className="flex flex-1 items-center">
          {STEPS.map((step, i) => {
            const isPast = i < currentIndex;
            const isCurrent = i === currentIndex;
            const isFutureStep = i > currentIndex;
            const timestamp = getTimestampForStep(step, statusHistory, createdAt);

            return (
              <div key={step} className="flex flex-1 items-center">
                <div className="flex flex-col items-center gap-1">
                  <div
                    className={cn(
                      "flex h-8 w-8 items-center justify-center rounded-full border-2 transition-colors",
                      isPast && "border-green-500 bg-green-500/15",
                      isCurrent && !isFailed && status !== "input_required" && "border-primary bg-primary/15",
                      isCurrent && isFailed && "border-red-500 bg-red-500/15",
                      isCurrent && status === "input_required" && "border-orange-500 bg-orange-500/15",
                      isFutureStep && "border-muted-foreground/30 bg-muted/30"
                    )}
                  >
                    {isPast && <Check className="h-4 w-4 text-green-500" />}
                    {isCurrent && !isFailed && status !== "input_required" && status !== "completed" && (
                      <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    )}
                    {isCurrent && status === "input_required" && (
                      <Pause className="h-4 w-4 text-orange-500" />
                    )}
                    {isCurrent && isFailed && <X className="h-4 w-4 text-red-500" />}
                    {isCurrent && status === "completed" && (
                      <Check className="h-4 w-4 text-green-500" />
                    )}
                    {isFutureStep && <Circle className="h-3 w-3 text-muted-foreground/40" />}
                  </div>

                  <span
                    className={cn(
                      "text-xs font-medium capitalize",
                      isPast && "text-green-500",
                      isCurrent && !isFailed && "text-foreground",
                      isCurrent && isFailed && "text-red-500",
                      isFutureStep && "text-muted-foreground/50"
                    )}
                  >
                    {isCurrent && isFailed ? status.replace(/_/g, " ") : step}
                  </span>

                  {timestamp && (isPast || isCurrent) && (
                    <span className="text-[10px] text-muted-foreground">
                      {formatRelativeTime(timestamp)}
                    </span>
                  )}
                </div>

                {i < STEPS.length - 1 && (
                  <div
                    className={cn(
                      "mx-2 h-0.5 flex-1",
                      i < currentIndex ? "bg-green-500" : "bg-muted-foreground/20"
                    )}
                  />
                )}
              </div>
            );
          })}
        </div>

        {elapsed && (
          <div className="ml-4 flex flex-col items-end text-xs">
            <span className="text-muted-foreground">Elapsed</span>
            <span className={cn("font-mono font-medium", isActive && "text-primary")}>
              {elapsed}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
