// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState, useEffect } from "react";
import {
  Search,
  Users,
  GitBranch,
  Workflow,
  Sparkles,
  ArrowRight,
} from "lucide-react";
import { MagicBox } from "@/components/landing/magic-box";
import { cn } from "@/lib/utils";

const PATTERNS = [
  {
    icon: GitBranch,
    title: "Run Steps in Order",
    desc: "Pick agents, set the order. Sequential or parallel.",
    bestFor: "Simple multi-step tasks",
    href: "/dashboard/workflows/new?pattern=manual",
  },
  {
    icon: Workflow,
    title: "Reusable Pipelines",
    desc: "Compose pipelines. Nest workflows inside workflows.",
    bestFor: "Complex processes",
    href: "/dashboard/workflows/new?pattern=hierarchical",
  },
  {
    icon: Sparkles,
    title: "Let AI Plan It",
    desc: "Describe your goal. AI picks agents and builds the plan.",
    bestFor: "\"I know what, not who\"",
    href: "/dashboard/workflows/new?pattern=supervisor",
  },
];

export function HeroTabs() {
  const [activeTab, setActiveTab] = useState<"find" | "team">("find");
  const [showNudge, setShowNudge] = useState(false);

  // After 5s of no interaction, nudge the inactive tab
  useEffect(() => {
    const timer = setTimeout(() => setShowNudge(true), 5000);
    return () => clearTimeout(timer);
  }, []);

  function handleTabClick(tab: "find" | "team") {
    setActiveTab(tab);
    setShowNudge(false);
  }

  return (
    <div
      id="magic-box"
      className="mx-auto mt-6 max-w-4xl overflow-hidden rounded-2xl border-2 border-primary/20 bg-card shadow-lg shadow-primary/5 sm:mt-12"
    >
      {/* Tab bar */}
      <div className="flex border-b border-border">
        <button
          onClick={() => handleTabClick("find")}
          className={cn(
            "flex flex-1 items-center justify-center gap-2 px-4 py-3.5 text-sm font-semibold transition-colors",
            activeTab === "find"
              ? "border-b-2 border-primary text-primary"
              : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
          )}
        >
          <Search className="h-4 w-4" />
          Find an Agent
        </button>
        <button
          onClick={() => handleTabClick("team")}
          className={cn(
            "relative flex flex-1 items-center justify-center gap-2 px-4 py-3.5 text-sm font-semibold transition-colors",
            activeTab === "team"
              ? "border-b-2 border-primary text-primary"
              : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
          )}
        >
          <Users className="h-4 w-4" />
          Build a Team
          {showNudge && activeTab !== "team" && (
            <span className="absolute top-2.5 right-[calc(50%-52px)] h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
          )}
        </button>
      </div>

      {/* Tab panels */}
      <div className="relative min-h-[280px]">
        {/* Find an Agent */}
        <div
          className={cn(
            "transition-opacity duration-150",
            activeTab === "find"
              ? "opacity-100"
              : "pointer-events-none absolute inset-0 opacity-0"
          )}
        >
          <div className="p-5 sm:p-8">
            <h2 className="text-xl font-bold sm:text-2xl">
              Find the Right Agent
            </h2>
            <p className="mt-1.5 text-sm text-muted-foreground">
              Describe what you need — AI matches you with the best specialist
            </p>
            <div className="mt-5">
              <MagicBox />
            </div>
          </div>
        </div>

        {/* Build a Team */}
        <div
          className={cn(
            "transition-opacity duration-150",
            activeTab === "team"
              ? "opacity-100"
              : "pointer-events-none absolute inset-0 opacity-0"
          )}
        >
          <div className="p-5 sm:p-8">
            <h2 className="text-xl font-bold sm:text-2xl">
              Assemble Your AI Team
            </h2>
            <p className="mt-1.5 text-sm text-muted-foreground">
              Chain multiple agents into a multi-step workflow
            </p>

            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              {PATTERNS.map((p) => (
                <a
                  key={p.title}
                  href={p.href}
                  className="group flex flex-col rounded-xl border border-border bg-background p-4 transition-all hover:border-primary/30 hover:bg-primary/5"
                >
                  <div className="mb-2.5 flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                    <p.icon className="h-4 w-4 text-primary" />
                  </div>
                  <h3 className="text-sm font-semibold">{p.title}</h3>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {p.desc}
                  </p>
                  <p className="mt-auto pt-2.5 text-[10px] font-medium text-primary/70">
                    Best for: {p.bestFor}
                  </p>
                </a>
              ))}
            </div>

            <div className="mt-5 flex justify-center">
              <a
                href="/dashboard/workflows/new"
                className="group inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-all hover:bg-primary/90"
              >
                Try Workflows
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
