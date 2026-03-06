# Streamlined Developer Journey — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the multi-step onboarding wizard with a streamlined 4-step developer journey: paste URL, detect, sign in, register.

**Architecture:** Dedicated `/register-agent` page (public, no auth until register step). Dashboard welcome state replaces `/onboarding`. Agent settings page at `/dashboard/agents/[id]` for owners. Simplified landing page with two CTAs.

**Tech Stack:** Next.js 14, React Query, shadcn/ui, Tailwind CSS, FastAPI backend

---

## Task 1: Backend — Make Detect Endpoint Public

**Files:**
- Modify: `src/api/detect.py:16-20`

**Step 1: Remove auth dependency from detect endpoint**

Replace the current function signature:

```python
@router.post("/detect", response_model=DetectResponse)
async def detect_agent(
    data: DetectRequest,
) -> DetectResponse:
    """Auto-detect an agent by fetching its .well-known/agent-card.json.

    Public endpoint — no auth required. Rate limited by IP (10/min).
    """
```

Remove the `current_user: dict = Depends(get_current_user)` parameter and the `from src.core.auth import get_current_user` import.

**Step 2: Verify the endpoint works without auth**

Run: `curl -X POST http://localhost:8080/api/v1/agents/detect -H 'Content-Type: application/json' -d '{"url":"https://arimatch1-crewhub-agent-summarizer.hf.space"}'`

Expected: 200 with detected agent data (no 401)

**Step 3: Commit**

```bash
git add src/api/detect.py
git commit -m "feat: make agent detect endpoint public (no auth required)"
```

---

## Task 2: Frontend — Add `/register-agent` Route and Constants

**Files:**
- Modify: `frontend/src/lib/constants.ts:5` (add route)
- Create: `frontend/src/app/(marketplace)/register-agent/page.tsx`

**Step 1: Add `registerAgent` route to constants**

In `frontend/src/lib/constants.ts`, add to the ROUTES object after `register`:

```typescript
registerAgent: "/register-agent",
```

**Step 2: Create the register-agent page**

```tsx
// frontend/src/app/(marketplace)/register-agent/page.tsx
"use client";

import { RegisterAgentFlow } from "@/components/agents/register-agent-flow";

export default function RegisterAgentPage() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <RegisterAgentFlow />
    </div>
  );
}
```

**Step 3: Commit**

```bash
git add frontend/src/lib/constants.ts frontend/src/app/\(marketplace\)/register-agent/page.tsx
git commit -m "feat: add /register-agent route and page shell"
```

---

## Task 3: Frontend — Build RegisterAgentFlow Component

**Files:**
- Create: `frontend/src/components/agents/register-agent-flow.tsx`

This is the core component. It reuses the detection + review logic from `dev-onboarding.tsx` but is standalone (no onboarding wrapper, no fork screen). Key differences from the old dev-onboarding:

1. No `onBack` prop — this is a standalone page
2. Conditional sign-in step (inline Google button if not authenticated)
3. On success → redirect to `/agents/{id}` (not dashboard)
4. No `POST /auth/onboarding` call — that's handled by dashboard welcome state

**Step 1: Create the component**

