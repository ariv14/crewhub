# Agent Orchestration Patterns Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Supervisor Agent Pattern, Hierarchical Agent Teams, Interactive Guide Page, and Landing Page orchestration showcase to CrewHub.

**Architecture:** Extends the existing Workflow model with `pattern_type` field. Hierarchical execution nests sub-workflows inside workflow steps. Supervisor uses LiteLLM (Groq) to generate workflow plans from natural language goals, with human-in-the-loop approval before execution. All patterns produce saved, schedulable Workflows.

**Tech Stack:** FastAPI, SQLAlchemy (async), Alembic, LiteLLM, Pydantic v2, Next.js 16 (static export), React 19, shadcn/ui, Tailwind CSS 4, pytest, Playwright

**Spec:** `docs/superpowers/specs/2026-03-18-agent-orchestration-patterns-design.md`

---

## File Structure

### New Backend Files
| File | Responsibility |
|------|---------------|
| `alembic/versions/028_orchestration_patterns.py` | Migration: new columns + alter nullable |
| `src/models/supervisor_plan.py` | Ephemeral plan storage model (1h TTL) |
| `src/schemas/supervisor.py` | Supervisor plan request/response schemas |
| `src/services/supervisor_planner.py` | LLM planning service (generate, replan, approve) |
| `src/api/supervisor.py` | 3 supervisor API endpoints |
| `tests/test_pattern_types.py` | Pattern type + cycle detection tests |
| `tests/test_hierarchical_execution.py` | Hierarchical execution tests |
| `tests/test_supervisor_planner.py` | Supervisor planner tests |
| `tests/test_supervisor_security.py` | Auth, rate limit, injection tests |
| `tests/test_supervisor_e2e.py` | Supervisor E2E tests (staging) |
| `tests/test_hierarchical_e2e.py` | Hierarchical E2E tests (staging) |

### Modified Backend Files
| File | Changes |
|------|---------|
| `src/models/workflow.py` | Add pattern_type, supervisor_config, sub_workflow_id, parent_run_id, depth, child_run_id; alter agent_id/skill_id to nullable |
| `src/schemas/workflow.py` | Add pattern_type, sub_workflow_id, XOR validator |
| `src/services/workflow_service.py` | Add cycle detection on create/update |
| `src/services/workflow_execution.py` | Hierarchical dispatch, depth enforcement, pump ordering, cancel cascade |
| `src/api/workflows.py` | Register supervisor router, add pattern_type filter |
| `src/main.py` | Register supervisor API router |

### New Frontend Files
| File | Responsibility |
|------|---------------|
| `frontend/src/app/(marketplace)/guide/page.tsx` | Interactive guide page (12 sections) |
| `frontend/src/app/(marketplace)/dashboard/workflows/new/supervisor-plan.tsx` | Supervisor plan review UI |
| `frontend/src/lib/api/supervisor.ts` | Supervisor API client |
| `frontend/src/lib/hooks/use-supervisor.ts` | Supervisor React Query hooks |

### Modified Frontend Files
| File | Changes |
|------|---------|
| `frontend/src/app/(marketplace)/page.tsx` | Orchestration showcase cards in "Assemble Your AI Team" |
| `frontend/src/app/(marketplace)/dashboard/workflows/new/page.tsx` | Pattern picker (3 cards) |
| `frontend/src/app/(marketplace)/dashboard/workflows/[id]/workflow-detail-client.tsx` | Sub-workflow step support |
| `frontend/src/types/workflow.ts` | Extended types for patterns |
| `frontend/src/lib/constants.ts` | Add ROUTES.guide |
| `frontend/src/components/layout/top-nav.tsx` | Add Guide link to nav + mobile menu |
| `e2e/orchestration-patterns.spec.ts` | Playwright E2E tests for all patterns |

---

## Review Fixes Applied

The following issues were found during plan review and have been addressed inline:

1. **BLOCKER: `Uuid` import** — `supervisor_plan.py` imports `Uuid` from `sqlalchemy`, not from `src.models.base` (which doesn't exist). Follow `workflow.py` import pattern.
2. **BLOCKER: `UserLLMKey` model** — BYOK check uses `src/api/llm_keys.py` existing endpoint pattern to query user's LLM keys table, not a nonexistent `UserLLMKey` model import.
3. **BLOCKER: Self-referential relationship** — Task 6 Step 4 includes `remote_side` on `parent_run` relationship.
4. **BLOCKER: Dead code guard** — Deleted sub-workflow check is placed at top of dispatch loop, before the `if step.sub_workflow_id:` branch.
5. **BLOCKER: Async lazy load** — `_pump_single_run` uses `select().options(selectinload(...))` to load child run, not `db.get()`.
6. **ISSUE: `Suspense` boundary** — Task 13 wraps `useSearchParams()` component in `<Suspense>`.
7. **ISSUE: Supervisor router prefix** — Router uses `prefix="/workflows/supervisor"` and is mounted on the workflows router as a sub-router.
8. **ISSUE: Missing tests** — `test_timeout_inheritance` and `test_credit_tallying` added to Task 10.

---

## Phase 1: Guide Page + Landing Page (no backend changes)

### Task 1: Add Guide Route and Nav Link

**Files:**
- Modify: `frontend/src/lib/constants.ts`
- Modify: `frontend/src/components/layout/top-nav.tsx`

- [ ] **Step 1: Add guide route to constants**

In `frontend/src/lib/constants.ts`, add to the ROUTES object:

```typescript
guide: "/guide",
```

- [ ] **Step 2: Add Guide link to desktop nav**

In `frontend/src/components/layout/top-nav.tsx`, find the desktop nav section (the `<nav className="hidden items-center gap-1 md:flex">` block). Add after the Explore button:

```tsx
<Button variant="ghost" size="sm" asChild className={pathname === "/guide" ? "bg-accent" : ""}>
  <a href={ROUTES.guide}>Guide</a>
</Button>
```

- [ ] **Step 3: Add Guide link to mobile hamburger menu**

In the same file, find the public section of the mobile nav (after the `<div className="my-2 border-t" />` separator near the bottom). Add before the "Explore Platform" button:

```tsx
<Button variant="ghost" className="justify-start" asChild>
  <a href="/guide" onClick={() => setMobileOpen(false)}>
    <BookOpen className="mr-2 h-4 w-4" />
    Guide
  </a>
</Button>
```

Import `BookOpen` is already imported at the top of the file.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/constants.ts frontend/src/components/layout/top-nav.tsx
git commit -m "feat: add Guide link to nav and mobile menu"
```

---

### Task 2: Build Guide Page

**Files:**
- Create: `frontend/src/app/(marketplace)/guide/page.tsx`

- [ ] **Step 1: Create the guide page**

Create `frontend/src/app/(marketplace)/guide/page.tsx` with:

```tsx
"use client";

import { useState } from "react";
import {
  Bot, Users, GitBranch, Sparkles, Search, CreditCard,
  ChevronRight, CheckCircle2, ArrowRight, BookOpen,
  LayoutDashboard, ListTodo, Clock, Settings, Zap,
  Shield, Code, Workflow
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ROUTES } from "@/lib/constants";

const sections = [
  { id: "overview", label: "Platform Overview", icon: LayoutDashboard },
  { id: "getting-started", label: "Getting Started", icon: Zap },
  { id: "single-agent", label: "Single Agent Tasks", icon: Bot },
  { id: "team-mode", label: "Team Mode", icon: Users },
  { id: "manual-pipelines", label: "Manual Pipelines", icon: GitBranch },
  { id: "hierarchical", label: "Hierarchical Pipelines", icon: Workflow },
  { id: "supervisor", label: "Supervisor (AI-Planned)", icon: Sparkles },
  { id: "pattern-recommender", label: "Choose Your Pattern", icon: Search },
  { id: "auto-delegation", label: "Auto-Delegation", icon: ChevronRight },
  { id: "credits", label: "Credits & Pricing", icon: CreditCard },
  { id: "building-agents", label: "Building Agents", icon: Code },
  { id: "api-reference", label: "API Reference", icon: BookOpen },
];

function PatternRecommender() {
  const [step, setStep] = useState(0);
  const [result, setResult] = useState<string | null>(null);

  const questions = [
    {
      q: "Is your task a single step that one agent can handle?",
      yes: () => setResult("single"),
      no: () => setStep(1),
    },
    {
      q: "Do you know which agents you want to use?",
      yes: () => setStep(2),
      no: () => setResult("supervisor"),
    },
    {
      q: "Does any step need its own multi-agent sub-pipeline?",
      yes: () => setResult("hierarchical"),
      no: () => setResult("manual"),
    },
  ];

  const results: Record<string, { title: string; desc: string; cta: string; href: string }> = {
    single: {
      title: "Single Agent Task",
      desc: "Browse agents, pick one, and send your task. Simple and fast.",
      cta: "Browse Agents",
      href: "/agents",
    },
    manual: {
      title: "Manual Pipeline",
      desc: "Chain agents in sequence or parallel. You control the order and input flow.",
      cta: "Create Workflow",
      href: ROUTES.newWorkflow + "?pattern=manual",
    },
    hierarchical: {
      title: "Hierarchical Pipeline",
      desc: "Build workflows with nested sub-workflows. Reuse pipelines as building blocks.",
      cta: "Create Workflow",
      href: ROUTES.newWorkflow + "?pattern=hierarchical",
    },
    supervisor: {
      title: "Supervisor (AI-Planned)",
      desc: "Describe your goal in plain English. AI selects the best agents and builds the plan. You review and approve before execution.",
      cta: "Try Supervisor",
      href: ROUTES.newWorkflow + "?pattern=supervisor",
    },
  };

  if (result) {
    const r = results[result];
    return (
      <Card className="border-primary/30 bg-primary/5">
        <CardContent className="pt-6">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 className="h-5 w-5 text-primary" />
            <h4 className="font-bold text-lg">{r.title}</h4>
          </div>
          <p className="text-muted-foreground mb-4">{r.desc}</p>
          <div className="flex gap-2">
            <Button asChild>
              <a href={r.href}>{r.cta} <ArrowRight className="ml-2 h-4 w-4" /></a>
            </Button>
            <Button variant="outline" onClick={() => { setStep(0); setResult(null); }}>
              Start Over
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="pt-6">
        <p className="text-lg font-medium mb-4">{questions[step].q}</p>
        <div className="flex gap-3">
          <Button onClick={questions[step].yes}>Yes</Button>
          <Button variant="outline" onClick={questions[step].no}>No</Button>
        </div>
        {step > 0 && (
          <Button variant="ghost" size="sm" className="mt-3" onClick={() => { setStep(0); setResult(null); }}>
            Start Over
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

function SectionBlock({ id, title, icon: Icon, children }: {
  id: string; title: string; icon: React.ElementType; children: React.ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-20">
      <div className="flex items-center gap-3 mb-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
          <Icon className="h-5 w-5 text-primary" />
        </div>
        <h2 className="text-2xl font-bold">{title}</h2>
      </div>
      <div className="space-y-4 text-muted-foreground">{children}</div>
    </section>
  );
}

export default function GuidePage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold sm:text-4xl">CrewHub Platform Guide</h1>
        <p className="mt-2 text-lg text-muted-foreground">
          Everything you need to know — from your first task to production workflows.
        </p>
      </div>

      <div className="flex gap-8">
        {/* Sticky sidebar nav */}
        <nav className="hidden lg:block w-56 shrink-0">
          <div className="sticky top-20 space-y-1">
            {sections.map((s) => (
              <a
                key={s.id}
                href={`#${s.id}`}
                className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              >
                <s.icon className="h-4 w-4" />
                {s.label}
              </a>
            ))}
          </div>
        </nav>

        {/* Main content */}
        <div className="min-w-0 flex-1 space-y-12">
          <SectionBlock id="overview" title="Platform Overview" icon={LayoutDashboard}>
            <p>CrewHub is an AI agent marketplace where you can discover, delegate tasks to, and orchestrate teams of AI agents. Agents register their skills and pricing, you send them work, and the platform handles authentication, credit payments, and real-time status updates.</p>
            <p>Whether you need a single agent for a quick task or a full pipeline of specialists working together, CrewHub provides the orchestration patterns to match your needs.</p>
          </SectionBlock>

          <SectionBlock id="getting-started" title="Getting Started" icon={Zap}>
            <p>1. <strong>Create an account</strong> — Sign up with Google or GitHub. You get 250 free credits to start.</p>
            <p>2. <strong>Browse agents</strong> — Visit the <a href="/agents" className="text-primary hover:underline">marketplace</a> to see available agents and their skills.</p>
            <p>3. <strong>Try an agent</strong> — Click any agent, then use the "Try It" panel to send a task. Results appear in seconds.</p>
            <p>4. <strong>Check your dashboard</strong> — Your <a href={ROUTES.dashboard} className="text-primary hover:underline">dashboard</a> shows all your tasks, agents, and credit balance.</p>
          </SectionBlock>

          <SectionBlock id="single-agent" title="Single Agent Tasks" icon={Bot}>
            <p>The simplest pattern — send one task to one agent. Use this when you have a clear task for a specific agent.</p>
            <Card>
              <CardContent className="pt-4">
                <p className="font-mono text-sm">You → Agent (skill) → Result</p>
                <p className="mt-2 text-sm">Example: "Translate this document to Spanish" → Translator Agent → Translated text</p>
              </CardContent>
            </Card>
            <p><strong>How to use:</strong> Browse agents → select one → click "Try It" → type your message → get results.</p>
            <p><strong>Credits:</strong> Each agent lists its cost per task. Credits are reserved when you create a task and charged on completion. If the task fails, credits are refunded.</p>
          </SectionBlock>

          <SectionBlock id="team-mode" title="Team Mode" icon={Users}>
            <p>Send the same task to multiple agents simultaneously. All agents work in parallel and you get a consolidated report combining all outputs.</p>
            <Card>
              <CardContent className="pt-4">
                <p className="font-mono text-sm">You → [Agent A, Agent B, Agent C] (parallel) → Combined Report</p>
                <p className="mt-2 text-sm">Example: "Analyze our Q4 results" → Researcher + Analyst + Writer → One unified report</p>
              </CardContent>
            </Card>
            <p><strong>Best for:</strong> Getting multiple perspectives on the same problem, or when different specialists should work on the same input independently.</p>
            <p><a href={ROUTES.teamMode} className="text-primary hover:underline">Try Team Mode →</a></p>
          </SectionBlock>

          <SectionBlock id="manual-pipelines" title="Manual Pipelines" icon={GitBranch}>
            <p>Chain agents in a specific order. Each agent's output flows as input to the next. You choose the agents, order, and how data flows between steps.</p>
            <Card>
              <CardContent className="pt-4">
                <p className="font-mono text-sm">You → Agent A → Agent B → Agent C → Final Result</p>
                <p className="mt-2 text-sm">Example: "Research competitors" → Researcher → Translator → Writer → Executive summary in Spanish</p>
              </CardContent>
            </Card>
            <p><strong>Step groups:</strong> Steps in the same group run in parallel. Different groups run sequentially. This lets you mix parallel and sequential execution.</p>
            <p><strong>Input modes:</strong></p>
            <ul className="list-disc pl-6 space-y-1">
              <li><strong>Chain</strong> (default) — use previous step's output as input</li>
              <li><strong>Original</strong> — always use your original message</li>
              <li><strong>Custom</strong> — template with variables like {"{{prev_output}}"} and {"{{input}}"}</li>
            </ul>
            <p><a href={ROUTES.newWorkflow} className="text-primary hover:underline">Create a Workflow →</a></p>
          </SectionBlock>

          <SectionBlock id="hierarchical" title="Hierarchical Pipelines" icon={Workflow}>
            <Badge variant="secondary" className="mb-2">Coming Soon</Badge>
            <p>Build workflows where a step can contain an entire sub-workflow. This lets you create reusable pipeline building blocks.</p>
            <Card>
              <CardContent className="pt-4">
                <p className="font-mono text-sm">You → [Research Sub-Pipeline] → Translator → Writer → Result</p>
                <p className="font-mono text-sm ml-8">↳ [Researcher A + Researcher B] (parallel sub-pipeline)</p>
              </CardContent>
            </Card>
            <p><strong>Nesting depth:</strong> Free tier supports 2 levels deep. Users with their own LLM keys can nest up to 10 levels.</p>
            <p><strong>Best for:</strong> Complex processes where some steps are themselves multi-agent pipelines. Save sub-workflows and reuse them across different parent workflows.</p>
          </SectionBlock>

          <SectionBlock id="supervisor" title="Supervisor (AI-Planned)" icon={Sparkles}>
            <Badge variant="secondary" className="mb-2">Coming Soon</Badge>
            <p>Describe your goal in plain English. An AI supervisor analyzes available agents and builds the optimal workflow plan. You review, edit if needed, and approve before execution.</p>
            <Card>
              <CardContent className="pt-4">
                <p className="font-mono text-sm">1. You describe goal → 2. AI builds plan → 3. You review & edit → 4. Approve → 5. Execute</p>
              </CardContent>
            </Card>
            <p><strong>How it works:</strong></p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Type your goal (e.g., "Research competitor pricing and write a Spanish executive summary")</li>
              <li>The supervisor AI analyzes all available agents and selects the best ones</li>
              <li>You see a draft plan with agent recommendations, confidence scores, and cost estimates</li>
              <li>Edit the plan (swap agents, reorder, add instructions) or regenerate with feedback</li>
              <li>Approve and run — or save as a reusable workflow for scheduling</li>
            </ul>
            <p><strong>LLM:</strong> Uses platform AI (Groq) by default. You can also use your own LLM keys for planning — configure them in Settings.</p>
          </SectionBlock>

          <SectionBlock id="pattern-recommender" title="Choose Your Pattern" icon={Search}>
            <p className="mb-4">Not sure which orchestration pattern to use? Answer a few questions:</p>
            <PatternRecommender />
          </SectionBlock>

          <SectionBlock id="auto-delegation" title="Auto-Delegation" icon={ChevronRight}>
            <p>When creating a task, CrewHub can automatically suggest the best agent and skill for your message. It uses semantic search (vector similarity) to match your description against all available agent skills.</p>
            <p><strong>How it works:</strong> Type your task description → click "Find Best Agent" → see ranked suggestions with confidence scores → select one and create the task.</p>
            <p>If no good match is found (confidence below 30%), you can create a custom agent tailored to your needs.</p>
          </SectionBlock>

          <SectionBlock id="credits" title="Credits & Pricing" icon={CreditCard}>
            <p>CrewHub uses a credit system for all transactions:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li><strong>New accounts</strong> get 250 free credits</li>
              <li><strong>Credit packs</strong> available at <a href={ROUTES.pricing} className="text-primary hover:underline">Pricing</a></li>
              <li><strong>Agent costs</strong> vary by skill — typically 1-20 credits per task</li>
              <li><strong>Workflow costs</strong> are the sum of all step costs (estimated before execution)</li>
              <li><strong>Platform fee</strong>: 10% on each task (goes to platform operations)</li>
              <li><strong>Refunds</strong>: Failed or canceled tasks refund reserved credits automatically</li>
            </ul>
            <p><strong>Developer payouts:</strong> Agent developers earn credits from tasks completed by their agents. Withdraw via Stripe Connect.</p>
          </SectionBlock>

          <SectionBlock id="building-agents" title="Building Agents" icon={Code}>
            <p>Three ways to create agents for the marketplace:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li><strong>No-Code Builder</strong> — Use the <a href="/dashboard/builder" className="text-primary hover:underline">visual builder</a> (powered by Langflow) to create agents without writing code</li>
              <li><strong>Register Existing Agent</strong> — If you have an A2A-compatible agent running somewhere, <a href="/onboarding" className="text-primary hover:underline">register it</a> with the marketplace</li>
              <li><strong>Create Custom Agent</strong> — Use AI to generate a specialized agent from a description</li>
            </ul>
            <p><strong>A2A Protocol:</strong> CrewHub uses Google's Agent-to-Agent protocol (JSON-RPC 2.0). Your agent needs a webhook endpoint that accepts <code>tasks/send</code> requests.</p>
          </SectionBlock>

          <SectionBlock id="api-reference" title="API Reference" icon={BookOpen}>
            <p>Full API documentation with endpoints, request/response schemas, and code examples is available on the <a href={ROUTES.docs} className="text-primary hover:underline">Docs page</a>.</p>
            <p>Key endpoint groups: Agents, Tasks, Workflows, Credits, Discovery, A2A Protocol.</p>
          </SectionBlock>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify the page renders locally**

Run: `cd frontend && npm run dev`
Navigate to: `http://localhost:3000/guide`
Expected: Guide page renders with sidebar, all 12 sections, and working pattern recommender.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/\(marketplace\)/guide/page.tsx
git commit -m "feat: add interactive guide page with pattern recommender"
```

---

### Task 3: Landing Page Orchestration Showcase

**Files:**
- Modify: `frontend/src/app/(marketplace)/page.tsx`

- [ ] **Step 1: Read the current landing page**

Read `frontend/src/app/(marketplace)/page.tsx` to find the "Assemble Your AI Team" card section (around lines 163-214). Note the exact surrounding code for the edit.

- [ ] **Step 2: Replace the single team card with 3 orchestration pattern cards**

Replace the existing "Assemble Your AI Team" `<Link>` block with 3 pattern cards inside a container. Keep the same grid column span (md:col-span-3). The new structure:

```tsx
{/* Orchestration Patterns — spans 3 cols */}
<div className="flex flex-col gap-4 overflow-hidden rounded-2xl border-2 border-primary/20 bg-card p-5 sm:p-6 md:col-span-3">
  <div>
    <h2 className="text-2xl font-bold">Assemble Your AI Team</h2>
    <p className="mt-1 text-sm text-muted-foreground">
      Choose how your agents work together
    </p>
  </div>
  <div className="grid gap-3 sm:grid-cols-3">
    {[
      {
        icon: GitBranch,
        title: "Manual Pipeline",
        desc: "You pick agents & order. Sequential and parallel chains.",
        best: "Simple multi-step tasks",
        href: "/dashboard/workflows/new?pattern=manual",
      },
      {
        icon: Workflow,
        title: "Hierarchical",
        desc: "Nested sub-workflows. Reusable pipeline building blocks.",
        best: "Complex multi-stage processes",
        href: "/dashboard/workflows/new?pattern=hierarchical",
        badge: "Coming Soon",
      },
      {
        icon: Sparkles,
        title: "Supervisor",
        desc: "Describe your goal. AI selects agents & builds the plan.",
        best: "\"I know what, not who\"",
        href: "/dashboard/workflows/new?pattern=supervisor",
        badge: "Coming Soon",
      },
    ].map((p) => (
      <a
        key={p.title}
        href={p.href}
        className="group flex flex-col gap-2 rounded-xl border border-border/50 bg-background/50 p-4 transition-all hover:border-primary/30 hover:bg-primary/5"
      >
        <div className="flex items-center gap-2">
          <p.icon className="h-5 w-5 text-primary" />
          <span className="font-semibold text-sm">{p.title}</span>
          {p.badge && <Badge variant="secondary" className="text-[10px] px-1.5 py-0">{p.badge}</Badge>}
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed">{p.desc}</p>
        <p className="mt-auto text-[11px] font-medium text-primary/70">Best for: {p.best}</p>
      </a>
    ))}
  </div>
  <a
    href="/team"
    className="flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-transform hover:translate-x-0.5"
  >
    Try Team Mode <ArrowRight className="h-4 w-4" />
  </a>
</div>
```

Make sure `Workflow` icon is imported from lucide-react (add to the import list if not already there). Also ensure `GitBranch`, `Sparkles`, `ArrowRight` are imported (they likely already are).

- [ ] **Step 3: Verify locally**

Navigate to `http://localhost:3000` on mobile (375px) and desktop. Verify 3 pattern cards render inside the team section with proper responsive layout.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/\(marketplace\)/page.tsx
git commit -m "feat: orchestration pattern showcase on landing page"
```

---

### Task 4: Deploy Phase 1 to Staging

- [ ] **Step 1: Push to staging**

```bash
git push origin staging
```

- [ ] **Step 2: Verify on staging**

Navigate to `https://marketplace-staging.aidigitalcrew.com/guide` — verify guide page loads.
Navigate to `https://marketplace-staging.aidigitalcrew.com/` — verify orchestration cards appear on landing page.
Check mobile hamburger menu for Guide link.

---

## Phase 2: Data Model + Hierarchical Backend

### Task 5: Alembic Migration

**Files:**
- Create: `alembic/versions/028_orchestration_patterns.py`

- [ ] **Step 1: Create the migration file**

```python
"""Add orchestration patterns support

Revision ID: 028
Revises: 027
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision = "028"
down_revision = "027"

def upgrade() -> None:
    # Workflow: add pattern_type and supervisor_config
    op.add_column("workflows", sa.Column("pattern_type", sa.String(), server_default="manual", nullable=False))
    op.add_column("workflows", sa.Column("supervisor_config", sa.JSON(), nullable=True))

    # WorkflowStep: add sub_workflow_id, make agent_id/skill_id nullable
    op.add_column("workflow_steps", sa.Column("sub_workflow_id", PG_UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_workflow_steps_sub_workflow",
        "workflow_steps", "workflows",
        ["sub_workflow_id"], ["id"],
        ondelete="SET NULL",
    )
    op.alter_column("workflow_steps", "agent_id", existing_type=PG_UUID(as_uuid=True), nullable=True)
    op.alter_column("workflow_steps", "skill_id", existing_type=PG_UUID(as_uuid=True), nullable=True)

    # WorkflowRun: add parent_run_id and depth
    op.add_column("workflow_runs", sa.Column("parent_run_id", PG_UUID(as_uuid=True), nullable=True))
    op.add_column("workflow_runs", sa.Column("depth", sa.Integer(), server_default="0", nullable=False))
    op.create_foreign_key(
        "fk_workflow_runs_parent",
        "workflow_runs", "workflow_runs",
        ["parent_run_id"], ["id"],
        ondelete="SET NULL",
    )

    # WorkflowStepRun: add child_run_id
    op.add_column("workflow_step_runs", sa.Column("child_run_id", PG_UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_workflow_step_runs_child",
        "workflow_step_runs", "workflow_runs",
        ["child_run_id"], ["id"],
        ondelete="SET NULL",
    )

    # SupervisorPlan: ephemeral plan storage
    op.create_table(
        "supervisor_plans",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", PG_UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("goal", sa.String(), nullable=False),
        sa.Column("plan_data", sa.JSON(), nullable=False),
        sa.Column("llm_provider", sa.String(), nullable=True),
        sa.Column("status", sa.String(), server_default="draft", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )

def downgrade() -> None:
    op.drop_table("supervisor_plans")
    op.drop_constraint("fk_workflow_step_runs_child", "workflow_step_runs", type_="foreignkey")
    op.drop_column("workflow_step_runs", "child_run_id")
    op.drop_constraint("fk_workflow_runs_parent", "workflow_runs", type_="foreignkey")
    op.drop_column("workflow_runs", "depth")
    op.drop_column("workflow_runs", "parent_run_id")
    op.alter_column("workflow_steps", "skill_id", existing_type=PG_UUID(as_uuid=True), nullable=False)
    op.alter_column("workflow_steps", "agent_id", existing_type=PG_UUID(as_uuid=True), nullable=False)
    op.drop_constraint("fk_workflow_steps_sub_workflow", "workflow_steps", type_="foreignkey")
    op.drop_column("workflow_steps", "sub_workflow_id")
    op.drop_column("workflows", "supervisor_config")
    op.drop_column("workflows", "pattern_type")
```

- [ ] **Step 2: Commit**

```bash
git add alembic/versions/028_orchestration_patterns.py
git commit -m "feat: add migration 028 for orchestration patterns"
```

---

### Task 6: Extend Workflow Models

**Files:**
- Modify: `src/models/workflow.py`
- Create: `src/models/supervisor_plan.py`

- [ ] **Step 1: Read current workflow model**

Read `src/models/workflow.py` to understand current field definitions and imports.

- [ ] **Step 2: Add new fields to Workflow model**

Add after existing fields in `Workflow` class:

```python
pattern_type: Mapped[str] = mapped_column(String, default="manual")
supervisor_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
```

- [ ] **Step 3: Modify WorkflowStep — make agent_id/skill_id nullable, add sub_workflow_id**

Change `agent_id` and `skill_id` from `nullable=False` to `nullable=True`. Add `sub_workflow_id`:

```python
agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
    Uuid, ForeignKey("agents.id", ondelete="CASCADE"), nullable=True
)
skill_id: Mapped[Optional[uuid.UUID]] = mapped_column(
    Uuid, ForeignKey("agent_skills.id", ondelete="CASCADE"), nullable=True
)
sub_workflow_id: Mapped[Optional[uuid.UUID]] = mapped_column(
    Uuid, ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True
)
sub_workflow: Mapped[Optional["Workflow"]] = relationship(
    "Workflow", foreign_keys=[sub_workflow_id], lazy="selectin"
)
```

- [ ] **Step 4: Add new fields and self-referential relationship to WorkflowRun**

```python
parent_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
    Uuid, ForeignKey("workflow_runs.id", ondelete="SET NULL"), nullable=True
)
depth: Mapped[int] = mapped_column(Integer, default=0)

# Self-referential relationship — MUST include remote_side to avoid AmbiguousForeignKeysError
parent_run: Mapped[Optional["WorkflowRun"]] = relationship(
    "WorkflowRun", remote_side="WorkflowRun.id", foreign_keys=[parent_run_id]
)
```

- [ ] **Step 5: Add child_run_id to WorkflowStepRun**

```python
child_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
    Uuid, ForeignKey("workflow_runs.id", ondelete="SET NULL"), nullable=True
)
```

- [ ] **Step 6: Create SupervisorPlan model**

Create `src/models/supervisor_plan.py`. **IMPORTANT:** Import `Uuid` from `sqlalchemy`, matching the pattern in `src/models/workflow.py`:

```python
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, JSON, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base


class SupervisorPlan(Base):
    __tablename__ = "supervisor_plans"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    goal: Mapped[str] = mapped_column(String, nullable=False)
    plan_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    llm_provider: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
```

- [ ] **Step 7: Commit**

```bash
git add src/models/workflow.py src/models/supervisor_plan.py
git commit -m "feat: extend workflow models for orchestration patterns"
```

---

### Task 7: Extend Workflow Schemas

**Files:**
- Modify: `src/schemas/workflow.py`

- [ ] **Step 1: Read current schemas**

Read `src/schemas/workflow.py` fully.

- [ ] **Step 2: Update WorkflowStepCreate — make agent_id/skill_id optional, add sub_workflow_id + XOR validator**

```python
from pydantic import model_validator

class WorkflowStepCreate(BaseModel):
    agent_id: Optional[UUID] = None       # was required UUID
    skill_id: Optional[UUID] = None       # was required UUID
    sub_workflow_id: Optional[UUID] = None  # NEW
    step_group: int = Field(0, ge=0)
    position: int = Field(0, ge=0)
    input_mode: str = Field("chain", pattern=r"^(chain|original|custom)$")
    input_template: Optional[str] = None
    label: Optional[str] = Field(None, max_length=255)
    instructions: Optional[str] = Field(None, max_length=1000)

    @model_validator(mode="after")
    def validate_step_target(self):
        has_agent = self.agent_id is not None and self.skill_id is not None
        has_sub = self.sub_workflow_id is not None
        if has_agent == has_sub:
            raise ValueError(
                "Step must have either (agent_id + skill_id) or sub_workflow_id, not both or neither"
            )
        return self
```

- [ ] **Step 3: Update WorkflowCreate — add pattern_type**

```python
class WorkflowCreate(BaseModel):
    name: str = Field(max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    icon: str = Field("🔗", max_length=10)
    is_public: bool = False
    pattern_type: str = Field("manual", pattern=r"^(manual|hierarchical|supervisor)$")  # NEW
    supervisor_config: Optional[dict] = None  # NEW
    max_total_credits: Optional[int] = Field(None, ge=1)
    timeout_seconds: Optional[int] = Field(1800, ge=60, le=7200)
    step_timeout_seconds: Optional[int] = Field(120, ge=30, le=3600)
    steps: list[WorkflowStepCreate] = Field(default=[], max_length=50)
```

- [ ] **Step 4: Update WorkflowResponse — add new fields**

Add to `WorkflowResponse`:

```python
pattern_type: str
supervisor_config: Optional[dict] = None
```

Add to `WorkflowStepResponse`:

```python
sub_workflow_id: Optional[UUID] = None
```

Add to `WorkflowRunResponse`:

```python
parent_run_id: Optional[UUID] = None
depth: int = 0
```

Add to `WorkflowStepRunResponse`:

```python
child_run_id: Optional[UUID] = None
```

- [ ] **Step 5: Commit**

```bash
git add src/schemas/workflow.py
git commit -m "feat: extend workflow schemas with pattern_type and sub_workflow_id"
```

---

### Task 8: Cycle Detection in WorkflowService

**Files:**
- Modify: `src/services/workflow_service.py`

- [ ] **Step 1: Read current workflow service**

Read `src/services/workflow_service.py` fully to understand create/update patterns.

- [ ] **Step 2: Add cycle detection function**

Add this method to the `WorkflowService` class:

```python
async def _detect_cycle(self, workflow_id: uuid.UUID, sub_workflow_id: uuid.UUID) -> bool:
    """Walk the sub-workflow graph via BFS to detect cycles."""
    visited = {workflow_id}
    queue = [sub_workflow_id]
    while queue:
        current_id = queue.pop(0)
        if current_id in visited:
            return True
        visited.add(current_id)
        result = await self.db.execute(
            select(WorkflowStep.sub_workflow_id)
            .where(WorkflowStep.workflow_id == current_id)
            .where(WorkflowStep.sub_workflow_id.isnot(None))
        )
        for (child_id,) in result:
            queue.append(child_id)
    return False
```

- [ ] **Step 3: Add cycle check to create_workflow and update_workflow**

In both `create_workflow()` and `update_workflow()`, after processing steps, add:

```python
for step_data in steps:
    if step_data.sub_workflow_id:
        if workflow.pattern_type == "manual":
            raise BadRequestError("Manual workflows cannot contain sub-workflows")
        if await self._detect_cycle(workflow.id, step_data.sub_workflow_id):
            raise BadRequestError("Circular sub-workflow reference detected")
```

- [ ] **Step 4: Commit**

```bash
git add src/services/workflow_service.py
git commit -m "feat: add cycle detection for hierarchical sub-workflows"
```

---

### Task 9: Hierarchical Execution Engine

**Files:**
- Modify: `src/services/workflow_execution.py`

- [ ] **Step 1: Read current execution service**

Read `src/services/workflow_execution.py` fully. Note the `_dispatch_step_group()`, `_pump_single_run()`, and `_collect_group_output()` methods.

- [ ] **Step 2: Update pump query to order by depth DESC**

In `pump_running_workflows()`, change the query to order by depth descending so child runs are processed before parents:

```python
result = await db.execute(
    select(WorkflowRun)
    .where(WorkflowRun.status == "running")
    .order_by(WorkflowRun.depth.desc())  # children first
    .limit(20)
)
```

- [ ] **Step 3: Update `_dispatch_step_group()` for sub-workflow steps**

In the loop where steps are dispatched, add a branch for sub-workflow steps:

```python
# Check for invalid step (deleted sub-workflow leaves both null)
# This MUST be BEFORE the sub_workflow_id branch, not inside it
if step.agent_id is None and step.skill_id is None and step.sub_workflow_id is None:
    step_run.status = "failed"
    step_run.error = f"Step '{step.label or step.id}' has no agent or sub-workflow (may have been deleted)"
    continue

if step.sub_workflow_id:
    # Enforce nesting depth
    user = await db.get(User, run.user_id)
    has_byok = await self._user_has_byok_keys(user, db)
    max_depth = 10 if has_byok else 2
    if run.depth + 1 >= max_depth:
        step_run.status = "failed"
        step_run.error = f"Maximum nesting depth ({max_depth}) exceeded"
        continue

    # Execute sub-workflow
    child_run = await self.execute_workflow(
        workflow_id=step.sub_workflow_id,
        input_message=resolved_input,
        user_id=run.user_id,
        db=db,
        parent_run_id=run.id,
        depth=run.depth + 1,
    )
    step_run.child_run_id = child_run.id
    step_run.status = "running"
    step_run.started_at = datetime.utcnow()
else:
    # Existing A2A task dispatch code
    ...
```

- [ ] **Step 4: Update `_pump_single_run()` for child run status checking**

In the status sync section, add child run checking:

```python
if step_run.child_run_id:
    # MUST use select+options, NOT db.get() — db.get() won't trigger selectin
    # loading of step_runs, causing MissingGreenlet when _collect_child_output reads them
    result = await db.execute(
        select(WorkflowRun)
        .options(selectinload(WorkflowRun.step_runs))
        .where(WorkflowRun.id == step_run.child_run_id)
    )
    child_run = result.scalar_one_or_none()
    if child_run and child_run.status == "completed":
        step_run.status = "completed"
        step_run.output_text = self._collect_child_output(child_run)
        step_run.credits_charged = child_run.total_credits_charged
        step_run.completed_at = datetime.utcnow()
    elif child_run and child_run.status == "failed":
        step_run.status = "failed"
        step_run.error = f"Sub-workflow failed: {child_run.error}"
        step_run.completed_at = datetime.utcnow()
    elif child_run and child_run.status == "canceled":
        step_run.status = "failed"
        step_run.error = "Sub-workflow was canceled"
        step_run.completed_at = datetime.utcnow()
elif step_run.task_id:
    # Existing task status sync
    ...
```

- [ ] **Step 5: Add `_collect_child_output()` helper**

```python
def _collect_child_output(self, child_run: WorkflowRun) -> str:
    """Collect output from a completed child workflow run."""
    if not child_run.step_runs:
        return ""
    last_group = max(sr.step_group for sr in child_run.step_runs)
    outputs = [
        sr.output_text for sr in child_run.step_runs
        if sr.step_group == last_group and sr.output_text
    ]
    return "\n\n---\n\n".join(outputs)
```

- [ ] **Step 6: Add `_user_has_byok_keys()` helper**

**IMPORTANT:** There is no `UserLLMKey` model. LLM keys are stored encrypted in the `user_llm_keys` table. Check by querying the table directly using text SQL, or check if the user has any decryptable keys via the existing `LLMKeyService`:

```python
async def _user_has_byok_keys(self, user_id, db) -> bool:
    """Check if user has any BYOK LLM keys configured."""
    result = await db.execute(
        text("SELECT 1 FROM user_llm_keys WHERE user_id = :uid LIMIT 1"),
        {"uid": str(user_id)},
    )
    return result.scalar_one_or_none() is not None
```

If the `user_llm_keys` table doesn't exist either, fall back to always returning `False` (free tier depth = 2) and add a TODO comment for future BYOK integration.

- [ ] **Step 7: Update cancel_run for cascade**

In `cancel_run()`, add recursive child cancellation:

```python
for step_run in run.step_runs:
    if step_run.status in ("pending", "running"):
        step_run.status = "canceled"
        if step_run.task_id:
            # existing task cancel
            ...
        if step_run.child_run_id:
            await self.cancel_run(step_run.child_run_id, db)
```

- [ ] **Step 8: Update `execute_workflow()` to accept parent_run_id and depth**

Add parameters `parent_run_id=None, depth=0` and set them on the created `WorkflowRun`.

- [ ] **Step 9: Commit**

```bash
git add src/services/workflow_execution.py
git commit -m "feat: hierarchical execution engine with sub-workflow dispatch"
```

---

### Task 10: Backend Tests for Hierarchical + Pattern Types

**Files:**
- Create: `tests/test_pattern_types.py`
- Create: `tests/test_hierarchical_execution.py`

- [ ] **Step 1: Write pattern type tests**

Create `tests/test_pattern_types.py` with tests for:
- `test_create_workflow_manual` — default behavior unchanged
- `test_create_workflow_hierarchical` — allows sub_workflow_id
- `test_create_workflow_supervisor` — stores supervisor_config
- `test_manual_rejects_sub_workflow` — pattern constraint enforcement
- `test_step_xor_validation` — rejects both agent_id and sub_workflow_id
- `test_step_xor_validation_neither` — rejects neither set
- `test_cycle_detection` — A→B→A cycle rejected
- `test_cycle_detection_deep` — A→B→C→A three-level cycle rejected

Follow the existing test patterns in `tests/` — use the test database fixtures, async test methods with `@pytest.mark.asyncio`.

- [ ] **Step 2: Run pattern type tests**

```bash
pytest tests/test_pattern_types.py -v
```

- [ ] **Step 3: Write hierarchical execution tests**

Create `tests/test_hierarchical_execution.py` with tests for:
- `test_step_with_sub_workflow` — dispatches child workflow run
- `test_child_output_chains_to_parent` — output flows correctly
- `test_depth_enforcement` — rejects beyond max depth
- `test_timeout_inheritance` — child respects parent step timeout
- `test_cancel_cascade` — parent cancel kills child runs
- `test_child_failure_fails_parent_step` — error propagation
- `test_credit_tallying` — child costs roll up to parent totals

- [ ] **Step 4: Run hierarchical tests**

```bash
pytest tests/test_hierarchical_execution.py -v
```

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v --ignore=tests/test_staging_e2e.py --ignore=tests/test_register_agent_e2e.py --ignore=tests/test_real_agents_e2e.py
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_pattern_types.py tests/test_hierarchical_execution.py
git commit -m "test: add pattern type and hierarchical execution tests"
```

---

### Task 11: Deploy Phase 2 Backend to Staging

- [ ] **Step 1: Push to staging**

```bash
git push origin staging
```

- [ ] **Step 2: Verify migration ran on staging**

Check HF Spaces build logs. Verify new columns exist by testing the workflow API.

---

## Phase 3: Hierarchical Frontend

### Task 12: Update Frontend Types

**Files:**
- Modify: `frontend/src/types/workflow.ts`

- [ ] **Step 1: Read current types**

Read `frontend/src/types/workflow.ts` fully.

- [ ] **Step 2: Add new fields to existing interfaces**

Add `pattern_type`, `supervisor_config` to Workflow. Add `sub_workflow_id`, `sub_workflow` to WorkflowStep. Add `parent_run_id`, `depth` to WorkflowRun. Add `child_run_id` to WorkflowStepRun. Add new `SupervisorPlan` and `SupervisorPlanStep` interfaces.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/workflow.ts
git commit -m "feat: extend workflow types for orchestration patterns"
```

---

### Task 13: Pattern Picker on New Workflow Page

**Files:**
- Modify: `frontend/src/app/(marketplace)/dashboard/workflows/new/page.tsx`

- [ ] **Step 1: Read current new workflow page**

Read the file fully. Note the existing template selection.

- [ ] **Step 2: Add pattern selection step before templates**

Add a first step that shows 3 pattern cards (Manual, Hierarchical, Supervisor). Use `useSearchParams()` to check for `?pattern=` query param (pre-select from landing page CTAs). **IMPORTANT:** Wrap the component using `useSearchParams()` in a `<Suspense>` boundary — required for Next.js static export. After selecting a pattern, show the appropriate form:
- Manual/Hierarchical: existing template picker + name/description form
- Supervisor: goal textarea (Phase 5 will complete this)

Store selected pattern in state, pass to `useCreateWorkflow` mutation.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/\(marketplace\)/dashboard/workflows/new/page.tsx
git commit -m "feat: pattern picker on new workflow page"
```

---

### Task 14: Sub-Workflow Support in Workflow Editor

**Files:**
- Modify: `frontend/src/app/(marketplace)/dashboard/workflows/[id]/workflow-detail-client.tsx`

- [ ] **Step 1: Read current workflow detail page**

Read the file fully. Note how step cards are rendered in edit mode.

- [ ] **Step 2: Add Agent/Sub-Workflow toggle to step card (edit mode)**

For hierarchical/supervisor workflows, add a segmented control ("Agent" | "Sub-Workflow") at the top of each step card. When "Sub-Workflow" is selected, replace the agent/skill picker with a dropdown of user's saved workflows (fetched via `useMyWorkflows()`). Filter out the current workflow to prevent self-reference.

- [ ] **Step 3: Show sub-workflow info in view mode**

When a step has `sub_workflow_id`, render the sub-workflow name and step count instead of agent name.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/\(marketplace\)/dashboard/workflows/\[id\]/workflow-detail-client.tsx
git commit -m "feat: sub-workflow step support in workflow editor"
```

---

### Task 15: Deploy Phase 3 + Verify

- [ ] **Step 1: Push to staging**

```bash
git push origin staging
```

- [ ] **Step 2: Verify on staging**

Navigate to `/dashboard/workflows/new` — verify 3 pattern cards appear.
Create a hierarchical workflow with a sub-workflow step — verify it saves.
Run the hierarchical workflow — verify child run executes and output chains.

---

## Phase 4: Supervisor Backend

### Task 16: Supervisor Schemas

**Files:**
- Create: `src/schemas/supervisor.py`

- [ ] **Step 1: Create supervisor schemas**

Create `src/schemas/supervisor.py` with `SupervisorPlanRequest`, `SupervisorPlanStep`, `SupervisorPlan`, `ReplanRequest`, `ApprovePlanRequest` as defined in the spec (section 2.2).

- [ ] **Step 2: Commit**

```bash
git add src/schemas/supervisor.py
git commit -m "feat: add supervisor plan schemas"
```

---

### Task 17: Supervisor Planner Service

**Files:**
- Create: `src/services/supervisor_planner.py`

- [ ] **Step 1: Create the planner service**

Create `src/services/supervisor_planner.py` implementing:
- `generate_plan()` — fetch agent registry, build prompt, call LLM via `src/core/llm_router.py` `completion()`, validate response, store plan in `supervisor_plans` table, return plan
- `replan()` — fetch previous plan, append feedback to prompt, generate new plan
- `approve_plan()` — look up plan by ID (verify ownership + not expired), create Workflow with `pattern_type="supervisor"`, return workflow

Use the existing `get_router()` from `src/core/llm_router.py` for LLM calls. Use `completion(messages=[...])` pattern.

Clean up expired plans (older than 1 hour) on each `generate_plan()` call.

- [ ] **Step 2: Commit**

```bash
git add src/services/supervisor_planner.py
git commit -m "feat: supervisor planner service with LLM planning"
```

---

### Task 18: Supervisor API Endpoints

**Files:**
- Create: `src/api/supervisor.py`
- Modify: `src/main.py`

- [ ] **Step 1: Create supervisor router**

Create `src/api/supervisor.py` with 3 endpoints:
- `POST /plan` — rate limited (5/hr free, 20/hr BYOK)
- `POST /replan`
- `POST /approve`

The router should declare `prefix="/workflows/supervisor"` and `tags=["supervisor"]`. Follow the existing router pattern from `src/api/workflows.py`.

- [ ] **Step 2: Register router in main.py**

Add import and include with the API prefix:
```python
from src.api.supervisor import router as supervisor_router
app.include_router(supervisor_router, prefix=settings.api_v1_prefix)
```

This gives endpoints at `/api/v1/workflows/supervisor/plan`, etc.

- [ ] **Step 3: Commit**

```bash
git add src/api/supervisor.py src/main.py
git commit -m "feat: supervisor API endpoints (plan, replan, approve)"
```

---

### Task 19: Add pattern_type filter to workflow list

**Files:**
- Modify: `src/api/workflows.py`

- [ ] **Step 1: Add optional pattern_type query param**

Add `pattern_type: Optional[str] = Query(None)` to the list endpoints. Filter the query when provided.

- [ ] **Step 2: Commit**

```bash
git add src/api/workflows.py
git commit -m "feat: add pattern_type filter to workflow list endpoint"
```

---

### Task 20: Supervisor Tests

**Files:**
- Create: `tests/test_supervisor_planner.py`
- Create: `tests/test_supervisor_security.py`

- [ ] **Step 1: Write supervisor planner tests**

Test plan generation, validation, budget enforcement, depth limits, BYOK support, replan with feedback, approve creates workflow. Mock the LLM calls (patch `completion()` to return a canned plan JSON).

- [ ] **Step 2: Write supervisor security tests**

Test unauthenticated access (401), rate limiting (429), cross-user plan access (403), prompt injection handling.

- [ ] **Step 3: Run all tests**

```bash
pytest tests/test_supervisor_planner.py tests/test_supervisor_security.py -v
```

- [ ] **Step 4: Run full test suite**

```bash
pytest tests/ -v --ignore=tests/test_staging_e2e.py --ignore=tests/test_register_agent_e2e.py --ignore=tests/test_real_agents_e2e.py
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_supervisor_planner.py tests/test_supervisor_security.py
git commit -m "test: add supervisor planner and security tests"
```

---

### Task 21: Deploy Phase 4 Backend

- [ ] **Step 1: Push to staging**

```bash
git push origin staging
```

- [ ] **Step 2: Verify supervisor endpoints on staging**

```bash
# Test plan generation (requires auth)
curl -X POST https://api-staging.crewhubai.com/api/v1/workflows/supervisor/plan \
  -H "X-API-Key: <key>" \
  -H "Content-Type: application/json" \
  -d '{"goal": "Research competitors and summarize findings"}'
```

---

## Phase 5: Supervisor Frontend

### Task 22: Supervisor API Client + Hooks

**Files:**
- Create: `frontend/src/lib/api/supervisor.ts`
- Create: `frontend/src/lib/hooks/use-supervisor.ts`

- [ ] **Step 1: Create API client**

```typescript
import { apiClient } from "./client";
import type { SupervisorPlan } from "@/types/workflow";

export async function generatePlan(goal: string, llmProvider?: string, maxCredits?: number) {
  return apiClient.post<SupervisorPlan>("/workflows/supervisor/plan", {
    goal, llm_provider: llmProvider, max_credits: maxCredits,
  });
}

export async function replan(goal: string, feedback: string, previousPlanId: string) {
  return apiClient.post<SupervisorPlan>("/workflows/supervisor/replan", {
    goal, feedback, previous_plan_id: previousPlanId,
  });
}

export async function approvePlan(planId: string, workflowName?: string) {
  return apiClient.post<Workflow>("/workflows/supervisor/approve", {
    plan_id: planId, workflow_name: workflowName,
  });
}
```

- [ ] **Step 2: Create React Query hooks**

```typescript
import { useMutation } from "@tanstack/react-query";
import { generatePlan, replan, approvePlan } from "@/lib/api/supervisor";

export function useSupervisorPlan() {
  return useMutation({ mutationFn: (data: { goal: string; llmProvider?: string; maxCredits?: number }) =>
    generatePlan(data.goal, data.llmProvider, data.maxCredits)
  });
}

export function useSupervisorReplan() {
  return useMutation({ mutationFn: (data: { goal: string; feedback: string; previousPlanId: string }) =>
    replan(data.goal, data.feedback, data.previousPlanId)
  });
}

export function useApprovePlan() {
  return useMutation({ mutationFn: (data: { planId: string; workflowName?: string }) =>
    approvePlan(data.planId, data.workflowName)
  });
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/api/supervisor.ts frontend/src/lib/hooks/use-supervisor.ts
git commit -m "feat: supervisor API client and React Query hooks"
```

---

### Task 23: Supervisor Plan Review UI

**Files:**
- Create: `frontend/src/app/(marketplace)/dashboard/workflows/new/supervisor-plan.tsx`
- Modify: `frontend/src/app/(marketplace)/dashboard/workflows/new/page.tsx`

- [ ] **Step 1: Create SupervisorPlan component**

Build the plan review UI as specified in the design spec section 4.3:
- Shows goal, estimated cost, step cards with agent info + confidence bars
- Buttons: Edit Plan, Regenerate (with feedback textarea), Approve & Run, Save as Workflow, Save & Schedule
- Regenerate opens inline textarea + calls `useSupervisorReplan()`
- Approve & Run calls `useApprovePlan()` then `useRunWorkflow()`
- Save as Workflow calls `useApprovePlan()` only, redirects to workflow detail

- [ ] **Step 2: Wire supervisor flow into new workflow page**

When pattern is "supervisor":
- Show goal textarea + "Generate Plan" button
- On submit, call `useSupervisorPlan()`, show loading spinner
- On success, render `<SupervisorPlan>` component with the returned plan
- Edit Plan button navigates to workflow editor (pre-populated)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/\(marketplace\)/dashboard/workflows/new/supervisor-plan.tsx
git add frontend/src/app/\(marketplace\)/dashboard/workflows/new/page.tsx
git commit -m "feat: supervisor plan review UI with approve/edit/regenerate"
```

---

### Task 24: Deploy Phase 5 + Verify

- [ ] **Step 1: Push to staging**

```bash
git push origin staging
```

- [ ] **Step 2: Full manual verification on staging**

1. Navigate to `/dashboard/workflows/new` — verify 3 pattern cards
2. Select Supervisor → type goal → Generate Plan → see plan UI
3. Click Approve & Run → verify workflow created and executes
4. Click Regenerate → add feedback → verify new plan returned
5. Click Save as Workflow → verify workflow appears in list
6. Create hierarchical workflow → add sub-workflow step → run → verify output chains
7. Check `/guide` page still works
8. Check landing page orchestration cards

---

## Phase 6: Integration Testing

### Task 25: E2E Tests

**Files:**
- Create: `tests/test_supervisor_e2e.py`
- Create: `tests/test_hierarchical_e2e.py`

- [ ] **Step 1: Write supervisor E2E tests (against staging)**

```python
# tests/test_supervisor_e2e.py
# Tests run against staging API with real agents

async def test_full_supervisor_flow():
    """Goal → plan → approve → execute → verify output"""
    plan = await api.post("/workflows/supervisor/plan", {"goal": "Summarize a document"})
    assert plan["steps"]
    assert plan["total_estimated_credits"] > 0

    workflow = await api.post("/workflows/supervisor/approve", {"plan_id": plan["plan_id"]})
    assert workflow["pattern_type"] == "supervisor"

    run = await api.post(f"/workflows/{workflow['id']}/run", {"message": "Test document text"})
    # Poll until complete
    ...

async def test_supervisor_replan():
    """Generate → feedback → regenerate → different plan"""
    ...

async def test_supervisor_save_and_schedule():
    """Approved plan saves as workflow, appears in list"""
    ...
```

- [ ] **Step 2: Write hierarchical E2E tests**

```python
# tests/test_hierarchical_e2e.py

async def test_nested_workflow_execution():
    """Parent with sub-workflow runs end-to-end, output chains"""
    ...

async def test_nested_cancel():
    """Cancel parent, verify child runs also canceled"""
    ...
```

- [ ] **Step 3: Run E2E tests**

```bash
python tests/test_supervisor_e2e.py --api-key <key>
python tests/test_hierarchical_e2e.py --api-key <key>
```

- [ ] **Step 4: Commit**

```bash
git add tests/test_supervisor_e2e.py tests/test_hierarchical_e2e.py
git commit -m "test: add E2E tests for supervisor and hierarchical workflows"
```

---

### Task 26: Update Documentation

**Files:**
- Modify: `docs/CHANGELOG.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `frontend/src/app/(marketplace)/docs/page.tsx`

- [ ] **Step 1: Add supervisor/hierarchical endpoints to docs page**

Add a new "Orchestration" section to the API reference on the docs page with the 3 supervisor endpoints and the `pattern_type` filter.

- [ ] **Step 2: Update CHANGELOG**

Add v0.6.0 entry with all orchestration pattern features.

- [ ] **Step 3: Update ARCHITECTURE**

Add Supervisor Planner service to the services layer diagram.

- [ ] **Step 4: Commit**

```bash
git add docs/CHANGELOG.md docs/ARCHITECTURE.md frontend/src/app/\(marketplace\)/docs/page.tsx
git commit -m "docs: add orchestration patterns to changelog, architecture, and API reference"
```

---

### Task 27: Final Deploy

- [ ] **Step 1: Push to staging**

```bash
git push origin staging
```

- [ ] **Step 2: Run full E2E test suite**

```bash
python tests/test_supervisor_e2e.py --api-key <key>
python tests/test_hierarchical_e2e.py --api-key <key>
python tests/test_staging_e2e.py --api-key <key>
```

- [ ] **Step 3: Merge to main**

```bash
git checkout main && git merge staging && git push origin main && git checkout staging
```

- [ ] **Step 4: Verify on production**

Check all features work on production domains.
