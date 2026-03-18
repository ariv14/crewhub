# Multi-Channel Gateway — Design Spec

> **Date:** 2026-03-18
> **Status:** Approved
> **Scope:** Multi-channel messaging gateway for CrewHub — Telegram, Slack, Discord, Teams, WhatsApp

---

## Overview

Enable developers to connect their CrewHub agents to messaging platforms (Telegram, Slack, Discord, Teams, WhatsApp). End users interact with agents via messaging apps without needing a CrewHub account. Developers pay credits per message — the same API-as-a-service model as Twilio.

---

## Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Business model | Developer-pays credits | End users don't need CrewHub accounts |
| Shared CrewHub bot | No — developer bots only | Cleaner model, website is the discovery layer |
| Setup UI | Settings wizard + API | Wizard for easy setup, API for automation |
| Gateway hosting | Separate HF Space (Python) | Isolated from main backend, free tier |
| Platform connections | Webhook-first (all platforms) | Stateless, reliable, handles restarts gracefully |
| WhatsApp pricing | 2 credits per 24h conversation window | Covers Meta Cloud API cost with margin |
| Budget controls | Daily limits + low-balance alerts | Prevents runaway costs, auto-topup optional later |
| Account linking | Not needed — developer's bot, developer pays | End users are anonymous platform_user_ids |
| Credit tracking | Computed from SUM(channel_messages) | No race conditions, no daily reset cron needed |
| Discord v1 | Interactions endpoint (webhook) not WebSocket | Simpler, stateless, defer WebSocket gateway to v2 |

---

## 1. Data Model

### 1.1 channel_connections

```python
class ChannelConnection(Base):
    __tablename__ = "channel_connections"

    id                    UUID PK
    owner_id              UUID FK → users.id (developer)
    platform              String(20) — telegram | slack | discord | teams | whatsapp
    platform_bot_id       String(200) nullable — platform's ID for this bot
    bot_token             String encrypted — platform bot token (envelope encryption, see §2.5)
    webhook_secret        String encrypted nullable — platform webhook signing secret (Slack signing secret, WhatsApp app secret, etc.)
    bot_name              String(200) — display name
    agent_id              UUID FK → agents.id
    skill_id              UUID FK → agent_skills.id nullable (null = auto-select via suggest)
    status                String(20) — active | paused | disconnected | pending
    paused_reason         String(50) nullable — manual | credit_exhausted | daily_limit | token_expired | rate_limited
    daily_credit_limit    Integer nullable — optional daily budget cap
    low_balance_threshold Integer default 20 — warn when account credits drop below
    pause_on_limit        Boolean default True — auto-pause when daily limit hit
    webhook_url           String nullable — registered webhook URL
    config                JSON nullable — platform-specific config (WhatsApp phone, Slack workspace, etc.)
    error_message         Text nullable — last error for debugging
    last_active_at        DateTime nullable — last processed message
    gateway_instance_id   String nullable — for future horizontal scaling
    created_at            DateTime
    updated_at            DateTime

Indexes:
    ix_channel_connections_owner ON (owner_id)
    ix_channel_connections_platform_status ON (platform, status)
```

### 1.2 channel_messages

```python
class ChannelMessage(Base):
    __tablename__ = "channel_messages"

    id                        UUID PK
    connection_id             UUID FK → channel_connections.id
    platform_user_id          String(200) — sender's platform ID
    platform_message_id       String(200) — platform's message ID (deduplication)
    platform_chat_id          String(200) nullable — conversation thread
    direction                 String(10) — inbound | outbound | system
    message_text              Text
    media_type                String(20) nullable — text | image | file | voice
    task_id                   UUID FK → tasks.id nullable
    credits_charged           Numeric(12, 4) default 0  — matches existing credit system precision
    response_time_ms          Integer nullable — latency tracking
    error                     Text nullable — outbound delivery failure
    whatsapp_window_expires_at DateTime nullable — 24h conversation window expiry
    created_at                DateTime

Indexes:
    ix_channel_messages_connection_created ON (connection_id, created_at)
    ux_channel_messages_dedup UNIQUE ON (connection_id, platform_message_id, direction)
```

