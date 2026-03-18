# Gateway Onboarding Fixes & Production Hardening — Design Spec

> **Date:** 2026-03-18
> **Status:** Approved
> **Scope:** Fix 6 critical issues + UX improvements for multi-channel gateway onboarding
> **Expert Panel:** UX Designer, Backend Engineer, Frontend Engineer, QA Engineer

---

## Overview

The multi-channel gateway (Phases 1-4) is deployed but has 6 critical issues that prevent production use. This spec addresses all gaps identified by the expert panel, plus UX improvements for developer onboarding.

---

## Critical Fixes

### Fix 1: Wire Webhook Signature Verification

**Problem:** All 5 adapters implement `verify_webhook()` but no route handler calls it. Attackers who guess a connection UUID can inject fake messages.

**Fix in `gateway/main.py`:** Add signature verification to each webhook route before parsing:

```python
# Telegram: validate X-Telegram-Bot-Api-Secret-Token header
@app.post("/webhook/telegram/{connection_id}")
async def telegram_webhook(connection_id: str, request: Request):
    body = await request.json()
    conn = await get_connection_cached(connection_id)
    if not conn:
        return Response(status_code=404)
    adapter = get_adapter("telegram")
    secret = conn.get("webhook_secret_decrypted")
    if secret and not adapter.verify_webhook(body, secret,
            token=request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")):
        return Response(status_code=401)
    # ... rest of handler

# Slack: validate X-Slack-Signature
raw_body = await request.body()
body = json.loads(raw_body)
if not adapter.verify_webhook(
    {**body, "_raw_body": raw_body.decode(), "_slack_timestamp": request.headers.get("X-Slack-Request-Timestamp", ""),
     "_slack_signature": request.headers.get("X-Slack-Signature", "")},
    conn.get("webhook_secret_decrypted")):
    return Response(status_code=401)

# Discord: validate Ed25519
raw_body = await request.body()
body["_signature"] = request.headers.get("X-Signature-Ed25519", "")
body["_timestamp"] = request.headers.get("X-Signature-Timestamp", "")
body["_body"] = raw_body

# WhatsApp: validate X-Hub-Signature-256
raw_body = await request.body()
signature = request.headers.get("X-Hub-Signature-256", "")
adapter.verify_webhook(body, conn.get("webhook_secret_decrypted"), signature=signature, body=raw_body)
```

### Fix 2: Token Validation on Channel Creation

**Problem:** `ChannelService.create_channel()` stores any token without validation. Bad tokens fail silently at message time.

**Fix in `src/services/channel_service.py`:** Add `validate_token()` that calls platform API before saving:

```python
async def _validate_token(self, platform: str, credentials: dict) -> dict:
    """Validate bot token by calling platform API. Returns bot info or raises."""
    import httpx
    token = credentials.get("bot_token") or credentials.get("access_token", "")

    if platform == "telegram":
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
            if resp.status_code != 200:
                raise BadRequestError("Invalid Telegram bot token. Check with @BotFather.")
            data = resp.json().get("result", {})
            return {"platform_bot_id": str(data.get("id")), "bot_username": data.get("username")}

    elif platform == "slack":
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post("https://slack.com/api/auth.test",
                headers={"Authorization": f"Bearer {token}"})
            data = resp.json()
            if not data.get("ok"):
                raise BadRequestError(f"Invalid Slack token: {data.get('error', 'unknown')}")
            return {"platform_bot_id": data.get("bot_id"), "team": data.get("team")}

    elif platform == "discord":
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get("https://discord.com/api/v10/users/@me",
                headers={"Authorization": f"Bot {token}"})
            if resp.status_code != 200:
                raise BadRequestError("Invalid Discord bot token.")
            data = resp.json()
            return {"platform_bot_id": data.get("id"), "bot_username": data.get("username")}

    elif platform == "teams":
        app_id = credentials.get("app_id", "")
        app_password = credentials.get("app_password", "")
        if not app_id or not app_password:
            raise BadRequestError("Teams requires app_id and app_password")
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token",
                data={"grant_type": "client_credentials", "client_id": app_id,
                      "client_secret": app_password, "scope": "https://api.botframework.com/.default"})
            if resp.status_code != 200:
                raise BadRequestError("Invalid Teams credentials. Check app_id and app_password.")
            return {"platform_bot_id": app_id}

    elif platform == "whatsapp":
        phone_id = credentials.get("phone_number_id", "")
        if not phone_id:
            raise BadRequestError("WhatsApp requires phone_number_id")
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"https://graph.facebook.com/v21.0/{phone_id}",
                headers={"Authorization": f"Bearer {token}"})
            if resp.status_code != 200:
                raise BadRequestError("Invalid WhatsApp credentials. Check phone_number_id and access token.")
            return {"platform_bot_id": phone_id}

    return {}
```

