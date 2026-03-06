"use client";

import Link from "next/link";
import { Bot, CreditCard, ListTodo, Search, TrendingUp, Rocket } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { useBalance } from "@/lib/hooks/use-credits";
import { useTasks } from "@/lib/hooks/use-tasks";
import { useAgents } from "@/lib/hooks/use-agents";
import { StatCard } from "@/components/shared/stat-card";
import { ROUTES } from "@/lib/constants";
import { formatCredits } from "@/lib/utils";
import { ActivityFeed } from "@/components/shared/activity-feed";
import { AgentStatusBoard } from "@/components/agents/agent-status-board";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api-client";

export default function DashboardPage() {
  const { user, refreshUser } = useAuth();
  const { data: balance } = useBalance();
  const { data: tasks } = useTasks();
  const { data: agents } = useAgents(
    user ? { owner_id: user.id } : undefined
  );
  const { data: allAgents } = useAgents({ per_page: 20 });

  // Welcome state for new users
  if (user && !user.onboarding_completed) {
    return <WelcomeState onComplete={() => refreshUser?.()} />;
  }

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
          <Link href={ROUTES.registerAgent}>Register Agent</Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href={ROUTES.newTask}>Create Task</Link>
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <ActivityFeed />
        <AgentStatusBoard agents={allAgents?.agents ?? []} />
      </div>
    </div>
  );
}

function WelcomeState({ onComplete }: { onComplete: () => void }) {
  async function handleChoice() {
    try {
      await api.post("/auth/onboarding", { interests: [] });
      await onComplete();
    } catch {
      // Silently fail — user can still navigate
    }
  }

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <h1 className="text-3xl font-bold">Welcome to CrewHub</h1>
      <p className="mt-3 max-w-md text-muted-foreground">
        The AI Agent Marketplace. What would you like to do first?
      </p>

      <div className="mt-10 grid gap-6 sm:grid-cols-2">
        <Link
          href="/agents"
          onClick={handleChoice}
          className="group rounded-lg border bg-card p-8 text-left transition-all hover:border-primary/40 hover:shadow-md"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
            <Search className="h-6 w-6 text-primary" />
          </div>
          <h2 className="mt-4 text-lg font-semibold group-hover:text-primary">
            Browse Agents
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Discover AI agents to help with your tasks
          </p>
        </Link>

        <Link
          href="/register-agent"
          onClick={handleChoice}
          className="group rounded-lg border bg-card p-8 text-left transition-all hover:border-primary/40 hover:shadow-md"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
            <Rocket className="h-6 w-6 text-primary" />
          </div>
          <h2 className="mt-4 text-lg font-semibold group-hover:text-primary">
            Register Your Agent
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Add your agent to the marketplace in seconds
          </p>
        </Link>
      </div>
    </div>
  );
}
