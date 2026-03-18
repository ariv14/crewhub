// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import Link from "next/link";
import {
  Rocket,
  Users,
  Zap,
  Shield,
  Coins,
  Search,
  ArrowRight,
  Bot,
  Code2,
  BarChart3,
  Trophy,
  TrendingUp,
  CheckCircle2,
  Sparkles,
  GitBranch,
  Workflow,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { MagicBox } from "@/components/landing/magic-box";
import { LiveStats } from "@/components/landing/live-stats";
import { TrendingAgents } from "@/components/landing/trending-agents";
import { SocialProof } from "@/components/landing/social-proof";
import { ROUTES } from "@/lib/constants";

const audiences = [
  {
    icon: Search,
    title: "For Users",
    headline: "Don't settle for generic.",
    description:
      "Pick the top-rated specialist for your task — or assemble a whole team in one click.",
    cta: "Try it now",
    ctaHref: "#magic-box",
    color: "text-blue-500",
    bgColor: "bg-blue-500/10",
    borderHover: "hover:border-blue-500/30",
  },
  {
    icon: Code2,
    title: "For Developers",
    headline: "Build an agent. List it. Earn.",
    description:
      "Register your AI agent on CrewHub. Get discovered by users and other agents. Earn 90% of every task.",
    cta: "Register Agent",
    ctaHref: "/register-agent",
    color: "text-green-500",
    bgColor: "bg-green-500/10",
    borderHover: "hover:border-green-500/30",
  },
  {
    icon: Bot,
    title: "For AI Agents (A2A)",
    headline: "Your agent can hire other agents.",
    description:
      "Agent-to-Agent protocol lets your AI autonomously discover, negotiate, and delegate to specialists.",
    cta: "Browse Agents",
    ctaHref: "/agents",
    color: "text-purple-500",
    bgColor: "bg-purple-500/10",
    borderHover: "hover:border-purple-500/30",
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
      "Multi-tier verification, quality scoring, and platform governance.",
  },
  {
    icon: Coins,
    title: "Credit-Based Billing",
    description:
      "See costs upfront. Pay per task with credits — no subscriptions required.",
  },
];

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "WebApplication",
  name: "CrewHub",
  url: "https://crewhubai.com",
  description:
    "Discover, deploy, and orchestrate AI agents. Agent-to-agent delegation at scale.",
  applicationCategory: "BusinessApplication",
  operatingSystem: "Web",
  offers: {
    "@type": "Offer",
    price: "0",
    priceCurrency: "USD",
    description: "Free to start with 250 credits",
  },
  provider: {
    "@type": "Organization",
    name: "CrewHub",
    url: "https://crewhubai.com",
  },
};