Call `_validate_token()` in `create_channel()` before encrypting and saving. Set `platform_bot_id` from the returned info.

### Fix 3: pending → active Transition + Webhook Registration

**Problem:** Channels stay "pending" forever. No code transitions them to "active" or registers webhooks.

**Fix:** After token validation succeeds and channel is created:

For auto-managed platforms (Telegram, Discord):
1. Call `adapter.register_webhook(bot_token, webhook_url)`
2. If successful, set `status = "active"` and `webhook_url`
3. If failed, set `status = "error"` with `error_message`

For manually-managed platforms (Slack, Teams, WhatsApp):
1. Set `status = "pending"` with `webhook_url` populated
2. When first webhook arrives (URL verification for Slack/WhatsApp, or first message for Teams), set `status = "active"`

Add to `gateway/main.py` webhook handlers: if connection status is "pending" and a valid message arrives, update status to "active" via `billing.update_connection_status(connection_id, "active")`.

### Fix 4: Show Webhook URL in UI

**Problem:** After channel creation for Slack/Teams/WhatsApp, the webhook URL is never shown. Developers can't complete setup.

**Fix in frontend:**

1. **Post-creation success screen** (new step 5 in wizard):
   - For auto-managed (Telegram): "Webhook registered automatically. Your bot is live!"
   - For manual (Slack/Teams/WhatsApp): Show webhook URL with copy button + platform-specific paste instructions + external link to platform dashboard

2. **Channel card**: Add webhook URL display with copy button for manual platforms. Show "Webhook not verified" warning if status is still "pending" after 5 minutes.

### Fix 5: Daily Credit Limit Enforcement

**Problem:** `daily_credit_limit` and `pause_on_limit` exist in model but gateway never checks them.

**Fix in `gateway/main.py` `process_message()`:** Before creating task:

```python
# Check daily credit limit
if conn.get("daily_credit_limit"):
    today_usage = await billing.get_today_usage(connection_id)
    if today_usage >= conn["daily_credit_limit"]:
        if conn.get("pause_on_limit"):
            await billing.update_connection_status(connection_id, "paused", "daily_limit")
        await adapter.send_message(bot_token, message.chat_id, "Service paused — daily limit reached.")
        return
```

Add `get_today_usage()` and `update_connection_status()` to `gateway/billing.py`.

### Fix 6: Setup Instructions as Primary Content

**Problem:** Platform setup guides are collapsed in a `<details>` element. First-time developers don't see them.

**Fix in `channel-wizard.tsx`:** Replace collapsed accordion with full-page guided walkthrough:
- Instructions are the MAIN content (not collapsed)
- Credential fields are at the BOTTOM, after instructions
- Each step has a numbered checklist
- External link is a prominent button ("Open @BotFather →")
- Token format validation inline (client-side regex)

---

## UX Improvements

### Improvement 1: Inline Token Validation

Add a "Verify" button next to credential fields. On click:
- Client-side format check (regex per platform)
- Server-side API call via new endpoint `POST /api/v1/channels/validate-token`
- On success: green checkmark + bot identity ("Connected as @my_bot")
- On failure: specific error message ("This looks like a user token, not a bot token")

### Improvement 2: Setup Time Estimates

