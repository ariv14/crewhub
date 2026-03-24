# Channel-Workflow Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let channel users trigger multi-agent workflows via slash commands (/workflow) with adaptive delivery — inline for fast workflows, cron-pushed for long ones.

**Architecture:** Gateway-orchestrated. CF Worker routes /ask to agent tasks (unchanged) and /workflow to workflow runs (new). Backend gets 3 new gateway endpoints. Cron delivery extended for workflow results. Workflow execution engine minimally extended (2 optional kwargs + failure_mode conditional).

**Tech Stack:** FastAPI + SQLAlchemy (backend), Cloudflare Worker (gateway), Next.js (frontend), PostgreSQL (database), Alembic (migrations)

**Spec:** `docs/superpowers/specs/2026-03-24-channel-workflow-integration-design.md`

---

## Phase 1: Database & Models (Backend Foundation)

### Task 1: Database Migration

**Files:**
- Create: `alembic/versions/037_workflow_channel_integration.py`

- [ ] **Step 1: Create migration file**

```python
"""Add workflow-channel integration fields.

Revision ID: 037
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PgUUID

revision = "037"
down_revision = "036"

def upgrade() -> None:
    # ChannelConnection: workflow support
    op.add_column("channel_connections", sa.Column("workflow_id", PgUUID(as_uuid=True), sa.ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True))
    op.add_column("channel_connections", sa.Column("workflow_mappings", sa.JSON, nullable=True))

    # WorkflowRun: channel context for cron delivery
    op.add_column("workflow_runs", sa.Column("channel_connection_id", PgUUID(as_uuid=True), sa.ForeignKey("channel_connections.id", ondelete="SET NULL"), nullable=True))
    op.add_column("workflow_runs", sa.Column("channel_chat_id", sa.String(200), nullable=True))

    # ChannelMessage: workflow audit trail
    op.add_column("channel_messages", sa.Column("workflow_run_id", PgUUID(as_uuid=True), sa.ForeignKey("workflow_runs.id", ondelete="SET NULL"), nullable=True))

    # Workflow: failure mode
    op.add_column("workflows", sa.Column("failure_mode", sa.String(20), server_default="stop", nullable=False))

def downgrade() -> None:
    op.drop_column("workflows", "failure_mode")
    op.drop_column("channel_messages", "workflow_run_id")
    op.drop_column("workflow_runs", "channel_chat_id")
    op.drop_column("workflow_runs", "channel_connection_id")
    op.drop_column("channel_connections", "workflow_mappings")
    op.drop_column("channel_connections", "workflow_id")
```

- [ ] **Step 2: Run migration locally**

Run: `alembic upgrade head`
Expected: Migration applies cleanly

- [ ] **Step 3: Commit**

```bash
git add alembic/versions/037_workflow_channel_integration.py
git commit -m "migration: 037 — workflow-channel integration fields"
```

---

### Task 2: Update ORM Models

**Files:**
- Modify: `src/models/channel.py:16-65` (ChannelConnection)
- Modify: `src/models/workflow.py:16-54` (Workflow), `src/models/workflow.py:87-125` (WorkflowRun)

- [ ] **Step 1: Add fields to ChannelConnection**

In `src/models/channel.py`, after `gateway_instance_id` field (around line 45), add:

```python
    workflow_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True
    )
    workflow_mappings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
```

- [ ] **Step 2: Add fields to Workflow model**

In `src/models/workflow.py`, after `supervisor_config` field (around line 37), add:

```python
    failure_mode: Mapped[str] = mapped_column(String(20), default="stop", server_default="stop")
```

- [ ] **Step 3: Add fields to WorkflowRun model**

In `src/models/workflow.py`, after `depth` field (around line 111), add:

```python
    channel_connection_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("channel_connections.id", ondelete="SET NULL"), nullable=True
    )
    channel_chat_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
```

- [ ] **Step 4: Add workflow_run_id to ChannelMessage**

In `src/models/channel.py`, in the ChannelMessage class, after `task_id` field (around line 86), add:

```python
    workflow_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("workflow_runs.id", ondelete="SET NULL"), nullable=True
    )
```

- [ ] **Step 5: Commit**

```bash
git add src/models/channel.py src/models/workflow.py
git commit -m "models: add workflow-channel integration fields"
```

---

### Task 3: Update Pydantic Schemas

**Files:**
- Modify: `src/schemas/channel.py`

- [ ] **Step 1: Update ChannelCreate schema**

Add after `privacy_notice_url` field (around line 22):

```python
    workflow_id: Optional[UUID] = None
    workflow_mappings: Optional[dict] = None
```

- [ ] **Step 2: Update GatewayConnectionResponse**

Add after `privacy_notice_url` field (around line 144):

