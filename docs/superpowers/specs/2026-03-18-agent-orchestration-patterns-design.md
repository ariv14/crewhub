# Agent Orchestration Patterns — Design Spec

> **Date:** 2026-03-18
> **Status:** Draft
> **Scope:** Supervisor Agent Pattern, Hierarchical Agent Teams, Interactive Guide Page, Landing Page Enhancement

---

## Overview

CrewHub currently supports single-agent execution, parallel dispatch (Team Mode), sequential chaining (Workflows), and auto-delegation suggestions. This spec adds three missing capabilities:

1. **Supervisor Agent Pattern** — AI plans the workflow from a natural language goal, user approves/edits, then executes
2. **Hierarchical Agent Teams** — Workflow steps can contain sub-workflows (nested pipelines)
3. **Interactive Guide Page** — Comprehensive `/guide` page covering all platform features + pattern recommender
4. **Landing Page Enhancement** — Orchestration pattern showcase in "Assemble Your AI Team" section

All three pattern types (Manual, Hierarchical, Supervisor) produce saved Workflows that can be scheduled, cloned, and shared.

---

## Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Pattern selection UI | Template-based on `/workflows/new` | Reuses existing workflow infrastructure, single unified model |
| Supervisor approval | Approve with edits | User sees draft in workflow editor, can modify before running |
| Supervisor LLM | Platform key (Groq) + BYOK override | Free tier uses Groq Llama 3.3 70B; users can test with own LLM keys for flexibility |
| Nesting depth | 2 levels free, unlimited BYOK | Natural monetization lever; safety cap at 10 for BYOK |
| Guide page | Dedicated `/guide` page | Comprehensive, covers all features from day 0 to production |
| Scheduled supervisor runs | Use saved/approved plan | Predictable, no surprise cost changes on scheduled runs |
| Testing | Unit + Integration + E2E against staging | Matches existing "always test backend AND frontend in parallel" rule |

---

## 1. Data Model Changes

### 1.1 Workflow Model Extensions

```python
# src/models/workflow.py — existing model, new fields

class Workflow:
    # ... existing fields ...
    pattern_type = Column(String, default="manual")  # "manual" | "hierarchical" | "supervisor"
    supervisor_config = Column(JSON, nullable=True)
    # supervisor_config schema:
    # {
    #   "goal": str,                    # user's natural language goal
    #   "plan_status": str,             # "draft" | "approved" | "rejected"
    #   "llm_provider": str | None,     # null = platform default (Groq)
    #   "plan_history": [               # audit trail
    #     {"plan": {...}, "timestamp": str, "status": str, "feedback": str | None}
    #   ]
    # }
```

### 1.2 WorkflowStep Extensions

```python
# src/models/workflow.py — WorkflowStep, modified + new fields

class WorkflowStep:
    # MODIFIED: agent_id and skill_id must become nullable for sub-workflow steps
    agent_id = Column(UUID, ForeignKey("agents.id", ondelete="CASCADE"), nullable=True)  # was nullable=False
    skill_id = Column(UUID, ForeignKey("agent_skills.id", ondelete="CASCADE"), nullable=True)  # was nullable=False

    # NEW field
    sub_workflow_id = Column(UUID, ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True)
    sub_workflow = relationship("Workflow", foreign_keys=[sub_workflow_id])

    # Rules:
    # - XOR constraint: exactly one of (agent_id+skill_id) or sub_workflow_id must be set
    # - Only sub_workflow_id allowed when parent workflow.pattern_type in ("hierarchical", "supervisor")
    # - Execution dispatches sub-workflow instead of A2A task
    # - ondelete=SET NULL: if sub-workflow is deleted, step becomes invalid (handled at execution time)
    #   Running child WorkflowRuns are NOT affected (they reference workflow_id, not step)

# Pydantic schema validation (src/schemas/workflow.py):
class WorkflowStepCreate(BaseModel):
    agent_id: UUID | None = None
    skill_id: UUID | None = None
    sub_workflow_id: UUID | None = None
    # ... existing fields ...

    @model_validator(mode="after")
    def validate_step_target(self):
        has_agent = self.agent_id is not None and self.skill_id is not None
        has_sub = self.sub_workflow_id is not None
        if has_agent == has_sub:  # both set or both null
            raise ValueError("Step must have either (agent_id + skill_id) or sub_workflow_id, not both/neither")
        return self
```

