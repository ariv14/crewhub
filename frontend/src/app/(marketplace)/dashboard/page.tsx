// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import {
  Bot,
  CreditCard,
  ListTodo,
  Search,
  TrendingUp,
  Rocket,
  Workflow,
  Zap,
  ArrowRight,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { useBalance } from "@/lib/hooks/use-credits";
import { useTasks } from "@/lib/hooks/use-tasks";
import { useAgents } from "@/lib/hooks/use-agents";
import { useMyWorkflows } from "@/lib/hooks/use-workflows";
import { StatCard } from "@/components/shared/stat-card";
import { ROUTES } from "@/lib/constants";
import { formatCredits } from "@/lib/utils";
import { ActivityFeed } from "@/components/shared/activity-feed";
import { AgentStatusBoard } from "@/components/agents/agent-status-board";
import { api } from "@/lib/api-client";

const ACTION_CARDS = [
  {
    icon: Workflow,
    title: "Create Workflow",
    description: "Chain agents together — sequential, parallel, or AI-orchestrated.",
    cta: "Create Workflow",
    href: "/dashboard/workflows/new",
    track: "dashboard_card_workflow",
    border: "border-2 border-primary/20 bg-card",
    hover: "hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5",
    gradient: true,
    iconBg: "bg-primary/10",
    iconColor: "text-primary",
    ctaColor: "text-primary",
  },
  {
    icon: Zap,
    title: "Find the Right Agent",
    description: "Describe your task — get matched with the best specialist.",
    cta: "Browse Agents",
    href: ROUTES.agents,
    track: "dashboard_card_find_agent",
    border: "border bg-card",
    hover: "hover:border-blue-500/30 hover:shadow-lg",
    gradient: false,
    iconBg: "bg-blue-500/10",
    iconColor: "text-blue-500",
    ctaColor: "text-blue-500",
  },
  {
    icon: Rocket,
    title: "List Your Agent",
    description: "Register your agent. Get discovered. Earn 90% per task.",
    cta: "Register Agent",
    href: ROUTES.registerAgent,
    track: "dashboard_card_list_agent",
    border: "border bg-card",
    hover: "hover:border-green-500/30 hover:shadow-lg",
    gradient: false,
    iconBg: "bg-green-500/10",
    iconColor: "text-green-500",
    ctaColor: "text-green-500",
  },
] as const;

function trackCardClick(event: string) {
  if (typeof window !== "undefined" && window.posthog?.capture) {
    window.posthog.capture(event);
  }
}

export default function DashboardPage() {
  const { user, refreshUser } = useAuth();
  const { data: balance } = useBalance();
  const { data: tasks } = useTasks();
  const { data: myAgentsData } = useAgents(
    user ? { owner_id: user.id, status: "active" } : undefined
  );
  const { data: allAgentsData } = useAgents({ per_page: 20, status: "active" });
  const { data: workflowsData } = useMyWorkflows();

  // Welcome state for new users
  if (user && !user.onboarding_completed) {
    return <WelcomeState onComplete={() => refreshUser?.()} />;
  }

  const activeTasks =
    tasks?.tasks.filter((t) =>
      ["submitted", "working", "input_required"].includes(t.status)
    ).length ?? 0;

  const myAgents = myAgentsData?.agents ?? [];
  const myAgentIds = new Set(myAgents.map((a) => a.id));
  const publicAgents = (allAgentsData?.agents ?? []).filter(
    (a) => !myAgentIds.has(a.id)
  );

  // Always show action cards — useful quick actions for all users
  const showActionCards = true;

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
          href={ROUTES.credits}
        />
        <StatCard
          title="Active Tasks"
          value={activeTasks}
          icon={ListTodo}
          href={ROUTES.myTasks}
        />
        <StatCard
          title="Total Tasks"
          value={tasks?.total ?? 0}
          icon={TrendingUp}
          href={ROUTES.myTasks}
        />
        <StatCard
          title="My Agents"
          value={myAgentsData?.total ?? 0}
          icon={Bot}
          href={ROUTES.myAgents}
        />
      </div>

      {/* Quick Action Cards — shown only while getting started */}
      {showActionCards && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {ACTION_CARDS.map((card) => (
            <a
              key={card.href}
              href={card.href}
              onClick={() => trackCardClick(card.track)}
              className={`group relative flex min-h-[140px] flex-col justify-between overflow-hidden rounded-xl p-5 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${card.border} ${card.hover}`}
            >
              {card.gradient && (
                <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent" />
              )}
              <div className="relative">
                <div className={`mb-3 flex h-10 w-10 items-center justify-center rounded-lg ${card.iconBg}`}>
                  <card.icon className={`h-5 w-5 ${card.iconColor}`} />
                </div>
                <h3 className="font-semibold">{card.title}</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  {card.description}
                </p>
              </div>
              <div className={`relative mt-4 flex items-center gap-1.5 text-sm font-medium ${card.ctaColor}`}>
                {card.cta}
                <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-1" />
              </div>
            </a>
          ))}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <ActivityFeed />
        <AgentStatusBoard myAgents={myAgents} publicAgents={publicAgents} />
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
        <a
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
        </a>

        <a
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
        </a>
      </div>
    </div>
  );
}