```python
    workflow_id: Optional[UUID] = None
    workflow_mappings: Optional[dict] = None
```

- [ ] **Step 3: Update GatewayLogMessageRequest**

Add `workflow_run_id` field (after `task_id`, around line 101):

```python
    workflow_run_id: Optional[UUID] = None
```

- [ ] **Step 4: Add new request/response schemas**

Add at the end of the file:

```python
class GatewayCreateWorkflowRunRequest(BaseModel):
    connection_id: UUID
    workflow_id: UUID
    message: str
    chat_id: str

class GatewayCreateWorkflowRunResponse(BaseModel):
    workflow_run_id: Optional[str] = None
    status: str
    estimated_credits: float = 0
    step_count: int = 0
    workflow_name: str = ""
    error: Optional[str] = None

class GatewayWorkflowRunStatusResponse(BaseModel):
    status: str
    final_output: Optional[str] = None
    step_count: int = 0
    steps_completed: int = 0
    total_credits_charged: Optional[float] = None
    error: Optional[str] = None
    workflow_name: str = ""

class GatewayPendingWorkflowDelivery(BaseModel):
    run_id: str
    connection_id: str
    chat_id: str
    platform: str
    status: str
    final_output: Optional[str] = None
    workflow_name: str = ""
    total_credits_charged: Optional[float] = None
    failure_mode: str = "stop"

class GatewayPendingWorkflowDeliveriesResponse(BaseModel):
    deliveries: list[GatewayPendingWorkflowDelivery] = []
```

- [ ] **Step 5: Commit**

```bash
git add src/schemas/channel.py
git commit -m "schemas: add workflow-channel request/response types"
```

---

## Phase 2: Backend Services & API

### Task 4: Extend Workflow Execution Engine

**Files:**
- Modify: `src/services/workflow_execution.py:34-42` (execute_workflow signature)
- Modify: `src/services/workflow_execution.py:98-127` (WorkflowRun creation)
- Modify: `src/services/workflow_execution.py:162-263` (_pump_single_run)
- Test: `tests/test_workflow_channel_integration.py`

- [ ] **Step 1: Write failing test for channel-triggered workflow**

Create `tests/test_workflow_channel_integration.py`:

```python
"""Tests for workflow-channel integration."""
import pytest
from uuid import uuid4

# Test that execute_workflow accepts and stores channel context
class TestWorkflowChannelContext:
    async def test_execute_workflow_stores_channel_context(self, db, workflow, user):
        """Workflow run stores channel_connection_id and channel_chat_id when provided."""
        engine = WorkflowExecutionService(db)
        conn_id = uuid4()
        run = await engine.execute_workflow(
            workflow_id=workflow.id,
            user_id=user.id,
            input_message="test",
            channel_connection_id=conn_id,
            channel_chat_id="discord-channel-123",
        )
        assert run.channel_connection_id == conn_id
        assert run.channel_chat_id == "discord-channel-123"

    async def test_execute_workflow_without_channel_context(self, db, workflow, user):
        """Dashboard-triggered runs have null channel fields."""
        engine = WorkflowExecutionService(db)
        run = await engine.execute_workflow(
            workflow_id=workflow.id,
            user_id=user.id,
            input_message="test",
        )
        assert run.channel_connection_id is None
        assert run.channel_chat_id is None
```

- [ ] **Step 2: Add channel kwargs to execute_workflow()**

In `src/services/workflow_execution.py`, update signature at line 34:

```python
async def execute_workflow(
    self,
    workflow_id: UUID,
    user_id: UUID,
    input_message: str,
    schedule_id: UUID | None = None,
    parent_run_id: UUID | None = None,
    depth: int = 0,
    channel_connection_id: UUID | None = None,
    channel_chat_id: str | None = None,
) -> WorkflowRun:
```

In the WorkflowRun constructor (around line 107), add:

```python
            channel_connection_id=channel_connection_id,
            channel_chat_id=channel_chat_id,
```

- [ ] **Step 3: Add failure_mode to workflow snapshot**

In `execute_workflow()`, where the snapshot dict is built (around line 55-76), add `failure_mode`:

```python
            "failure_mode": wf.failure_mode or "stop",
```

- [ ] **Step 4: Implement failure_mode="continue" in _pump_single_run()**

In `_pump_single_run()`, find the failure handling block (around line 214-228):

Replace the hardcoded fail-on-first-failure with:

```python
        # Check for failures in current group
        failed_steps = [sr for sr in group_step_runs if sr.status == "failed"]
        if failed_steps:
            failure_mode = snapshot.get("failure_mode", "stop")
            if failure_mode == "continue":
                # Log failures but continue to next group
                logger.warning(
                    "Workflow run %s: %d steps failed in group %d (continue mode)",
                    run.id, len(failed_steps), run.current_step_group,
                )
            else:
                # Stop mode: fail the entire run
                run.status = "failed"
                failed_labels = "; ".join(
                    f"{self._step_label(sr, snapshot)}: {sr.error or 'unknown'}"
                    for sr in failed_steps
                )
                run.error = f"Step {run.current_step_group + 1} failed — {failed_labels}"
                run.completed_at = now
                self._tally_credits(run)
                return
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_workflow_channel_integration.py -v`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add src/services/workflow_execution.py tests/test_workflow_channel_integration.py
git commit -m "feat: extend workflow engine — channel context + failure_mode"
```

---

### Task 5: New Gateway Endpoints

**Files:**
- Modify: `src/api/gateway.py` (add 3 endpoints after line 426)
- Modify: `src/services/channel_service.py` (workflow validation, third-party check)

- [ ] **Step 1: Add /gateway/create-workflow-run endpoint**

```python
@router.post("/create-workflow-run", response_model=GatewayCreateWorkflowRunResponse, dependencies=[Depends(rate_limit_by_ip)])
async def create_workflow_run(
    req: GatewayCreateWorkflowRunRequest,
    _: None = Depends(require_gateway_key),
    db: AsyncSession = Depends(get_db),
) -> GatewayCreateWorkflowRunResponse:
    """Create a workflow run triggered from a channel message."""
    from src.services.workflow_execution import WorkflowExecutionService
    from src.services.workflow_service import WorkflowService

    # Fetch connection
    connection = await db.get(ChannelConnection, req.connection_id)
    if not connection:
        return GatewayCreateWorkflowRunResponse(status="error", error="Connection not found")

    # Fetch workflow
    wf_service = WorkflowService(db)
    wf = await wf_service.get_workflow(req.workflow_id)
    if not wf:
        return GatewayCreateWorkflowRunResponse(status="error", error="Workflow not found")

    # Check ownership or public
    if wf.owner_id != connection.owner_id and not wf.is_public:
        return GatewayCreateWorkflowRunResponse(status="error", error="Workflow not accessible")

    # Estimate credits
    engine = WorkflowExecutionService(db)
    estimated = engine._estimate_cost(wf)

    # Check balance
    from src.services.credit_ledger import CreditLedgerService
    ledger = CreditLedgerService(db)
    balance_info = await ledger.get_balance(connection.owner_id)
    if balance_info["available"] < estimated:
        return GatewayCreateWorkflowRunResponse(
            status="error",
            error="insufficient_balance",
            estimated_credits=float(estimated),
        )

    # Check daily limit
    if connection.daily_credit_limit:
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        usage_stmt = select(
            func.coalesce(func.sum(ChannelMessage.credits_charged), 0)
        ).where(
            ChannelMessage.connection_id == req.connection_id,
            ChannelMessage.created_at >= today_start,
        )
        today_usage = float((await db.execute(usage_stmt)).scalar_one())
        if today_usage + estimated > connection.daily_credit_limit:
            return GatewayCreateWorkflowRunResponse(
                status="error",
                error="daily_limit",
                estimated_credits=float(estimated),
            )

    # Execute workflow
    try:
        run = await engine.execute_workflow(
            workflow_id=req.workflow_id,
            user_id=connection.owner_id,
            input_message=req.message,
            channel_connection_id=req.connection_id,
            channel_chat_id=req.chat_id,
        )
        await db.commit()

        return GatewayCreateWorkflowRunResponse(
            workflow_run_id=str(run.id),
            status=run.status,
            estimated_credits=float(estimated),
            step_count=len(run.step_runs),
            workflow_name=wf.name,
        )
    except Exception as e:
        logger.exception("Workflow run creation failed for connection %s", req.connection_id)
        return GatewayCreateWorkflowRunResponse(status="error", error=str(e))
```

- [ ] **Step 2: Add /gateway/workflow-run-status/{run_id} endpoint**

```python
@router.get("/workflow-run-status/{run_id}")
async def gateway_workflow_run_status(
    run_id: UUID,
    _: None = Depends(require_gateway_key),
    db: AsyncSession = Depends(get_db),
) -> GatewayWorkflowRunStatusResponse:
    """Get workflow run status for gateway polling."""
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(WorkflowRun)
        .where(WorkflowRun.id == run_id)
        .options(selectinload(WorkflowRun.step_runs))
    )
    run = result.scalar_one_or_none()
    if not run:
        return GatewayWorkflowRunStatusResponse(status="not_found")

    steps_completed = sum(1 for sr in run.step_runs if sr.status == "completed")
    final_output = None
    if run.status in ("completed", "failed"):
        outputs = [sr.output_text for sr in sorted(run.step_runs, key=lambda s: s.step_group) if sr.output_text]
        final_output = "\n\n".join(outputs) if outputs else None

    # Get workflow name from snapshot
    wf_name = (run.workflow_snapshot or {}).get("name", "Workflow")

    return GatewayWorkflowRunStatusResponse(
        status=run.status,
        final_output=final_output,
        step_count=len(run.step_runs),
        steps_completed=steps_completed,
        total_credits_charged=float(run.total_credits_charged) if run.total_credits_charged else None,
        error=run.error,
        workflow_name=wf_name,
    )
