// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import {
  GitBranch,
  Workflow,
  Sparkles,
  ArrowRight,
} from "lucide-react";
import { MagicBox } from "@/components/landing/magic-box";

export function HeroPanels() {
  return (
    <div className="mx-auto mt-8 max-w-5xl" id="magic-box">
      <div className="grid gap-6 lg:grid-cols-5">
        {/* Left panel: Find an Agent (3 cols) */}
        <div className="rounded-2xl border bg-card p-5 sm:p-6 lg:col-span-3">
          <h2 className="mb-1 text-lg font-bold">Find an Agent</h2>
          <p className="mb-4 text-sm text-muted-foreground">Describe what you need — AI matches the best specialist</p>
          <MagicBox />
        </div>

        {/* Right panel: Build a Workflow (2 cols) */}
        <div className="rounded-2xl border bg-card p-5 sm:p-6 lg:col-span-2">
          <h2 className="mb-1 text-lg font-bold">Build a Workflow</h2>
          <p className="mb-4 text-sm text-muted-foreground">Chain agents into multi-step pipelines</p>

          <div className="space-y-2">
            {[
              { icon: GitBranch, title: "Run Steps in Order", desc: "Sequential or parallel chains", href: "/dashboard/workflows/new?pattern=manual" },
              { icon: Workflow, title: "Reusable Pipelines", desc: "Nested sub-workflows", href: "/dashboard/workflows/new?pattern=hierarchical" },
              { icon: Sparkles, title: "Let AI Plan It", desc: "AI picks agents & builds the plan", href: "/dashboard/workflows/new?pattern=supervisor" },
            ].map((p) => (
              <a
                key={p.title}
                href={p.href}
                className="group flex items-center gap-3 rounded-lg border border-transparent px-3 py-2.5 transition-colors hover:border-primary/30 hover:bg-primary/5"
              >
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary/10">
                  <p.icon className="h-4 w-4 text-primary" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">{p.title}</p>
                  <p className="text-xs text-muted-foreground">{p.desc}</p>
                </div>
                <ArrowRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
              </a>
            ))}
          </div>

          <a href="/dashboard/workflows/new" className="mt-4 flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-transform hover:translate-x-0.5">
            Create Workflow <ArrowRight className="h-4 w-4" />
          </a>
        </div>
      </div>
    </div>
  );
}