### 1.2.1 Cycle Detection

```python
# src/services/workflow_service.py — added to create_workflow() and update_workflow()

async def detect_cycle(workflow_id: UUID, sub_workflow_id: UUID, db: AsyncSession) -> bool:
    """Walk the sub-workflow graph to detect cycles. Returns True if cycle found."""
    visited = {workflow_id}
    queue = [sub_workflow_id]
    while queue:
        current_id = queue.pop(0)
        if current_id in visited:
            return True  # cycle detected
        visited.add(current_id)
        # Find all sub-workflow references from current workflow's steps
        steps = await db.execute(
            select(WorkflowStep.sub_workflow_id)
            .where(WorkflowStep.workflow_id == current_id)
            .where(WorkflowStep.sub_workflow_id.isnot(None))
        )
        for (child_id,) in steps:
            queue.append(child_id)
    return False

# Called before persisting any step with sub_workflow_id:
if step_data.sub_workflow_id:
    if await detect_cycle(workflow_id, step_data.sub_workflow_id, db):
        raise ValueError("Circular sub-workflow reference detected")
```

### 1.3 WorkflowRun Extensions

```python
# src/models/workflow.py — WorkflowRun, new fields

class WorkflowRun:
    # ... existing fields ...
    parent_run_id = Column(UUID, ForeignKey("workflow_runs.id"), nullable=True)
    depth = Column(Integer, default=0)

    parent_run = relationship("WorkflowRun", remote_side="WorkflowRun.id")
    child_runs = relationship("WorkflowRun", back_populates="parent_run")
```

### 1.4 Alembic Migration

Single migration file: `028_orchestration_patterns.py`

**New columns:**
- Add `pattern_type` (String, default "manual") to `workflows`
- Add `supervisor_config` (JSON, nullable) to `workflows`
- Add `sub_workflow_id` (UUID FK → workflows.id, nullable, ondelete SET NULL) to `workflow_steps`
- Add `parent_run_id` (UUID FK → workflow_runs.id, nullable) to `workflow_runs`
- Add `depth` (Integer, default 0) to `workflow_runs`
- Add `child_run_id` (UUID FK → workflow_runs.id, nullable) to `workflow_step_runs`

**Altered columns:**
- Alter `workflow_steps.agent_id` from NOT NULL to nullable
- Alter `workflow_steps.skill_id` from NOT NULL to nullable

**Backfill:**
- Set `pattern_type = "manual"` for all existing workflows

---

## 2. Supervisor Planning Service

### 2.1 Service: `src/services/supervisor_planner.py`

```
SupervisorPlanner:
  generate_plan(goal: str, user_id: UUID, llm_provider: str | None) → SupervisorPlan
  replan(goal: str, feedback: str, previous_plan: dict, user_id: UUID) → SupervisorPlan
  approve_plan(plan: SupervisorPlan, workflow_name: str, user_id: UUID) → Workflow
```

**`generate_plan()` flow:**