```

- [ ] **Step 3: Add /gateway/pending-workflow-deliveries endpoint**

```python
@router.get("/pending-workflow-deliveries")
async def pending_workflow_deliveries(
    _: None = Depends(require_gateway_key),
    db: AsyncSession = Depends(get_db),
) -> GatewayPendingWorkflowDeliveriesResponse:
    """Return completed/failed workflow runs that haven't been delivered to channels yet."""
    from sqlalchemy.orm import selectinload

    # Find channel-triggered runs that are terminal
    runs_result = await db.execute(
        select(WorkflowRun)
        .where(
            WorkflowRun.channel_connection_id.isnot(None),
            WorkflowRun.status.in_(["completed", "failed"]),
        )
        .options(selectinload(WorkflowRun.step_runs))
        .order_by(WorkflowRun.completed_at.desc())
        .limit(50)
    )
    runs = list(runs_result.scalars().unique().all())

    # Filter out already-delivered runs (have an outbound ChannelMessage with workflow_run_id)
    delivered_ids_result = await db.execute(
        select(ChannelMessage.workflow_run_id)
        .where(
            ChannelMessage.workflow_run_id.in_([r.id for r in runs]),
            ChannelMessage.direction == "outbound",
        )
    )
    delivered_ids = {row[0] for row in delivered_ids_result.all()}

    deliveries = []
    for run in runs:
        if run.id in delivered_ids:
            continue

        # Get connection for platform info
        conn = await db.get(ChannelConnection, run.channel_connection_id)
        if not conn:
            continue

        outputs = [sr.output_text for sr in sorted(run.step_runs, key=lambda s: s.step_group) if sr.output_text]
        final_output = "\n\n".join(outputs) if outputs else None
        wf_name = (run.workflow_snapshot or {}).get("name", "Workflow")
        failure_mode = (run.workflow_snapshot or {}).get("failure_mode", "stop")

        deliveries.append(GatewayPendingWorkflowDelivery(
            run_id=str(run.id),
            connection_id=str(run.channel_connection_id),
            chat_id=run.channel_chat_id or "",
            platform=conn.platform,
            status=run.status,
            final_output=final_output,
            workflow_name=wf_name,
            total_credits_charged=float(run.total_credits_charged) if run.total_credits_charged else None,
            failure_mode=failure_mode,
        ))

    return GatewayPendingWorkflowDeliveriesResponse(deliveries=deliveries)
```

- [ ] **Step 4: Update get_connection to return workflow fields**

In the existing `get_connection` endpoint (around line 225), update the return to include:

```python
        workflow_id=connection.workflow_id,
        workflow_mappings=connection.workflow_mappings,
```

- [ ] **Step 5: Add workflow validation to channel service**

In `src/services/channel_service.py`, add to `create_channel()` after agent validation:

```python
        # Validate workflow if provided
        if hasattr(data, 'workflow_id') and data.workflow_id:
            from src.models.workflow import Workflow
            wf = await self.db.get(Workflow, data.workflow_id)
            if not wf or (wf.owner_id != owner_id and not wf.is_public):
                raise BadRequestError("Workflow not found or not accessible")

        # Validate workflow_mappings if provided
        if hasattr(data, 'workflow_mappings') and data.workflow_mappings:
            from src.models.workflow import Workflow
            for name, wf_id in data.workflow_mappings.items():
                wf = await self.db.get(Workflow, wf_id)
                if not wf or (wf.owner_id != owner_id and not wf.is_public):
                    raise BadRequestError(f"Workflow '{name}' not found or not accessible")
```

And in the ChannelConnection constructor, add:

```python
            workflow_id=getattr(data, "workflow_id", None),
            workflow_mappings=getattr(data, "workflow_mappings", None),
