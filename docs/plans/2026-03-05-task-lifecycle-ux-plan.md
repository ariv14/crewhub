# Task Lifecycle UX Enhancement — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Overhaul the task detail page with a visual progress stepper, markdown-rendered artifacts, live elapsed timer, agent identity card, retry/duplicate actions, and agent performance badges.

**Architecture:** Enhance existing task detail page (Approach C — dashboard-style cards). Add one new component (`TaskProgressStepper`), one new hook (`useElapsedTime`), install `react-markdown` + `remark-gfm`. All agent performance data already exists in the backend (`success_rate`, `avg_latency_ms`, `total_tasks_completed` on Agent model) — no backend changes needed.

**Tech Stack:** Next.js, React, TanStack Query, Tailwind CSS, shadcn/ui, react-markdown, remark-gfm, lucide-react

---

### Task 1: Install markdown dependencies

**Files:**
- Modify: `frontend/package.json`

**Step 1: Install react-markdown and remark-gfm**

Run:
```bash
cd frontend && npm install react-markdown remark-gfm
```

**Step 2: Verify installation**

Run:
```bash
cd frontend && node -e "require('react-markdown'); require('remark-gfm'); console.log('OK')"
```
Expected: `OK`

**Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore: add react-markdown and remark-gfm dependencies"
```

---

### Task 2: Create `useElapsedTime` hook

**Files:**
- Create: `frontend/src/lib/hooks/use-elapsed-time.ts`

**Step 1: Create the hook**

```typescript
// frontend/src/lib/hooks/use-elapsed-time.ts
import { useState, useEffect } from "react";

export function useElapsedTime(startTime: string | null, active: boolean) {
  const [elapsed, setElapsed] = useState("");

  useEffect(() => {
    if (!startTime || !active) {
      if (startTime && !active) {
        // Show final elapsed time (static)
        setElapsed(formatElapsed(Date.now() - new Date(startTime).getTime()));
      }
      return;
    }

    function tick() {
      const ms = Date.now() - new Date(startTime!).getTime();
      setElapsed(formatElapsed(ms));
    }

    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [startTime, active]);

  return elapsed;
}

function formatElapsed(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  if (totalSeconds < 60) return `${totalSeconds}s`;
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes < 60) return `${minutes}m ${seconds}s`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m`;
}
```

**Step 2: Verify build**

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/src/lib/hooks/use-elapsed-time.ts
git commit -m "feat: add useElapsedTime hook for live task timer"
```

---

### Task 3: Create `TaskProgressStepper` component

**Files:**
- Create: `frontend/src/components/tasks/task-progress-stepper.tsx`

**Step 1: Create the component**

```tsx
// frontend/src/components/tasks/task-progress-stepper.tsx
"use client";

import { Check, Circle, Loader2, Pause, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatRelativeTime } from "@/lib/utils";
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
  // failed/canceled/rejected — stays at wherever it failed
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
  const elapsed = useElapsedTime(createdAt, isActive);
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
                  {/* Icon */}
                  <div
                    className={cn(
                      "flex h-8 w-8 items-center justify-center rounded-full border-2 transition-colors",
                      isPast && "border-green-500 bg-green-500/15",
                      isCurrent && !isFailed && "border-primary bg-primary/15",
                      isCurrent && isFailed && "border-red-500 bg-red-500/15",
                      isCurrent && status === "input_required" && "border-orange-500 bg-orange-500/15",
                      isFutureStep && "border-muted-foreground/30 bg-muted/30"
                    )}
                  >
                    {isPast && <Check className="h-4 w-4 text-green-500" />}
                    {isCurrent && !isFailed && status !== "input_required" && (
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

                  {/* Label */}
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

                  {/* Timestamp */}
                  {timestamp && (isPast || isCurrent) && (
                    <span className="text-[10px] text-muted-foreground">
                      {formatRelativeTime(timestamp)}
                    </span>
                  )}
                </div>

                {/* Connector line */}
                {i < STEPS.length - 1 && (
                  <div
                    className={cn(
                      "mx-2 h-0.5 flex-1",
                      i < currentIndex
                        ? "bg-green-500"
                        : "bg-muted-foreground/20"
                    )}
                  />
                )}
              </div>
            );
          })}
        </div>

        {/* Elapsed time */}
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
```

**Step 2: Verify build**

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/src/components/tasks/task-progress-stepper.tsx
git commit -m "feat: add TaskProgressStepper component with live elapsed timer"
```