### 1.3 Alembic Migration

Single migration: `029_multi_channel_gateway.py`
- Create `channel_connections` table
- Create `channel_messages` table
- All indexes

---

## 2. Gateway Service

### 2.1 Architecture

```
Developer's Customers → Platform webhooks → Gateway (HF Space) → CrewHub API → Agent → Response → Platform

gateway/ (arimatch1/crewhub-gateway HF Space)
  adapters/
    base.py              — AbstractPlatformAdapter
    telegram.py          — Telegram Bot API (setWebhook, sendMessage)
    slack.py             — Slack Events API (webhook verification, chat.postMessage)
    discord.py           — Discord Interactions (webhook verification, followup messages)
    teams.py             — Bot Framework (webhook, activity handling)
    whatsapp.py          — Meta Cloud API (webhook verification, messages endpoint)
  billing.py             — atomic credit charge via CrewHub API
  dedup.py               — platform_message_id deduplication
  rate_limiter.py        — 3-layer rate limiting
  main.py                — FastAPI app
  config.py              — settings (CrewHub API URL, service account key)
```

### 2.2 Message Flow (Async Callback Pattern)

**CRITICAL:** All messaging platforms require webhook response within 3-5 seconds. The gateway MUST acknowledge immediately and process asynchronously. Never block the webhook handler waiting for agent completion.

```python
# PHASE 1: Immediate webhook handler (must return within 3 seconds)
async def handle_webhook(platform, connection_id, request):
    # 1. Parse inbound message via platform adapter
    adapter = get_adapter(platform)
    message = adapter.parse_inbound(request)

    # 2. Verify webhook signature (platform-specific)
    if not adapter.verify_webhook(request, connection.webhook_secret):
        return Response(status_code=401)

    # 3. Deduplicate via DB unique constraint
    if await is_duplicate(connection_id, message.platform_message_id):
        return adapter.ack_response()

    # 4. Rate limit (per-end-user: 10 msg/min, in-memory best-effort)
    if is_rate_limited(message.platform_user_id):
        return adapter.ack_response()

    # 5. Acknowledge immediately — platform gets 200 OK within 1 second
    #    Dispatch processing as background task
    asyncio.create_task(process_message(platform, connection_id, message))
    return adapter.ack_response()


# PHASE 2: Background processing (runs after webhook returns)
async def process_message(platform, connection_id, message):
    adapter = get_adapter(platform)
    connection = await get_connection(connection_id)  # cached, 60s TTL

    # 1. Check daily credit limit
    today_usage = await get_today_usage(connection_id)  # SUM from channel_messages
    if connection.daily_credit_limit and today_usage >= connection.daily_credit_limit:
        if connection.pause_on_limit:
            await pause_connection(connection_id, "daily_limit")
        await adapter.send_message(message.chat_id, "Service paused — daily limit reached.")
        return

    # 2. Check developer balance
    balance = await crewhub_api.get_balance(connection.owner_id)
    estimated_cost = agent_credits + (2 if platform == "whatsapp" and not within_window(message) else 0)
    if balance < estimated_cost:
        await pause_connection(connection_id, "credit_exhausted")
        await adapter.send_message(message.chat_id, "Service temporarily unavailable.")
        return

    # 3. Create task with callback URL
    #    The callback URL tells CrewHub to POST the result back to the gateway
    #    when the agent finishes — no polling needed.
    callback_url = f"{GATEWAY_URL}/internal/task-callback/{connection_id}/{message.platform_chat_id}"
    task = await crewhub_api.create_task(
        agent_id=connection.agent_id,
        skill_id=connection.skill_id,
        message=message.text,
        client_user_id=connection.owner_id,
        callback_url=callback_url,
        idempotency_key=message.platform_message_id,  # prevents double task creation
    )

    # 4. Log inbound message
    await log_message(connection_id, message, task_id=task.id, direction="inbound")

    # 5. Optional: send "typing" indicator to platform while agent works
    await adapter.send_typing(message.chat_id)


# PHASE 3: Callback handler (called by CrewHub when task completes)
async def handle_task_callback(connection_id, chat_id, request):
    task_result = parse_callback(request)
    connection = await get_connection(connection_id)
    adapter = get_adapter(connection.platform)

    # 1. Send agent response to platform
    await adapter.send_message(chat_id, task_result.text)

    # 2. Log outbound message + credits
    await log_message(
        connection_id, task_result,
        task_id=task_result.task_id,
        direction="outbound",
        credits_charged=task_result.credits_used,
        response_time_ms=task_result.latency_ms,
    )
```

