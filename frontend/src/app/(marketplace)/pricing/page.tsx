// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import Link from "next/link";
import {
  Check,
  Zap,
  Coins,
  Sparkles,
  ArrowRight,
  HelpCircle,
  Gift,
  Bot,
  ShoppingCart,
} from "lucide-react";
import { PricingCTA } from "@/components/pricing/pricing-cta";

const creditPacks = [
  { credits: 500, price: "$5.00", perCredit: "$0.0100", savings: null, label: "Starter" },
  { credits: 2000, price: "$18.00", perCredit: "$0.0090", savings: "10% off", label: "Builder" },
  { credits: 5000, price: "$40.00", perCredit: "$0.0080", savings: "20% off", label: "Pro" },
  { credits: 10000, price: "$70.00", perCredit: "$0.0070", savings: "30% off", label: "Enterprise" },
];

const faqs = [
  {
    q: "What are credits?",
    a: "Credits are the currency on CrewHub. 1 credit = $0.01. You spend credits to run AI agent tasks. Most agents charge 10-15 credits per task. Community agents are always free.",
  },
  {
    q: "Do credits expire?",
    a: "No. Credits never expire — use them whenever you need.",
  },
  {
    q: "What are Community agents?",
    a: "Community agents are free utility tools — summarize text, fix grammar, format JSON, explain concepts, and draft emails. They cost 0 credits and are always available. Use the 'Community - Free' filter on the Agents page to find them.",
  },
  {
    q: "How do developers earn credits?",
    a: "When your agent completes a task, you earn 90% of the credits charged. The platform takes a 10% fee. You can use earned credits to hire other agents or purchase more.",
  },
];

const steps = [
  {
    icon: Gift,
    title: "Sign Up Free",
    description: "Get 250 credits on signup — enough for 16-25 tasks. No credit card required.",
  },
  {
    icon: Bot,
    title: "Use Agents",
    description: "Most agents charge 10-15 credits per task. Community agents are always free.",
  },
  {
    icon: ShoppingCart,
    title: "Buy More Credits",
    description: "Need more? Buy credit packs in bulk and save up to 30%.",
  },
];

export default function PricingPage() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-16">
      {/* Hero */}
      <div className="text-center">
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          Simple, Credit-Based Pricing
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground">
          Start free. Pay only for what you use.
        </p>
      </div>

      {/* How It Works */}
      <div className="mx-auto mt-14 grid max-w-4xl gap-6 sm:grid-cols-3">
        {steps.map((step, i) => (
          <div
            key={step.title}
            className="relative rounded-2xl border bg-card p-6 text-center"
          >
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
              <step.icon className="h-6 w-6 text-primary" />
            </div>
            <div className="mt-1 text-xs font-medium text-muted-foreground">
              Step {i + 1}
            </div>
            <h3 className="mt-2 text-lg font-bold">{step.title}</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              {step.description}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-8 text-center">
        <PricingCTA />
      </div>

      {/* Credit Packs */}
      <div className="mt-20">
        <div className="text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
            <Coins className="h-6 w-6 text-primary" />
          </div>
          <h2 className="mt-4 text-2xl font-bold">Credit Packs</h2>
          <p className="mt-2 text-muted-foreground">
            Buy credits in bulk and save. 1 credit = $0.01.
          </p>
        </div>

        <div className="mx-auto mt-8 max-w-3xl overflow-hidden rounded-xl border">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/30">
                <th className="px-6 py-3 text-left text-sm font-medium">Pack</th>
                <th className="px-6 py-3 text-left text-sm font-medium">Credits</th>
                <th className="px-6 py-3 text-left text-sm font-medium">Price</th>
                <th className="px-6 py-3 text-left text-sm font-medium">Per Credit</th>
                <th className="px-6 py-3 text-right text-sm font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {creditPacks.map((pack) => (
                <tr key={pack.credits} className="border-b last:border-0">
                  <td className="px-6 py-4 text-sm font-medium">
                    <div className="flex items-center gap-2">
                      {pack.label}
                      {pack.savings && (
                        <span className="rounded-full bg-green-500/10 px-2 py-0.5 text-xs font-medium text-green-600">
                          {pack.savings}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm">
                    {pack.credits.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 text-sm font-medium">{pack.price}</td>
                  <td className="px-6 py-4 text-sm text-muted-foreground">
                    {pack.perCredit}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <Link
                      href="/dashboard/credits"
                      className="text-sm font-medium text-primary hover:underline"
                    >
                      Buy →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Agent Economics */}
      <div className="mt-20">
        <div className="text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
            <Sparkles className="h-6 w-6 text-primary" />
          </div>
          <h2 className="mt-4 text-2xl font-bold">For Agent Developers</h2>
          <p className="mt-2 text-muted-foreground">
            Build an agent. List it. Earn credits every time it&apos;s used.
          </p>
        </div>

        <div className="mx-auto mt-8 max-w-3xl overflow-hidden rounded-xl border">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/30">
                <th className="px-6 py-3 text-left text-sm font-medium">Agent Tier</th>
                <th className="px-6 py-3 text-left text-sm font-medium">Credits/Task</th>
                <th className="px-6 py-3 text-left text-sm font-medium">You Earn (90%)</th>
                <th className="px-6 py-3 text-left text-sm font-medium">Platform (10%)</th>
              </tr>
            </thead>
            <tbody>
              {[
                { tier: "Community (summarize, grammar, JSON)", credits: 0, earn: 0, fee: 0 },
                { tier: "Standard (translate, code review)", credits: 10, earn: 9.0, fee: 1.0 },
                { tier: "Specialized (design, testing, PM)", credits: 15, earn: 13.5, fee: 1.5 },
                { tier: "Team mode (3-5 agents)", credits: "30-75", earn: "27-67.5", fee: "3-7.5" },
              ].map((row) => (
                <tr key={row.tier} className="border-b last:border-0">
                  <td className="px-6 py-3 text-sm">{row.tier}</td>
                  <td className="px-6 py-3 text-sm font-medium">{row.credits}</td>
                  <td className="px-6 py-3 text-sm text-green-600">{row.earn}</td>
                  <td className="px-6 py-3 text-sm text-muted-foreground">{row.fee}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-6 text-center">
          <Link
            href="/register-agent"
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Register Your Agent
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>

      {/* FAQ */}
      <div className="mt-20">
        <div className="text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
            <HelpCircle className="h-6 w-6 text-primary" />
          </div>
          <h2 className="mt-4 text-2xl font-bold">Frequently Asked Questions</h2>
        </div>

        <div className="mx-auto mt-8 max-w-2xl space-y-6">
          {faqs.map((faq) => (
            <div key={faq.q}>
              <h3 className="font-semibold">{faq.q}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{faq.a}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
