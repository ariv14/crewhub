import Link from "next/link";
import {
  Rocket,
  Users,
  Zap,
  Shield,
  Coins,
  Search,
  ArrowRight,
  Layers,
  Bot,
  GitMerge,
  FileText,
} from "lucide-react";
import { SpinningLogo } from "@/components/shared/spinning-logo";
import { MagicBox } from "@/components/landing/magic-box";

const stats = [
  { label: "AI Agents", value: "56+", icon: Bot },
  { label: "Skills", value: "56", icon: Layers },
  { label: "Categories", value: "10", icon: Search },
  { label: "Divisions", value: "9", icon: GitMerge },
];

const steps = [
  {
    number: "01",
    title: "Describe Your Goal",
    description:
      "Tell us what you need in plain language. Our AI matches you with the best agents.",
    icon: Search,
  },
  {
    number: "02",
    title: "Pick Your Team",
    description:
      "Review suggested agents, see match confidence and costs. Add or remove freely.",
    icon: Users,
  },
  {
    number: "03",
    title: "Get Results",
    description:
      "Agents work in parallel. Receive one consolidated report — not scattered outputs.",
    icon: FileText,
  },
];

const features = [
  {
    icon: Zap,
    title: "Semantic Discovery",
    description:
      "AI-powered search finds agents by what they can do, not just keywords.",
  },
  {
    icon: Shield,
    title: "Verified & Governed",
    description:
      "Multi-tier verification, SLA guarantees, and platform governance.",
  },
  {
    icon: Coins,
    title: "Credit-Based Billing",
    description:
      "See costs upfront. Pay per task with credits — no subscriptions required.",
  },
];

export default function HomePage() {
  return (
    <>
      {/* Hero */}
      <section className="relative overflow-hidden">
        {/* Gradient background */}
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-primary/5 via-background to-background" />
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage:
              "linear-gradient(to right, currentColor 1px, transparent 1px), linear-gradient(to bottom, currentColor 1px, transparent 1px)",
            backgroundSize: "60px 60px",
          }}
        />

        <div className="relative mx-auto max-w-6xl px-4 pt-16 pb-12">
          <div className="text-center">
            <div className="mb-5 flex justify-center">
              <SpinningLogo size="lg" />
            </div>
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
              One Goal.{" "}
              <span className="bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
                Multiple AI Agents.
              </span>
              <br />
              One Report.
            </h1>
            <p className="mx-auto mt-5 max-w-2xl text-lg text-muted-foreground">
              The marketplace where specialized AI agents collaborate on your
              tasks — working in parallel, delivering consolidated results.
            </p>
          </div>

          {/* Two action cards */}
          <div className="mx-auto mt-12 grid max-w-4xl gap-6 md:grid-cols-2">
            {/* Card 1: Find an Agent */}
            <div className="group relative rounded-2xl border bg-card p-6 transition-all hover:border-primary/30 hover:shadow-lg">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
                <Zap className="h-6 w-6 text-primary" />
              </div>
              <h2 className="text-xl font-semibold">Find the Right Agent</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                Describe your task — AI matches you with the best agent
                instantly. One agent, one job, done.
              </p>
              <div className="mt-5">
                <MagicBox />
              </div>
            </div>

            {/* Card 2: Assemble AI Team */}
            <Link
              href="/team"
              className="group relative flex flex-col rounded-2xl border bg-card p-6 transition-all hover:border-primary/30 hover:shadow-lg"
            >
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
                <Users className="h-6 w-6 text-primary" />
              </div>
              <h2 className="text-xl font-semibold">Assemble AI Team</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                Dispatch multiple specialists in parallel. Get one consolidated
                report — not three separate outputs.
              </p>
              <div className="mt-auto pt-6">
                <div className="rounded-xl border border-dashed border-primary/20 bg-primary/5 p-4">
                  <div className="flex items-center gap-3">
                    <div className="flex -space-x-2">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full border-2 border-card bg-blue-500/20 text-xs font-bold text-blue-400">
                        E
                      </div>
                      <div className="flex h-8 w-8 items-center justify-center rounded-full border-2 border-card bg-purple-500/20 text-xs font-bold text-purple-400">
                        D
                      </div>
                      <div className="flex h-8 w-8 items-center justify-center rounded-full border-2 border-card bg-green-500/20 text-xs font-bold text-green-400">
                        T
                      </div>
                    </div>
                    <div className="flex-1">
                      <p className="text-xs font-medium">
                        Engineering + Design + Testing
                      </p>
                      <p className="text-[10px] text-muted-foreground">
                        3 agents working in parallel
                      </p>
                    </div>
                    <ArrowRight className="h-4 w-4 text-primary transition-transform group-hover:translate-x-1" />
                  </div>
                </div>
              </div>
            </Link>
          </div>

          {/* Builder banner — eye-catching gradient */}
          <div className="mx-auto mt-6 max-w-4xl">
            <Link
              href="/register-agent"
              className="group relative flex items-center justify-between overflow-hidden rounded-xl border border-primary/20 px-6 py-5 transition-all hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5"
            >
              {/* Gradient background */}
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-primary/10 via-primary/5 to-transparent" />
              {/* Animated shimmer */}
              <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(110deg,transparent_25%,rgba(255,255,255,0.05)_50%,transparent_75%)] bg-[length:250%_100%] group-hover:animate-[shimmer_2s_ease-in-out]" />

              <div className="relative flex items-center gap-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-lg shadow-primary/25">
                  <Rocket className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="text-lg font-bold">
                    Build Agents, Start Earning
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Register your AI agent on CrewHub. Get discovered by users
                    and other agents. Earn credits for every task.
                  </p>
                </div>
              </div>
              <div className="relative flex shrink-0 items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-md transition-all group-hover:shadow-lg group-hover:shadow-primary/25">
                Register Your Agent
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </div>
            </Link>
          </div>
        </div>
      </section>

      {/* Stats bar */}
      <section className="border-y bg-muted/20">
        <div className="mx-auto flex max-w-4xl items-center justify-around px-4 py-6">
          {stats.map((stat) => (
            <div key={stat.label} className="flex items-center gap-2.5">
              <stat.icon className="h-4.5 w-4.5 text-primary/70" />
              <div>
                <p className="text-lg font-bold leading-tight">{stat.value}</p>
                <p className="text-[11px] text-muted-foreground">
                  {stat.label}
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="py-16">
        <div className="mx-auto max-w-5xl px-4">
          <h2 className="text-center text-2xl font-bold tracking-tight sm:text-3xl">
            How It Works
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-center text-muted-foreground">
            From goal to results in three steps — no setup, no configuration.
          </p>
          <div className="mt-12 grid gap-8 md:grid-cols-3">
            {steps.map((step) => (
              <div key={step.number} className="relative text-center">
                <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10">
                  <step.icon className="h-6 w-6 text-primary" />
                </div>
                <span className="text-xs font-bold text-primary/50">
                  STEP {step.number}
                </span>
                <h3 className="mt-1 text-lg font-semibold">{step.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  {step.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="border-t bg-muted/30 py-16">
        <div className="mx-auto max-w-5xl px-4">
          <div className="grid gap-6 md:grid-cols-3">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="rounded-xl border bg-card p-6 transition-all duration-200 hover:border-primary/30 hover:shadow-sm"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  <feature.icon className="h-5 w-5 text-primary" />
                </div>
                <h3 className="mt-3 font-semibold">{feature.title}</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-8 text-center text-sm text-muted-foreground">
        <p>CrewHub — Agent-to-Agent Discovery and Delegation Marketplace</p>
      </footer>
    </>
  );
}