```tsx
// frontend/src/components/agents/register-agent-flow.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Globe,
  LogIn,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useDetectAgent, useCreateAgent } from "@/lib/hooks/use-agents";
import { useAuth } from "@/lib/auth-context";
import { ROUTES, CATEGORIES } from "@/lib/constants";
import type { DetectResponse, AgentCreate } from "@/types/agent";

type Step = "paste" | "review" | "success";

export function RegisterAgentFlow() {
  const router = useRouter();
  const { user, loginWithGoogle, loading: authLoading } = useAuth();
  const detectMutation = useDetectAgent();
  const createMutation = useCreateAgent();

  const [step, setStep] = useState<Step>("paste");
  const [url, setUrl] = useState("");
  const [detected, setDetected] = useState<DetectResponse | null>(null);
  const [registeredId, setRegisteredId] = useState<string | null>(null);
  const [signingIn, setSigningIn] = useState(false);

  // Editable fields
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [version, setVersion] = useState("");
  const [category, setCategory] = useState("general");
  const [licenseType, setLicenseType] = useState("open");
  const [credits, setCredits] = useState("1");
  const [billingModel, setBillingModel] = useState("per_task");

  async function handleDetect() {
    if (!url.trim()) return;
    try {
      const result = await detectMutation.mutateAsync(url.trim());
      setDetected(result);
      setName(result.name);
      setDescription(result.description);
      setVersion(result.version || "1.0.0");
      if (result.suggested_registration.category) {
        setCategory(result.suggested_registration.category);
      }
      setStep("review");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Detection failed";
      toast.error(message);
    }
  }

  async function handleSignIn() {
    setSigningIn(true);
    try {
      await loginWithGoogle();
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Sign in failed"
      );
    } finally {
      setSigningIn(false);
    }
  }

  async function handleRegister() {
    if (!detected) return;

    const data: AgentCreate = {
      ...detected.suggested_registration,
      name,
      description: description || `Agent: ${name}`,
      version,
      category,
      pricing: {
        license_type: licenseType as AgentCreate["pricing"]["license_type"],
        tiers: [],
        model: billingModel,
        credits: Number(credits),
        trial_days: null,
        trial_task_limit: null,
      },
    };

    try {
      const agent = await createMutation.mutateAsync(data);
      setRegisteredId(agent.id);
      setStep("success");
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Registration failed"
      );
    }
  }

  const stepLabels = ["Paste URL", "Review & Register", "Live"];
  const stepIndex = step === "paste" ? 0 : step === "review" ? 1 : 2;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Register Your Agent</h1>
        <p className="mt-1 text-muted-foreground">
          Paste your agent&apos;s endpoint URL and we&apos;ll auto-detect its
          capabilities
        </p>
      </div>

      {/* Step indicator */}
      <div className="flex gap-2">
        {stepLabels.map((label, i) => (
          <span
            key={label}
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              i === stepIndex
                ? "bg-primary text-primary-foreground"
                : i < stepIndex
                  ? "bg-primary/20 text-primary"
                  : "bg-muted text-muted-foreground"
            }`}
          >
            {label}
          </span>
        ))}
      </div>

      <Card>
        <CardContent className="p-6">
          {/* Step 1: Paste URL */}
          {step === "paste" && (
            <div className="space-y-4">
              <div className="space-y-1">
                <h2 className="text-lg font-semibold">Agent Endpoint</h2>
                <p className="text-sm text-muted-foreground">
                  We&apos;ll read your{" "}
                  <code className="rounded bg-muted px-1 text-xs">
                    /.well-known/agent-card.json
                  </code>
                </p>
              </div>

              <div className="space-y-2">
                <Label>Endpoint URL</Label>
                <div className="flex gap-2">
                  <Input
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://my-agent.example.com"
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleDetect();
                    }}
                    data-testid="detect-url-input"
                    className="flex-1"
                  />
                  <Button
                    onClick={handleDetect}
                    disabled={!url.trim() || detectMutation.isPending}
                    data-testid="detect-button"
                  >
                    {detectMutation.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Globe className="mr-2 h-4 w-4" />
                    )}
                    Detect Agent
                  </Button>
                </div>
              </div>

              {detectMutation.error && (
                <div className="flex items-start gap-2 rounded border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>
                    {detectMutation.error instanceof Error
                      ? detectMutation.error.message
                      : "Detection failed"}
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Step 2: Review & Register */}
          {step === "review" && detected && (
            <div className="space-y-4">
              <div className="space-y-1">
                <h2 className="text-lg font-semibold">Review & Register</h2>
                <p className="text-sm text-muted-foreground">
                  Detected from your agent card. Edit as needed.
                </p>
              </div>

              {detected.warnings.length > 0 && (
                <div className="flex items-start gap-2 rounded border border-yellow-500/50 bg-yellow-500/10 p-3 text-sm text-yellow-600 dark:text-yellow-400">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <div>
                    {detected.warnings.map((w, i) => (
                      <p key={i}>{w}</p>
                    ))}
                  </div>
                </div>
              )}

              <div className="space-y-2">
                <Label>Name</Label>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  data-testid="review-name"
                />
              </div>

              <div className="space-y-2">
                <Label>Description</Label>
                <Textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Version</Label>
                  <Input
                    value={version}
                    onChange={(e) => setVersion(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Category</Label>
                  <Select value={category} onValueChange={setCategory}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CATEGORIES.map((c) => (
                        <SelectItem key={c.slug} value={c.slug}>
                          {c.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {detected.skills.length > 0 && (
                <div className="space-y-2">
                  <Label>Detected Skills ({detected.skills.length})</Label>
                  <div className="flex flex-wrap gap-2">
                    {detected.skills.map((s) => (
                      <Badge key={s.skill_key} variant="secondary">
                        {s.name}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              <div className="space-y-3 rounded border bg-muted/30 p-4">
                <h3 className="text-sm font-semibold">Pricing</h3>
                <div className="grid grid-cols-3 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs">License</Label>
                    <Select value={licenseType} onValueChange={setLicenseType}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="open">Open</SelectItem>
                        <SelectItem value="freemium">Freemium</SelectItem>
                        <SelectItem value="commercial">Commercial</SelectItem>
                        <SelectItem value="subscription">
                          Subscription
                        </SelectItem>
                        <SelectItem value="trial">Trial</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Credits/Task</Label>
                    <Input
                      type="number"
                      min="0"
                      value={credits}
                      onChange={(e) => setCredits(e.target.value)}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Billing</Label>
                    <Select
                      value={billingModel}
                      onValueChange={setBillingModel}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="per_task">Per Task</SelectItem>
                        <SelectItem value="per_token">Per Token</SelectItem>
                        <SelectItem value="per_minute">Per Minute</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              {/* Sign-in gate: show inline Google sign-in if not authenticated */}
              {!user && !authLoading && (
                <div className="rounded border border-primary/30 bg-primary/5 p-4">
                  <p className="mb-3 text-sm font-medium">
                    Sign in to register your agent
                  </p>
                  <Button onClick={handleSignIn} disabled={signingIn}>
                    {signingIn ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <LogIn className="mr-2 h-4 w-4" />
                    )}
                    Sign in with Google
                  </Button>
                </div>
              )}

              <div className="flex justify-between">
                <Button variant="outline" onClick={() => setStep("paste")}>
                  Back
                </Button>
                <Button
                  onClick={handleRegister}
                  disabled={
                    !name.trim() ||
                    !user ||
                    createMutation.isPending
                  }
                  data-testid="register-button"
                >
                  {createMutation.isPending && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  Register Agent
                </Button>
              </div>
            </div>
          )}

          {/* Step 3: Success */}
          {step === "success" && (
            <div className="flex flex-col items-center gap-4 py-8 text-center">
              <div className="rounded-full bg-green-500/10 p-4">
                <CheckCircle2 className="h-10 w-10 text-green-500" />
              </div>
              <h2 className="text-xl font-semibold">Agent Registered!</h2>
              <p className="text-sm text-muted-foreground">
                Your agent <strong>{name}</strong> is now live on the
                marketplace.
              </p>
              <Button
                onClick={() =>
                  router.push(
                    registeredId
                      ? ROUTES.agentDetail(registeredId)
                      : ROUTES.agents
                  )
                }
                data-testid="view-agent-button"
              >
                View Agent
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

**Step 2: Verify it compiles**

Run: `cd frontend && npx next build 2>&1 | head -30` or just check the dev server at `http://localhost:3000/register-agent`

**Step 3: Commit**

```bash
git add frontend/src/components/agents/register-agent-flow.tsx
git commit -m "feat: add RegisterAgentFlow component for /register-agent page"
```

---

## Task 4: Frontend — Update Landing Page

**Files:**
- Modify: `frontend/src/app/(marketplace)/page.tsx`

**Step 1: Replace the hero section**

Replace the entire content with two CTAs ("Browse Agents" and "Register Your Agent") instead of the single "Get Started" button. Keep the features section and footer.

```tsx
// frontend/src/app/(marketplace)/page.tsx
import Link from "next/link";
import { Zap, Shield, Coins } from "lucide-react";
import { Button } from "@/components/ui/button";
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
          <div className="mt-10 flex items-center justify-center gap-4">
            <Button size="lg" className="shadow-lg shadow-primary/20" asChild>
              <Link href="/agents">Browse Agents</Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link href="/register-agent">Register Your Agent</Link>
            </Button>
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
        <p>CrewHub -- Agent-to-Agent Discovery and Delegation Marketplace</p>
      </footer>
    </>
  );
}
```

**Step 2: Verify at `http://localhost:3000/`**

Expected: Two CTA buttons side by side, no "Get Started" button, heading says "The AI Agent Marketplace"

**Step 3: Commit**

```bash
git add frontend/src/app/\(marketplace\)/page.tsx
git commit -m "feat: update landing page with two CTAs (Browse + Register)"
```

---

## Task 5: Frontend — Dashboard Welcome State

**Files:**
- Modify: `frontend/src/app/(marketplace)/dashboard/page.tsx`

Replace the `router.replace("/onboarding")` redirect with an inline welcome state when `onboarding_completed === false`.

**Step 1: Update the dashboard page**

```tsx
// frontend/src/app/(marketplace)/dashboard/page.tsx
"use client";

import Link from "next/link";
import { Bot, CreditCard, ListTodo, Search, TrendingUp, Rocket } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { useBalance } from "@/lib/hooks/use-credits";
import { useTasks } from "@/lib/hooks/use-tasks";
import { useAgents } from "@/lib/hooks/use-agents";
import { StatCard } from "@/components/shared/stat-card";
import { ROUTES } from "@/lib/constants";
import { formatCredits } from "@/lib/utils";
import { ActivityFeed } from "@/components/shared/activity-feed";
import { AgentStatusBoard } from "@/components/agents/agent-status-board";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api-client";

export default function DashboardPage() {
  const { user, refreshUser } = useAuth();
  const { data: balance } = useBalance();
  const { data: tasks } = useTasks();
  const { data: agents } = useAgents(
    user ? { owner_id: user.id } : undefined
  );
  const { data: allAgents } = useAgents({ per_page: 20 });

  // Welcome state for new users
  if (user && !user.onboarding_completed) {
    return <WelcomeState onComplete={() => refreshUser?.()} />;
  }

  const activeTasks =
    tasks?.tasks.filter((t) =>
      ["submitted", "working", "input_required"].includes(t.status)
    ).length ?? 0;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">
          Welcome back, {user?.name ?? "User"}
        </h1>
        <p className="mt-1 text-muted-foreground">
          Here&apos;s an overview of your CrewHub activity
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Available Credits"
          value={balance ? formatCredits(balance.available) : "--"}
          icon={CreditCard}
        />
        <StatCard
          title="Active Tasks"
          value={activeTasks}
          icon={ListTodo}
        />
        <StatCard
          title="Total Tasks"
          value={tasks?.total ?? 0}
          icon={TrendingUp}
        />
        <StatCard
          title="My Agents"
          value={agents?.total ?? 0}
          icon={Bot}
        />
      </div>

      <div className="flex gap-3">
        <Button asChild>
          <Link href={ROUTES.agents}>Browse Agents</Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href={ROUTES.registerAgent}>Register Agent</Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href={ROUTES.newTask}>Create Task</Link>
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <ActivityFeed />
        <AgentStatusBoard agents={allAgents?.agents ?? []} />
      </div>
    </div>
  );
}

function WelcomeState({ onComplete }: { onComplete: () => void }) {
  async function handleChoice() {
    try {
      await api.post("/auth/onboarding", { interests: [] });
      await onComplete();
    } catch {
      // Silently fail — user can still navigate
    }
  }

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <h1 className="text-3xl font-bold">Welcome to CrewHub</h1>
      <p className="mt-3 max-w-md text-muted-foreground">
        The AI Agent Marketplace. What would you like to do first?
      </p>

      <div className="mt-10 grid gap-6 sm:grid-cols-2">
        <Link
          href="/agents"
          onClick={handleChoice}
          className="group rounded-lg border bg-card p-8 text-left transition-all hover:border-primary/40 hover:shadow-md"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
            <Search className="h-6 w-6 text-primary" />
          </div>
          <h2 className="mt-4 text-lg font-semibold group-hover:text-primary">
            Browse Agents
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Discover AI agents to help with your tasks
          </p>
        </Link>

        <Link
          href="/register-agent"
          onClick={handleChoice}
          className="group rounded-lg border bg-card p-8 text-left transition-all hover:border-primary/40 hover:shadow-md"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
            <Rocket className="h-6 w-6 text-primary" />
          </div>
          <h2 className="mt-4 text-lg font-semibold group-hover:text-primary">
            Register Your Agent
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Add your agent to the marketplace in seconds
          </p>
        </Link>
      </div>
    </div>
  );
}
```

**Step 2: Verify at `http://localhost:3000/dashboard`**

Expected: If `onboarding_completed === false`, shows two large cards. If `true`, shows normal dashboard.

**Step 3: Commit**

```bash
git add frontend/src/app/\(marketplace\)/dashboard/page.tsx
git commit -m "feat: replace onboarding redirect with dashboard welcome state"
```

---

## Task 6: Frontend — Agent Settings Page

**Files:**
- Create: `frontend/src/app/(marketplace)/dashboard/agents/[id]/page.tsx`
- Create: `frontend/src/components/agents/agent-settings.tsx`
- Modify: `frontend/src/lib/constants.ts` (add `agentSettings` route)

**Step 1: Add route to constants**

In `frontend/src/lib/constants.ts`, add to the ROUTES object after `newAgent`:

```typescript
agentSettings: (id: string) => `/dashboard/agents/${id}`,
```

**Step 2: Create the agent settings component**

```tsx
// frontend/src/components/agents/agent-settings.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import {
  AlertTriangle,
  Loader2,
  RefreshCw,
  Trash2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  useAgent,
  useUpdateAgent,
  useDeleteAgent,
  useDetectAgent,
} from "@/lib/hooks/use-agents";
import { useAuth } from "@/lib/auth-context";
import { ROUTES, CATEGORIES } from "@/lib/constants";
import type { AgentUpdate } from "@/types/agent";

export function AgentSettings({ agentId }: { agentId: string }) {
  const router = useRouter();
  const { user } = useAuth();
  const { data: agent, isLoading } = useAgent(agentId);
  const updateMutation = useUpdateAgent(agentId);
  const deleteMutation = useDeleteAgent();
  const detectMutation = useDetectAgent();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [version, setVersion] = useState("");
  const [category, setCategory] = useState("general");
  const [endpoint, setEndpoint] = useState("");
  const [initialized, setInitialized] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState("");

  // Initialize form from agent data
  if (agent && !initialized) {
    setName(agent.name);
    setDescription(agent.description);
    setVersion(agent.version);
    setCategory(agent.category);
    setEndpoint(agent.endpoint);
    setInitialized(true);
  }

  if (isLoading) {
    return (
      <div className="flex min-h-[200px] items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!agent) {
    return <p className="text-muted-foreground">Agent not found.</p>;
  }

  // Owner check
  if (user && agent.owner_id !== user.id) {
    return <p className="text-muted-foreground">You don&apos;t own this agent.</p>;
  }

  async function handleSave() {
    const data: AgentUpdate = {
      name,
      description,
      version,
      category,
      endpoint,
    };
    try {
      await updateMutation.mutateAsync(data);
      toast.success("Agent updated");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Update failed");
    }
  }

  async function handleRedetect() {
    if (!endpoint) return;
    try {
      const result = await detectMutation.mutateAsync(endpoint);
      setName(result.name);
      setDescription(result.description);
      setVersion(result.version || version);
      toast.success(
        `Re-detected: ${result.skills.length} skills, ${result.warnings.length} warnings`
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Re-detect failed");
    }
  }

  async function handleDeactivate() {
    try {
      await deleteMutation.mutateAsync(agentId);
      toast.success("Agent deactivated");
      router.push(ROUTES.myAgents);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Deactivate failed");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Agent Settings</h1>
        <p className="mt-1 text-muted-foreground">
          Manage <strong>{agent.name}</strong>
        </p>
      </div>

      {/* Details */}
      <Card>
        <CardHeader>
          <CardTitle>Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Description</Label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
            />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label>Version</Label>
              <Input
                value={version}
                onChange={(e) => setVersion(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Category</Label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CATEGORIES.map((c) => (
                    <SelectItem key={c.slug} value={c.slug}>
                      {c.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Endpoint URL</Label>
              <Input
                value={endpoint}
                onChange={(e) => setEndpoint(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label>Skills</Label>
            <div className="flex flex-wrap gap-2">
              {agent.skills.map((s) => (
                <Badge key={s.id} variant="secondary">
                  {s.name}
                </Badge>
              ))}
            </div>
          </div>

          <Button
            onClick={handleSave}
            disabled={updateMutation.isPending}
          >
            {updateMutation.isPending && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            Save Changes
          </Button>
        </CardContent>
      </Card>

      {/* Re-detect */}
      <Card>
        <CardHeader>
          <CardTitle>Re-detect from Agent Card</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-4 text-sm text-muted-foreground">
            Re-fetch your agent&apos;s capabilities from the agent card. This
            will update the name, description, and skills.
          </p>
          <Button
            variant="outline"
            onClick={handleRedetect}
            disabled={detectMutation.isPending}
          >
            {detectMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-4 w-4" />
            )}
            Re-detect
          </Button>
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card className="border-destructive/30">
        <CardHeader>
          <CardTitle className="text-destructive">Danger Zone</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between rounded border border-destructive/20 p-4">
            <div>
              <p className="font-medium">Deactivate Agent</p>
              <p className="text-sm text-muted-foreground">
                Hides from marketplace. Existing tasks will complete.
              </p>
            </div>
            <Dialog>
              <DialogTrigger asChild>
                <Button variant="destructive" size="sm">
                  Deactivate
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Deactivate {agent.name}?</DialogTitle>
                  <DialogDescription>
                    This will hide the agent from the marketplace. Existing
                    tasks will still complete. You can reactivate later.
                  </DialogDescription>
                </DialogHeader>
                <DialogFooter>
                  <Button variant="destructive" onClick={handleDeactivate}>
                    Deactivate
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          <div className="flex items-center justify-between rounded border border-destructive/20 p-4">
            <div>
              <p className="font-medium">Delete Agent</p>
              <p className="text-sm text-muted-foreground">
                Permanent. Type the agent name to confirm.
              </p>
            </div>
            <Dialog>
              <DialogTrigger asChild>
                <Button variant="destructive" size="sm">
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Delete {agent.name}?</DialogTitle>
                  <DialogDescription>
                    This action is permanent. Type{" "}
                    <strong>{agent.name}</strong> to confirm.
                  </DialogDescription>
                </DialogHeader>
                <Input
                  value={deleteConfirm}
                  onChange={(e) => setDeleteConfirm(e.target.value)}
                  placeholder={agent.name}
                />
                <DialogFooter>
                  <Button
                    variant="destructive"
                    disabled={deleteConfirm !== agent.name}
                    onClick={handleDeactivate}
                  >
                    Delete Permanently
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

**Step 3: Create the page**

```tsx
// frontend/src/app/(marketplace)/dashboard/agents/[id]/page.tsx
"use client";

import { useParams } from "next/navigation";
import { AgentSettings } from "@/components/agents/agent-settings";

export default function AgentSettingsPage() {
  const params = useParams<{ id: string }>();
  return <AgentSettings agentId={params.id} />;
}
```

**Step 4: Commit**

```bash
git add frontend/src/lib/constants.ts \
  frontend/src/components/agents/agent-settings.tsx \
  frontend/src/app/\(marketplace\)/dashboard/agents/\[id\]/page.tsx
git commit -m "feat: add agent settings page for owners"
```

---

## Task 7: Frontend — Add Owner Links (Agent Detail + My Agents Table)

**Files:**
- Modify: `frontend/src/app/(marketplace)/agents/[id]/agent-detail-client.tsx:50-58`
- Modify: `frontend/src/app/(marketplace)/dashboard/agents/page.tsx:60-107`

**Step 1: Add "Manage Agent" button to agent detail page**

In `agent-detail-client.tsx`, add after the "Back to Marketplace" button (around line 57), before `<AgentDetailHeader>`:

```tsx
{user && agent.owner_id === user.id && (
  <Button variant="outline" size="sm" className="mb-4 ml-2" asChild>
    <Link href={ROUTES.agentSettings(agent.id)}>
      <Settings className="mr-2 h-4 w-4" />
      Manage Agent
    </Link>
  </Button>
)}
```

Add these imports at the top:
- `import { Settings } from "lucide-react";`
- `import { useAuth } from "@/lib/auth-context";`
- `import { ROUTES } from "@/lib/constants";`

Inside the component, add: `const { user } = useAuth();` after the existing hooks.

**Step 2: Add "Settings" link to My Agents table**

In `dashboard/agents/page.tsx`, add a new column "Actions" to the table header and a settings link to each row:

Add to `<TableHeader>` after the "Created" column:
```tsx
<TableHead className="w-[80px]">Actions</TableHead>
```

Add to each `<TableRow>` after the created_at cell:
```tsx
<TableCell>
  <Button variant="ghost" size="sm" asChild>
    <Link href={ROUTES.agentSettings(agent.id)}>
      <Settings className="h-4 w-4" />
    </Link>
  </Button>
</TableCell>
```

Add `Settings` to the lucide import, and add `import { ROUTES } from "@/lib/constants";`.

Also update the "Register Agent" button link from `ROUTES.newAgent` to `ROUTES.registerAgent`:
```tsx
<Link href={ROUTES.registerAgent}>
```

**Step 3: Commit**

```bash
git add frontend/src/app/\(marketplace\)/agents/\[id\]/agent-detail-client.tsx \
  frontend/src/app/\(marketplace\)/dashboard/agents/page.tsx
git commit -m "feat: add owner links to agent detail and My Agents pages"
```

---

## Task 8: Frontend — Delete Onboarding Files

**Files:**
- Delete: `frontend/src/app/(marketplace)/onboarding/page.tsx`
- Delete: `frontend/src/components/onboarding/onboarding-wizard.tsx`
- Delete: `frontend/src/components/onboarding/fork-screen.tsx`
- Delete: `frontend/src/components/onboarding/dev-onboarding.tsx`
- Delete: `frontend/src/components/onboarding/step-welcome.tsx`
- Delete: `frontend/src/components/onboarding/step-api-keys.tsx`
- Delete: `frontend/src/components/onboarding/step-interests.tsx`
- Delete: `frontend/src/components/onboarding/step-recommended.tsx`
- Delete: `frontend/src/components/onboarding/step-try-agent.tsx`
- Delete: `frontend/src/components/onboarding/step-success.tsx`
- Delete: `frontend/e2e/dev-onboarding.spec.ts`

**Step 1: Remove all onboarding files**

```bash
rm -rf frontend/src/app/\(marketplace\)/onboarding
rm -rf frontend/src/components/onboarding
rm frontend/e2e/dev-onboarding.spec.ts
```

**Step 2: Search for remaining `/onboarding` references and clean up**

```bash
grep -r "onboarding" frontend/src --include="*.ts" --include="*.tsx" -l
```

Expected references to keep:
- `dashboard/page.tsx` — uses `user.onboarding_completed` (correct, this is the welcome state)
- `api-client.ts` — comment mentions `/onboarding` in public paths list — update comment

Remove/update any stale references.

**Step 3: Verify build**

Run: `cd frontend && npx next build 2>&1 | tail -20`
Expected: Build succeeds with no import errors

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: delete onboarding wizard and all step components"
```

---

## Task 9: Frontend — Update Middleware for /register-agent

**Files:**
- Modify: `frontend/src/middleware.ts:4`

**Step 1: Add `/register-agent` to PUBLIC_PATHS**

The middleware already allows paths that start with `/register`. Since `/register-agent` starts with `/register`, it should be public already. But verify by checking the matching logic at line 12:

```typescript
PUBLIC_PATHS.some(
  (p) => pathname === p || (p !== "/" && pathname.startsWith(p))
)
```

`/register-agent` starts with `/register`, so it will match. No change needed to middleware.

However, add `/agents` explicitly to be safe (it's currently public by not matching dashboard/admin, but an explicit entry is clearer):

```typescript
const PUBLIC_PATHS = ["/", "/login", "/register", "/agents", "/register-agent"];
```

**Step 2: Commit**

```bash
git add frontend/src/middleware.ts
git commit -m "chore: add /register-agent and /agents to explicit public paths"
```

---

## Task 10: Integration Test — End to End

**Step 1: Manual test the full flow**

1. Open `http://localhost:3000/` — verify two CTAs visible
2. Click "Register Your Agent" — goes to `/register-agent`
3. Paste `https://arimatch1-crewhub-agent-summarizer.hf.space` → click "Detect Agent"
4. Verify: name, description, skills auto-filled
5. If not signed in: verify inline Google Sign-In button appears
6. Click "Register Agent" (sign in first if needed)
7. Verify: success screen with "View Agent" button
8. Click "View Agent" → goes to `/agents/{id}`
9. Verify: "Manage Agent" button visible (you're the owner)
10. Click "Manage Agent" → goes to `/dashboard/agents/{id}`
11. Verify: details form, re-detect button, danger zone all visible
12. Go to dashboard → verify welcome state (if new user) or normal dashboard
13. Go to "My Agents" → verify settings icon in actions column

**Step 2: Commit all remaining changes**

```bash
git add -A
git commit -m "feat: complete streamlined developer journey implementation"
```

---

## Verification Checklist

1. `/register-agent` page works without auth (detect is public)
2. Inline Google Sign-In appears on review step when not authenticated
3. Registration redirects to agent detail page (not dashboard)
4. Dashboard shows welcome state for new users (no redirect to /onboarding)
5. Agent settings page editable by owner only
6. Re-detect works from settings page
7. Deactivate/delete work with confirmation
8. Landing page shows two CTAs
9. All `/onboarding` files deleted
10. No broken imports or build errors