1. **Fetch agent registry** — all active agents with skills, pricing, ratings
2. **Build LLM prompt:**
   ```
   System: You are a workflow architect for CrewHub, an AI agent marketplace.
   Given a user's goal and available agents, produce a workflow plan as JSON.

   Rules:
   - Choose the best agent/skill for each step
   - Use step_group numbers: same group = parallel, sequential groups = chained
   - Set input_mode: "chain" (default), "original", or "custom" with template
   - Add clear instructions per step
   - Consider agent ratings and pricing
   - Stay within the user's credit balance
   - Nest sub-workflows only when a step requires multiple sub-agents

   Available agents:
   [truncated agent registry with name, skills, category, avg_credits, rating]

   User's credit balance: {balance}
   Max nesting depth: {depth_limit}

   Output JSON schema:
   {
     "name": "workflow name",
     "description": "what this workflow does",
     "estimated_credits": number,
     "steps": [
       {
         "agent_id": "uuid",
         "skill_id": "uuid",
         "step_group": 0,
         "input_mode": "chain",
         "instructions": "what this step should do",
         "label": "Step label",
         "sub_steps": [...] | null  // for hierarchical nesting
       }
     ]
   }
   ```
3. **Call LLM:**
   - Default: Groq (`groq/llama-3.3-70b-versatile`) via LiteLLM
   - BYOK: user's configured key via LiteLLM Router
4. **Validate response:**
   - All agent_ids exist and are active
   - All skill_ids belong to their agents
   - Estimated cost within user balance
   - Nesting depth within limits (2 free, 10 BYOK)
   - Retry once with error feedback if validation fails
5. **Return `SupervisorPlan`** with steps, cost estimate, agent details

### 2.2 Schemas: `src/schemas/supervisor.py`

```python
class SupervisorPlanRequest(BaseModel):
    goal: str                           # natural language goal
    llm_provider: str | None = None     # optional BYOK provider
    max_credits: float | None = None    # budget cap

class SupervisorPlanStep(BaseModel):
    agent_id: UUID
    skill_id: UUID
    agent_name: str                     # for display
    skill_name: str                     # for display
    step_group: int
    input_mode: str = "chain"
    input_template: str | None = None
    instructions: str | None = None
    label: str | None = None
    confidence: float                   # 0-1, how confident the supervisor is
    estimated_credits: float
    sub_steps: list["SupervisorPlanStep"] | None = None

class SupervisorPlan(BaseModel):
    name: str
    description: str
    steps: list[SupervisorPlanStep]
    total_estimated_credits: float
    llm_provider_used: str
    plan_id: str                        # UUID for tracking

class ReplanRequest(BaseModel):
    goal: str
    feedback: str                       # what should be different
    previous_plan_id: str

class ApprovePlanRequest(BaseModel):
    plan_id: str
    workflow_name: str | None = None    # override generated name
```

### 2.3 Plan Storage

Plans are stored ephemerally in the `supervisor_plans` table (new model) with 1-hour TTL:

```python
# src/models/supervisor_plan.py
class SupervisorPlanRecord(Base):
    __tablename__ = "supervisor_plans"
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    goal = Column(String, nullable=False)
    plan_data = Column(JSON, nullable=False)     # full SupervisorPlan as JSON
    llm_provider = Column(String, nullable=True)
    status = Column(String, default="draft")     # "draft" | "approved" | "expired"
    created_at = Column(DateTime, default=utcnow)
    expires_at = Column(DateTime)                # created_at + 1 hour

# Cleanup: expired plans deleted on each generate_plan() call (lazy GC)
# This prevents plan tampering — approve endpoint looks up plan_id server-side,
# not from client-submitted data.
```

Add to migration `028_orchestration_patterns.py`.

### 2.4 Rate Limiting

Supervisor plan generation is rate-limited:
- **Free tier (platform Groq key):** 5 plans per hour per user
- **BYOK users:** 20 plans per hour per user (uses their own key)
- Enforced via existing `rate_limiter.py` sliding window

### 2.5 API: `src/api/supervisor.py`

```
POST /api/v1/workflows/supervisor/plan
  Body: SupervisorPlanRequest
  Returns: SupervisorPlan
  Auth: required (uses user's balance for budget, checks BYOK keys)

POST /api/v1/workflows/supervisor/replan
  Body: ReplanRequest
  Returns: SupervisorPlan
  Auth: required

POST /api/v1/workflows/supervisor/approve
  Body: ApprovePlanRequest
  Returns: WorkflowResponse (the created workflow, ready to run or schedule)
  Auth: required
  Action: converts plan to Workflow with pattern_type="supervisor"
```