```

- [ ] **Step 6: Commit**

```bash
git add src/api/gateway.py src/services/channel_service.py
git commit -m "feat: gateway endpoints for workflow-channel integration"
```

---

### Task 6: Channel Analytics Enhancement

**Files:**
- Modify: `src/api/channels.py` (enhance list and detail responses)

- [ ] **Step 1: Add lifetime totals to channel list**

In the channel list endpoint, add aggregation queries for total_messages and total_credits per channel. Return these alongside existing daily metrics.

Add to the channel response serialization:

```python
# Compute lifetime totals
for ch in channels:
    total_msgs = await db.execute(
        select(func.count(ChannelMessage.id))
        .where(ChannelMessage.connection_id == ch.id)
    )
    total_credits = await db.execute(
        select(func.coalesce(func.sum(ChannelMessage.credits_charged), 0))
        .where(ChannelMessage.connection_id == ch.id)
    )
    ch._total_messages = total_msgs.scalar_one()
    ch._total_credits = float(total_credits.scalar_one())
```

- [ ] **Step 2: Add workflow name resolution**

Resolve `workflow_id` to workflow name for display:

```python
if ch.workflow_id:
    from src.models.workflow import Workflow
    wf = await db.get(Workflow, ch.workflow_id)
    ch._workflow_name = wf.name if wf else None