---

### Task 4: Enhance `TaskArtifactsDisplay` with markdown + copy

**Files:**
- Modify: `frontend/src/components/tasks/task-artifacts-display.tsx`

**Step 1: Rewrite the artifacts display**

Replace the entire file contents with:

```tsx
// frontend/src/components/tasks/task-artifacts-display.tsx
"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Check, ChevronDown, ChevronRight, Copy, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Artifact } from "@/types/task";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <Button variant="ghost" size="sm" onClick={handleCopy} className="h-7 gap-1.5 text-xs">
      {copied ? (
        <>
          <Check className="h-3 w-3" />
          Copied
        </>
      ) : (
        <>
          <Copy className="h-3 w-3" />
          Copy
        </>
      )}
    </Button>
  );
}

function ArtifactPart({ part }: { part: { type: string; content: string | null; data: Record<string, unknown> | null; mime_type: string | null } }) {
  const [showRaw, setShowRaw] = useState(false);

  if (part.type === "text" && part.content) {
    return (
      <div className="space-y-2">
        <div className="prose prose-sm dark:prose-invert max-w-none prose-pre:bg-muted prose-pre:text-sm prose-code:text-sm">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{part.content}</ReactMarkdown>
        </div>
        <div className="flex items-center gap-2 border-t pt-2">
          <CopyButton text={part.content} />
          <button
            type="button"
            onClick={() => setShowRaw(!showRaw)}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            {showRaw ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
            {showRaw ? "Hide raw" : "Show raw"}
          </button>
        </div>
        {showRaw && (
          <pre className="overflow-auto rounded bg-muted p-3 text-xs">{part.content}</pre>
        )}
      </div>
    );
  }

  if (part.type === "file" && part.mime_type?.startsWith("image/") && part.content) {
    return (
      <div className="mt-2">
        <img
          src={part.content}
          alt="Artifact image"
          className="max-h-64 rounded border"
        />
      </div>
    );
  }

  if (part.type === "data" && part.data) {
    const json = JSON.stringify(part.data, null, 2);
    return (
      <div className="space-y-2">
        <pre className="overflow-auto rounded bg-muted p-3 text-xs">{json}</pre>
        <CopyButton text={json} />
      </div>
    );
  }

  return null;
}

interface TaskArtifactsDisplayProps {
  artifacts: Artifact[];
}

export function TaskArtifactsDisplay({ artifacts }: TaskArtifactsDisplayProps) {
  if (!artifacts || artifacts.length === 0) return null;

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold">Output</h3>
      {artifacts.map((artifact, i) => (
        <div key={i} className="rounded-lg border p-4">
          {artifact.name && (
            <div className="mb-3 flex items-center gap-2 text-sm font-medium">
              <FileText className="h-4 w-4" />
              {artifact.name}
            </div>
          )}
          <div className="space-y-4">
            {artifact.parts.map((part, j) => (
              <ArtifactPart key={j} part={part} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
```

**Step 2: Verify build**

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/src/components/tasks/task-artifacts-display.tsx
git commit -m "feat: render artifact markdown with copy-to-clipboard and raw toggle"
```

---

### Task 5: Enhance `TaskMessageThread` with labels and timestamps

**Files:**
- Modify: `frontend/src/components/tasks/task-message-thread.tsx`

**Step 1: Update the message thread**

Replace the entire file contents with:

```tsx
// frontend/src/components/tasks/task-message-thread.tsx
import { cn, formatRelativeTime } from "@/lib/utils";
import type { TaskMessage } from "@/types/task";

interface TaskMessageThreadProps {
  messages: TaskMessage[];
  agentName?: string;
  statusHistory?: { status: string; at: string }[] | null;
}

