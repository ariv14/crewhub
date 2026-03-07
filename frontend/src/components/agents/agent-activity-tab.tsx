"use client";

import { useState, useCallback } from "react";
import {
  Activity,
  CheckCircle2,
  Clock,
  Coins,
  TrendingUp,
  Zap,
} from "lucide-react";
import { useTasks } from "@/lib/hooks/use-tasks";
import { formatCredits, formatRelativeTime } from "@/lib/utils";
import { ROUTES } from "@/lib/constants";
import { TaskStatusBadge } from "@/components/tasks/task-status-badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Agent } from "@/types/agent";
import type { Task } from "@/types/task";

const PER_PAGE = 10;

const STATUS_FILTERS = [
  { label: "All", value: undefined },
  { label: "Active", value: "working" },
  { label: "Completed", value: "completed" },
  { label: "Failed", value: "failed" },
  { label: "Canceled", value: "canceled" },
] as const;

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  sub?: string;
}) {
  return (
    <div className="rounded-lg border p-4">
      <div className="flex items-center gap-2 text-muted-foreground">
        <Icon className="h-4 w-4" />
        <span className="text-xs font-medium">{label}</span>
      </div>
      <p className="mt-1 text-2xl font-bold">{value}</p>
      {sub && <p className="text-xs text-muted-foreground">{sub}</p>}
    </div>
  );
}

function getMessagePreview(task: Task): string {
  const userMsg = task.messages?.find((m) => m.role === "user");
  if (!userMsg) return "";
  const text = userMsg.parts?.find((p) => p.type === "text")?.content;
  return text ?? "";
}

function TaskRow({ task }: { task: Task }) {
  const preview = getMessagePreview(task);
  const skillName = task.skill_name;

  return (
    <a
      href={ROUTES.taskDetail(task.id)}
      className="flex items-center gap-4 rounded-lg border p-3 transition-colors hover:border-primary/30 hover:bg-muted/30"
      data-testid="activity-task-row"
    >
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">
          {preview || "No message"}
        </p>
        <div className="mt-0.5 flex items-center gap-2 text-xs text-muted-foreground">
          {skillName && <span>{skillName}</span>}
          {skillName && <span>&middot;</span>}
          <span>{formatRelativeTime(task.created_at)}</span>
          {task.latency_ms != null && (
            <>
              <span>&middot;</span>
              <span>{task.latency_ms}ms</span>
            </>
          )}
        </div>
      </div>
      <div className="flex items-center gap-3 shrink-0">
        <span className="text-xs text-muted-foreground">
          {formatCredits(task.credits_charged || task.credits_quoted)}c
        </span>
        <TaskStatusBadge status={task.status} />
      </div>
    </a>
  );
}

/** Public summary stats visible to all visitors. */
function ActivityStats({ agent }: { agent: Agent }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4" data-testid="activity-stats">
      <StatCard
        icon={CheckCircle2}
        label="Tasks Completed"
        value={agent.total_tasks_completed}
      />
      <StatCard
        icon={TrendingUp}
        label="Success Rate"
        value={`${(agent.success_rate * 100).toFixed(1)}%`}
      />
      <StatCard
        icon={Zap}
        label="Avg Latency"
        value={agent.avg_latency_ms > 0 ? `${Math.round(agent.avg_latency_ms)}ms` : "--"}
      />
      <StatCard
        icon={Coins}
        label="Reputation"
        value={agent.reputation_score.toFixed(1)}
        sub="out of 5.0"
      />
    </div>
  );
}

/** Owner-only task list with status filters and pagination. */
function ActivityTaskList({ agentId }: { agentId: string }) {
  const [statusFilter, setStatusFilter] = useState<string | undefined>(
    undefined
  );
  const [page, setPage] = useState(1);
  const { data, isLoading } = useTasks({
    agent_id: agentId,
    ...(statusFilter ? { status: statusFilter } : {}),
    page,
    per_page: PER_PAGE,
  });
  const tasks = data?.tasks ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / PER_PAGE);

  const changeFilter = useCallback((value: string | undefined) => {
    setStatusFilter(value);
    setPage(1);
  }, []);

  return (
    <div className="space-y-3" data-testid="activity-task-list">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Task Log</h3>
        <div className="flex gap-1.5">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.label}
              onClick={() => changeFilter(f.value)}
              className={cn(
                "rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors",
                statusFilter === f.value
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:text-foreground"
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      ) : tasks.length === 0 ? (
        <div className="rounded-lg border border-dashed p-8 text-center">
          <Activity className="mx-auto h-8 w-8 text-muted-foreground/50" />
          <p className="mt-2 text-sm text-muted-foreground">
            {statusFilter
              ? "No tasks with this status"
              : "No tasks routed to this agent yet"}
          </p>
        </div>
      ) : (
        <>
          <p className="text-xs text-muted-foreground">
            {total} task{total !== 1 ? "s" : ""} total
          </p>
          <div className="space-y-2">
            {tasks.map((task) => (
              <TaskRow key={task.id} task={task} />
            ))}
          </div>
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                Previous
              </Button>
              <span className="text-xs text-muted-foreground">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => p + 1)}
                disabled={page >= totalPages}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export function AgentActivityTab({
  agent,
  isOwner,
}: {
  agent: Agent;
  isOwner: boolean;
}) {
  return (
    <div className="space-y-6">
      <ActivityStats agent={agent} />
      {isOwner ? (
        <ActivityTaskList agentId={agent.id} />
      ) : (
        <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
          Task details are only visible to the agent owner.
        </div>
      )}
    </div>
  );
}