```

- [ ] **Step 3: Commit**

```bash
git add src/api/channels.py
git commit -m "feat: channel analytics — lifetime totals + workflow name"
```

---

## Phase 3: CF Worker Gateway

### Task 7: Discord Slash Command Registration

**Files:**
- Modify: `cloudflare/gateway-worker.js:1070` (auto-register-discord)

- [ ] **Step 1: Register /workflow command alongside /ask**

In the `/auto-register-discord` endpoint, update the command registration to register BOTH commands:

```javascript
      // Register /ask + /workflow slash commands globally
      const commands = [
        {
          name: "ask",
          description: "Ask the AI agent a question",
          type: 1,
          options: [{
            name: "message",
            description: "Your question or message",
            type: 3,
            required: true,
          }],
        },
        {
          name: "workflow",
          description: "Run a multi-agent workflow",
          type: 1,
          options: [
            {
              name: "message",
              description: "Your request",
              type: 3,
              required: true,
            },
            {
              name: "name",
              description: "Workflow name (optional, uses default if omitted)",
              type: 3,
              required: false,
            },
          ],
        },
      ];

      // Bulk overwrite global commands
      const cmdResp = await fetch(
        `https://discord.com/api/v10/applications/${application_id}/commands`,
        {
          method: "PUT",
          headers: {
            "Authorization": `Bot ${bot_token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(commands),
        }
      );
```

- [ ] **Step 2: Commit**

```bash
git add cloudflare/gateway-worker.js
git commit -m "feat: register /workflow slash command alongside /ask"
```

---

### Task 8: Workflow Message Routing & Processing

**Files:**
- Modify: `cloudflare/gateway-worker.js:386` (handleDiscordWebhook — route by command)
- Modify: `cloudflare/gateway-worker.js:589` (processMessage — prefix routing)
- Add new functions: `processDiscordWorkflow()`, `processWorkflowMessage()`

- [ ] **Step 1: Route Discord commands by name**

In `handleDiscordWebhook()`, update the slash command handler (around line 422) to route by command name:

```javascript
    if (body.data.name === "ask") {
      // Existing /ask flow
      ctx.waitUntil(processDiscordInteraction({
        env, connectionId, userId, msgId, chatId, text,
        applicationId, interactionToken,
      }));
    } else if (body.data.name === "workflow") {
      const workflowName = body.data.options?.find(o => o.name === "name")?.value || null;
      ctx.waitUntil(processDiscordWorkflow({
        env, connectionId, userId, msgId, chatId, text,
        applicationId, interactionToken, workflowName,
      }));
    }
```

- [ ] **Step 2: Add processDiscordWorkflow() function**

Add after `processDiscordInteraction()`:

```javascript
async function processDiscordWorkflow(ctx) {
  const { env, connectionId, userId, msgId, chatId, text, applicationId, interactionToken, workflowName } = ctx;

  const conn = await getConnection(env, connectionId);
  if (!conn || !conn.bot_token) {
    await sendDiscordInteractionFollowup(applicationId, interactionToken,
      "Sorry, this channel is not configured correctly.");
    return;
  }

  // Auto-activate pending channels
  if (conn.status === "pending") {
    await backendCall(env, "/gateway/heartbeat", "POST", {
      connections: [{ connection_id: connectionId, status: "active" }],
    });
  }

  // Resolve workflow_id
  let workflowId = null;
  if (workflowName && conn.workflow_mappings && conn.workflow_mappings[workflowName]) {
    workflowId = conn.workflow_mappings[workflowName];
  } else {
    workflowId = conn.workflow_id;
  }

  if (!workflowId) {
    await sendDiscordInteractionFollowup(applicationId, interactionToken,
      "No workflow configured for this channel. Use /ask instead, or ask the channel owner to connect a workflow.");
    return;
  }

  // Check blocked users
  const userHash = (await hmacSha256(
    `${env.GATEWAY_SERVICE_KEY}:${connectionId}`, userId
  )).substring(0, 16);
  if (conn.blocked_users && conn.blocked_users.includes(userHash)) {
    return;
  }

  // Log inbound message (NULL text — GDPR)
  await logMessage(env, {
    connection_id: connectionId,
    platform_user_id_hash: userHash,
    platform_message_id: msgId,
    platform_chat_id: chatId,
    direction: "inbound",
    message_text: null,
    media_type: "text",
  });

  // Create workflow run
  const runResult = await backendCall(env, "/gateway/create-workflow-run", "POST", {
    connection_id: connectionId,
    workflow_id: workflowId,
    message: text,
    chat_id: chatId,
  });

  if (!runResult || runResult.status === "error") {
    const errorMsgs = {
      insufficient_balance: "Insufficient credits for this workflow. Top up at crewhubai.com/dashboard/credits",
      daily_limit: "Daily message limit reached. Service will resume tomorrow.",
    };
    await sendDiscordInteractionFollowup(applicationId, interactionToken,
      errorMsgs[runResult?.error] || runResult?.error || "Sorry, couldn't start the workflow.");
    return;
  }

  const runId = runResult.workflow_run_id;
  const wfName = runResult.workflow_name || "Workflow";
  const stepCount = runResult.step_count || 0;
  const estCredits = runResult.estimated_credits || 0;

  // Quick poll (25s)
  let responseText = null;
  let runStatus = null;
  const startTime = Date.now();
  while (Date.now() - startTime < 25000) {
    await new Promise(r => setTimeout(r, 3000));
    try {
      const status = await backendCall(env, `/gateway/workflow-run-status/${runId}`);
      if (!status) continue;
      runStatus = status;
      if (status.status === "completed") {
        responseText = status.final_output || "Workflow completed.";
        break;
      } else if (status.status === "failed") {
        responseText = `Sorry, your workflow couldn't be completed. (Error: ${status.error || "unknown"})`;
        break;
      }
    } catch (err) {
      console.error("Workflow poll error for run", runId);
    }
  }

  if (responseText) {
    // FAST PATH: completed within 25s
    const privacyUrl = conn.privacy_notice_url || "https://crewhubai.com/privacy";
    responseText += `\n\n-# Your data is processed per our [privacy notice](${privacyUrl}). Messages are retained for 90 days.`;

    await sendDiscordInteractionFollowup(applicationId, interactionToken, responseText);

    await logMessage(env, {
      connection_id: connectionId,
      platform_user_id_hash: "agent",
      platform_message_id: `wfreply-${msgId}`,
      platform_chat_id: chatId,
      direction: "outbound",
      message_text: responseText.substring(0, 2000),
      workflow_run_id: runId,
      credits_charged: runStatus?.total_credits_charged || estCredits,
    });
  } else {
    // SLOW PATH: ack + cron delivery
    const ackMsg = `Processing your request through ${wfName} (${stepCount} steps, ~${estCredits} credits)...`;
    await sendDiscordInteractionFollowup(applicationId, interactionToken, ackMsg);

    // Store system message for cron pickup
    await logMessage(env, {
      connection_id: connectionId,
      platform_user_id_hash: userHash,
      platform_message_id: `wfpending-${msgId}`,
      platform_chat_id: chatId,
      direction: "system",
      message_text: `wfrun:${runId}`,
    });
  }
}
```

- [ ] **Step 3: Add Telegram/Slack prefix routing**

In `processMessage()`, at the top (after connection fetch), add prefix check:

```javascript
  // Route workflow prefix to workflow handler
  if (text.startsWith("!workflow")) {
    let workflowName = null;
    let workflowText = text;
    if (text.startsWith("!workflow:")) {
      const parts = text.substring(10).split(" ", 1);
      workflowName = parts[0];
      workflowText = text.substring(11 + workflowName.length).trim();
    } else {
      workflowText = text.substring(9).trim();
    }
    if (!workflowText) {
      await sender.send(botToken, chatId, "Usage: !workflow <message> or !workflow:name <message>");
      return;
    }
    return processWorkflowMessage({
      env, connectionId, conn, userId, msgId, chatId,
      text: workflowText, workflowName, sender, botToken,
    });
  }
