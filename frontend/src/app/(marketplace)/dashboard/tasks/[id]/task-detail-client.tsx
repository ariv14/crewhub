"use client";

import { useState } from "react";
import { AlertCircle, ArrowLeft, Send, XCircle } from "lucide-react";
import { SpinningLogo } from "@/components/shared/spinning-logo";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useTask, useCancelTask, useRateTask, useSendMessage } from "@/lib/hooks/use-tasks";
import { formatCredits, formatDate } from "@/lib/utils";
import { ROUTES } from "@/lib/constants";
import { TaskStatusBadge } from "@/components/tasks/task-status-badge";
import { TaskMessageThread } from "@/components/tasks/task-message-thread";
import { TaskTimeline } from "@/components/tasks/task-timeline";
import { TaskArtifactsDisplay } from "@/components/tasks/task-artifacts-display";
import { TaskRatingForm } from "@/components/tasks/task-rating-form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

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

      {["submitted", "working"].includes(task.status) && (
        <div className="mt-4 flex items-center gap-3 rounded-lg border bg-muted/30 p-3">
          <SpinningLogo spinning size="sm" />
          <span className="text-sm text-muted-foreground">
            Agent is processing your task...
          </span>
        </div>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <TaskMessageThread
            messages={task.messages}
            artifacts={task.artifacts}
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

        <div className="space-y-4">
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

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Agent</span>
                <Link
                  href={ROUTES.agentDetail(task.provider_agent_id)}
                  className="font-mono text-xs hover:text-primary"
                >
                  {task.provider_agent_id.slice(0, 8)}...
                </Link>
              </div>
              <Separator />
              <div className="flex justify-between">
                <span className="text-muted-foreground">Quoted</span>
                <span>{formatCredits(task.credits_quoted)} credits</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Charged</span>
                <span>{formatCredits(task.credits_charged)} credits</span>
              </div>
              <Separator />
              <div className="flex justify-between">
                <span className="text-muted-foreground">Payment</span>
                <span className="capitalize">{task.payment_method}</span>
              </div>
              {task.latency_ms != null && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Latency</span>
                  <span>{task.latency_ms}ms</span>
                </div>
              )}
              {task.client_rating != null && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Rating</span>
                  <span>{task.client_rating}/5</span>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
