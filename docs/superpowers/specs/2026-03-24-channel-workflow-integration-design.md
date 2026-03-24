# Channel-Workflow Integration — Design Spec

**Date:** 2026-03-24
**Status:** Reviewed (v2 — blockers resolved)
**Author:** Claude + Arivoli
**Approach:** Gateway-Orchestrated (Approach A)
**Review:** Spec review passed — 5 blockers fixed, 7 warnings addressed

---

## 1. Problem Statement

Channels (Discord, Telegram, Slack) currently support only single-agent tasks. Users send a message, one agent processes it, one response comes back. This limits channels to simple Q&A interactions.

Workflows allow multi-agent pipelines — sequential steps, parallel execution, sub-workflows, supervisor patterns. But workflows are only accessible through the dashboard UI, not through messaging platforms.

**Goal:** Let channel users trigger multi-agent workflows via slash commands, with seamless adaptive delivery that handles both fast and long-running workflows.

---

## 2. User Experience

### 2.1 Command Routing

| Command | Platform | Behavior |
|---------|----------|----------|
| `/ask <message>` | Discord | Single-agent task (unchanged) |
| `/workflow <message>` | Discord | Triggers default workflow |
| `/workflow message:<msg> name:<name>` | Discord | Triggers named workflow from mappings |
| `<message>` | Telegram/Slack | Single-agent task (unchanged) |
| `!workflow <message>` | Telegram/Slack | Triggers default workflow |
| `!workflow:name <message>` | Telegram/Slack | Triggers named workflow from mappings |

### 2.2 Adaptive Delivery

**Fast path (workflow completes in < 25s):**
User sends `/workflow summarize this article` → sees "thinking..." → gets full result inline. Indistinguishable from a single-agent response.

**Slow path (workflow takes > 25s):**
User sends `/workflow research quantum computing` → sees ack message:
> "Processing your request through Research Pipeline (3 steps, ~5 credits)..."

1-30 minutes later, a new message arrives:
> **Research Pipeline** — completed in 2m 14s (4.5 credits)
>
> [final output]
>
> Your data is processed per our privacy notice: [url] — Messages retained 90 days.

### 2.3 Error Messages

**No workflow configured:**
> "No workflow configured for this channel. Use /ask instead, or ask the channel owner to connect a workflow."

**Insufficient credits:**
> "Insufficient credits for this workflow (estimated: 5 credits, available: 2.3). Top up at crewhubai.com/dashboard/credits"

**Workflow failed (stop mode):**
> "Sorry, your workflow couldn't be completed. (Error: step 2 — Analysis Agent timed out)"

**Partial results (continue mode):**
> "Completed 2/3 steps of Research Pipeline:
>
> **Research:** [output from step 1]
>
> **Analysis:** Failed — agent timed out
>
> **Summary:** [output from step 3]"

### 2.4 Channel Card (Enhanced)

```
CrewHub Agent              Active
Discord
Agent: AI Agency: Engineering
Workflow: Research Pipeline
────────────────────────────
142 messages   487.5 credits (total)
12 today       38.0 credits (today)
[Pause] [Configure]
```

### 2.5 Channel Stats Bar (Enhanced)

```
Total Channels: 3    Messages Today: 12    Credits Today: 38.0
                     Total Messages: 1,247  Total Credits: 2,891.5
```

---

## 3. Data Model Changes

### 3.1 ChannelConnection — New Fields

```
workflow_id: UUID | None (FK workflows.id)
  — Default workflow for /workflow command. Nullable.

workflow_mappings: dict | None
  — Named workflow shortcuts. Example:
    {"summarize": "uuid-1", "translate": "uuid-2", "research": "uuid-3"}
```

`agent_id` remains required — every channel needs a default agent for `/ask`.

### 3.2 WorkflowRun — New Fields

```
channel_connection_id: UUID | None (FK channel_connections.id)
  — Which channel triggered this run. Null for dashboard-triggered runs.

channel_chat_id: str | None
  — Platform chat/channel ID for result delivery. Stored so cron knows WHERE to send.
```

### 3.3 ChannelMessage — New Field

```
workflow_run_id: UUID | None (FK workflow_runs.id)
  — Links outbound message to its workflow run for audit trail.
```

### 3.4 Workflow — New Field

```
failure_mode: str (default "stop")
  — "stop": first step failure stops the workflow, user gets error.
  — "continue": failed steps skipped, user gets partial results.
```

### 3.5 Database Migration

Single migration adds all fields as nullable columns with FK constraints. No data migration needed — all new fields default to NULL, preserving existing behavior.

---

## 4. Architecture — Gateway-Orchestrated