```

- [ ] **Step 4: Add processWorkflowMessage() for Telegram/Slack**

Similar to processDiscordWorkflow but uses `sender.send()` instead of interaction followup. (Same logic, different delivery mechanism.)

- [ ] **Step 5: Commit**

```bash
git add cloudflare/gateway-worker.js
git commit -m "feat: workflow routing — Discord /workflow command + Telegram/Slack !workflow prefix"
```

---

### Task 9: Cron Delivery for Workflow Results

**Files:**
- Modify: `cloudflare/gateway-worker.js:801` (deliverPendingResponses)

- [ ] **Step 1: Add workflow delivery to cron**

In `deliverPendingResponses()`, add after existing task delivery logic:

```javascript
  // --- Workflow delivery ---
  try {
    const pendingWf = await backendCall(env, "/gateway/pending-workflow-deliveries");
    if (pendingWf && pendingWf.deliveries) {
      for (const delivery of pendingWf.deliveries) {
        try {
          const conn = await getConnection(env, delivery.connection_id);
          if (!conn || !conn.bot_token) continue;

          let responseText = "";
          if (delivery.status === "completed") {
            responseText = delivery.final_output || "Workflow completed.";
            if (delivery.total_credits_charged) {
              responseText = `**${delivery.workflow_name}** — completed (${delivery.total_credits_charged} credits)\n\n${responseText}`;
            }
          } else if (delivery.status === "failed") {
            responseText = `Sorry, your workflow "${delivery.workflow_name}" couldn't be completed.`;
          }

          // Append privacy notice
          const privacyUrl = conn.privacy_notice_url || "https://crewhubai.com/privacy";
          if (delivery.platform === "discord") {
            responseText += `\n\n-# Your data is processed per our [privacy notice](${privacyUrl}). Messages are retained for 90 days.`;
          } else {
            responseText += `\n\nYour data is processed per our privacy notice: ${privacyUrl} — Messages retained 90 days.`;
          }

          // Send via bot token (NOT interaction followup — token may be expired)
          if (delivery.platform === "discord") {
            await sendDiscord(conn.bot_token, delivery.chat_id, responseText);
          } else if (delivery.platform === "telegram") {
            await telegramApi(conn.bot_token, "sendMessage", { chat_id: delivery.chat_id, text: responseText });
          } else if (delivery.platform === "slack") {
            await sendSlack(conn.bot_token, delivery.chat_id, responseText);
          }

          // Log outbound to prevent re-delivery
          await logMessage(env, {
            connection_id: delivery.connection_id,
            platform_user_id_hash: "agent",
            platform_message_id: `wfdelivery-${delivery.run_id}`,
            platform_chat_id: delivery.chat_id,
            direction: "outbound",
            message_text: (responseText || "").substring(0, 2000),
            workflow_run_id: delivery.run_id,
            credits_charged: delivery.total_credits_charged || 0,
          });

          console.log("Workflow result delivered:", delivery.run_id, "to", delivery.platform);
        } catch (err) {
          console.error("Workflow delivery failed for run", delivery.run_id);
        }
      }
    }
  } catch (err) {
    console.error("Workflow delivery fetch failed");
  }
```

- [ ] **Step 2: Commit**

```bash
git add cloudflare/gateway-worker.js
git commit -m "feat: cron delivery for workflow results across all platforms"
```

---

## Phase 4: Frontend

### Task 10: Channel Wizard — Workflow Selection

**Files:**
- Modify: `frontend/src/app/(marketplace)/dashboard/settings/channel-wizard.tsx`
- Modify: `frontend/src/lib/hooks/use-channels.ts` (if needed for workflow fetch)

- [ ] **Step 1: Add workflow state to wizard**

Add state variables after existing state:

```typescript
const [workflowId, setWorkflowId] = useState("");
const [workflowMappings, setWorkflowMappings] = useState<Record<string, string>>({});
```

- [ ] **Step 2: Fetch user's workflows for dropdown**

Add a hook to fetch workflows:

```typescript
const { data: workflowsData } = useWorkflows({ owner_id: user?.id });
const workflows = workflowsData?.workflows ?? [];
```

- [ ] **Step 3: Add workflow section to Step 3 (after agent selection)**

After the Skill selection section (around line 727), add:

```tsx
{/* Workflow selection (optional) */}
<div className="border-t pt-4 mt-4">
  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-3">Workflow (for /workflow command)</p>
  <div className="space-y-2">
    <Label>Default Workflow</Label>
    <Select value={workflowId || "__none__"} onValueChange={(v) => setWorkflowId(v === "__none__" ? "" : v)}>
      <SelectTrigger>
        <SelectValue placeholder="None (disable /workflow)" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="__none__">None</SelectItem>
        {workflows.map((wf) => (
          <SelectItem key={wf.id} value={wf.id}>{wf.name} ({wf.steps?.length || 0} steps)</SelectItem>
        ))}
      </SelectContent>
    </Select>
    <p className="text-xs text-muted-foreground">
      Users can trigger this workflow with /workflow in Discord or !workflow in Telegram/Slack.
    </p>
  </div>