---

## 3. Hierarchical Execution Engine

### 3.1 Changes to `src/services/workflow_execution.py`

**`_dispatch_step_group()` modification:**

```python
for step_run in group_step_runs:
    step = get_step(step_run.step_id)

    if step.sub_workflow_id:
        # Hierarchical: dispatch sub-workflow
        child_run = await self.execute_workflow(
            workflow_id=step.sub_workflow_id,
            input_message=resolved_input,
            user_id=run.user_id,
            parent_run_id=run.id,
            depth=run.depth + 1
        )
        step_run.task_id = None  # no direct task
        step_run.child_run_id = child_run.id  # NEW field on WorkflowStepRun
        step_run.status = "running"
    else:
        # Existing: dispatch A2A task
        task = await broker.create_task(...)
        step_run.task_id = task.id
```

**`_pump_single_run()` modification:**

```python
for step_run in current_group_runs:
    if step_run.child_run_id:
        # Check child workflow run status
        child_run = await get_run(step_run.child_run_id)
        if child_run.status == "completed":
            step_run.status = "completed"
            step_run.output_text = _collect_child_output(child_run)
            step_run.credits_charged = child_run.total_credits_charged
        elif child_run.status == "failed":
            step_run.status = "failed"
            step_run.error = f"Sub-workflow failed: {child_run.error}"
    else:
        # Existing: check task status
        ...
```

**Depth enforcement in `execute_workflow()`:**

```python
async def execute_workflow(self, workflow_id, input_message, user_id,
                           parent_run_id=None, depth=0):
    workflow = await get_workflow(workflow_id)

    # Depth limit based on user tier
    user = await get_user(user_id)
    if user_has_byok_keys(user):
        max_depth = 10  # BYOK users: up to 10 levels
    else:
        max_depth = 2   # Free tier: max 2 levels

    if depth >= max_depth:
        raise ValueError(f"Maximum nesting depth ({max_depth}) exceeded")

    # Check for null sub_workflow_id (deleted sub-workflow)
    for step in workflow.steps:
        if step.agent_id is None and step.sub_workflow_id is None:
            raise ValueError(f"Step '{step.label or step.id}' has no agent or sub-workflow (may have been deleted)")

    run = WorkflowRun(
        workflow_id=workflow_id,
        user_id=user_id,
        parent_run_id=parent_run_id,
        depth=depth,
        ...
    )
```

**Pump ordering — process children before parents:**

```python
async def pump_running_workflows(self, db):
    """Pump all running workflow runs, processing deepest children first."""
    runs = await db.execute(
        select(WorkflowRun)
        .where(WorkflowRun.status == "running")
        .order_by(WorkflowRun.depth.desc())  # children first, parents last
        .limit(20)
    )
    for run in runs.scalars():
        await self._pump_single_run(run, db)
    await db.commit()
```

This ensures child runs complete and commit their status before parent runs check them in the same pump cycle.

**Timeout inheritance:**

```python
# Child workflow timeout = min(parent step timeout, child workflow timeout)
child_timeout = min(
    parent_step.step_timeout_seconds or 120,
    child_workflow.timeout_seconds or 1800
)
```

**Cancellation cascade:**

```python
async def cancel_run(self, run_id):
    run = await get_run(run_id)
    run.status = "canceled"

    for step_run in run.step_runs:
        if step_run.status in ("pending", "running"):
            step_run.status = "canceled"
            if step_run.task_id:
                await broker.cancel_task(step_run.task_id)
            if step_run.child_run_id:
                await self.cancel_run(step_run.child_run_id)  # recursive
```

### 3.2 Helper: `_collect_child_output`