**Why this works:** The existing `task.callback_url` field in `task_broker.py` already supports POST-back when a task completes. The gateway registers its callback URL during task creation. When the agent finishes (could take 5-120 seconds), CrewHub POSTs the result to the gateway, which then sends it to the user's chat. No polling, no timeout, no blocked webhook handler.

### 2.3 Platform Adapter Interface

```python
class AbstractPlatformAdapter:
    def verify_webhook(self, request) -> bool
    def parse_inbound(self, request) -> NormalizedMessage
    async def send_message(self, chat_id, text, media=None) -> bool
    async def send_typing(self, chat_id) -> None  # typing indicator while agent works
    async def register_webhook(self, connection, webhook_url) -> bool
    async def deregister_webhook(self, connection) -> bool
    def ack_response(self) -> Response  # platform-specific 200 acknowledgment
```

### 2.4 Rate Limiting (3 layers)

**Note:** In-memory rate limiting is best-effort — clears on gateway restart. The DB unique constraint on `(connection_id, platform_message_id, direction)` is the authoritative dedup guarantee. Rate limiting is an optimization to reduce unnecessary API calls.

```
Layer 1: Platform API limits (enforced by gateway)
  Telegram: 30 msg/sec per bot, 20 msg/min per chat
  Discord: 50 requests/sec per bot
  Slack: 1 msg/sec per channel
  WhatsApp: 80 msg/sec (tier dependent)

Layer 2: Per-developer (enforced by CrewHub API)
  60 messages/min across all bots (configurable)
  Daily credit limit (per connection)

Layer 3: Per-end-user (enforced by gateway)
  10 messages/min per platform_user_id (configurable in connection config)
  In-memory counters with TTL (no Redis needed at this scale)
```

### 2.5 Envelope Encryption for Bot Tokens

Bot tokens use envelope encryption to support key rotation without re-entering tokens:

```
Per-connection:
  1. Generate random 256-bit data encryption key (DEK)
  2. Encrypt bot_token with DEK (Fernet)
  3. Encrypt DEK with master key (derived from SECRET_KEY + key_version)
  4. Store: encrypted_token + encrypted_DEK + key_version

On read:
  1. Read key_version → derive master key for that version
  2. Decrypt DEK with master key
  3. Decrypt bot_token with DEK

On SECRET_KEY rotation:
  1. Migration script reads all connections
  2. Decrypts each DEK with OLD master key
  3. Re-encrypts each DEK with NEW master key
  4. Updates key_version
  → Bot tokens themselves are NOT re-encrypted (DEKs protect them)
```

Column format: `bot_token` stores `{key_version}:{encrypted_dek}:{encrypted_token}` as a single string. The `webhook_secret` column uses the same format.

### 2.6 Async Task Callback

The gateway registers a callback URL when creating tasks. CrewHub's existing `task.callback_url` field (in `task_broker.py`) POSTs the result back when the agent completes.

Gateway callback endpoint: `POST /internal/task-callback/{connection_id}/{chat_id}`

This is an internal endpoint on the gateway (not exposed publicly). The CrewHub backend calls it from the task broker after task completion. Secured by a shared HMAC secret between CrewHub and the gateway.

### 2.7 Known Limitations (v1)

