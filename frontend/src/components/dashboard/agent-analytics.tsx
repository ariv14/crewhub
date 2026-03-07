"use client";

import { useMemo } from "react";
import {
  BarChart3,
  CheckCircle2,
  Clock,
  Coins,
  TrendingUp,
  Zap,
} from "lucide-react";
import {
  AreaChart,
  Area,
  ResponsiveContainer,
  Tooltip,
  XAxis,
} from "recharts";
import { useAgentStats } from "@/lib/hooks/use-agents";
import { useUsage } from "@/lib/hooks/use-credits";
import { StatCard } from "@/components/shared/stat-card";
import { formatCredits } from "@/lib/utils";
import type { Agent } from "@/types/agent";

/** Aggregate stats across all owned agents. */
function AggregateStats({ agents }: { agents: Agent[] }) {
  const { data: usage } = useUsage("30d");

  const totals = useMemo(() => {
    const totalTasks = agents.reduce(
      (sum, a) => sum + a.total_tasks_completed,
      0
    );
    const avgSuccess =
      agents.length > 0
        ? agents.reduce((sum, a) => sum + a.success_rate, 0) / agents.length
        : 0;
    const avgLatency =
      agents.filter((a) => a.avg_latency_ms > 0).length > 0
        ? agents
            .filter((a) => a.avg_latency_ms > 0)
            .reduce((sum, a) => sum + a.avg_latency_ms, 0) /
          agents.filter((a) => a.avg_latency_ms > 0).length
        : 0;
    const bestAgent = agents.reduce(
      (best, a) =>
        a.total_tasks_completed > (best?.total_tasks_completed ?? 0) ? a : best,
      agents[0]
    );
    return { totalTasks, avgSuccess, avgLatency, bestAgent };
  }, [agents]);

  return (
    <div
      className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
      data-testid="analytics-aggregate-stats"
    >
      <StatCard
        title="Total Tasks (all agents)"
        value={totals.totalTasks}
        icon={CheckCircle2}
      />
      <StatCard
        title="Avg Success Rate"
        value={`${(totals.avgSuccess * 100).toFixed(1)}%`}
        icon={TrendingUp}
      />
      <StatCard
        title="Avg Latency"
        value={
          totals.avgLatency > 0 ? `${Math.round(totals.avgLatency)}ms` : "--"
        }
        icon={Zap}
      />
      <StatCard
        title="Earnings (30d)"
        value={
          usage ? `${formatCredits(usage.total_earned)} credits` : "--"
        }
        icon={Coins}
        description={
          usage
            ? `${usage.tasks_received} tasks received`
            : undefined
        }
      />
    </div>
  );
}

/** Mini sparkline showing 30-day task volume for a single agent. */
function AgentSparkline({ agentId }: { agentId: string }) {
  const { data, isLoading } = useAgentStats(agentId);

  if (isLoading || !data?.daily_tasks?.length) {
    return (
      <div className="flex h-10 w-24 items-center justify-center text-xs text-muted-foreground">
        {isLoading ? "..." : "No data"}
      </div>
    );
  }

  return (
    <div className="h-10 w-24">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data.daily_tasks}>
          <defs>
            <linearGradient id={`grad-${agentId}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
              <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey="count"
            stroke="hsl(var(--primary))"
            fill={`url(#grad-${agentId})`}
            strokeWidth={1.5}
          />
          <Tooltip
            content={({ payload }) => {
              if (!payload?.[0]) return null;
              const d = payload[0].payload as { date: string; count: number };
              return (
                <div className="rounded border bg-popover px-2 py-1 text-xs shadow">
                  {d.date}: {d.count} tasks
                </div>
              );
            }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Enhanced agent row with sparkline and key metrics. */
export function AgentAnalyticsRow({ agent }: { agent: Agent }) {
  return (
    <div
      className="flex items-center gap-4 rounded-lg border p-4 transition-colors hover:border-primary/30 hover:bg-muted/30"
      data-testid="analytics-agent-row"
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-sm font-bold text-primary">
        {agent.name.charAt(0).toUpperCase()}
      </div>

      <div className="min-w-0 flex-1">
        <a
          href={`/agents/${agent.id}/`}
          className="text-sm font-medium hover:text-primary hover:underline"
        >
          {agent.name}
        </a>
        <p className="truncate text-xs text-muted-foreground">
          {agent.category} &middot; {agent.skills.length} skill
          {agent.skills.length !== 1 ? "s" : ""}
        </p>
      </div>

      <div className="hidden items-center gap-6 text-xs text-muted-foreground sm:flex">
        <div className="text-center">
          <p className="font-medium text-foreground">
            {agent.total_tasks_completed}
          </p>
          <p>tasks</p>
        </div>
        <div className="text-center">
          <p className="font-medium text-foreground">
            {(agent.success_rate * 100).toFixed(0)}%
          </p>
          <p>success</p>
        </div>
        <div className="text-center">
          <p className="font-medium text-foreground">
            {agent.avg_latency_ms > 0
              ? `${(agent.avg_latency_ms / 1000).toFixed(1)}s`
              : "--"}
          </p>
          <p>latency</p>
        </div>
        <div className="text-center">
          <p className="font-medium text-foreground">
            {agent.reputation_score.toFixed(1)}
          </p>
          <p>score</p>
        </div>
      </div>

      <AgentSparkline agentId={agent.id} />
    </div>
  );
}

/** Full analytics section for the My Agents dashboard page. */
export function AgentAnalyticsSection({ agents }: { agents: Agent[] }) {
  if (agents.length === 0) return null;

  return (
    <div className="space-y-6" data-testid="analytics-section">
      <div>
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <BarChart3 className="h-5 w-5" />
          Analytics
        </h2>
        <p className="text-sm text-muted-foreground">
          Performance overview across your agents
        </p>
      </div>

      <AggregateStats agents={agents} />

      <div>
        <h3 className="mb-3 text-sm font-semibold">Per-Agent Performance</h3>
        <div className="space-y-2">
          {agents.map((agent) => (
            <AgentAnalyticsRow key={agent.id} agent={agent} />
          ))}
        </div>
      </div>
    </div>
  );
}
