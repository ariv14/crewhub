// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import {
  GitBranch,
  Workflow,
  Sparkles,
  ArrowRight,
  Search,
  Zap,
} from "lucide-react";
import { MagicBox } from "@/components/landing/magic-box";

function GlowCard({
  children,
  accentFrom,
  accentTo,
}: {
  children: React.ReactNode;
  accentFrom: string;
  accentTo: string;
}) {
  return (
    <div className="group/card relative min-w-0">
      {/* Animated gradient border */}
      <div
        className="absolute -inset-[1px] rounded-xl opacity-50 blur-[1px] transition-all duration-500 group-hover/card:opacity-100 group-hover/card:blur-[2px] sm:rounded-2xl"
        style={{
          background: `linear-gradient(135deg, ${accentFrom}, ${accentTo}, ${accentFrom})`,
          backgroundSize: "200% 200%",
          animation: "shimmer 3s ease-in-out infinite",
        }}
      />
      {/* Card content — z-10 to sit above gradient border, overflow-visible for dropdowns */}
      <div className="relative z-10 flex flex-col overflow-visible rounded-xl border border-white/[0.08] bg-card p-3.5 backdrop-blur-sm transition-shadow duration-500 group-hover/card:shadow-lg group-hover/card:shadow-primary/5 sm:rounded-2xl sm:p-6">
        {children}
      </div>
    </div>
  );
}

export function HeroPanels() {
  return (
    <>
      {/* Keyframe animation for gradient shimmer */}
      <style>{`
        @keyframes shimmer {
          0%, 100% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
        }
      `}</style>

      <div className="mx-auto mt-6 max-w-5xl sm:mt-8" id="magic-box">
        <div className="grid grid-cols-1 gap-3 sm:gap-6 lg:grid-cols-2">
          {/* Left panel: Find an Agent */}
          <GlowCard accentFrom="oklch(0.55 0.22 275)" accentTo="oklch(0.6 0.18 240)">
            <div className="mb-2 flex items-center gap-2 sm:mb-3">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/15 sm:h-8 sm:w-8">
                <Search className="h-3.5 w-3.5 text-primary sm:h-4 sm:w-4" />
              </div>
              <div>
                <h2 className="text-base font-bold sm:text-lg">Find an Agent</h2>
              </div>
            </div>
            <p className="mb-3 hidden text-sm text-muted-foreground sm:block">Describe what you need — AI matches the best specialist</p>
            <p className="mb-2 text-xs text-muted-foreground sm:hidden">AI matches the best specialist</p>
            <MagicBox />
          </GlowCard>

          {/* Right panel: Build a Workflow */}
          <GlowCard accentFrom="oklch(0.55 0.18 200)" accentTo="oklch(0.5 0.22 275)">
            <div className="mb-2 flex items-center gap-2 sm:mb-3">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/15 sm:h-8 sm:w-8">
                <Zap className="h-3.5 w-3.5 text-primary sm:h-4 sm:w-4" />
              </div>
              <div>
                <h2 className="text-base font-bold sm:text-lg">Build a Workflow</h2>
              </div>
            </div>
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
                  className="group flex items-center gap-2.5 rounded-lg border border-white/[0.04] px-2.5 py-2 transition-all hover:border-primary/30 hover:bg-primary/5 sm:gap-3 sm:px-3 sm:py-2.5"
                >
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary/10 transition-colors group-hover:bg-primary/20 sm:h-8 sm:w-8">
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

            <a href="/dashboard/workflows/new" className="mt-3 flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground shadow-sm shadow-primary/20 transition-all hover:shadow-md hover:shadow-primary/30 hover:translate-x-0.5 sm:mt-4 sm:text-sm">
              Create Workflow <ArrowRight className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
            </a>
          </GlowCard>
        </div>
      </div>
    </>
  );
}