- **No conversation history** — each message is independent. Agents don't have context from prior messages. Add conversation threading in v2.
- **Text only** — media messages (images, files, voice) are rejected with "Text messages only, please." Add media handling in v2.
- **No typing indicators on all platforms** — some adapters may not support `send_typing`. Best-effort.
- **Phase 1 ships UI without gateway** — channels show "Pending" status until Phase 2 gateway deploys. Setup wizard shows a note: "Your channel is registered. The messaging gateway is being deployed — your bot will go live within 48 hours."

### 2.8 Test Endpoint Design

`POST /api/v1/channels/{id}/test` sends a test message through the full pipeline:
1. Gateway sends "Hello from CrewHub! Testing your agent connection." to the bot's own chat (using `getMe` + `sendMessage` on Telegram, or the bot's DM channel on Discord/Slack)
2. If the agent responds, returns `{ success: true, response: "...", latency_ms: 123 }`
3. If timeout (30s) or error, returns `{ success: false, error: "Agent did not respond within 30 seconds" }`
4. Only works when gateway is deployed (Phase 2+). In Phase 1, returns `{ success: false, error: "Gateway not yet deployed" }`

---

## 3. Backend API Endpoints

### 3.1 Developer-facing (existing auth)

```
POST   /api/v1/channels/                  — create connection
GET    /api/v1/channels/                  — list my connections (with today's stats computed)
GET    /api/v1/channels/{id}              — get connection + stats
PATCH  /api/v1/channels/{id}              — update config/limits/status
DELETE /api/v1/channels/{id}              — remove connection
POST   /api/v1/channels/{id}/rotate-token — rotate bot token
GET    /api/v1/channels/{id}/analytics    — message/credit charts (7/30 day)
POST   /api/v1/channels/{id}/test         — send test message through pipeline
```

### 3.2 Gateway-facing (service account auth)

```
POST   /api/v1/gateway/charge                      — atomic credit charge for a message
GET    /api/v1/gateway/connections/{connection_id}  — single connection lookup with decrypted token (NOT bulk)
POST   /api/v1/gateway/heartbeat                    — gateway reports per-connection health
POST   /api/v1/gateway/log-message                  — log a channel message
POST   /api/v1/gateway/task-callback                — async callback when agent task completes (see §2.6)
```

Service account: new `key_type = "service"` on API key model. Scoped to gateway operations only.

**Security:** Gateway fetches connection config on-demand per `connection_id` with a 60s TTL cache — never bulk-fetches all tokens. Limits blast radius of gateway compromise to connections actively being served.

### 3.3 Gateway webhook receivers

```
POST   /gateway/webhook/telegram/{connection_id}
POST   /gateway/webhook/slack/{connection_id}
POST   /gateway/webhook/discord/{connection_id}
POST   /gateway/webhook/teams/{connection_id}
POST   /gateway/webhook/whatsapp/{connection_id}
GET    /gateway/webhook/whatsapp/{connection_id}   — Meta verification challenge
```

---

## 4. Frontend — Settings Channels Tab

### 4.1 Tab Integration

5th tab on Settings page: `Profile | API Keys | LLM Keys | Builder | Channels`

### 4.2 Channel Cards

Each connected channel shows as a card:
- Platform icon + name + bot name + status badge
- Agent → Skill mapping
- Today's stats: messages, credits used, daily limit
- Last message time
- Actions: Pause/Resume, Edit, overflow menu (Analytics, Test, Delete)

Status badges:
- `● Active` (green) — working
- `⏸ Paused` (yellow) — manual or daily limit or credits exhausted
- `⚠ Disconnected` (red) — token invalid
- `○ Pending` (gray) — setup in progress

### 4.3 Setup Wizard (4 steps in Dialog)

**Step 1:** Choose platform — 5 cards (Telegram, Slack, Discord, Teams, WhatsApp with premium badge)

**Step 2:** Platform credentials — token fields + collapsible step-by-step guide with external link. WhatsApp shows pricing acknowledgment checkbox.

