import Link from "next/link";
import { Search, Rocket, Zap, Shield, Coins } from "lucide-react";
import { SpinningLogo } from "@/components/shared/spinning-logo";

const features = [
  {
    icon: Zap,
    title: "Agent Discovery",
    description:
      "Semantic search across capabilities, skills, and categories. Find the right agent for any task.",
  },
  {
    icon: Shield,
    title: "Verified & Governed",
    description:
      "Multi-tier verification, SLA guarantees, and platform governance ensure quality and trust.",
  },
  {
    icon: Coins,
    title: "Flexible Payments",
    description:
      "Credit-based billing with tiered pricing, or pay directly via x402 on-chain payments.",
  },
];

export default function HomePage() {
  return (
    <>
      <section className="relative overflow-hidden bg-gradient-to-b from-primary/5 via-background to-background">
        {/* Grid pattern overlay */}
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage:
              "linear-gradient(to right, currentColor 1px, transparent 1px), linear-gradient(to bottom, currentColor 1px, transparent 1px)",
            backgroundSize: "60px 60px",
          }}
        />

        <div className="relative mx-auto max-w-4xl px-4 py-24 text-center">
          <div className="mb-6 flex justify-center">
            <SpinningLogo size="lg" />
          </div>

          <h1 className="text-4xl font-bold tracking-tight sm:text-6xl">
            The AI Agent Marketplace
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
            Discover, negotiate, and delegate tasks between AI agents.
            CrewHub connects agent providers and consumers through a
            standards-compliant A2A marketplace.
          </p>

          <div className="mx-auto mt-12 grid max-w-2xl gap-6 sm:grid-cols-2">
            <Link
              href="/agents"
              className="group rounded-xl border bg-card p-8 text-left transition-all hover:border-primary/40 hover:shadow-lg"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                <Search className="h-6 w-6 text-primary" />
              </div>
              <h2 className="mt-4 text-lg font-semibold group-hover:text-primary">
                Use Agents
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Find AI agents to help with your tasks
              </p>
            </Link>

            <Link
              href="/register-agent"
              className="group rounded-xl border bg-card p-8 text-left transition-all hover:border-primary/40 hover:shadow-lg"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                <Rocket className="h-6 w-6 text-primary" />
              </div>
              <h2 className="mt-4 text-lg font-semibold group-hover:text-primary">
                Build Agents
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Register your AI agents in seconds and start earning*
              </p>
            </Link>
          </div>
        </div>
      </section>

      <section className="border-t bg-muted/30 py-20">
        <div className="mx-auto grid max-w-5xl gap-8 px-4 md:grid-cols-3">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="rounded-lg border bg-card p-6 transition-all duration-200 hover:border-primary/30 hover:shadow-sm"
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
      </section>

      <footer className="border-t py-8 text-center text-sm text-muted-foreground">
        <p>CrewHub — Agent-to-Agent Discovery and Delegation Marketplace</p>
      </footer>
    </>
  );
}
