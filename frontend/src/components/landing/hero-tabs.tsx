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
    <div className="mx-auto mt-6 max-w-5xl sm:mt-8" id="magic-box">
      <div className="grid gap-3 sm:gap-6 lg:grid-cols-2">
        {/* Left panel: Find an Agent */}
        <div className="flex flex-col rounded-xl border bg-card p-3.5 sm:rounded-2xl sm:p-6">
          <h2 className="mb-0.5 text-base font-bold sm:mb-1 sm:text-lg">Find an Agent</h2>
          <p className="mb-3 hidden text-sm text-muted-foreground sm:block">Describe what you need — AI matches the best specialist</p>
          <p className="mb-2 text-xs text-muted-foreground sm:hidden">AI matches the best specialist</p>
          <MagicBox />
        </div>

        {/* Right panel: Build a Workflow */}
        <div className="flex flex-col rounded-xl border bg-card p-3.5 sm:rounded-2xl sm:p-6">
          <h2 className="mb-0.5 text-base font-bold sm:mb-1 sm:text-lg">Build a Workflow</h2>
          <p className="mb-3 hidden text-sm text-muted-foreground sm:block">Chain agents into multi-step pipelines</p>
          <p className="mb-2 text-xs text-muted-foreground sm:hidden">Chain agents into pipelines</p>

          <div className="space-y-1 sm:space-y-2">
            {[
              { icon: GitBranch, title: "Run Steps in Order", desc: "Sequential or parallel chains", href: "/dashboard/workflows/new?pattern=manual" },
              { icon: Workflow, title: "Reusable Pipelines", desc: "Nested sub-workflows", href: "/dashboard/workflows/new?pattern=hierarchical" },
              { icon: Sparkles, title: "Let AI Plan It", desc: "AI picks agents & builds the plan", href: "/dashboard/workflows/new?pattern=supervisor" },
            ].map((p) => (
              <a
                key={p.title}
                href={p.href}
                className="group flex items-center gap-2.5 rounded-lg border border-transparent px-2.5 py-2 transition-colors hover:border-primary/30 hover:bg-primary/5 sm:gap-3 sm:px-3 sm:py-2.5"
              >
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary/10 sm:h-8 sm:w-8">
                  <p.icon className="h-3.5 w-3.5 text-primary sm:h-4 sm:w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium sm:text-sm">{p.title}</p>
                  <p className="hidden text-xs text-muted-foreground sm:block">{p.desc}</p>
                </div>
                <ArrowRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
              </a>
            ))}
          </div>

          <a href="/dashboard/workflows/new" className="mt-3 flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground transition-transform hover:translate-x-0.5 sm:mt-4 sm:text-sm">
            Create Workflow <ArrowRight className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
          </a>
        </div>
      </div>
    </div>
  );
}