**Step 3:** Agent/skill selection + budget controls — agent dropdown (developer's agents only), skill dropdown, daily credit limit, low-balance threshold, pause-on-limit toggle

**Step 4:** Confirmation — summary card, webhook URL with copy button, "Send Test Message" button. For auto-registered platforms (Telegram, Discord): "Webhook registered automatically." For manual platforms (Slack, Teams, WhatsApp): "Paste this webhook URL in your platform settings."

### 4.4 Channel Analytics (expandable accordion)

- Message volume chart (7 days)
- Credit burn chart (7 days)
- Top users by message count (anonymized platform IDs)
- Cost breakdown (agent processing + platform surcharge)

### 4.5 WhatsApp Premium

- `💎 PREMIUM` badge on WhatsApp channel cards
- "2 credits/msg surcharge" shown in setup wizard and cost breakdown
- 24h window explanation in setup guide

---

## 5. Frontend File Structure

```
types/channel.ts                          — TypeScript types
lib/api/channels.ts                       — API client (8 functions)
lib/hooks/use-channels.ts                 — React Query hooks (7 hooks)
app/(marketplace)/dashboard/settings/
  channels-tab.tsx                        — Tab content: channel list + empty state
  channel-card.tsx                        — Individual card component
  channel-analytics.tsx                   — Expandable charts
  channel-wizard.tsx                      — 4-step wizard orchestrator
  channel-wizard-steps/
    platform-select.tsx                   — Step 1
    platform-credentials.tsx              — Step 2 + platform guide
    agent-skill-select.tsx                — Step 3 + budget
    confirmation.tsx                      — Step 4 + webhook URL
  channel-edit-sheet.tsx                  — Edit slide-over
  platform-guides.ts                      — Static platform data
```

13 new frontend files, ~1,310 lines. 1 existing file modified (settings page tab list).

---

## 6. Implementation Phases

### Phase 1: Data Model + CRUD API + Settings UI
- Migration 029
- ChannelConnection + ChannelMessage models
- CRUD API endpoints (/api/v1/channels/*)
- Frontend: Channels tab, setup wizard, channel cards
- No gateway yet — channels are "pending" status until gateway connects

### Phase 2: Gateway Service + Telegram
- Deploy arimatch1/crewhub-gateway HF Space
- Gateway main.py + config + billing + dedup + rate_limiter
- Telegram adapter (webhook-based)
- Service account auth
- End-to-end test: Telegram → Gateway → CrewHub API → Agent → Response

### Phase 3: Slack + Discord Adapters
- Slack adapter (Events API webhook)
- Discord adapter (Interactions endpoint)
- Webhook verification for both

### Phase 4: Teams + WhatsApp (Premium)
- Teams adapter (Bot Framework webhook)
- WhatsApp adapter (Meta Cloud API)
- WhatsApp 24h window tracking + surcharge billing
- Meta webhook verification (GET challenge)

### Phase 5: Analytics + Alerts
- Channel analytics endpoint + frontend charts
- Low-balance email/webhook notifications
- Daily usage reports for developers

---

## 7. Testing Strategy

### Backend Tests (pytest)
- Channel CRUD operations (create, list, update, delete)
- Atomic credit charging (race condition prevention)
- Message deduplication (unique constraint)
- Daily limit enforcement
- Service account auth scoping

### Gateway Tests
- Per-adapter webhook parsing (Telegram, Slack, Discord, Teams, WhatsApp)
- Rate limiting (all 3 layers)
- Credit exhaustion handling
- Webhook registration/deregistration lifecycle

### E2E Tests (staging)
- Create Telegram channel → send message → receive response
- Daily limit → bot pauses → increase limit → bot resumes
- Token rotation → gateway reconnects
- WhatsApp surcharge billing accuracy

---

## 8. Cost Analysis

| Item | Cost |
|------|------|
| Gateway HF Space | $0 (free tier) |
| Telegram Bot API | $0 |
| Slack Events API | $0 |
| Discord Interactions | $0 |
| Teams Bot Framework | $0 |
| WhatsApp Cloud API | $0.03-0.08/conversation (covered by 2 credit surcharge) |
| **Total platform cost** | **$0 + WhatsApp pass-through** |

Developer revenue model: developers buy credits ($5-70 packs), credits consumed per message. CrewHub takes 10% platform fee on agent tasks + 100% of WhatsApp surcharge.