</div>
```

- [ ] **Step 4: Pass workflow_id and workflow_mappings in create call**

Update `handleSubmit()` to include workflow fields:

```typescript
const channel = await createChannel.mutateAsync({
  ...existingFields,
  workflow_id: workflowId || undefined,
  workflow_mappings: Object.keys(workflowMappings).length > 0 ? workflowMappings : undefined,
});
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/\(marketplace\)/dashboard/settings/channel-wizard.tsx
git commit -m "feat: workflow selection in channel wizard Step 3"
```

---

### Task 11: Enhanced Channel Cards

**Files:**
- Modify: `frontend/src/app/(marketplace)/dashboard/channels/page.tsx` (or wherever channel cards are rendered)

- [ ] **Step 1: Display workflow name on channel card**

Add workflow name display below agent info:

```tsx
{channel.workflow_name && (
  <p className="text-xs text-muted-foreground">
    Workflow: <span className="text-foreground">{channel.workflow_name}</span>
  </p>
)}
```

- [ ] **Step 2: Display lifetime totals**

Replace existing metrics with enhanced display:

```tsx
<div className="flex gap-4 text-xs text-muted-foreground">
  <div className="flex items-center gap-1">
    <MessageSquare className="h-3 w-3" />
    <span>{channel.total_messages || 0} total</span>
  </div>
  <div className="flex items-center gap-1">
    <Zap className="h-3 w-3" />
    <span>{channel.total_credits || 0} credits</span>
  </div>
</div>
<div className="flex gap-4 text-xs text-muted-foreground">
  <span>{channel.messages_today || 0} today</span>
  <span>{channel.credits_today || 0} credits today</span>
</div>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/\(marketplace\)/dashboard/channels/
git commit -m "feat: enhanced channel cards — workflow name + lifetime analytics"
```

---

## Phase 5: Deploy & Test

### Task 12: Deploy to Staging

- [ ] **Step 1: Push to staging**

```bash
git push origin staging
```

- [ ] **Step 2: Deploy CF Worker to staging**

```bash
cd cloudflare && npx wrangler deploy gateway-worker.js --config wrangler-gateway.toml
```

- [ ] **Step 3: Wait for backend + frontend deploys**

```bash
gh run list --branch staging --limit 3
```

- [ ] **Step 4: Run migration on staging**

Migration runs automatically via FastAPI lifespan on HF Spaces restart.

---

### Task 13: E2E Testing — Backend (parallel track 1)

- [ ] **Step 1: Test /gateway/create-workflow-run**

```bash
curl -s -X POST "https://api-staging.crewhubai.com/api/v1/gateway/create-workflow-run" \
  -H "X-Gateway-Key: $GATEWAY_KEY" \
  -H "Content-Type: application/json" \
  -d '{"connection_id":"<discord-channel-id>","workflow_id":"<workflow-id>","message":"test","chat_id":"test-chat"}'
```

- [ ] **Step 2: Test /gateway/workflow-run-status/{run_id}**

```bash
curl -s "https://api-staging.crewhubai.com/api/v1/gateway/workflow-run-status/<run-id>" \
  -H "X-Gateway-Key: $GATEWAY_KEY"
```

- [ ] **Step 3: Test /gateway/pending-workflow-deliveries**

```bash
curl -s "https://api-staging.crewhubai.com/api/v1/gateway/pending-workflow-deliveries" \
  -H "X-Gateway-Key: $GATEWAY_KEY"
```

- [ ] **Step 4: Test channel creation with workflow_id**

- [ ] **Step 5: Test insufficient credits rejection**

- [ ] **Step 6: Test daily limit enforcement**

---

### Task 14: E2E Testing — Frontend (parallel track 2)

- [ ] **Step 1: Open channel wizard, verify workflow dropdown in Step 3**
- [ ] **Step 2: Create Discord channel with workflow selected**
- [ ] **Step 3: Send /ask in Discord — verify agent task works (regression)**
- [ ] **Step 4: Send /workflow in Discord — verify workflow triggers**
- [ ] **Step 5: Wait for cron delivery of workflow result**
- [ ] **Step 6: Verify channel card shows workflow name + lifetime metrics**
- [ ] **Step 7: Send /workflow with insufficient credits — verify error message**

---

### Task 15: Merge to Production

- [ ] **Step 1: Merge staging to main**

```bash
git checkout main && git merge staging --no-edit && git push origin main
```

- [ ] **Step 2: Deploy CF Worker to production**

```bash
cd cloudflare && npx wrangler deploy gateway-worker.js --config wrangler-production.toml
```

- [ ] **Step 3: Verify production health**

```bash
curl -sf https://crewhub-gateway-production.arimatch1.workers.dev/health
```
