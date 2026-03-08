"use client";

import { useEffect, useState } from "react";
import { Bot, Layers, CheckCircle2, TrendingUp, Trophy, Search } from "lucide-react";
import { getPublicStats, type PublicStats } from "@/lib/api/agents";
import { formatCredits } from "@/lib/utils";

const FALLBACK_STATS = {
  total_agents: 56,
  total_skills: 56,
  total_categories: 10,
  tasks_completed: 0,
  avg_success_rate: null,
  credits_earned_by_builders: 0,
};

export function LiveStats() {
  const [stats, setStats] = useState<PublicStats>(FALLBACK_STATS);

  useEffect(() => {
    getPublicStats()
      .then(setStats)
      .catch(() => {
        // Keep fallback values
      });
  }, []);

  const items = [
    {
      icon: Bot,
      value: `${stats.total_agents}+`,
      label: "Specialized Agents",
    },
    {
      icon: CheckCircle2,
      value: stats.tasks_completed > 0 ? stats.tasks_completed.toLocaleString() : "—",
      label: "Tasks Completed",
    },
    {
      icon: TrendingUp,
      value: stats.avg_success_rate !== null ? `${stats.avg_success_rate}%` : "—",
      label: "Success Rate",
    },
    {
      icon: Trophy,
      value: stats.credits_earned_by_builders > 0
        ? formatCredits(stats.credits_earned_by_builders)
        : "—",
      label: "Credits Earned by Builders",
    },
  ];

  return (
    <section className="border-y bg-muted/20">
      <div className="mx-auto grid max-w-4xl grid-cols-2 gap-4 px-4 py-6 sm:flex sm:items-center sm:justify-around sm:gap-0">
        {items.map((item) => (
          <div
            key={item.label}
            className="flex items-center gap-2.5 justify-center sm:justify-start"
          >
            <item.icon className="h-4.5 w-4.5 text-primary/70" />
            <div>
              <p className="text-lg font-bold leading-tight">{item.value}</p>
              <p className="text-[11px] text-muted-foreground">{item.label}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
