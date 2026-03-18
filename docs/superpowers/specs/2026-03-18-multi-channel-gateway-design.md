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
    bot_token             String encrypted — platform bot token (Fernet, per-developer derived key)
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
    credits_charged           Float default 0
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

### 2.2 Message Flow

```python
async def handle_webhook(platform, connection_id, request):
    # 1. Parse inbound message via platform adapter
    adapter = get_adapter(platform)
    message = adapter.parse_inbound(request)

    # 2. Deduplicate
    if await is_duplicate(connection_id, message.platform_message_id):
        return adapter.ack_response()

    # 3. Rate limit (per-end-user: 10 msg/min)
    if is_rate_limited(message.platform_user_id):
        return adapter.ack_response()

    # 4. Get connection config
    connection = await get_connection(connection_id)

    # 5. Check daily credit limit
    today_usage = await get_today_usage(connection_id)
    if connection.daily_credit_limit and today_usage >= connection.daily_credit_limit:
        if connection.pause_on_limit:
            await pause_connection(connection_id, "daily_limit")
            return adapter.send_message(message.chat_id, "Service paused — daily limit reached.")
        return adapter.ack_response()  # silently drop

    # 6. Check developer balance
    balance = await crewhub_api.get_balance(connection.owner_id)
    estimated_cost = agent_credits + (2 if platform == "whatsapp" and not within_window(message) else 0)
    if balance < estimated_cost:
        await pause_connection(connection_id, "credit_exhausted")
        return adapter.send_message(message.chat_id, "Service temporarily unavailable.")

    # 7. Create task via CrewHub API
    task = await crewhub_api.create_task(
        agent_id=connection.agent_id,
        skill_id=connection.skill_id,
        message=message.text,
        client_user_id=connection.owner_id,  # developer pays
    )

    # 8. Poll for completion (with timeout)
    result = await poll_task(task.id, timeout=120)

    # 9. Send response back to platform
    await adapter.send_message(message.chat_id, result.text)

    # 10. Log message + credits
    await log_message(connection_id, message, task, credits_charged)
```

### 2.3 Platform Adapter Interface

```python
class AbstractPlatformAdapter:
    def verify_webhook(self, request) -> bool
    def parse_inbound(self, request) -> NormalizedMessage
    async def send_message(self, chat_id, text, media=None) -> bool
    async def register_webhook(self, connection, webhook_url) -> bool
    async def deregister_webhook(self, connection) -> bool
    def ack_response(self) -> Response  # platform-specific 200 acknowledgment
```

### 2.4 Rate Limiting (3 layers)

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
POST   /api/v1/gateway/charge             — atomic credit charge for a message
GET    /api/v1/gateway/connections         — all active connections (with tokens for gateway use only)
POST   /api/v1/gateway/heartbeat          — gateway reports per-connection health
POST   /api/v1/gateway/log-message        — log a channel message
```

Service account: new `key_type = "service"` on API key model. Scoped to gateway operations only.

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