```python
def _collect_child_output(child_run: WorkflowRun) -> str:
    """Collect output from a completed child workflow run.
    Returns the last step group's output (same as workflow output endpoint).
    Falls back to concatenating all completed step outputs if no final group."""
    last_group = max(sr.step_group for sr in child_run.step_runs)
    final_outputs = [
        sr.output_text for sr in child_run.step_runs
        if sr.step_group == last_group and sr.output_text
    ]
    return "\n\n---\n\n".join(final_outputs) if final_outputs else ""
```

This mirrors the existing `_collect_group_output` pattern — the child's final step group output becomes the parent step's output, which then feeds into the next parent step's `input_mode: "chain"`.

### 3.3 Snapshot Format for Sub-Workflow Steps

```python
# In workflow_snapshot["steps"], sub-workflow steps store:
{
    "step_group": 0,
    "sub_workflow_id": "uuid",
    "sub_workflow_name": "Research Pipeline",  # for error messages
    "agent_id": None,
    "skill_id": None,
    "label": "Research sub-pipeline",
    "input_mode": "chain"
}
# This ensures timeout/failure error messages show meaningful names
```

### 3.4 WorkflowStepRun Extension

```python
class WorkflowStepRun:
    # ... existing fields ...
    child_run_id = Column(UUID, ForeignKey("workflow_runs.id"), nullable=True)
```

Add to migration `028_orchestration_patterns.py`.

---

## 4. Frontend Changes

### 4.1 New Workflow Page — Pattern Picker

**File:** `frontend/src/app/(marketplace)/dashboard/workflows/new/page.tsx`

Replace current template grid with a two-step flow:

**Step 1: Pattern Selection**
- 3 cards: Manual Pipeline, Hierarchical Pipeline, Supervisor (AI-Planned)
- Each card: icon, title, 2-line description, "Best for" bullet, [Select] button
- Cards use shadcn `Card` with hover border highlight

**Step 2: Configuration (varies by pattern)**
- Manual: existing template picker + name/description form
- Hierarchical: same as manual but with "hierarchical" badge
- Supervisor: goal textarea + optional LLM provider select + "Generate Plan" button

### 4.2 Workflow Editor — Hierarchical Support

**File:** `frontend/src/app/(marketplace)/dashboard/workflows/[id]/workflow-detail-client.tsx`

Step card changes (edit mode):
- Toggle: "Agent" | "Sub-Workflow" (radio or segmented control)
- Agent mode: existing agent/skill picker
- Sub-Workflow mode: dropdown of user's saved workflows (filtered to exclude current + ancestors to prevent cycles)
- Visual: sub-workflow step card shows mini-pipeline preview (step count, pattern badge)
- Depth indicator badge on nested steps

### 4.3 Supervisor Plan Review UI

**File:** `frontend/src/app/(marketplace)/dashboard/workflows/new/supervisor-plan.tsx` (new component)

```
┌──────────────────────────────────────────────────┐
│  🤖 Supervisor Plan                    [Draft]    │
│                                                   │
│  Goal: "Research competitor pricing, translate     │
│  findings to Spanish, write executive summary"     │
│                                                   │
│  Estimated cost: 15 credits                       │
│                                                   │
│  ┌─ Step 1 (Group 0) ───────────────────────┐    │
│  │ 🔍 Market Researcher                      │    │
│  │ Skill: competitive-analysis               │    │
│  │ Confidence: 92%  •  ~5 credits            │    │
│  │ Instructions: "Analyze pricing of..."     │    │
│  └───────────────────────────────────────────┘    │
│           ↓                                       │
│  ┌─ Step 2 (Group 1) ───────────────────────┐    │
│  │ 🌐 Spanish Translator                     │    │
│  │ Skill: translate-text                     │    │
│  │ Confidence: 97%  •  ~3 credits            │    │
│  └───────────────────────────────────────────┘    │
│           ↓                                       │
│  ┌─ Step 3 (Group 2) ───────────────────────┐    │
│  │ ✍️ Content Writer                         │    │
│  │ Skill: executive-summary                  │    │
│  │ Confidence: 88%  •  ~7 credits            │    │
│  └───────────────────────────────────────────┘    │
│                                                   │
│  [Edit Plan]  [Regenerate]  [Approve & Run]      │
│                                                   │
│  ── or ──                                        │
│  [Save as Workflow]  [Save & Schedule]            │
└──────────────────────────────────────────────────┘

Edit Plan → opens existing workflow editor pre-populated
Regenerate → textarea for feedback → calls /supervisor/replan
Approve & Run → creates workflow + executes immediately
Save as Workflow → creates workflow without running
Save & Schedule → creates workflow + opens schedule dialog
```

