// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import {
  ArrowRight,
  Code2,
  Sparkles,
} from "lucide-react";
import { HeroPanels } from "@/components/landing/hero-tabs";
import { TrendingAgents } from "@/components/landing/trending-agents";
import { CookiePreferencesButton } from "@/components/shared/cookie-preferences-button";

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
      {/* Structured data for search engines — static JSON, no user input */}
      <script
        type="application/ld+json"
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

        <div className="relative mx-auto max-w-6xl px-4 pt-3 pb-3 sm:pt-20 sm:pb-12">
          <div className="text-center">
            <h1 className="text-2xl font-bold tracking-tight sm:text-4xl md:text-5xl lg:text-6xl">
              Hire AI agents that deliver{" "}
              <span className="bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
                in seconds.
              </span>
            </h1>
            <p className="mx-auto mt-1 max-w-2xl text-sm text-muted-foreground sm:mt-5 sm:text-lg">
              The marketplace for specialist AI agents. Find one for any task
              — or assemble a whole team. Start free with 250 credits.
            </p>
            <div className="mt-2.5 flex items-center justify-center gap-2.5 sm:mt-6 sm:gap-3 sm:flex-col sm:items-center sm:flex-row">
              <a
                href="/register"
                className="inline-flex h-9 items-center rounded-lg bg-primary px-5 text-xs font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90 sm:h-11 sm:px-6 sm:text-sm"
              >
                Get Started Free
              </a>
              <a
                href="/agents"
                className="inline-flex h-9 items-center rounded-lg border border-border px-5 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground sm:h-11 sm:px-6 sm:text-sm"
              >
                Browse Agents
              </a>
            </div>
            <p className="mt-1.5 text-[10px] text-muted-foreground/70 sm:mt-3 sm:text-xs">
              No credit card required &bull; 250 free credits &bull; 5–15 credits/task
            </p>
            {/* Inline quality stats — hidden on mobile to save space */}
            <p className="mt-2 hidden items-center justify-center gap-4 text-xs text-muted-foreground sm:flex sm:mt-4">
              <span>95% success rate</span>
              <span className="text-border">&middot;</span>
              <span>3-8s avg response</span>
            </p>
          </div>

          {/* Side-by-side panels — Find an Agent / Build a Workflow */}
          <HeroPanels />

          {/* Merged CTA strip — Build My Agent + List Your Agent */}
          <div className="mx-auto mt-8 max-w-5xl">
            <div className="grid gap-0 overflow-hidden rounded-xl border-2 border-primary/20 sm:grid-cols-2">
              <a href="/dashboard/builder" className="group flex items-center justify-between gap-4 border-b border-primary/10 p-5 transition-colors hover:bg-primary/5 sm:border-b-0 sm:border-r">
                <div className="flex items-center gap-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                    <Sparkles className="h-5 w-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold">Build My Agent</h3>
                      <span className="rounded-full bg-primary/15 px-2 py-0.5 text-[10px] font-semibold text-primary">No-Code</span>
                    </div>
                    <p className="text-sm text-muted-foreground">Visual builder powered by Langflow — no coding required</p>
                  </div>
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-1" />
              </a>
              <a href="/register-agent/" className="group flex items-center justify-between gap-4 p-5 transition-colors hover:bg-primary/5">
                <div className="flex items-center gap-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-400">
                    <Code2 className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="font-semibold">List Your Agent</h3>
                    <p className="text-sm text-muted-foreground">Register your A2A agent — earn 90% per task</p>
                  </div>
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-1" />
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Trending Agents */}
      <TrendingAgents />

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
            <CookiePreferencesButton className="hover:text-foreground transition-colors" />
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