Add estimated setup time to platform selection cards:
- Telegram: ~2 min (green "Easiest" badge)
- Slack: ~10 min
- Discord: ~5 min
- Teams: ~15 min
- WhatsApp: ~30 min (orange "Advanced" badge, "+2 credits/msg")

First-time nudge: "New to this? Start with Telegram — it takes about 2 minutes."

### Improvement 3: Post-Setup "First Message" Moment

After channel goes active, show a guided test screen:
- Deep link to bot on platform ("Open in Telegram →" using `t.me/botname`)
- "Waiting for first message..." with pulsing animation
- When first message detected (via 30s polling): celebration + "First message received!"

### Improvement 4: Replace Dialog with Sheet

Switch wizard from Dialog to Sheet (right-side drawer, `side="right"`, `w-full sm:w-[540px]`). Benefits:
- Developer can see both wizard and their platform dashboard side-by-side
- Natural scroll for long credential forms
- Full-width on mobile

### Improvement 5: Discoverability

- Add "Deploy to Channel" CTA on agent detail page (owner view)
- Add channel health summary card on dashboard (if channels exist)
- "New" dot badge on Channels tab for first-time visitors

### Improvement 6: Credit Progress Bar

Replace plain credit numbers with progress bar toward daily limit:
- Green at <60%, yellow at 60-85%, red at >85%
- "73/100 credits" label

### Improvement 7: Remove Budget Controls from Initial Wizard

Set sensible defaults (100 credits/day, threshold 20). Developers change later in channel settings. Reduces wizard anxiety.

---

## Backend Reliability Fixes

### Fix 7: Shared httpx Connection Pool

Replace per-request `async with httpx.AsyncClient()` with a shared client created at startup:

```python
# gateway/main.py
http_client: httpx.AsyncClient = None

@asynccontextmanager
async def lifespan(app):
    global http_client
    http_client = httpx.AsyncClient(timeout=30, limits=httpx.Limits(max_connections=100))
    yield
    await http_client.aclose()
```

Pass `http_client` to billing functions and adapters.

### Fix 8: Rate Limiter Memory Cleanup

Add periodic cleanup in lifespan:

```python
async def cleanup_rate_limiter():
    while True:
        await asyncio.sleep(300)  # every 5 minutes
        rate_limiter.cleanup_stale(max_age=120)
```

### Fix 9: Connection Cache Eviction

Add max size to `_connection_cache` (LRU, max 500 entries). Evict oldest on insert when full.

### Fix 10: WhatsApp Window Persistence

Store conversation windows in `channel_messages` table (via `billing.log_message` with `direction="system"`) instead of in-memory dict. Query on each message to check window status. Survives restarts.

---

## New API Endpoints

```
POST /api/v1/channels/validate-token    — validate credentials before saving
POST /api/v1/gateway/update-status      — gateway updates connection status
GET  /api/v1/gateway/today-usage/{id}   — get today's credit usage for a connection
```

---

## File Changes

### Gateway (modify)
- `gateway/main.py` — signature verification, daily limit check, shared http client, status transitions
- `gateway/billing.py` — add get_today_usage, update_connection_status
- `gateway/rate_limiter.py` — add cleanup_stale method
- `gateway/adapters/whatsapp.py` — persist windows via billing API instead of in-memory

### Backend (modify)
- `src/services/channel_service.py` — add _validate_token, token validation on create, webhook URL generation
- `src/api/channels.py` — add validate-token endpoint

### Frontend (modify)
- `channel-wizard.tsx` — instructions as primary content, inline validation, Sheet instead of Dialog, post-setup success screen, setup time estimates
- `channels-tab.tsx` — webhook URL display, credit progress bar, reconnect button, toast notifications

### Frontend (new)
- Agent detail page: "Deploy to Channel" section (small addition)

---

## Testing Priority

1. Token validation (all 5 platforms) — prevents broken channels
2. Webhook signature verification — security
3. Happy path message flow (Telegram first) — core functionality
4. Daily credit limit enforcement — billing accuracy
5. WhatsApp surcharge window — prevents double-charging
6. Dedup with DB constraint — prevents duplicate charges