### 4.4 Types & Hooks

**File:** `frontend/src/types/workflow.ts` — extend:

```typescript
interface Workflow {
  // ... existing ...
  pattern_type: "manual" | "hierarchical" | "supervisor";
  supervisor_config?: {
    goal: string;
    plan_status: "draft" | "approved" | "rejected";
    llm_provider?: string;
  };
}

interface WorkflowStep {
  // ... existing ...
  sub_workflow_id?: string;
  sub_workflow?: Workflow;  // populated on fetch
}

interface WorkflowRun {
  // ... existing ...
  parent_run_id?: string;
  depth: number;
}

interface SupervisorPlan {
  name: string;
  description: string;
  steps: SupervisorPlanStep[];
  total_estimated_credits: number;
  llm_provider_used: string;
  plan_id: string;
}

interface SupervisorPlanStep {
  agent_id: string;
  skill_id: string;
  agent_name: string;
  skill_name: string;
  step_group: number;
  input_mode: string;
  instructions?: string;
  label?: string;
  confidence: number;
  estimated_credits: number;
  sub_steps?: SupervisorPlanStep[];
}
```

**File:** `frontend/src/lib/hooks/use-supervisor.ts` — new:

```typescript
useSupervisorPlan()       // POST /workflows/supervisor/plan
useSupervisorReplan()     // POST /workflows/supervisor/replan
useApprovePlan()          // POST /workflows/supervisor/approve
```

**File:** `frontend/src/lib/api/supervisor.ts` — new:

```typescript
generatePlan(goal, llmProvider?, maxCredits?)  → SupervisorPlan
replan(goal, feedback, previousPlanId)          → SupervisorPlan
approvePlan(planId, workflowName?)              → Workflow
```

### 4.5 Landing Page — Orchestration Showcase

**File:** `frontend/src/app/(marketplace)/page.tsx`

In the "Assemble Your AI Team" section, replace single card with 3 pattern cards:

- **Manual Pipeline** — icon: 📋, animated mini-pipeline (3 boxes with arrows)
- **Hierarchical Pipeline** — icon: 🏗️, animated nested pipeline (box containing mini-boxes)
- **Supervisor (AI-Planned)** — icon: 🤖, animated goal → plan → execute flow

Each card: title, 2-line description, subtle animation, "Try It →" CTA linking to `/workflows/new?pattern=<type>`

### 4.6 Guide Page

**File:** `frontend/src/app/(marketplace)/guide/page.tsx` (new)

Comprehensive interactive guide with sections:

1. **Platform Overview** — what CrewHub is, value prop
2. **Getting Started** — account creation, credits, first task
3. **Single Agent Tasks** — Try It panel, task lifecycle diagram
4. **Team Mode** — parallel dispatch, consolidated reports
5. **Manual Pipelines** — sequential chaining, input modes, templates
6. **Hierarchical Pipelines** — sub-workflows, nesting, reusable pipelines
7. **Supervisor (AI-Planned)** — goal → plan → approve → execute flow
8. **Pattern Recommender** — interactive decision tree widget:
   - "Is your task a single step?" → Single Agent
   - "Do you know which agents to use?" → Yes: Manual/Hierarchical, No: Supervisor
   - "Does any step need multiple sub-agents?" → Yes: Hierarchical, No: Manual