### 4.1 Component Diagram

```
Discord/Telegram/Slack
        │
        ▼
  CF Worker Gateway
  ├── /ask → processMessage() / processDiscordInteraction()  [unchanged]
  ├── /workflow → processWorkflowMessage() / processDiscordWorkflow()  [NEW]
  └── cron (every 60s) → deliverPendingResponses()  [UPDATED]
        │
        ▼
  Backend API (FastAPI on HF Spaces)
  ├── /gateway/create-task              [unchanged]
  ├── /gateway/task-status/{id}         [unchanged]
  ├── /gateway/create-workflow-run      [NEW]
  ├── /gateway/workflow-run-status/{id} [NEW]
  ├── /gateway/pending-workflow-deliveries [NEW]
  └── /gateway/charge                   [unchanged, used by both]
        │
        ▼
  Workflow Execution Engine
  ├── execute_workflow()         [2 optional kwargs added]
  ├── pump_running_workflows()   [unchanged]
  └── _pump_single_run()         [failure_mode conditional added]
```

### 4.2 Key Principle

The workflow execution engine is **minimally extended** — two optional kwargs on `execute_workflow()` for channel context, and one conditional branch in `_pump_single_run()` for the `failure_mode` feature. The engine's core lifecycle (pump, sync, dispatch) is unchanged.

### 4.3 Architecture Decisions (from spec review)

**AD-1: Channel fields on WorkflowRun** — `execute_workflow()` gains two optional kwargs: `channel_connection_id` and `channel_chat_id`. These are passed through to the `WorkflowRun` constructor. The gateway endpoint sets them; dashboard-triggered runs pass `None`. This is a 2-line change to the engine signature.

**AD-2: Cron re-delivery prevention** — The `GatewayLogMessageRequest` schema gains an optional `workflow_run_id` field. When the cron logs an outbound workflow delivery, it includes the `run_id`. The `/gateway/pending-workflow-deliveries` endpoint filters out runs that already have an outbound `ChannelMessage` with matching `workflow_run_id`. This prevents duplicate delivery.

**AD-3: Discord slow-path delivery uses bot token, not interaction followup** — Discord interaction tokens expire in 15 minutes. For slow-path workflows (>25s), the cron stores `chat_id` (channel ID) in the system message, and delivers via `sendDiscord(botToken, chatId, text)` — a regular bot message, not an interaction edit. The ack message (within 15 min) uses the interaction followup; the final result (possibly >15 min later) uses the bot token.

**AD-4: `_estimate_cost()` access** — The gateway endpoint imports `WorkflowExecutionService` and calls `_estimate_cost()` on a loaded `Workflow` object. This is an existing private method made accessible via the service class — no duplication of cost logic.

**AD-5: `failure_mode` modifies `_pump_single_run()`** — When `failure_mode = "continue"` is read from the workflow snapshot, `_pump_single_run()` skips the early-return-on-failure block and instead marks failed steps as terminal, then advances to the next group. `failure_mode` is captured in the `workflow_snapshot` at run creation time (immutable for in-flight runs).

**AD-6: Discord named workflows via option parameter, not colon syntax** — Discord slash command names cannot contain colons. Named workflows use a second optional `name` parameter on the `/workflow` command: `/workflow message:hello name:translate`. Telegram/Slack continue using `!workflow:name` prefix (free-text, no restriction). If `name` is omitted, the default `workflow_id` is used.

**AD-7: `GatewayConnectionResponse` includes workflow fields** — The schema and `get_connection` endpoint return `workflow_id`, `workflow_mappings`, and `workflow_name` so the CF Worker can resolve commands without extra API calls.

**AD-8: `workflow_mappings` values are authorization-checked** — The backend validates each workflow_id in `workflow_mappings` at channel create/update time: each must exist and be owned by the channel owner or be public. This prevents credential-stuffing arbitrary workflow IDs.

**AD-9: Discord cron skip is conditional** — The existing `if (platform === "discord") continue;` in the cron handler is updated to: skip Discord for TASK deliveries (interaction tokens may have expired), but DO deliver Discord WORKFLOW results (using bot token + channel ID).

**AD-10: Daily limit race condition accepted** — Concurrent workflow submissions may both pass the upfront balance check and collectively exceed the daily limit. This is a known limitation, accepted because: (a) the daily limit is a soft cap, not a billing guarantee; (b) adding credit reservation would significantly complicate the workflow engine; (c) the per-step charge still enforces balance sufficiency at each step.

**AD-11: Sub-workflow depth safeguard** — Channel-triggered workflows inherit the existing depth-10 limit. The daily credit limit is the primary safeguard against runaway costs from deeply nested sub-workflows. No additional channel-specific depth limit is added.

