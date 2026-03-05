"use client";

import Link from "next/link";
import { ListTodo, Plus } from "lucide-react";
import { useTasks } from "@/lib/hooks/use-tasks";
import { formatCredits, formatRelativeTime } from "@/lib/utils";
import { ROUTES } from "@/lib/constants";
import { TaskStatusBadge } from "@/components/tasks/task-status-badge";
import { EmptyState } from "@/components/shared/empty-state";
import { Button } from "@/components/ui/button";
import type { Task } from "@/types/task";

function getMessagePreview(task: Task): string {
  const userMsg = task.messages?.find((m) => m.role === "user");
  if (!userMsg) return "";
  const text = userMsg.parts?.find((p) => p.type === "text")?.content;
  return text ?? "";
}

function TaskCard({ task }: { task: Task }) {
  const preview = getMessagePreview(task);
  const agentName = task.provider_agent_name ?? task.provider_agent_id.slice(0, 8);
  const skillName = task.skill_name;

  return (
    <Link
      href={ROUTES.taskDetail(task.id)}
      className="block rounded-lg border p-4 transition-colors hover:border-primary/30 hover:bg-muted/30"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">
            {preview || "No message"}
          </p>
          <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
            <span>{agentName}</span>
            {skillName && (
              <>
                <span>&middot;</span>
                <span>{skillName}</span>
              </>
            )}
          </div>
        </div>
        <TaskStatusBadge status={task.status} />
      </div>

      <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
        <span>{formatCredits(task.credits_charged || task.credits_quoted)} credits</span>
        <span>{formatRelativeTime(task.created_at)}</span>
        {task.latency_ms != null && <span>{task.latency_ms}ms</span>}
        {task.client_rating != null && <span>{task.client_rating}/5</span>}
      </div>
    </Link>
  );
}

export default function MyTasksPage() {
  const { data, isLoading } = useTasks();
  const tasks = data?.tasks ?? [];

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">My Tasks</h1>
          <p className="mt-1 text-muted-foreground">
            Track your delegated tasks
          </p>
        </div>
        <Button asChild>
          <Link href={ROUTES.newTask}>
            <Plus className="mr-2 h-4 w-4" />
            New Task
          </Link>
        </Button>
      </div>

      <div className="mt-6 space-y-2">
        {!isLoading && tasks.length === 0 ? (
          <EmptyState
            icon={ListTodo}
            title="No tasks yet"
            description="Delegate your first task to an agent"
            action={
              <Button asChild>
                <Link href={ROUTES.agents}>Browse Agents</Link>
              </Button>
            }
          />
        ) : (
          tasks.map((task) => <TaskCard key={task.id} task={task} />)
        )}
      </div>
    </div>
  );
}