9. **Auto-Delegation** — how suggestion scoring works
10. **Credits & Pricing** — cost breakdown across patterns
11. **Building Agents** — registration, Langflow builder, A2A protocol basics
12. **API Reference** — link to `/docs` page

Navigation: sticky sidebar with section links, smooth scroll anchors using `<a>` tags (per project convention — no `<Link>` or `router.push`). Guide link added to both public nav (desktop) and mobile hamburger menu. Page is a static route (no dynamic segments), no `_redirects` entry needed.

---

## 5. Testing Strategy

### 5.1 Backend Unit/Integration Tests (pytest)

**`tests/test_supervisor_planner.py`** (~8 tests):
- `test_generate_plan_valid_goal` — returns valid workflow steps with real agent IDs
- `test_generate_plan_invalid_agents` — filters out inactive/nonexistent agents
- `test_generate_plan_respects_budget` — stays within user balance
- `test_generate_plan_nesting_depth_free` — enforces 2-level cap for free tier
- `test_generate_plan_nesting_depth_byok` — allows deeper nesting for BYOK users
- `test_replan_with_feedback` — modifies plan based on user input
- `test_approve_plan_creates_workflow` — converts plan to saved workflow with correct pattern_type
- `test_plan_with_byok_key` — uses user's LLM key when configured

**`tests/test_hierarchical_execution.py`** (~7 tests):
- `test_step_with_sub_workflow` — dispatches child workflow run
- `test_child_output_chains_to_parent` — output flows to next parent step
- `test_depth_enforcement` — rejects execution beyond max depth
- `test_timeout_inheritance` — child respects parent step timeout
- `test_cancel_cascade` — parent cancel kills child runs and tasks
- `test_child_failure_fails_parent_step` — error propagation works
- `test_credit_tallying` — child costs roll up to parent totals

**`tests/test_pattern_types.py`** (~8 tests):
- `test_create_workflow_manual` — existing behavior unchanged
- `test_create_workflow_hierarchical` — allows sub_workflow_id on steps
- `test_create_workflow_supervisor` — stores supervisor_config correctly
- `test_manual_rejects_sub_workflow` — enforces pattern constraints
- `test_step_xor_validation` — rejects steps with both agent_id and sub_workflow_id
- `test_step_xor_validation_neither` — rejects steps with neither agent_id nor sub_workflow_id
- `test_cycle_detection` — rejects A→B→A circular sub-workflow references
- `test_cycle_detection_deep` — rejects A→B→C→A three-level cycle

**`tests/test_supervisor_security.py`** (~4 tests):
- `test_unauthenticated_plan_generation` — returns 401
- `test_plan_rate_limiting` — exceeding 5/hour returns 429
- `test_approve_other_users_plan` — returns 403
- `test_plan_prompt_injection` — goal with injection attempts produces valid/safe plan

### 5.2 E2E Tests (staging)

**`tests/test_supervisor_e2e.py`** (~3 tests):
- `test_full_supervisor_flow` — goal → plan → approve → execute → verify output
- `test_supervisor_replan` — generate → feedback → regenerate → different plan
- `test_supervisor_save_and_schedule` — approved plan saves as workflow, appears in list

**`tests/test_hierarchical_e2e.py`** (~2 tests):
- `test_nested_workflow_execution` — parent with sub-workflow runs end-to-end, output chains
- `test_nested_cancel` — cancel parent, verify child runs also canceled

### 5.3 Frontend E2E Tests (Playwright against staging)

**`e2e/orchestration-patterns.spec.ts`** (~5 tests):
- `test_pattern_picker` — `/workflows/new` shows 3 pattern cards, selecting each changes form
- `test_supervisor_ui` — type goal → see loading → see plan → edit → approve → verify run created
- `test_hierarchical_editor` — create workflow → add sub-workflow step → verify nested display
- `test_guide_page` — `/guide` loads, all sections render, pattern recommender returns result
- `test_landing_page_patterns` — orchestration cards visible, CTAs link to correct URLs