---

## 5. New Gateway API Endpoints

### 5.1 POST `/gateway/create-workflow-run`

**Request:**
```json
{
  "connection_id": "uuid",
  "workflow_id": "uuid",
  "message": "user input text",
  "chat_id": "platform-specific-chat-id"
}
```

**Response (success):**
```json
{
  "workflow_run_id": "uuid",
  "status": "running",
  "estimated_credits": 5.0,
  "step_count": 3,
  "workflow_name": "Research Pipeline"
}
```

**Response (error):**
```json
{
  "workflow_run_id": null,
  "status": "error",
  "error": "insufficient_balance",
  "estimated_credits": 5.0
}
```

**Logic:**
1. Validate workflow exists, is owned by channel owner or is public
2. Estimate credits via `WorkflowExecutionService._estimate_cost()`
3. Check balance and daily limit
4. Call `execute_workflow()` with `channel_connection_id` and `channel_chat_id`
5. Return run metadata

### 5.2 GET `/gateway/workflow-run-status/{run_id}`

**Response:**
```json
{
  "status": "completed",
  "final_output": "concatenated step outputs",
  "step_count": 3,
  "steps_completed": 3,
  "total_credits_charged": 4.5,
  "error": null,
  "workflow_name": "Research Pipeline"
}
```

**Logic:** Query WorkflowRun + step_runs. Concatenate completed step outputs. Count completed vs total steps.

### 5.3 GET `/gateway/pending-workflow-deliveries`

**Response:**
```json
{
  "deliveries": [
    {
      "run_id": "uuid",
      "connection_id": "uuid",
      "chat_id": "platform-chat-id",
      "platform": "discord",
      "status": "completed",
      "final_output": "result text",
      "workflow_name": "Research Pipeline",
      "total_credits_charged": 4.5,
      "failure_mode": "stop"
    }
  ]
}
```

**Logic:** Query WorkflowRun where:
- `channel_connection_id IS NOT NULL`
- `status IN ("completed", "failed")`
- Not yet delivered (no outbound ChannelMessage with matching `workflow_run_id`)

---

## 6. CF Worker Changes

### 6.1 Slash Command Registration

`/auto-register-discord` registers both commands:
```javascript
[
  { name: "ask", description: "Ask the AI agent a question", type: 1,
    options: [{ name: "message", description: "Your question", type: 3, required: true }] },
  { name: "workflow", description: "Run a multi-agent workflow", type: 1,
    options: [
      { name: "message", description: "Your request", type: 3, required: true },
      { name: "name", description: "Workflow name (optional, uses default if omitted)", type: 3, required: false }
    ] }
]
```

### 6.2 New Function: `processDiscordWorkflow()`

```
1. Get connection config
2. Auto-activate pending channel
3. Check blocked users
4. Parse message: extract workflow name prefix if present
5. Resolve workflow_id from mappings or default
6. If no workflow configured → send error via interaction followup
7. Call /gateway/create-workflow-run
8. If error → send error message
9. Log inbound message (NULL text — GDPR)
10. Poll /gateway/workflow-run-status/{run_id} for 25s
11. FAST: completed → format output → send via interaction followup → log outbound
12. SLOW: send ack "Processing through [name] (N steps, ~X credits)..."
    → store system message "wfrun:{run_id}" for cron
```

### 6.3 New Function: `processWorkflowMessage()`

Same logic as above but for Telegram/Slack. Uses `sender.send()` instead of interaction followup.

### 6.4 Updated: Message Routing

**Discord:** `handleDiscordWebhook()` routes by `body.data.name`:
- `"ask"` → `processDiscordInteraction()` (existing)
- `"workflow"` → `processDiscordWorkflow()` (new)

**Telegram/Slack:** `processMessage()` checks text prefix:
- Starts with `!workflow` → `processWorkflowMessage()` (new)
- Otherwise → existing agent task flow

### 6.5 Updated: Cron Delivery

`deliverPendingResponses()` adds workflow delivery:

```
1. [Existing] Scan system messages for pending task deliveries
2. [New] Call /gateway/pending-workflow-deliveries
3. For each delivery:
   a. Format output (add workflow name header if multi-step)
   b. Append privacy notice footer
   c. Send to platform via appropriate sender
   d. Log outbound message with workflow_run_id
```

### 6.6 Output Formatting

**Single final output (most workflows):**
```
[response text]

Your data is processed per our privacy notice: [url] — Messages retained 90 days.
```