export function TaskMessageThread({ messages, agentName, statusHistory }: TaskMessageThreadProps) {
  // Use created_at from status_history to estimate message timestamps
  const createdAt = statusHistory?.find((h) => h.status === "submitted")?.at;

  return (
    <div className="space-y-4">
      {messages.map((msg, i) => {
        const isUser = msg.role === "user";
        const label = isUser ? "You" : agentName || "Agent";
        // First message timestamp = task created, agent responses = working timestamp
        const timestamp =
          i === 0 && createdAt
            ? createdAt
            : !isUser
              ? statusHistory?.find((h) => h.status === "working" || h.status === "completed")?.at
              : null;

        return (
          <div
            key={i}
            className={cn(
              "rounded-lg border p-4",
              isUser ? "ml-8 bg-primary/5" : "mr-8 bg-muted/30"
            )}
          >
            <div className="mb-1 flex items-center justify-between">
              <p className="text-xs font-medium text-muted-foreground">
                {label}
              </p>
              {timestamp && (
                <span className="text-[10px] text-muted-foreground">
                  {formatRelativeTime(timestamp)}
                </span>
              )}
            </div>
            {msg.parts.map((part, j) => (
              <div key={j}>
                {part.type === "text" && part.content && (
                  <p className="whitespace-pre-wrap text-sm">{part.content}</p>
                )}
                {part.type === "data" && part.data && (
                  <pre className="mt-1 overflow-auto rounded bg-muted p-2 text-xs">
                    {JSON.stringify(part.data, null, 2)}
                  </pre>
                )}
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}
```

**Step 2: Verify build**

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/src/components/tasks/task-message-thread.tsx
git commit -m "feat: show 'You'/agent name labels and timestamps in message thread"
```

---

### Task 6: Enhance processing state banner

**Files:**
- Modify: `frontend/src/app/(marketplace)/dashboard/tasks/[id]/task-detail-client.tsx`

This is the working/submitted state banner. We will update it in the full task-detail-client rewrite in Task 8. For now, this task is a no-op — handled in Task 8.

---

### Task 7: Add retry/duplicate actions to task API

**Files:**
- No new API endpoints needed — retry/duplicate creates a new task via existing `POST /tasks/`
- We just need a "Retry" / "Run Again" button that navigates to `/dashboard/tasks/new` with pre-filled params

The approach: navigate to `/dashboard/tasks/new?agent={agentId}&skill={skillId}&message={encodedMessage}` and have the create page read those params.

**Step 1: Update `NewTaskForm` to accept `skill` and `message` URL params**

In `frontend/src/app/(marketplace)/dashboard/tasks/new/page.tsx`, after line 95 (`const preselectedAgent = ...`), add:

```typescript
const preselectedSkill = searchParams.get("skill") ?? "";
const preselectedMessage = searchParams.get("message") ?? "";
```

Update initial state for `skillId` and `message`:

```typescript
const [skillId, setSkillId] = useState(preselectedSkill);
const [message, setMessage] = useState(preselectedMessage);
```

**Step 2: Add ROUTES helper for retry URL**

In `frontend/src/lib/constants.ts`, add to the ROUTES object:

```typescript
retryTask: (agentId: string, skillId: string, message: string) =>
  `/dashboard/tasks/new?agent=${agentId}&skill=${encodeURIComponent(skillId)}&message=${encodeURIComponent(message)}`,
```

**Step 3: Verify build**

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds

**Step 4: Commit**

```bash
git add frontend/src/app/\(marketplace\)/dashboard/tasks/new/page.tsx frontend/src/lib/constants.ts
git commit -m "feat: support pre-filling task creation from URL params (retry/duplicate)"
```

---

### Task 8: Rewrite `task-detail-client.tsx` with all enhancements

**Files:**
- Modify: `frontend/src/app/(marketplace)/dashboard/tasks/[id]/task-detail-client.tsx`

**Step 1: Rewrite the task detail client**

Replace the entire file contents with:

```tsx
// frontend/src/app/(marketplace)/dashboard/tasks/[id]/task-detail-client.tsx
"use client";

import { useState } from "react";
import { AlertCircle, ArrowLeft, Clock, Copy, RefreshCw, Send, XCircle } from "lucide-react";
import { SpinningLogo } from "@/components/shared/spinning-logo";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useTask, useCancelTask, useRateTask, useSendMessage } from "@/lib/hooks/use-tasks";
import { useAgent } from "@/lib/hooks/use-agents";
import { useElapsedTime } from "@/lib/hooks/use-elapsed-time";
import { formatCredits, formatDate } from "@/lib/utils";
import { ROUTES } from "@/lib/constants";
import { TaskStatusBadge } from "@/components/tasks/task-status-badge";
import { TaskMessageThread } from "@/components/tasks/task-message-thread";
import { TaskProgressStepper } from "@/components/tasks/task-progress-stepper";
import { TaskArtifactsDisplay } from "@/components/tasks/task-artifacts-display";
import { TaskRatingForm } from "@/components/tasks/task-rating-form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

const TERMINAL_STATUSES = ["completed", "failed", "canceled", "rejected"];
const PLATFORM_FEE_RATE = 0.1;

function AgentIdentityCard({
  agentId,
  skillName,
}: {
  agentId: string;
  skillName: string | null;
}) {
  const { data: agent } = useAgent(agentId);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">Agent</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div>
          <p className="font-medium">{agent?.name ?? agentId.slice(0, 8)}</p>
          {skillName && (
            <p className="text-xs text-muted-foreground">{skillName}</p>
          )}
        </div>

        {agent && (
          <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
            {agent.total_tasks_completed > 0 && (
              <span>{agent.total_tasks_completed} tasks</span>
            )}
            {agent.success_rate > 0 && (
              <span>{Math.round(agent.success_rate * 100)}% success</span>
            )}
            {agent.avg_latency_ms > 0 && (
              <span>{(agent.avg_latency_ms / 1000).toFixed(1)}s avg</span>
            )}
            {agent.reputation_score > 0 && (
              <span>{"★".repeat(Math.round(agent.reputation_score))}</span>
            )}
          </div>
        )}

        <Button variant="outline" size="sm" className="w-full" asChild>
          <Link href={ROUTES.agentDetail(agentId)}>View Agent</Link>
        </Button>
      </CardContent>
    </Card>
  );
}

function ProcessingBanner({ createdAt }: { createdAt: string }) {
  const elapsed = useElapsedTime(createdAt, true);

  return (
    <div className="rounded-lg border bg-muted/30 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <SpinningLogo spinning size="sm" />
          <span className="text-sm font-medium">Agent is working on your task...</span>
        </div>
        {elapsed && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" />
            <span className="font-mono">{elapsed}</span>
          </div>
        )}
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-muted">
        <div className="h-full w-1/3 animate-pulse rounded-full bg-primary/60" />
      </div>
    </div>
  );
}

export default function TaskDetailClient({ id: serverId }: { id: string }) {
  const params = useParams<{ id: string }>();
  const id = params.id && params.id !== "__fallback" ? params.id : serverId;

  const { data: task, isLoading, isError } = useTask(id);
  const cancelTask = useCancelTask();
  const rateTask = useRateTask(id);
  const sendMessage = useSendMessage(id);
  const [message, setMessage] = useState("");

  if (isLoading) {
    return (
      <div className="flex min-h-[300px] items-center justify-center">
        <SpinningLogo spinning size="lg" />
      </div>
    );
  }

  if (isError || !task) {
    return (
      <div className="flex min-h-[300px] flex-col items-center justify-center gap-4">
        <AlertCircle className="h-10 w-10 text-muted-foreground" />
        <div className="text-center">
          <p className="font-medium">Task not found</p>
          <p className="mt-1 text-sm text-muted-foreground">
            This task doesn&apos;t exist or you don&apos;t have access to it.
          </p>
        </div>
        <Button variant="outline" size="sm" asChild>
          <Link href={ROUTES.myTasks}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Tasks
          </Link>
        </Button>
      </div>
    );
  }

  const canCancel = ["submitted", "pending_payment", "working"].includes(task.status);
  const canRate = task.status === "completed" && task.client_rating == null;
  const canMessage = task.status === "input_required";
  const isProcessing = ["submitted", "working"].includes(task.status);
  const isTerminal = TERMINAL_STATUSES.includes(task.status);
  const canRetry = ["failed", "canceled", "rejected"].includes(task.status);
  const canDuplicate = task.status === "completed";

  // Extract original user message for retry/duplicate
  const userMessage = task.messages?.find((m) => m.role === "user");
  const originalText = userMessage?.parts?.find((p) => p.type === "text")?.content ?? "";

  // Cost breakdown
  const charged = task.credits_charged || 0;
  const platformFee = charged > 0 ? charged * PLATFORM_FEE_RATE : 0;

  function handleSend() {
    if (!message.trim()) return;
    sendMessage.mutate(
      { role: "user", parts: [{ type: "text", content: message }] },
      { onSuccess: () => setMessage("") }
    );
  }

  return (
    <div>
      <Button variant="ghost" size="sm" className="mb-4" asChild>
        <Link href={ROUTES.myTasks}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Tasks
        </Link>
      </Button>

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-3 text-2xl font-bold">
            Task
            <span className="font-mono text-base text-muted-foreground">
              {task.id.slice(0, 8)}
            </span>
            <TaskStatusBadge status={task.status} />
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Created {formatDate(task.created_at)}
            {task.completed_at && ` · Completed ${formatDate(task.completed_at)}`}
          </p>
        </div>
        <div className="flex gap-2">
          {canRetry && (
            <Button variant="outline" size="sm" asChild>
              <Link href={ROUTES.retryTask(task.provider_agent_id, task.skill_id, originalText)}>
                <RefreshCw className="mr-2 h-4 w-4" />
                Retry
              </Link>
            </Button>
          )}
          {canDuplicate && (
            <Button variant="outline" size="sm" asChild>
              <Link href={ROUTES.retryTask(task.provider_agent_id, task.skill_id, originalText)}>
                <Copy className="mr-2 h-4 w-4" />
                Run Again
              </Link>
            </Button>
          )}
          {canCancel && (
            <Button
              variant="destructive"
              size="sm"
              onClick={() => cancelTask.mutate(task.id)}
              disabled={cancelTask.isPending}
            >
              <XCircle className="mr-2 h-4 w-4" />
              Cancel
            </Button>
          )}
        </div>
      </div>

      {/* Progress Stepper */}
      <div className="mt-4">
        <TaskProgressStepper
          status={task.status}
          statusHistory={task.status_history}
          createdAt={task.created_at}
        />
      </div>

      {/* Processing Banner */}
      {isProcessing && (
        <div className="mt-4">
          <ProcessingBanner createdAt={task.created_at} />
        </div>
      )}

      {/* Main Content */}
      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <TaskMessageThread
            messages={task.messages}
            agentName={task.provider_agent_name ?? undefined}
            statusHistory={task.status_history}
          />

          {task.status === "completed" &&
            (!task.artifacts || task.artifacts.length === 0) &&
            task.messages.length <= 1 && (
              <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                Task completed — no output was returned by the agent.
              </div>
            )}

          <TaskArtifactsDisplay artifacts={task.artifacts} />

          {canMessage && (
            <div className="flex gap-2">
              <Input
                placeholder="Type your response..."
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
              />
              <Button onClick={handleSend} disabled={sendMessage.isPending}>
                <Send className="h-4 w-4" />
              </Button>
            </div>
          )}

          {canRate && (
            <TaskRatingForm
              onSubmit={(score, comment) =>
                rateTask.mutate({ score, comment })
              }
              loading={rateTask.isPending}
            />
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          <AgentIdentityCard
            agentId={task.provider_agent_id}
            skillName={task.skill_name}
          />

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Quoted</span>
                <span>{formatCredits(task.credits_quoted)} credits</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Charged</span>
                <span>{formatCredits(task.credits_charged)} credits</span>
              </div>
              {platformFee > 0 && (
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">Platform fee</span>
                  <span className="text-muted-foreground">
                    incl. {formatCredits(platformFee)}
                  </span>
                </div>
              )}
              <Separator />
              <div className="flex justify-between">
                <span className="text-muted-foreground">Payment</span>
                <span className="capitalize">{task.payment_method}</span>
              </div>
              {task.latency_ms != null && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Latency</span>
                  <span>
                    {task.latency_ms > 1000
                      ? `${(task.latency_ms / 1000).toFixed(1)}s`
                      : `${task.latency_ms}ms`}
                  </span>
                </div>
              )}
              {task.client_rating != null && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Rating</span>
                  <span>{"★".repeat(task.client_rating)}{"☆".repeat(5 - task.client_rating)}/5</span>
                </div>
              )}
            </CardContent>
          </Card>

          {task.status_history && task.status_history.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Timeline</CardTitle>
              </CardHeader>
              <CardContent>
                <TaskTimeline history={task.status_history} />
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

// Inline TaskTimeline since it's only used here
function TaskTimeline({ history }: { history: { status: string; at: string }[] }) {
  return (
    <div className="space-y-0">
      {history.map((entry, i) => {
        const isLast = i === history.length - 1;
        const time = new Date(entry.at);
        const statusColors: Record<string, string> = {
          submitted: "text-blue-500",
          working: "text-purple-500",
          completed: "text-green-500",
          failed: "text-red-500",
          canceled: "text-muted-foreground",
          rejected: "text-red-500",
          input_required: "text-orange-500",
          pending_payment: "text-yellow-500",
        };
        const color = statusColors[entry.status] ?? "text-muted-foreground";

        return (
          <div key={i} className="flex gap-3">
            <div className="flex flex-col items-center">
              <div className={cn("h-2 w-2 rounded-full mt-1.5", color.replace("text-", "bg-"))} />
              {!isLast && <div className="my-1 w-px flex-1 bg-border" />}
            </div>
            <div className="pb-3">
              <p className={cn("text-xs font-medium capitalize", color)}>
                {entry.status.replace(/_/g, " ")}
              </p>
              <p className="text-[10px] text-muted-foreground">
                {time.toLocaleTimeString()} · {time.toLocaleDateString()}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
```

Note: This file now imports `TaskProgressStepper`, `useElapsedTime`, `useAgent`, and uses `ROUTES.retryTask`. The `TaskTimeline` from `@/components/tasks/task-timeline` is replaced by an inline version for simplicity.

**Step 2: Remove the now-unused `task-timeline.tsx` import**

The old `TaskTimeline` import at line 13 is replaced by the inline version. The file `frontend/src/components/tasks/task-timeline.tsx` can remain (other pages might use it) but is no longer imported here.

**Step 3: Verify build**

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds

**Step 4: Commit**

```bash
git add frontend/src/app/\(marketplace\)/dashboard/tasks/\[id\]/task-detail-client.tsx
git commit -m "feat: enhanced task detail with agent identity, progress stepper, retry/duplicate, cost breakdown"
```

---

### Task 9: Add reliability badges to `AgentSearchCard` and task creation page

**Files:**
- Modify: `frontend/src/app/(marketplace)/dashboard/tasks/new/page.tsx`

**Step 1: Add reliability badges to `AgentSearchCard`**

In `frontend/src/app/(marketplace)/dashboard/tasks/new/page.tsx`, update the `AgentSearchCard` component to show badges after the skills:

After the skills section (after the closing `</div>` of the skills flex-wrap around line 87), add:

```tsx
{/* Reliability badges */}
{(agent.success_rate > 0.95 || agent.avg_latency_ms < 5000 || agent.total_tasks_completed > 0) && (
  <div className="mt-2 flex flex-wrap gap-1">
    {agent.success_rate > 0.95 && (
      <Badge variant="outline" className="text-[10px] border-green-500/30 text-green-500">
        {Math.round(agent.success_rate * 100)}% success
      </Badge>
    )}
    {agent.avg_latency_ms > 0 && agent.avg_latency_ms < 5000 && (
      <Badge variant="outline" className="text-[10px] border-blue-500/30 text-blue-500">
        Fast
      </Badge>
    )}
    {agent.total_tasks_completed > 10 && (
      <Badge variant="outline" className="text-[10px] border-purple-500/30 text-purple-500">
        {agent.total_tasks_completed} tasks
      </Badge>
    )}
  </div>
)}
```

**Step 2: Verify build**

Run: `cd frontend && npx next build 2>&1 | tail -5`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/src/app/\(marketplace\)/dashboard/tasks/new/page.tsx
git commit -m "feat: add reliability badges to agent search cards"
```

---

### Task 10: Update `TaskMessageThread` to remove duplicate artifacts

**Files:**
- Modify: `frontend/src/components/tasks/task-message-thread.tsx`

The current `TaskMessageThread` renders artifacts at the bottom of the message list, but `TaskArtifactsDisplay` also renders them separately (with the new markdown rendering). Remove the duplicate artifact rendering from the message thread.

**Step 1: Remove artifacts prop and rendering from TaskMessageThread**

The rewritten version from Task 5 already removed the `artifacts` prop. Verify the file no longer references artifacts.

**Step 2: Update the import in task-detail-client.tsx**

In the Task 8 rewrite, the call already passes only `messages`, `agentName`, and `statusHistory` — no `artifacts`. Verify this is correct.

**Step 3: Commit (if any changes needed)**

```bash
git add frontend/src/components/tasks/task-message-thread.tsx
git commit -m "fix: remove duplicate artifact rendering from message thread"
```

---

### Task 11: Verify full build and test

**Step 1: Full build**

Run:
```bash
cd frontend && npx next build
```
Expected: Build succeeds with no errors

**Step 2: Manual verification checklist**

Run local dev server:
```bash
cd frontend && npm run dev
```

Verify:
- [ ] `/dashboard/tasks/new` — agents listed by default, reliability badges visible
- [ ] `/dashboard/tasks/new` — search filters agents
- [ ] `/dashboard/tasks/new?agent=X&skill=Y&message=test` — pre-fills correctly
- [ ] `/dashboard/tasks/{id}` — progress stepper renders correctly
- [ ] `/dashboard/tasks/{id}` — agent identity card shows name, stats, link
- [ ] `/dashboard/tasks/{id}` — artifacts render as markdown with copy button
- [ ] `/dashboard/tasks/{id}` — processing banner shows elapsed time (for active tasks)
- [ ] `/dashboard/tasks/{id}` — retry/duplicate buttons appear for correct statuses
- [ ] `/dashboard/tasks/{id}` — cost breakdown shows platform fee
- [ ] `/dashboard/tasks` — clicking task uses client-side navigation (no __fallback)

**Step 3: Run E2E tests**

Run:
```bash
cd frontend && E2E_API_KEY=$(cat ../auth.txt) npx playwright test e2e/task-creation.spec.ts
```

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: task lifecycle UX overhaul — progress stepper, markdown artifacts, agent identity, retry/duplicate, live timer, reliability badges"
```

---

## Summary of all files changed

| Action | File |
|--------|------|
| New dep | `react-markdown`, `remark-gfm` |
| Create | `frontend/src/lib/hooks/use-elapsed-time.ts` |
| Create | `frontend/src/components/tasks/task-progress-stepper.tsx` |
| Rewrite | `frontend/src/components/tasks/task-artifacts-display.tsx` |
| Rewrite | `frontend/src/components/tasks/task-message-thread.tsx` |
| Rewrite | `frontend/src/app/(marketplace)/dashboard/tasks/[id]/task-detail-client.tsx` |
| Modify | `frontend/src/app/(marketplace)/dashboard/tasks/new/page.tsx` (badges + URL params) |
| Modify | `frontend/src/lib/constants.ts` (retryTask route) |
