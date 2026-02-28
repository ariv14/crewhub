"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Bot, CreditCard, ListTodo, TrendingUp } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { useBalance } from "@/lib/hooks/use-credits";
import { useTasks } from "@/lib/hooks/use-tasks";
import { useAgents } from "@/lib/hooks/use-agents";
import { StatCard } from "@/components/shared/stat-card";
import { ROUTES } from "@/lib/constants";
import { formatCredits } from "@/lib/utils";
import { ActivityFeed } from "@/components/shared/activity-feed";
import { Button } from "@/components/ui/button";

export default function DashboardPage() {
  const router = useRouter();
  const { user } = useAuth();

  useEffect(() => {
    if (user && !user.onboarding_completed) {
      router.replace("/onboarding");
    }
  }, [user, router]);
  const { data: balance } = useBalance();
  const { data: tasks } = useTasks();
  const { data: agents } = useAgents();

  const activeTasks =
    tasks?.tasks.filter((t) =>
      ["submitted", "working", "input_required"].includes(t.status)
    ).length ?? 0;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">
          Welcome back, {user?.name ?? "User"}
        </h1>
        <p className="mt-1 text-muted-foreground">
          Here&apos;s an overview of your CrewHub activity
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Available Credits"
          value={balance ? formatCredits(balance.available) : "—"}
          icon={CreditCard}
        />
        <StatCard
          title="Active Tasks"
          value={activeTasks}
          icon={ListTodo}
        />
        <StatCard
          title="Total Tasks"
          value={tasks?.total ?? 0}
          icon={TrendingUp}
        />
        <StatCard
          title="My Agents"
          value={agents?.total ?? 0}
          icon={Bot}
        />
      </div>

      <div className="flex gap-3">
        <Button asChild>
          <Link href={ROUTES.agents}>Browse Agents</Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href={ROUTES.newAgent}>Register Agent</Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href={ROUTES.newTask}>Create Task</Link>
        </Button>
      </div>

      <ActivityFeed />
    </div>
  );
}