**Multi-step with labels (for transparency):**
```
Research Pipeline — completed in 2m 14s (4.5 credits)

[concatenated step outputs]

Your data is processed per our privacy notice: [url] — Messages retained 90 days.
```

---

## 7. Credit Charging

### 7.1 Flow

1. CF Worker calls `/gateway/create-workflow-run` with `connection_id`
2. Backend estimates cost: `sum(step.skill.avg_credits for step in workflow.steps)`
3. Backend checks: `user.available_balance >= estimated_cost`
4. Backend checks: `daily_usage + estimated_cost <= daily_credit_limit`
5. If either fails → return error, CF Worker sends error to user
6. Workflow executes — each step charges actual credits via existing workflow engine
7. `WorkflowRun.total_credits_charged` tallied on completion
8. Cron delivery logs `credits_charged` on outbound ChannelMessage

### 7.2 Daily Limit Enforcement

The daily limit check uses the ESTIMATED cost at workflow creation time. This prevents starting workflows that would exceed the limit. Actual charges may differ slightly (under or over estimate) — this is acceptable as the estimate is a soft cap, not a hard reservation.

### 7.3 Agent/Workflow Credit Costs

Credits are based on the agent's configured costs (from `skill.avg_credits`), not a flat rate. A workflow with 3 steps using agents that cost 2, 1, and 3 credits respectively would estimate 6 credits total.

---

## 8. Compliance

### 8.1 GDPR — Data Controller Model

The channel owner is the data controller. Their `privacy_notice_url` covers all processing, including multi-agent workflows. No per-agent disclosure needed.

### 8.2 Third-Party Agent Warning

When a channel owner selects a workflow that includes agents owned by OTHER developers:

**Backend check:** Compare `workflow.steps[].agent.owner_id` against channel `owner_id`. Return `third_party_agents: true` if any differ.

**Frontend display:**
> "This workflow uses agents from other developers. Your privacy notice must disclose this data sharing. By connecting this workflow, you confirm your privacy notice covers all agents involved."

Channel owner must acknowledge before saving.

### 8.3 Audit Trail

Full chain: `ChannelMessage.workflow_run_id` → `WorkflowRun.step_runs` → `WorkflowStepRun.task_id` → individual Task artifacts.

Every credit charge goes through `/gateway/charge` with SOC 2 CC7.2 audit logging.

### 8.4 Encryption

`workflow_mappings` stored in channel `config` dict — not in `_SENSITIVE_CONFIG_KEYS` since workflow IDs are not secrets. `workflow_id` is a standard FK column.

### 8.5 HIPAA

Same healthcare disclaimer applies. Workflows don't change the PHI exclusion.

---

## 9. Error Handling

### 9.1 Failure Modes

Configurable per workflow via `failure_mode` field:

| Mode | Behavior | User sees |
|------|----------|-----------|
| `"stop"` (default) | First step failure stops execution | Error message with failed step name |
| `"continue"` | Failed steps skipped, others continue | Partial results with failure note |

### 9.2 Timeout Handling

| Level | Default | Behavior |
|-------|---------|----------|
| Workflow | 1800s (30 min) | Run marked failed, cron delivers error |
| Step | 120s (2 min) | Step marked failed, triggers failure_mode logic |
| CF Worker poll | 25s | Switches to slow path (ack + cron) |

### 9.3 Credit Handling on Failure

- Completed steps: charged (credits already deducted)
- Failed steps: not charged
- Unexecuted steps (stop mode): not charged
- No refunds needed — credits are charged per-step as they complete, not reserved upfront

---

## 10. Frontend Changes

### 10.1 Channel Wizard — Step 3 Enhancement

```
Agent (for /ask)             [dropdown — required]
─────────────────────────────────────────────────
Workflow (for /workflow)      [dropdown — optional]
Named Workflows              [+ Add: name → workflow dropdown]
```

When a workflow is selected that contains third-party agents, show compliance warning banner.

### 10.2 Channel Card — Enhanced Metrics

Display `agent_name`, `workflow_name`, lifetime message count, lifetime credit total, plus existing daily metrics.

### 10.3 Channel Stats Bar

Add lifetime totals row below daily totals.

### 10.4 Channel Configure Page

New "Workflow" section:
- Connected workflow name + step count
- Named workflow mappings editor (add/remove)
- Recent workflow runs from this channel (last 10)

---

## 11. Database Migration

Single migration file. All new columns are nullable — zero impact on existing data.

