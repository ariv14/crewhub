"use client";

import { Activity, Bot, CreditCard, ListTodo, Users, CheckCircle2, XCircle } from "lucide-react";
import { useAdminStats } from "@/lib/hooks/use-admin";
import { useHealth } from "@/lib/hooks/use-health";
import { formatCredits } from "@/lib/utils";
import { StatCard } from "@/components/shared/stat-card";

export default function AdminPage() {
  const { data: stats, isLoading: statsLoading } = useAdminStats();
  const { data: health } = useHealth();

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Admin Overview</h1>
        <p className="mt-1 text-muted-foreground">
          Platform KPIs and management (auto-refreshes every 30s)
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Platform Status"
          value={health?.status === "ok" ? "Healthy" : "—"}
          icon={Activity}
        />
        <StatCard
          title="Total Users"
          value={statsLoading ? "—" : (stats?.total_users ?? "—")}
          description={stats ? `${stats.active_users} active` : undefined}
          icon={Users}
        />
        <StatCard
          title="Total Agents"
          value={statsLoading ? "—" : (stats?.total_agents ?? "—")}
          description={stats ? `${stats.active_agents} active` : undefined}
          icon={Bot}
        />
        <StatCard
          title="Total Tasks"
          value={statsLoading ? "—" : (stats?.total_tasks ?? "—")}
          description={
            stats
              ? `${stats.completed_tasks} completed / ${stats.failed_tasks} failed`
              : undefined
          }
          icon={ListTodo}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <StatCard
          title="Transaction Volume"
          value={
            statsLoading
              ? "—"
              : stats
                ? formatCredits(stats.total_transaction_volume)
                : "—"
          }
          description="Total credits transacted"
          icon={CreditCard}
        />
        <StatCard
          title="Task Completion Rate"
          value={
            statsLoading || !stats || stats.total_tasks === 0
              ? "—"
              : `${Math.round((stats.completed_tasks / stats.total_tasks) * 100)}%`
          }
          description={
            stats && stats.total_tasks > 0
              ? `${stats.completed_tasks} of ${stats.total_tasks} tasks`
              : undefined
          }
          icon={CheckCircle2}
        />
      </div>
    </div>
  );
}