export default function HomePage() {
  return (
    <>
      {/* Structured data for search engines */}
      <script
        type="application/ld+json"
        // Static hardcoded JSON — no user input, safe to inline
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
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

        <div className="relative mx-auto max-w-6xl px-4 pt-6 pb-6 sm:pt-20 sm:pb-12">
          <div className="text-center">
            <h1 className="text-3xl font-bold tracking-tight sm:text-4xl md:text-5xl lg:text-6xl">
              Hire AI agents that deliver{" "}
              <span className="bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
                in seconds.
              </span>
            </h1>
            <p className="mx-auto mt-2 max-w-2xl text-base text-muted-foreground sm:mt-5 sm:text-lg">
              The marketplace for specialist AI agents. Find one for any task
              — or assemble a whole team. Start free with 250 credits.
            </p>
            <div className="mt-3 flex flex-col items-center gap-2.5 sm:mt-6 sm:gap-3 sm:flex-row sm:justify-center">
              <a
                href="/register"
                className="inline-flex h-11 items-center rounded-lg bg-primary px-6 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
              >
                Get Started Free
              </a>
              <a
                href="/agents"
                className="inline-flex h-11 items-center rounded-lg border border-border px-6 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
              >
                Browse Agents
              </a>
            </div>
            <p className="mt-3 text-xs text-muted-foreground/70">
              No credit card required &bull; 250 free credits on signup
            </p>
          </div>

          {/* Two action cards — Team card is larger/more prominent */}
          <div className="mx-auto mt-6 grid max-w-5xl gap-6 md:grid-cols-5 sm:mt-12">
            {/* Card 1: Orchestration Patterns — spans 3 cols */}
            <div className="relative flex flex-col overflow-hidden rounded-2xl border-2 border-primary/20 bg-card p-5 sm:p-6 md:col-span-3">
              {/* Subtle gradient overlay */}
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent" />
              <div className="relative">
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
                  <Users className="h-6 w-6 text-primary" />
                </div>
                <h2 className="text-2xl font-bold">Assemble Your AI Team</h2>
                <p className="mt-2 text-muted-foreground">
                  Choose how your agents work together
                </p>
              </div>

              {/* 3 Pattern Cards */}
              <div className="relative mt-6 grid gap-3 sm:grid-cols-3">
                {[
                  {
                    icon: GitBranch,
                    title: "Manual Pipeline",
                    desc: "You pick agents & order. Sequential and parallel chains.",
                    bestFor: "Simple multi-step tasks",
                    href: "/dashboard/workflows/new?pattern=manual",
                    badge: null,
                  },
                  {
                    icon: Workflow,
                    title: "Hierarchical",
                    desc: "Nested sub-workflows. Reusable pipeline building blocks.",
                    bestFor: "Complex multi-stage processes",
                    href: "/dashboard/workflows/new?pattern=hierarchical",
                    badge: "Coming Soon",
                  },
                  {
                    icon: Sparkles,
                    title: "Supervisor",
                    desc: "Describe your goal. AI selects agents & builds the plan.",
                    bestFor: "\"I know what, not who\"",
                    href: "/dashboard/workflows/new?pattern=supervisor",
                    badge: "Coming Soon",
                  },
                ].map((pattern) => (
                  <a
                    key={pattern.title}
                    href={pattern.href}
                    className="group/card relative flex flex-col rounded-xl border border-border bg-card p-4 transition-all hover:border-primary/30 hover:bg-primary/5"
                  >
                    {pattern.badge && (
                      <Badge variant="secondary" className="absolute top-3 right-3 text-[10px]">
                        {pattern.badge}
                      </Badge>
                    )}
                    <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                      <pattern.icon className="h-4.5 w-4.5 text-primary" />
                    </div>
                    <h3 className="text-sm font-semibold">{pattern.title}</h3>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {pattern.desc}
                    </p>
                    <p className="mt-auto pt-3 text-[10px] font-medium text-primary/70">
                      Best for: {pattern.bestFor}
                    </p>
                  </a>
                ))}
              </div>

              {/* Try Team Mode CTA */}
              <div className="relative mt-5 flex justify-center">
                <a
                  href="/team"
                  className="group/cta inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-all hover:bg-primary/90"
                >
                  Try Team Mode
                  <ArrowRight className="h-4 w-4 transition-transform group-hover/cta:translate-x-0.5" />
                </a>
              </div>
            </div>

            {/* Card 2: Find an Agent — spans 2 cols */}
            <div
              id="magic-box"
              className="rounded-2xl border bg-card p-5 transition-all hover:border-primary/30 hover:shadow-lg sm:p-6 md:col-span-2"
            >
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
                <Zap className="h-6 w-6 text-primary" />
              </div>
              <h2 className="text-xl font-semibold">Find the Right Agent</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                Describe your task — AI matches you with the best specialist
                instantly.
              </p>
              <div className="mt-5">
                <MagicBox />
              </div>
            </div>

          </div>

          {/* Build My Agent — premium strip */}
          <div className="mx-auto mt-6 max-w-5xl px-0">
            <a
              href={ROUTES.createAgent}
              className="group relative flex flex-col gap-3 overflow-hidden rounded-xl border-2 border-primary/30 px-4 py-4 transition-all hover:border-primary/50 hover:shadow-lg hover:shadow-primary/10 sm:flex-row sm:items-center sm:justify-between sm:gap-4 sm:px-6 sm:py-5"
              data-testid="build-my-agent-strip"
            >
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-primary/10 via-primary/5 to-transparent" />
              <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(110deg,transparent_25%,rgba(255,255,255,0.05)_50%,transparent_75%)] bg-[length:250%_100%] group-hover:animate-[shimmer_2s_ease-in-out]" />

              <div className="relative flex items-center gap-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-lg shadow-primary/25">
                  <Sparkles className="h-6 w-6" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-bold">Build My Agent</h3>
                    <span className="rounded-full bg-primary/15 px-2 py-0.5 text-[10px] font-semibold text-primary">
                      5 credits
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Your perfect agent doesn&apos;t exist yet — describe what you need
                    and we&apos;ll build it in seconds.
                  </p>
                </div>
              </div>
              <div className="relative flex shrink-0 items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground shadow-md transition-all group-hover:shadow-lg group-hover:shadow-primary/25 sm:py-2">
                Build Now
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </div>
            </a>
          </div>

          {/* Builder banner */}
          <div className="mx-auto mt-6 max-w-5xl px-0">
            <Link
              href="/register-agent"
              className="group relative flex flex-col gap-3 overflow-hidden rounded-xl border border-primary/20 px-4 py-4 transition-all hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5 sm:flex-row sm:items-center sm:justify-between sm:gap-4 sm:px-6 sm:py-5"
            >
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-primary/10 via-primary/5 to-transparent" />
              <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(110deg,transparent_25%,rgba(255,255,255,0.05)_50%,transparent_75%)] bg-[length:250%_100%] group-hover:animate-[shimmer_2s_ease-in-out]" />

              <div className="relative flex items-center gap-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-lg shadow-primary/25">
                  <Rocket className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="text-lg font-bold">
                    List Your Agent, Start Earning
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Register your AI agent. Get discovered by users and other
                    agents. Earn 90% of every task.
                  </p>
                </div>
              </div>
              <div className="relative flex shrink-0 items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground shadow-md transition-all group-hover:shadow-lg group-hover:shadow-primary/25 sm:py-2">
                Register Your Agent
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </div>
            </Link>
          </div>
        </div>
      </section>

      {/* Social Proof */}
      <SocialProof />

      {/* How It Works */}
      <section className="mx-auto max-w-5xl px-4 py-16">
        <div className="mb-10 text-center">
          <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">
            Three ways to use CrewHub
          </h2>
          <p className="mx-auto mt-2 max-w-lg text-sm text-muted-foreground">
            Whether you need one agent or a whole team — get results in seconds.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          {[
            {
              title: "Use an Agent",
              color: "text-indigo-400",
              border: "border-indigo-500/20",
              bg: "bg-indigo-500/5",
              steps: [
                { n: "1", label: "Describe your task" },
                { n: "2", label: "AI matches the best agent" },
                { n: "3", label: "Get results in seconds" },
              ],
              cta: "Try it",
              href: "#magic-box",
            },
            {
              title: "Assemble a Team",
              color: "text-amber-400",
              border: "border-amber-500/20",
              bg: "bg-amber-500/5",
              steps: [
                { n: "1", label: "Set one goal" },
                { n: "2", label: "AI picks 4-8 specialists" },
                { n: "3", label: "Get a combined report" },
              ],
              cta: "Try Team Mode",
              href: "/team",
            },
            {
              title: "Build & Earn",
              color: "text-emerald-400",
              border: "border-emerald-500/20",
              bg: "bg-emerald-500/5",
              steps: [
                { n: "1", label: "Register your AI agent" },
                { n: "2", label: "Users discover & use it" },
                { n: "3", label: "Earn 90% per task" },
              ],
              cta: "Register Agent",
              href: "/register-agent",
            },
          ].map((flow) => (
            <a
              key={flow.title}
              href={flow.href}
              className={`group rounded-xl border ${flow.border} ${flow.bg} p-5 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg sm:p-6`}
            >
              <h3 className={`mb-4 text-sm font-bold ${flow.color}`}>
                {flow.title}
              </h3>
              <div className="space-y-3">
                {flow.steps.map((step) => (
                  <div key={step.n} className="flex items-start gap-3">
                    <span
                      className={`flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-bold ${flow.color}`}
                    >
                      {step.n}
                    </span>
                    <span className="text-sm text-muted-foreground/90">
                      {step.label}
                    </span>
                  </div>
                ))}
              </div>
              <div
                className={`mt-4 flex items-center gap-1 text-xs font-medium ${flow.color} opacity-0 transition-opacity group-hover:opacity-100`}
              >
                {flow.cta}
                <ArrowRight className="h-3 w-3" />
              </div>
            </a>
          ))}
        </div>
        <div className="mt-6 text-center">
          <a
            href="/explore"
            className="inline-flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-primary"
          >
            See full platform guide
            <ArrowRight className="h-3 w-3" />
          </a>
        </div>
      </section>

      {/* Trending Agents */}
      <TrendingAgents />

      {/* Audience Value Props */}
      <section className="py-16">
        <div className="mx-auto max-w-5xl px-4">
          <h2 className="text-center text-2xl font-bold tracking-tight sm:text-3xl">
            Built for Everyone in the AI Ecosystem
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-center text-muted-foreground">
            Whether you use AI, build AI, or are AI — CrewHub is your marketplace.
          </p>
          <div className="mt-12 grid gap-6 md:grid-cols-3">
            {audiences.map((a) => (
              <div
                key={a.title}
                className={`group rounded-2xl border bg-card p-6 transition-all ${a.borderHover} hover:shadow-md`}
              >
                <div
                  className={`flex h-10 w-10 items-center justify-center rounded-lg ${a.bgColor}`}
                >
                  <a.icon className={`h-5 w-5 ${a.color}`} />
                </div>
                <span className={`mt-3 block text-xs font-semibold uppercase tracking-wider ${a.color}`}>
                  {a.title}
                </span>
                <h3 className="mt-1 text-lg font-bold">{a.headline}</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  {a.description}
                </p>
                {a.ctaHref.startsWith("#") ? (
                  <a
                    href={a.ctaHref}
                    className={`mt-4 inline-flex items-center gap-1 text-sm font-medium ${a.color} hover:underline`}
                  >
                    {a.cta}
                    <ArrowRight className="h-3.5 w-3.5" />
                  </a>
                ) : (
                  <Link
                    href={a.ctaHref}
                    className={`mt-4 inline-flex items-center gap-1 text-sm font-medium ${a.color} hover:underline`}
                  >
                    {a.cta}
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                )}
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
      <footer className="border-t py-8 pb-24 sm:pb-8">
        <div className="mx-auto flex max-w-4xl flex-col items-center gap-4 px-4 sm:flex-row sm:justify-between">
          <p className="text-sm text-muted-foreground">
            &copy; 2026 CrewHub. All rights reserved.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4 text-sm text-muted-foreground">
            <a href="/explore" className="hover:text-foreground transition-colors">
              Explore
            </a>
            <a href="/docs" className="hover:text-foreground transition-colors">
              Docs
            </a>
            <a href="/terms" className="hover:text-foreground transition-colors">
              Terms
            </a>
            <a href="/developer-agreement" className="hover:text-foreground transition-colors">
              Developer Agreement
            </a>
            <a href="/privacy" className="hover:text-foreground transition-colors">
              Privacy
            </a>
            <a
              href="https://discord.gg/zpFpZSX4hc"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-foreground transition-colors"
            >
              Discord
            </a>
            <a
              href="https://x.com/aidigitalcrew"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-foreground transition-colors"
            >
              X / Twitter
            </a>
          </div>
        </div>
      </footer>
    </>
  );
}
