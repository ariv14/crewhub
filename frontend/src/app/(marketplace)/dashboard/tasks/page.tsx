"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { ListTodo, Plus } from "lucide-react";
import { useTasks } from "@/lib/hooks/use-tasks";
import { formatCredits, formatRelativeTime } from "@/lib/utils";
import { ROUTES } from "@/lib/constants";
import { TaskStatusBadge } from "@/components/tasks/task-status-badge";
import { EmptyState } from "@/components/shared/empty-state";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Task } from "@/types/task";

const PER_PAGE = 20;

const STATUS_FILTERS = [
  { label: "All", value: undefined },
  { label: "Active", value: "working" },
  { label: "Completed", value: "completed" },
  { label: "Failed", value: "failed" },
  { label: "Canceled", value: "canceled" },
] as const;

function getMessagePreview(task: Task): string {
  const userMsg = task.messages?.find((m) => m.role === "user");
  if (!userMsg) return "";
  const text = userMsg.parts?.find((p) => p.type === "text")?.content;
  return text ?? "";
}

function TaskCard({ task }: { task: Task }) {
  const preview = getMessagePreview(task);
  const agentName = task.provider_agent_name ?? (task.provider_agent_id ? task.provider_agent_id.slice(0, 8) : "Deleted Agent");
  const skillName = task.skill_name;

  return (
    <a
      href={ROUTES.taskDetail(task.id)}
      onClick={() => sessionStorage.setItem("nav_task_id", task.id)}
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
    </a>
  );
}

export default function MyTasksPage() {
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [page, setPage] = useState(1);
  const { data, isLoading } = useTasks(
    { ...(statusFilter ? { status: statusFilter } : {}), page, per_page: PER_PAGE }
  );
  const tasks = data?.tasks ?? [];
  const total = data?.total ?? 0;
  const hasMore = page * PER_PAGE < total;

  const changeFilter = useCallback((value: string | undefined) => {
    setStatusFilter(value);
    setPage(1);
  }, []);

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

      {/* Status Filters */}
      <div className="mt-4 flex gap-2">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.label}
            onClick={() => changeFilter(f.value)}
            className={cn(
              "rounded-full px-3 py-1 text-xs font-medium transition-colors",
              statusFilter === f.value
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:text-foreground"
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="mt-4 space-y-2">
        {isLoading ? (
          <div className="flex justify-center py-12">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : tasks.length === 0 ? (
          <EmptyState
            icon={ListTodo}
            title={statusFilter ? "No tasks with this status" : "No tasks yet"}
            description={statusFilter ? "Try a different filter" : "Delegate your first task to an agent"}
            action={
              !statusFilter ? (
                <Button asChild>
                  <Link href={ROUTES.agents}>Browse Agents</Link>
                </Button>
              ) : undefined
            }
          />
        ) : (
          <>
            <div className="flex items-center justify-between">
              <p className="text-xs text-muted-foreground">
                Showing {Math.min(page * PER_PAGE, total)} of {total} task{total !== 1 ? "s" : ""}
              </p>
              {total > PER_PAGE && (
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                  >
                    Previous
                  </Button>
                  <span className="text-xs text-muted-foreground">
                    Page {page} of {Math.ceil(total / PER_PAGE)}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => p + 1)}
                    disabled={!hasMore}
                  >
                    Next
                  </Button>
                </div>
              )}
            </div>
            {tasks.map((task) => <TaskCard key={task.id} task={task} />)}
            {total > PER_PAGE && (
              <div className="flex justify-center pt-2">
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                  >
                    Previous
                  </Button>
                  <span className="text-xs text-muted-foreground">
                    Page {page} of {Math.ceil(total / PER_PAGE)}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => p + 1)}
                    disabled={!hasMore}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
