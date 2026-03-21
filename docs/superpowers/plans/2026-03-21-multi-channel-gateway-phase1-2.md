# Multi-Channel Gateway Phase 1-2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the Multi-Channel Gateway to deliver a working end-to-end Telegram integration — developer connects bot in Settings, end user messages bot on Telegram, agent processes and responds.

**Architecture:** Developer's Telegram bot → Gateway HF Space (webhook receiver) → CrewHub API (task creation + credit charging) → Agent HF Space → callback to Gateway → Telegram response. The Gateway is a separate FastAPI service deployed as an HF Space, communicating with the main CrewHub backend via service account API key.

**Tech Stack:** FastAPI, httpx (raw Telegram API calls, no python-telegram-bot), Fernet encryption, asyncio background tasks, HF Spaces Docker deployment.

**Spec:** `docs/superpowers/specs/2026-03-18-multi-channel-gateway-design.md`

---

## Current State (as of Mar 21)

Phase 1 CRUD + UI is ~75% complete from a prior implementation cycle:

| Component | Status | Notes |
|-----------|--------|-------|
| Models (ChannelConnection, ChannelMessage) | ✅ Built | `src/models/channel.py`, all spec columns |
| Migration 029 | ✅ Applied | Both tables + indexes |
| CRUD API (7 endpoints) | ✅ Built | `src/api/channels.py`, registered in `main.py` |
| ChannelService (token validation, CRUD) | ✅ Built | Real platform API calls for all 5 platforms |
| Schemas | ✅ Built | `src/schemas/channel.py` |
| Frontend (types, API client, hooks, wizard, tab) | ✅ Built | Settings → Channels tab, 4-step wizard |

**This plan covers:** Phase 1 remaining gaps + full Phase 2 gateway service.

**IMPORTANT constraints:**
- `X-Gateway-Key` header is server-to-server only — does NOT need CORS whitelisting
- Local dev with `localhost` callback URLs will be blocked by SSRF validation in `push_notifier.py` — use a tunneling service (ngrok/cloudflared) or deploy to staging for E2E testing
- Gateway task callback endpoint MUST verify a shared HMAC secret to prevent forged responses

---

## File Map

### Backend (CrewHub main — `src/`)

| File | Action | Responsibility |
|------|--------|---------------|
| `src/models/__init__.py` | Modify | Export ChannelConnection, ChannelMessage |
| `src/config.py` | Modify | Add `gateway_url`, `gateway_service_key` settings |
| `src/api/channels.py` | Modify | Add `rotate-token` endpoint |
| `src/api/gateway.py` | Create | 5 gateway-facing endpoints (charge, connection, heartbeat, log-message, task-callback) |
| `src/services/channel_service.py` | Modify | Add `rotate_token`, `deregister_webhook` methods; real analytics query |
| `src/schemas/channel.py` | Modify | Add gateway-facing request/response schemas |
| `src/main.py` | Modify | Register gateway router |
| `tests/test_channels.py` | Create | Channel CRUD + gateway endpoint tests |

### Gateway Service (`demo_agents/gateway/`)

| File | Action | Responsibility |
|------|--------|---------------|
| `demo_agents/gateway/Dockerfile` | Create | HF Space Docker deployment |
| `demo_agents/gateway/requirements.txt` | Create | Dependencies |
| `demo_agents/gateway/config.py` | Create | Gateway settings (CrewHub API URL, service key) |
| `demo_agents/gateway/main.py` | Create | FastAPI app, webhook routes, startup/shutdown |
| `demo_agents/gateway/adapters/__init__.py` | Create | Adapter registry |
| `demo_agents/gateway/adapters/base.py` | Create | AbstractPlatformAdapter interface |
| `demo_agents/gateway/adapters/telegram.py` | Create | Telegram Bot API adapter |
| `demo_agents/gateway/billing.py` | Create | Credit check + charge via CrewHub API |
| `demo_agents/gateway/dedup.py` | Create | DB-backed deduplication via log-message endpoint |
| `demo_agents/gateway/rate_limiter.py` | Create | In-memory per-user rate limiting |
| `demo_agents/gateway/crewhub_client.py` | Create | HTTP client for CrewHub API calls |
| `tests/test_gateway.py` | Create | Gateway unit tests |