---

## 6. File Inventory

### New Backend Files
- `src/services/supervisor_planner.py` — LLM planning service
- `src/api/supervisor.py` — 3 supervisor API endpoints
- `src/schemas/supervisor.py` — request/response schemas
- `src/models/supervisor_plan.py` — ephemeral plan storage model (1h TTL)
- `alembic/versions/028_orchestration_patterns.py` — migration
- `tests/test_supervisor_planner.py` — supervisor unit tests
- `tests/test_hierarchical_execution.py` — hierarchical unit tests
- `tests/test_pattern_types.py` — pattern type + cycle detection tests
- `tests/test_supervisor_security.py` — auth, rate limiting, injection tests
- `tests/test_supervisor_e2e.py` — supervisor E2E tests
- `tests/test_hierarchical_e2e.py` — hierarchical E2E tests

### Modified Backend Files
- `src/models/workflow.py` — add pattern_type, supervisor_config, sub_workflow_id (nullable), parent_run_id, depth, child_run_id; alter agent_id/skill_id to nullable
- `src/schemas/workflow.py` — add pattern_type, sub_workflow_id to WorkflowCreate/WorkflowStepCreate; add XOR validator
- `src/services/workflow_execution.py` — hierarchical dispatch + depth enforcement + cancel cascade + pump ordering (depth DESC)
- `src/services/workflow_service.py` — add cycle detection on create/update
- `src/api/workflows.py` — register supervisor router, add ?pattern_type filter to list endpoint
- `src/main.py` — register supervisor API router

### New Frontend Files
- `frontend/src/app/(marketplace)/dashboard/workflows/new/supervisor-plan.tsx` — plan review UI
- `frontend/src/app/(marketplace)/guide/page.tsx` — interactive guide page
- `frontend/src/lib/hooks/use-supervisor.ts` — supervisor React Query hooks
- `frontend/src/lib/api/supervisor.ts` — supervisor API client
- `e2e/orchestration-patterns.spec.ts` — Playwright tests

### Modified Frontend Files
- `frontend/src/app/(marketplace)/dashboard/workflows/new/page.tsx` — pattern picker
- `frontend/src/app/(marketplace)/dashboard/workflows/[id]/workflow-detail-client.tsx` — sub-workflow support in editor
- `frontend/src/app/(marketplace)/page.tsx` — orchestration showcase cards
- `frontend/src/types/workflow.ts` — extended types
- `frontend/src/lib/hooks/use-workflows.ts` — extended hooks if needed
- `frontend/src/components/layout/top-nav.tsx` — add Guide link
- `frontend/src/lib/constants.ts` — add ROUTES.guide

---

## 7. Implementation Order

Build incrementally, each phase deployable independently:

### Phase 1: Guide Page + Landing Page (no backend changes)
- Build `/guide` page with all sections
- Add orchestration cards to landing page
- Add Guide link to nav
- Deploy and verify

### Phase 2: Data Model + Hierarchical Backend
- Alembic migration (028)
- Extend workflow models
- Implement hierarchical execution in workflow_execution.py
- Backend tests for hierarchical
- Deploy backend to staging

### Phase 3: Hierarchical Frontend
- Pattern picker on `/workflows/new`
- Sub-workflow step support in editor
- Playwright tests
- Deploy frontend to staging

### Phase 4: Supervisor Backend
- SupervisorPlanner service
- Supervisor API endpoints + schemas
- Backend tests for supervisor
- E2E tests against staging
- Deploy backend to staging

### Phase 5: Supervisor Frontend
- Supervisor plan review UI
- Goal input → plan display → edit → approve flow
- Playwright tests
- Deploy frontend to staging

### Phase 6: Integration Testing
- Full E2E test suite across all patterns
- Test scheduled supervisor workflows
- Test hierarchical + supervisor combined (supervisor plans a hierarchical workflow)
- Verify credit flows across all patterns
