// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState, type FormEvent } from "react";
import { Activity, Bot, CreditCard, ListTodo, Users, CheckCircle2, Gift, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { useAdminStats, useGrantCredits } from "@/lib/hooks/use-admin";
import { useHealth } from "@/lib/hooks/use-health";
import { useAuth } from "@/lib/auth-context";
import { formatCredits } from "@/lib/utils";
import { StatCard } from "@/components/shared/stat-card";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function CreditGrantForm() {
  const [userId, setUserId] = useState("");
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");
  const grantMutation = useGrantCredits();
  const { user } = useAuth();

  const isSelfGrant = user && userId.trim() === user.id;

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const parsedAmount = Number(amount);
    if (!userId.trim() || !parsedAmount || parsedAmount <= 0 || !reason.trim()) {
      toast.error("All fields are required and amount must be positive");
      return;
    }
    if (isSelfGrant) {
      toast.error("Cannot grant credits to yourself. Ask another admin.");
      return;
    }
    grantMutation.mutate(
      { userId: userId.trim(), amount: parsedAmount, reason: reason.trim() },
      {
        onSuccess: () => {
          toast.success(`Granted ${parsedAmount} credits to user`);
          setUserId("");
          setAmount("");
          setReason("");
        },
        onError: (err) =>
          toast.error(err instanceof Error ? err.message : "Failed to grant credits"),
      }
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Gift className="h-5 w-5" />
          Grant Credits
        </CardTitle>
        <CardDescription>
          Manually add credits to a user account
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4 sm:flex-row sm:items-end">
          <div className="grid flex-1 gap-1.5">
            <Label htmlFor="grant-user-id">User ID</Label>
            <Input
              id="grant-user-id"
              placeholder="User UUID"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
            />
          </div>
          <div className="grid w-full gap-1.5 sm:w-32">
            <Label htmlFor="grant-amount">Amount</Label>
            <Input
              id="grant-amount"
              type="number"
              min={1}
              placeholder="100"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
          </div>
          <div className="grid flex-1 gap-1.5">
            <Label htmlFor="grant-reason">Reason</Label>
            <Input
              id="grant-reason"
              placeholder="e.g. Promotional bonus"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </div>
          <Button type="submit" disabled={grantMutation.isPending || !!isSelfGrant} className="sm:w-auto">
            {grantMutation.isPending ? "Granting..." : "Grant"}
          </Button>
        </form>
        {isSelfGrant && (
          <div className="mt-3 flex items-center gap-2 rounded-md border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-sm text-amber-500">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            Cannot grant credits to yourself. Ask another admin to grant credits to your account.
          </div>
        )}
      </CardContent>
    </Card>
  );
}

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

      <CreditGrantForm />
    </div>
  );
}