### Frontend (`frontend/src/`)

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/src/app/(marketplace)/dashboard/settings/channel-wizard.tsx` | Modify | Add budget controls in step 3 |
| `frontend/src/app/(marketplace)/dashboard/settings/channels-tab.tsx` | Modify | Add edit button on channel cards |
| `frontend/src/app/(marketplace)/dashboard/settings/channel-edit-sheet.tsx` | Create | Edit slide-over for existing channels |
| `frontend/src/lib/hooks/use-channels.ts` | Modify | Add `useRotateChannelToken` hook |
| `frontend/src/components/layout/user-sidebar.tsx` | Modify | Add Channels entry to sidebar nav |

### Deployment

| File | Action | Responsibility |
|------|--------|---------------|
| `.github/workflows/deploy-gateway.yml` | Create | GitHub Actions deploy to HF Space |
| `scripts/deploy_gateway.py` | Create | Deploy script using huggingface_hub |

---

## Task 1: Backend — Export Models + Config

**Files:**
- Modify: `src/models/__init__.py`
- Modify: `src/config.py`

- [ ] **Step 1: Add channel models to `__init__.py`**

In `src/models/__init__.py`, add to imports and `__all__`:
```python
from src.models.channel import ChannelConnection, ChannelMessage
```
Add `"ChannelConnection"` and `"ChannelMessage"` to the `__all__` list.

- [ ] **Step 2: Add gateway config to Settings**

In `src/config.py`, add to the `Settings` class:
```python
# Multi-Channel Gateway
gateway_url: str = ""  # URL of the gateway HF Space
gateway_service_key: str = ""  # Shared secret for gateway → backend auth
```

- [ ] **Step 3: Verify imports**

Run: `python -c "from src.models import ChannelConnection, ChannelMessage; from src.config import settings; print('OK', settings.gateway_url)"`
Expected: `OK `

- [ ] **Step 4: Commit**

```bash
git add src/models/__init__.py src/config.py
git commit -m "feat: export channel models + add gateway config settings"
```

---

## Task 2: Backend — Token Rotation Endpoint

**Files:**
- Modify: `src/api/channels.py`
- Modify: `src/services/channel_service.py`

- [ ] **Step 1: Add `rotate_token` to ChannelService**

In `src/services/channel_service.py`, add method:
```python
async def rotate_token(self, connection_id: UUID, owner_id: UUID, credentials: dict) -> ChannelConnection:
    """Rotate bot token for an existing channel. Validates new token against platform API."""
    conn = await self.get_channel(connection_id, owner_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Validate new token
    platform = conn.platform
    bot_token = credentials.get("bot_token", "")
    if not bot_token:
        raise HTTPException(status_code=400, detail="bot_token is required")

    is_valid, bot_info = await self._validate_token(platform, credentials)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid {platform} token")

    # Encrypt and store new token
    from src.core.encryption import encrypt_value
    conn.bot_token = encrypt_value(bot_token)
    if credentials.get("signing_secret"):
        conn.webhook_secret = encrypt_value(credentials["signing_secret"])
    conn.status = "active"
    conn.error_message = None
    await self.db.flush()
    return conn
```

- [ ] **Step 2: Add endpoint to `channels.py`**

Note: The existing frontend API client sends `credentials` as the body directly (not wrapped),
so the endpoint accepts a plain dict to match:

```python
@router.post("/{channel_id}/rotate-token", response_model=ChannelResponse)
async def rotate_channel_token(
    channel_id: UUID,
    credentials: dict,
    user_id: UUID = Depends(resolve_db_user_id),
    db: AsyncSession = Depends(get_db),
) -> ChannelResponse:
    """Rotate bot token for an existing channel connection."""
    service = ChannelService(db)
    conn = await service.rotate_token(channel_id, user_id, credentials)
    return ChannelResponse.model_validate(conn)
```

- [ ] **Step 3: Verify endpoint registered**

Run: `python -c "from src.main import app; paths = [r.path for r in app.routes if 'rotate' in str(getattr(r, 'path', ''))]; print(paths)"`
Expected: `['/api/v1/channels/{channel_id}/rotate-token']`

- [ ] **Step 4: Commit**

```bash
git add src/api/channels.py src/services/channel_service.py
git commit -m "feat: token rotation endpoint for channel connections"
```

---

## Task 3: Backend — Gateway-Facing API Endpoints

**Files:**
- Create: `src/api/gateway.py`
- Modify: `src/schemas/channel.py`
- Modify: `src/main.py`

- [ ] **Step 1: Add gateway schemas**

In `src/schemas/channel.py`, add:
```python
class GatewayChargeRequest(BaseModel):
    connection_id: UUID
    platform_user_id: str
    credits: float = Field(gt=0, le=100)
    message_text: str = ""

class GatewayChargeResponse(BaseModel):
    success: bool
    remaining_balance: float = 0
    error: str | None = None

class GatewayLogMessageRequest(BaseModel):
    connection_id: UUID
    platform_user_id: str
    platform_message_id: str
    platform_chat_id: str | None = None
    direction: str = Field(pattern="^(inbound|outbound|system)$")
    message_text: str
    media_type: str | None = None
    task_id: UUID | None = None
    credits_charged: float = 0
    response_time_ms: int | None = None
    error: str | None = None

class GatewayHeartbeatRequest(BaseModel):
    connections: list[dict]  # [{connection_id, status, error_message}]

class GatewayConnectionResponse(BaseModel):
    id: UUID
    owner_id: UUID  # needed by billing to check balance + charge credits
    platform: str
    bot_token: str  # decrypted — only exposed to gateway
    webhook_secret: str | None = None  # decrypted
    agent_id: UUID
    skill_id: UUID | None = None
    status: str
    daily_credit_limit: int | None = None
    pause_on_limit: bool = True
    low_balance_threshold: int = 20
    config: dict | None = None
```

- [ ] **Step 2: Create `src/api/gateway.py`**

Create gateway router with service-key auth dependency and 5 endpoints:
- `POST /gateway/charge` — deduct credits from connection owner's account
- `GET /gateway/connections/{connection_id}` — return connection with decrypted token
- `POST /gateway/heartbeat` — update connection health status
- `POST /gateway/log-message` — log a channel message (dedup via unique constraint)
- `POST /gateway/task-callback` — receive agent task result, forward to gateway's platform adapter

The service-key auth dependency checks `X-Gateway-Key` header against `settings.gateway_service_key`.

- [ ] **Step 3: Register router in `src/main.py`**

```python
from src.api.gateway import router as gateway_router
app.include_router(gateway_router, prefix=settings.api_v1_prefix)
```

- [ ] **Step 4: Verify routes registered**

Run: `python -c "from src.main import app; gw = [r.path for r in app.routes if 'gateway' in str(getattr(r, 'path', ''))]; print(len(gw), gw)"`
Expected: `5 ['/api/v1/gateway/charge', '/api/v1/gateway/connections/{connection_id}', ...]`

- [ ] **Step 5: Commit**

```bash
git add src/api/gateway.py src/schemas/channel.py src/main.py
git commit -m "feat: gateway-facing API endpoints (charge, connection, heartbeat, log, callback)"
```

---

## Task 4: Backend — Telegram Webhook Cleanup + Analytics

**Files:**
- Modify: `src/services/channel_service.py`

- [ ] **Step 1: Add `deregister_webhook` for Telegram**

In `delete_channel` method, before deleting, call Telegram's `deleteWebhook` API:
```python
if connection.platform == "telegram" and connection.bot_token:
    from src.core.encryption import decrypt_value
    try:
        token = decrypt_value(connection.bot_token)
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(f"https://api.telegram.org/bot{token}/deleteWebhook")
    except Exception:
        pass  # best-effort cleanup
```

- [ ] **Step 2: Implement real analytics query**

Replace the stub `get_analytics` with actual SQL:
```python
async def get_analytics(self, connection_id: UUID, owner_id: UUID, days: int = 7):
    conn = await self.get_channel(connection_id, owner_id)
    if not conn:
        return None

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await self.db.execute(
        select(
            func.date(ChannelMessage.created_at).label("date"),
            func.count().label("messages"),
            func.sum(ChannelMessage.credits_charged).label("credits"),
        )
        .where(ChannelMessage.connection_id == connection_id)
        .where(ChannelMessage.created_at >= cutoff)
        .group_by(func.date(ChannelMessage.created_at))
        .order_by(func.date(ChannelMessage.created_at))
    )
    rows = result.all()
    return {
        "daily": [{"date": str(r.date), "messages": r.messages, "credits": float(r.credits or 0)} for r in rows],
        "total_messages": sum(r.messages for r in rows),
        "total_credits": sum(float(r.credits or 0) for r in rows),
    }
```

- [ ] **Step 3: Commit**

```bash
git add src/services/channel_service.py
git commit -m "feat: Telegram webhook cleanup on delete + real analytics queries"
```

---

## Task 5: Gateway Service — Core Infrastructure

**Files:**
- Create: `demo_agents/gateway/Dockerfile`
- Create: `demo_agents/gateway/requirements.txt`
- Create: `demo_agents/gateway/config.py`
- Create: `demo_agents/gateway/crewhub_client.py`
- Create: `demo_agents/gateway/rate_limiter.py`
- Create: `demo_agents/gateway/dedup.py`
- Create: `demo_agents/gateway/billing.py`

- [ ] **Step 1: Create `requirements.txt`**

```
fastapi>=0.115.0
uvicorn>=0.30.0
httpx>=0.27.0
pydantic>=2.9.0
pydantic-settings>=2.0.0
```

- [ ] **Step 2: Create `config.py`**

```python
from pydantic_settings import BaseSettings

class GatewaySettings(BaseSettings):
    crewhub_api_url: str = "https://api.crewhubai.com/api/v1"
    gateway_service_key: str = ""  # matches CrewHub's gateway_service_key
    port: int = 7860
    model_config = {"env_file": ".env", "extra": "ignore"}

settings = GatewaySettings()
```

- [ ] **Step 3: Create `crewhub_client.py`**

HTTP client wrapper for all CrewHub API calls:
- `get_connection(connection_id)` — GET with 60s TTL cache (returns decrypted token + owner_id)
- `charge_credits(connection_id, user_id, credits, message)` — POST /gateway/charge
- `create_task(agent_id, skill_id, message, owner_id, callback_url)` — POST /tasks/
- `log_message(data)` — POST /gateway/log-message
- `get_balance(owner_id)` — GET /credits/balance
- `get_today_usage(connection_id)` — computed from log-message data or a dedicated endpoint

All calls include `X-Gateway-Key` header.

Note: `get_today_usage` can query the gateway's `/charge` response (which returns remaining balance)
or use a separate `GET /gateway/connections/{id}/usage` endpoint. Simplest approach: the `/gateway/charge`
response includes `today_usage` so the billing module can check limits inline.

- [ ] **Step 4: Create `rate_limiter.py`**

In-memory TTL-based rate limiter:
```python
class InMemoryRateLimiter:
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self._counters: dict[str, list[float]] = {}
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def is_limited(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        hits = self._counters.get(key, [])
        hits = [t for t in hits if t > cutoff]
        hits.append(now)
        self._counters[key] = hits
        return len(hits) > self.max_requests
```

- [ ] **Step 5: Create `dedup.py`**

Simple set-based dedup with TTL (backup — primary dedup is DB unique constraint):
```python
class MessageDedup:
    def __init__(self, ttl: int = 300):
        self._seen: dict[str, float] = {}
        self.ttl = ttl

    def is_duplicate(self, connection_id: str, message_id: str) -> bool:
        key = f"{connection_id}:{message_id}"
        now = time.time()
        # Cleanup old entries
        self._seen = {k: v for k, v in self._seen.items() if now - v < self.ttl}
        if key in self._seen:
            return True
        self._seen[key] = now
        return False
```

- [ ] **Step 6: Create `billing.py`**

Credit check + charge wrapper:
```python
async def check_and_charge(client: CrewHubClient, connection, message, platform_surcharge: float = 0):
    """Check balance + daily limit, charge credits atomically. Returns (ok, error_msg).

    Atomicity: The /gateway/charge endpoint uses SELECT FOR UPDATE on the account
    row to serialize concurrent charges for the same developer. The endpoint also
    returns today_usage so daily limits can be checked server-side.
    """
    cost = 1 + platform_surcharge  # base cost + platform surcharge (WhatsApp = 2)

    # Single atomic call: checks balance, daily limit, and charges
    result = await client.charge_credits(
        connection_id=connection["id"],
        owner_id=connection["owner_id"],
        credits=cost,
        message_text=message.text,
        daily_credit_limit=connection.get("daily_credit_limit"),
    )

    if not result["success"]:
        return False, result.get("error", "charge_failed")
    return True, None
```

- [ ] **Step 7: Create `Dockerfile`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-7860} --workers 1
```

- [ ] **Step 8: Commit**

```bash
git add demo_agents/gateway/
git commit -m "feat: gateway core infrastructure — config, client, billing, dedup, rate limiter"
```

---

## Task 6: Gateway Service — Telegram Adapter + Main App

**Files:**
- Create: `demo_agents/gateway/adapters/__init__.py`
- Create: `demo_agents/gateway/adapters/base.py`
- Create: `demo_agents/gateway/adapters/telegram.py`
- Create: `demo_agents/gateway/main.py`

- [ ] **Step 1: Create `adapters/base.py`**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class NormalizedMessage:
    platform_user_id: str
    platform_message_id: str
    platform_chat_id: str
    text: str
    media_type: str = "text"

class AbstractPlatformAdapter(ABC):
    @abstractmethod
    def verify_webhook(self, request_body: bytes, headers: dict) -> bool: ...

    @abstractmethod
    def parse_inbound(self, body: dict) -> NormalizedMessage | None: ...

    @abstractmethod
    async def send_message(self, bot_token: str, chat_id: str, text: str) -> bool: ...

    @abstractmethod
    async def send_typing(self, bot_token: str, chat_id: str) -> None: ...

    def ack_response(self) -> dict:
        return {"ok": True}
```

- [ ] **Step 2: Create `adapters/telegram.py`**

Implements `AbstractPlatformAdapter` for Telegram Bot API:
- `verify_webhook` — Telegram doesn't sign webhooks; returns True (security via secret URL path)
- `parse_inbound` — extracts message from Telegram Update JSON
- `send_message` — POST to `https://api.telegram.org/bot{token}/sendMessage`
- `send_typing` — POST to `sendChatAction` with `action=typing`

- [ ] **Step 3: Create `adapters/__init__.py`**

Adapter registry:
```python
from .telegram import TelegramAdapter

ADAPTERS = {
    "telegram": TelegramAdapter(),
}

def get_adapter(platform: str) -> AbstractPlatformAdapter:
    adapter = ADAPTERS.get(platform)
    if not adapter:
        raise ValueError(f"Unsupported platform: {platform}")
    return adapter
```

- [ ] **Step 4: Create `main.py`**

FastAPI app with:
- Health endpoint: `GET /health`
- Telegram webhook: `POST /webhook/telegram/{connection_id}`
- Task callback: `POST /internal/task-callback/{connection_id}/{chat_id}`
  - MUST verify `X-Gateway-Key` header matches `settings.gateway_service_key` (shared secret)
  - Reject with 401 if header missing or wrong — prevents forged callback responses
- Background `process_message` function (billing → task creation → typing indicator)
- Startup: initialize `CrewHubClient`, `InMemoryRateLimiter`, `MessageDedup`

Key flow:
1. Webhook receives Telegram update → parse → dedup → rate limit → ack immediately
2. Background task: check credits → create task with callback URL → send typing
3. Callback receives task result → send response to Telegram chat

- [ ] **Step 5: Verify gateway starts locally**

Run: `cd demo_agents/gateway && python -c "from main import app; print('Gateway app OK')"`

- [ ] **Step 6: Commit**

```bash
git add demo_agents/gateway/
git commit -m "feat: gateway Telegram adapter + main FastAPI app with async callback flow"
```

---

## Task 7: Frontend — Budget Controls + Edit Sheet

**Files:**
- Modify: `frontend/src/app/(marketplace)/dashboard/settings/channel-wizard.tsx`
- Create: `frontend/src/app/(marketplace)/dashboard/settings/channel-edit-sheet.tsx`
- Modify: `frontend/src/app/(marketplace)/dashboard/settings/channels-tab.tsx`
- Modify: `frontend/src/lib/hooks/use-channels.ts`

- [ ] **Step 1: Add budget inputs to wizard step 3**

Replace hardcoded `daily_credit_limit: 100` with actual form inputs:
- Daily credit limit (number input, default 100)
- Low balance threshold (number input, default 20)
- Pause on limit toggle (checkbox, default true)

- [ ] **Step 2: Create `channel-edit-sheet.tsx`**

Sheet component for editing existing channels:
- Agent selector (change assigned agent)
- Skill selector
- Budget controls (daily limit, threshold, pause toggle)
- Bot name
- Save button → calls `useUpdateChannel`

- [ ] **Step 3: Add edit button to channel cards**

In `channels-tab.tsx`, add a "Configure" button next to Pause/Delete that opens the edit sheet.

- [ ] **Step 4: Add `useRotateChannelToken` hook**

In `use-channels.ts`:
```typescript
export function useRotateChannelToken() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ channelId, credentials }: { channelId: string; credentials: Record<string, string> }) =>
      rotateChannelToken(channelId, credentials),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["channels"] }),
  });
}
```

- [ ] **Step 5: TypeScript check**

Run: `cd frontend && npx tsc --noEmit`
Expected: Clean compile.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/
git commit -m "feat: channel budget controls, edit sheet, token rotation hook"
```

---

## Task 8: Frontend — Sidebar Entry

**Files:**
- Modify: `frontend/src/components/layout/user-sidebar.tsx`

- [ ] **Step 1: Add Channels to sidebar**

Add to the Orchestration section in `NAV_SECTIONS`:
```typescript
{ label: "Channels", href: "/dashboard/settings?tab=channels", icon: Radio },
```

Import `Radio` from lucide-react.

- [ ] **Step 2: Verify**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/layout/user-sidebar.tsx
git commit -m "feat: add Channels entry to dashboard sidebar navigation"
```

---

## Task 9: Deploy Gateway + Integration Test

**Files:**
- Create: `.github/workflows/deploy-gateway.yml`
- Create: `scripts/deploy_gateway.py`

- [ ] **Step 1: Create deploy script**

Similar to `deploy_demo_agents.py` but for the gateway:
- Uploads `demo_agents/gateway/` to `arimatch1/crewhub-gateway` HF Space
- Sets secrets: `CREWHUB_API_URL`, `GATEWAY_SERVICE_KEY`

- [ ] **Step 2: Create GitHub Actions workflow**

Trigger on push to `demo_agents/gateway/**` on main/staging branches.

- [ ] **Step 3: Deploy to staging**

Run deploy script with staging config:
- `CREWHUB_API_URL=https://api-staging.crewhubai.com/api/v1`
- Generate a unique `GATEWAY_SERVICE_KEY` and set it on both gateway and backend

- [ ] **Step 4: Set backend env var**

Set `GATEWAY_SERVICE_KEY` and `GATEWAY_URL` on the staging HF Space.

- [ ] **Step 5: End-to-end test**

1. Create a Telegram test bot via @BotFather
2. Connect it via the Settings wizard on staging
3. Send a message to the bot on Telegram
4. Verify: message → gateway → CrewHub task → agent response → Telegram reply
5. Verify: credits deducted from developer account
6. Verify: channel_messages table has inbound + outbound entries

- [ ] **Step 6: Commit deployment files**

```bash
git add .github/workflows/deploy-gateway.yml scripts/deploy_gateway.py
git commit -m "feat: gateway deployment script + GitHub Actions workflow"
```

---

## Task 10: Tests

**Files:**
- Create: `tests/test_channels.py` — backend CRUD + gateway endpoint tests
- Create: `tests/test_gateway.py` — gateway service unit tests (adapters, billing, dedup)

- [ ] **Step 1: Write channel CRUD tests** (`tests/test_channels.py`)

Test channel creation, listing, update, delete, token rotation via API.

- [ ] **Step 2: Write gateway endpoint tests** (`tests/test_channels.py`)

Test the 5 gateway-facing endpoints with mock service key auth. Test that missing/wrong key returns 401.

- [ ] **Step 3: Write Telegram adapter unit tests** (`tests/test_gateway.py`)

Test `parse_inbound` with sample Telegram webhook payloads. Test `send_message` with mocked httpx.
Test `verify_webhook` returns True (Telegram uses secret URL paths, not signatures).

- [ ] **Step 4: Write billing + dedup tests** (`tests/test_gateway.py`)

Test rate limiter, message dedup TTL, billing charge flow with mocked client.

- [ ] **Step 5: Run all tests**

Run: `pytest tests/test_channels.py tests/test_gateway.py -v`
Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add tests/test_channels.py tests/test_gateway.py
git commit -m "test: channel CRUD, gateway endpoints, Telegram adapter, billing + dedup"
```

---

## Definition of Done

- [ ] Developer can connect a Telegram bot via Settings → Channels wizard
- [ ] End user sends message to Telegram bot → agent processes → response sent back
- [ ] Credits deducted from developer's account per message
- [ ] Daily credit limit enforced (auto-pause when exceeded)
- [ ] Duplicate messages rejected (DB unique constraint)
- [ ] Rate limiting prevents spam (10 msg/min per end user)
- [ ] Developer can edit channel config (agent, budget) after creation
- [ ] Developer can rotate bot token without recreating channel
- [ ] Channels visible in sidebar navigation
- [ ] Gateway deployed to HF Spaces with CI/CD
- [ ] All tests pass