```python
# channel_connections
op.add_column("channel_connections", sa.Column("workflow_id", Uuid, sa.ForeignKey("workflows.id"), nullable=True))
op.add_column("channel_connections", sa.Column("workflow_mappings", JSON, nullable=True))

# workflow_runs
op.add_column("workflow_runs", sa.Column("channel_connection_id", Uuid, sa.ForeignKey("channel_connections.id"), nullable=True))
op.add_column("workflow_runs", sa.Column("channel_chat_id", sa.String(200), nullable=True))

# channel_messages
op.add_column("channel_messages", sa.Column("workflow_run_id", Uuid, sa.ForeignKey("workflow_runs.id"), nullable=True))

# workflows
op.add_column("workflows", sa.Column("failure_mode", sa.String(20), server_default="stop", nullable=False))
```

---

## 12. Testing Strategy

### 12.1 Unit Tests (12)

- Gateway endpoint: create workflow run (success, insufficient credits, daily limit, not found)
- Gateway endpoint: workflow run status (running, completed, failed stop, failed continue)
- Gateway endpoint: pending deliveries (filters correctly)
- Channel creation with workflow_id + mappings
- Third-party agent detection
- Channel analytics lifetime aggregation

### 12.2 Integration Tests (10)

- Discord /workflow slash command → creates run
- Discord /workflow:name → resolves from mappings
- Discord /workflow with no workflow → error message
- Telegram !workflow prefix → triggers workflow
- Fast path: inline delivery < 25s
- Slow path: ack message + system message stored
- Cron workflow delivery → sends result to user
- Cron failed workflow delivery → sends error
- Partial failure (continue mode) → partial output
- Credit charging per step with daily limit

### 12.3 E2E Test (7 steps)

1. Create channel with workflow via wizard
2. Send `/ask` via Discord (regression — unchanged)
3. Send `/workflow` via Discord (triggers workflow)
4. Wait for completion (cron delivers result)
5. Send `/workflow:name` (named workflow resolves)
6. Check channel analytics (messages + credits updated)
7. Trigger workflow with insufficient credits (error returned)

---

## 13. Files Modified

| File | Changes |
|------|---------|
| `src/models/channel.py` | Add workflow_id, workflow_mappings fields |
| `src/models/workflow.py` | Add channel_connection_id, channel_chat_id to WorkflowRun. Add failure_mode to Workflow. Add failure_mode to workflow_snapshot |
| `src/schemas/channel.py` | Update ChannelCreate/Update/Response, GatewayConnectionResponse (add workflow_id, workflow_mappings, workflow_name, privacy_notice_url), GatewayLogMessageRequest (add workflow_run_id) |
| `src/api/gateway.py` | 3 new endpoints + update connection response to include workflow fields |
| `src/api/channels.py` | Channel analytics: lifetime totals query. Workflow runs list per channel |
| `src/services/channel_service.py` | Validation for workflow_id, workflow_mappings auth check, third-party agent detection |
| `src/services/workflow_execution.py` | Add channel_connection_id + channel_chat_id kwargs to execute_workflow(). Add failure_mode conditional to _pump_single_run(). Capture failure_mode in workflow_snapshot |
| `cloudflare/gateway-worker.js` | Workflow routing, processDiscordWorkflow, processWorkflowMessage, cron update (conditional Discord skip), slash command registration (/workflow with name option) |
| `frontend/.../channel-wizard.tsx` | Workflow selection in Step 3, named mappings editor, third-party warning |
| `frontend/.../channels page` | Enhanced channel cards with agent_name, workflow_name, lifetime totals |
| `alembic/versions/0XX_*.py` | New migration (ordered: channel_connections → workflow_runs → channel_messages → workflows) |
| `tests/` | Unit + integration + E2E tests |

---

## 14. Implementation Notes

- **Output truncation:** `ChannelMessage.message_text` is `String(2000)`. Multi-step workflow output may exceed this. The full output is sent to the user (chunked if needed), but only the first 2000 chars are stored in the audit log.
- **Workflow dropdown API:** The channel wizard's workflow dropdown calls `GET /workflows/?owner_id={user_id}` to populate options. This endpoint already exists and requires authentication.
- **Credit estimates:** `_estimate_cost()` returns integers (rounds per-step). The `estimated_credits` field in API responses reflects this — fractional credits are not estimated, only actual charges are fractional.
- **Recent workflow runs:** The channel configure page needs `GET /channels/{id}/workflow-runs` — a new lightweight endpoint returning the last 10 `WorkflowRun` records where `channel_connection_id` matches.

---

## 15. Out of Scope

- Webhook callback mode (real-time push on completion) — future enhancement
- Step-by-step progress updates to user — future enhancement
- LLM-based routing (auto-detect if message needs agent or workflow) — future enhancement
- Workflow creation from chat commands — use dashboard
- Message retention cleanup job — separate initiative
