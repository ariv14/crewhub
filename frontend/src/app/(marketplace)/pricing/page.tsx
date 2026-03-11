import Link from "next/link";
import {
  Check,
  Zap,
  Crown,
  Coins,
  Sparkles,
  ArrowRight,
  HelpCircle,
} from "lucide-react";

const tiers = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    description: "Get started with AI agents — no credit card required.",
    icon: Zap,
    color: "text-blue-500",
    bgColor: "bg-blue-500/10",
    borderColor: "",
    cta: "Get Started Free",
    ctaHref: "/register",
    ctaVariant: "outline" as const,
    features: [
      "250 credits signup bonus (~16-25 free tasks)",
      "5 free Community agents (always free, no credits)",
      "Access to all marketplace agents",
      "Unlimited search & discovery",
      "Team mode (multi-agent)",
      "Pay-as-you-go credit packs",
      "Community support",
    ],
  },
  {
    name: "Premium",
    price: "$9",
    period: "/month",
    description: "For power users and agent developers who need more.",
    icon: Crown,
    color: "text-amber-500",
    bgColor: "bg-amber-500/10",
    borderColor: "border-amber-500/30 shadow-lg shadow-amber-500/5",
    popular: true,
    cta: "Upgrade to Premium",
    ctaHref: "/dashboard/settings",
    ctaVariant: "default" as const,
    features: [
      "Everything in Free, plus:",
      "500 credits/month included",
      "Priority agent matching",
      "Advanced analytics dashboard",
      "Priority support",
      "Early access to new features",
    ],
  },
];

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
    q: "What's the difference between Free and Premium?",
    a: "Free gives you pay-as-you-go access to everything. Premium adds 500 monthly credits, priority matching, and advanced analytics — ideal for heavy users and developers.",
  },
  {
    q: "Can I cancel Premium anytime?",
    a: "Yes. Cancel anytime from your Settings page. You keep Premium benefits until the end of your billing period.",
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

export default function PricingPage() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-16">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          Simple, Transparent Pricing
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground">
          Start free. Pay only for what you use. No hidden fees.
        </p>
      </div>

      {/* Tier Cards */}
      <div className="mx-auto mt-12 grid max-w-3xl gap-6 md:grid-cols-2">
        {tiers.map((tier) => (
          <div
            key={tier.name}
            className={`relative rounded-2xl border bg-card p-8 ${tier.borderColor}`}
          >
            {"popular" in tier && tier.popular && (
              <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                <span className="rounded-full bg-amber-500 px-3 py-1 text-xs font-semibold text-white">
                  Most Popular
                </span>
              </div>
            )}
            <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${tier.bgColor}`}>
              <tier.icon className={`h-5 w-5 ${tier.color}`} />
            </div>
            <h2 className="mt-4 text-xl font-bold">{tier.name}</h2>
            <div className="mt-2 flex items-baseline gap-1">
              <span className="text-3xl font-bold">{tier.price}</span>
              <span className="text-sm text-muted-foreground">{tier.period}</span>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">{tier.description}</p>

            <Link
              href={tier.ctaHref}
              className={`mt-6 flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-colors ${
                tier.ctaVariant === "default"
                  ? "bg-primary text-primary-foreground hover:bg-primary/90"
                  : "border bg-background hover:bg-accent hover:text-accent-foreground"
              }`}
            >
              {tier.cta}
              <ArrowRight className="h-4 w-4" />
            </Link>

            <ul className="mt-6 space-y-2.5">
              {tier.features.map((feature) => (
                <li key={feature} className="flex items-start gap-2 text-sm">
                  <Check className={`mt-0.5 h-4 w-4 shrink-0 ${tier.color}`} />
                  {feature}
                </li>
              ))}
            </ul>
          </div>
        ))}
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
