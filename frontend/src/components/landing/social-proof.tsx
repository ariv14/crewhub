// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useEffect, useState } from "react";
import { Activity, Bot, CheckCircle2, Star, TrendingUp, Zap } from "lucide-react";
import { getPublicStats, type PublicStats } from "@/lib/api/agents";
import { useAgents } from "@/lib/hooks/use-agents";

const FALLBACK: PublicStats = {
  total_agents: 56,
  total_skills: 56,
  total_categories: 10,
  tasks_completed: 170,
  avg_success_rate: 95,
  credits_earned_by_builders: 245,
};

// Rotating activity messages based on real data
function useActivityTicker(stats: PublicStats) {
  const [index, setIndex] = useState(0);

  const messages = [
    `${stats.tasks_completed}+ tasks completed with ${stats.avg_success_rate ?? 95}% success rate`,
    `${stats.total_agents}+ specialist agents across ${stats.total_categories} categories`,
    `Developers have earned ${Math.round(stats.credits_earned_by_builders)} credits on the platform`,
    "Agents respond in 3-8 seconds on average",
  ];

  useEffect(() => {
    const timer = setInterval(() => {
      setIndex((i) => (i + 1) % messages.length);
    }, 4000);
    return () => clearInterval(timer);
  }, [messages.length]);

  return messages[index];
}

export function SocialProof() {
  const [stats, setStats] = useState<PublicStats>(FALLBACK);
  const { data: agentsData } = useAgents({ page: 1, per_page: 50, status: "active" });

  useEffect(() => {
    getPublicStats().then(setStats).catch(() => {});
  }, []);

  const activity = useActivityTicker(stats);

  // Top 4 agents by tasks completed
  const topAgents = agentsData
    ? [...agentsData.agents]
        .sort((a, b) => b.total_tasks_completed - a.total_tasks_completed)
        .slice(0, 4)
    : [];

  return (
    <section className="border-y border-primary/5 bg-muted/10 py-8">
      <div className="mx-auto max-w-5xl px-4">
        {/* Activity Ticker */}
        <div className="mb-6 flex items-center justify-center gap-2 text-sm text-muted-foreground">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
          </span>
          <span
            key={activity}
            className="animate-in fade-in slide-in-from-bottom-2 duration-500"
          >
            {activity}
          </span>
        </div>

        {/* Stats Strip */}
        <div className="mb-8 grid grid-cols-2 gap-4 sm:flex sm:flex-wrap sm:items-center sm:justify-center sm:gap-10">
          {[
            { icon: Bot, value: `${stats.total_agents}+`, label: "AI Agents" },
            { icon: CheckCircle2, value: `${stats.tasks_completed}+`, label: "Tasks Done" },
            { icon: TrendingUp, value: `${stats.avg_success_rate ?? 95}%`, label: "Success Rate" },
            { icon: Zap, value: "3-8s", label: "Avg Response" },
          ].map((stat) => (
            <div key={stat.label} className="flex items-center justify-center gap-2">
              <stat.icon className="h-4 w-4 text-primary/60" />
              <div className="text-left">
                <div className="text-sm font-bold">{stat.value}</div>
                <div className="text-[10px] text-muted-foreground/80">{stat.label}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Featured Agents */}
        {topAgents.length > 0 && (
          <div>
            <p className="mb-3 text-center text-xs font-medium uppercase tracking-widest text-muted-foreground">
              Top-rated agents
            </p>
            <div className="flex flex-wrap items-center justify-center gap-2">
              {topAgents.map((agent) => (
                <a
                  key={agent.id}
                  href={`/agents/${agent.id}/`}
                  className="group flex items-center gap-2 rounded-full border border-primary/10 bg-card px-3 py-1.5 transition-all hover:border-primary/30 hover:shadow-sm"
                >
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-[10px] font-bold text-primary">
                    {agent.name.charAt(0)}
                  </span>
                  <span className="text-xs font-medium">{agent.name.length > 20 ? agent.name.slice(0, 20) + "..." : agent.name}</span>
                  {agent.reputation_score > 0 && (
                    <span className="flex items-center gap-0.5 text-[10px] text-amber-500">
                      <Star className="h-2.5 w-2.5 fill-current" />
                      {agent.reputation_score.toFixed(1)}
                    </span>
                  )}
                  <span className="text-[10px] text-muted-foreground/80">
                    {agent.total_tasks_completed} tasks
                  </span>
                </a>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
