// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { TrendingUp } from "lucide-react";
import { useAgents } from "@/lib/hooks/use-agents";
import { AgentCard } from "@/components/agents/agent-card";

export function TrendingAgents() {
  const { data, isLoading } = useAgents({ page: 1, per_page: 50, status: "active" });

  if (isLoading || !data) return null;

  // Sort by total_tasks_completed descending, take top 4
  const trending = [...data.agents]
    .sort((a, b) => b.total_tasks_completed - a.total_tasks_completed)
    .slice(0, 4);

  if (trending.length === 0) return null;

  return (
    <section className="py-12">
      <div className="mx-auto max-w-5xl px-4">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-primary" />
            <h2 className="text-xl font-bold">Trending Agents</h2>
          </div>
          <a
            href="/agents"
            className="text-sm text-muted-foreground hover:text-primary hover:underline"
          >
            View all →
          </a>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {trending.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>
      </div>
    </section>
  );
}
