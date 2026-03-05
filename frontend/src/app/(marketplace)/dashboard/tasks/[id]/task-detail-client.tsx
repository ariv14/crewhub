"use client";

import { useState } from "react";
import {
  AlertCircle,
  ArrowLeft,
  Clock,
  Copy,
  RefreshCw,
  Send,
  XCircle,
} from "lucide-react";
import { SpinningLogo } from "@/components/shared/spinning-logo";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  useTask,
  useCancelTask,
  useRateTask,
  useSendMessage,
} from "@/lib/hooks/use-tasks";
import { useAgent } from "@/lib/hooks/use-agents";
import { useElapsedTime } from "@/lib/hooks/use-elapsed-time";
import { formatCredits, formatDate, cn } from "@/lib/utils";
import { ROUTES } from "@/lib/constants";
import { TaskStatusBadge } from "@/components/tasks/task-status-badge";
import { TaskMessageThread } from "@/components/tasks/task-message-thread";
import { TaskProgressStepper } from "@/components/tasks/task-progress-stepper";
import { TaskArtifactsDisplay } from "@/components/tasks/task-artifacts-display";
import { TaskRatingForm } from "@/components/tasks/task-rating-form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

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
          <p className="font-medium">
            {agent?.name ?? agentId.slice(0, 8)}
          </p>
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
              <span>
                {Math.round(agent.success_rate * 100)}% success
              </span>
            )}
            {agent.avg_latency_ms > 0 && (
              <span>
                {(agent.avg_latency_ms / 1000).toFixed(1)}s avg
              </span>
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
          <span className="text-sm font-medium">
            Agent is working on your task...
          </span>
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

function TaskTimeline({
  history,
}: {
  history: { status: string; at: string }[];
}) {
  const statusColors: Record<string, string> = {
    submitted: "bg-blue-500",
    working: "bg-purple-500",
    completed: "bg-green-500",
    failed: "bg-red-500",
    canceled: "bg-zinc-400",
    rejected: "bg-red-500",
    input_required: "bg-orange-500",
    pending_payment: "bg-yellow-500",
  };
  const textColors: Record<string, string> = {
    submitted: "text-blue-500",
    working: "text-purple-500",
    completed: "text-green-500",
    failed: "text-red-500",
    canceled: "text-muted-foreground",
    rejected: "text-red-500",
    input_required: "text-orange-500",
    pending_payment: "text-yellow-500",
  };

  return (
    <div className="space-y-0">
      {history.map((entry, i) => {
        const isLast = i === history.length - 1;
        const time = new Date(entry.at);
        const dotColor =
          statusColors[entry.status] ?? "bg-muted-foreground";
        const labelColor =
          textColors[entry.status] ?? "text-muted-foreground";

        return (
          <div key={i} className="flex gap-3">
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  "h-2 w-2 rounded-full mt-1.5",
                  dotColor
                )}
              />
              {!isLast && (
                <div className="my-1 w-px flex-1 bg-border" />
              )}
            </div>
            <div className="pb-3">
              <p
                className={cn(
                  "text-xs font-medium capitalize",
                  labelColor
                )}
              >
                {entry.status.replace(/_/g, " ")}
              </p>
              <p className="text-[10px] text-muted-foreground">
                {time.toLocaleTimeString()} &middot;{" "}
                {time.toLocaleDateString()}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function TaskDetailClient({
  id: serverId,
}: {
  id: string;
}) {
  const params = useParams<{ id: string }>();
  const id =
    params.id && params.id !== "__fallback" ? params.id : serverId;

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
            This task doesn&apos;t exist or you don&apos;t have access
            to it.
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

  const canCancel = ["submitted", "pending_payment", "working"].includes(
    task.status
  );
  const canRate =
    task.status === "completed" && task.client_rating == null;
  const canMessage = task.status === "input_required";
  const isProcessing = ["submitted", "working"].includes(task.status);
  const canRetry = ["failed", "canceled", "rejected"].includes(
    task.status
  );
  const canDuplicate = task.status === "completed";

  // Extract original user message for retry/duplicate
  const userMessage = task.messages?.find((m) => m.role === "user");
  const originalText =
    userMessage?.parts?.find((p) => p.type === "text")?.content ?? "";

  // Cost breakdown
  const charged = task.credits_charged || 0;
  const platformFee = charged > 0 ? charged * PLATFORM_FEE_RATE : 0;

  function handleSend() {
    if (!message.trim()) return;
    sendMessage.mutate(
      {
        role: "user",
        parts: [{ type: "text", content: message }],
      },
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
            {task.completed_at &&
              ` · Completed ${formatDate(task.completed_at)}`}
          </p>
        </div>
        <div className="flex gap-2">
          {canRetry && (
            <Button variant="outline" size="sm" asChild>
              <Link
                href={ROUTES.retryTask(
                  task.provider_agent_id,
                  task.skill_id,
                  originalText
                )}
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Retry
              </Link>
            </Button>
          )}
          {canDuplicate && (
            <Button variant="outline" size="sm" asChild>
              <Link
                href={ROUTES.retryTask(
                  task.provider_agent_id,
                  task.skill_id,
                  originalText
                )}
              >
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
                onKeyDown={(e) =>
                  e.key === "Enter" && handleSend()
                }
              />
              <Button
                onClick={handleSend}
                disabled={sendMessage.isPending}
              >
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
                <span>
                  {formatCredits(task.credits_quoted)} credits
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Charged</span>
                <span>
                  {formatCredits(task.credits_charged)} credits
                </span>
              </div>
              {platformFee > 0 && (
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">
                    Platform fee
                  </span>
                  <span className="text-muted-foreground">
                    incl. {formatCredits(platformFee)}
                  </span>
                </div>
              )}
              <Separator />
              <div className="flex justify-between">
                <span className="text-muted-foreground">Payment</span>
                <span className="capitalize">
                  {task.payment_method}
                </span>
              </div>
              {task.latency_ms != null && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">
                    Latency
                  </span>
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
                  <span>
                    {"★".repeat(task.client_rating)}
                    {"☆".repeat(5 - task.client_rating)}/5
                  </span>
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
