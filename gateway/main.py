"""CrewHub Multi-Channel Gateway — FastAPI app."""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx

from config import PORT, GATEWAY_URL
from dedup import dedup
from rate_limiter import rate_limiter
import billing

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("gateway")

http_client: httpx.AsyncClient | None = None


def get_adapter(platform: str):
    """Get the appropriate adapter for a platform."""
    if platform == "telegram":
        from adapters.telegram import TelegramAdapter
        return TelegramAdapter()
    elif platform == "slack":
        from adapters.slack import SlackAdapter
        return SlackAdapter()
    elif platform == "discord":
        from adapters.discord import DiscordAdapter
        return DiscordAdapter()
    elif platform == "teams":
        from adapters.teams import TeamsAdapter
        return TeamsAdapter()
    elif platform == "whatsapp":
        from adapters.whatsapp import WhatsAppAdapter
        return WhatsAppAdapter()
    raise ValueError(f"Unknown platform: {platform}")


async def _cleanup_loop():
    """Periodically clean stale rate limiter entries."""
    while True:
        await asyncio.sleep(300)
        rate_limiter.cleanup_stale()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient(timeout=30, limits=httpx.Limits(max_connections=100))
    billing.set_http_client(http_client)
    logger.info("Gateway starting — URL: %s", GATEWAY_URL)
    asyncio.create_task(_cleanup_loop())
    yield
    await http_client.aclose()
    logger.info("Gateway shutting down")

app = FastAPI(title="CrewHub Gateway", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Connection config cache (TTL 60s, max 500 entries)
_connection_cache: dict[str, tuple[dict, float]] = {}
CACHE_TTL = 60
MAX_CACHE_SIZE = 500

async def get_connection_cached(connection_id: str) -> dict | None:
    import time
    cached = _connection_cache.get(connection_id)
    if cached and time.time() - cached[1] < CACHE_TTL:
        return cached[0]
    conn = await billing.get_connection(connection_id)
    if conn:
        _connection_cache[connection_id] = (conn, time.time())
        # Evict oldest if over limit
        if len(_connection_cache) > MAX_CACHE_SIZE:
            oldest = min(_connection_cache, key=lambda k: _connection_cache[k][1])
            del _connection_cache[oldest]
    return conn


@app.get("/health")
async def health():
    return {"status": "ok", "service": "crewhub-gateway"}


# ── Generic webhook handler ─────────────────────────────────────

async def handle_platform_webhook(platform: str, connection_id: str, message):
    """Common webhook handling: dedup, rate limit, dispatch."""
    if dedup.is_duplicate(connection_id, message.platform_message_id):
        return Response(status_code=200)

    user_key = f"user:{connection_id}:{message.platform_user_id}"
    if rate_limiter.is_rate_limited(user_key, max_requests=10, window_seconds=60):
        return Response(status_code=200)

    asyncio.create_task(process_message(platform, connection_id, message))
    return Response(status_code=200)


# ── Telegram ─────────────────────────────────────────────────────

@app.post("/webhook/telegram/{connection_id}")
async def telegram_webhook(connection_id: str, request: Request):
    # Verify webhook signature if secret is configured
    conn = await get_connection_cached(connection_id)
    if conn and conn.get("webhook_secret_decrypted"):
        expected = conn["webhook_secret_decrypted"]
        actual = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if actual != expected:
            return Response(status_code=401)

    body = await request.json()
    adapter = get_adapter("telegram")
    message = adapter.parse_inbound(body)
    if not message:
        return Response(status_code=200)
    return await handle_platform_webhook("telegram", connection_id, message)


# ── Slack ────────────────────────────────────────────────────────

@app.post("/webhook/slack/{connection_id}")
async def slack_webhook(connection_id: str, request: Request):
    raw_body = await request.body()
    adapter = get_adapter("slack")

    # Verify Slack webhook signature
    conn = await get_connection_cached(connection_id)
    signing_secret = conn.get("config", {}).get("signing_secret", "") if conn else ""
    if signing_secret:
        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        signature = request.headers.get("X-Slack-Signature", "")
        verified = adapter.verify_webhook(
            {"_slack_timestamp": timestamp, "_slack_signature": signature,
             "_raw_body": raw_body.decode()},
            secret=signing_secret,
        )
        if not verified:
            return Response(status_code=401)

    body = json.loads(raw_body)

    # Handle Slack URL verification challenge
    challenge = adapter.handle_url_verification(body)
    if challenge is not None:
        return {"challenge": challenge}

    message = adapter.parse_inbound(body)
    if not message:
        return Response(status_code=200)
    return await handle_platform_webhook("slack", connection_id, message)


# ── Discord ──────────────────────────────────────────────────────

@app.post("/webhook/discord/{connection_id}")
async def discord_webhook(connection_id: str, request: Request):
    raw_body = await request.body()
    adapter = get_adapter("discord")

    # Verify Discord Ed25519 signature
    conn = await get_connection_cached(connection_id)
    public_key = conn.get("config", {}).get("public_key", "") if conn else ""
    if public_key:
        signature = request.headers.get("X-Signature-Ed25519", "")
        timestamp = request.headers.get("X-Signature-Timestamp", "")
        verified = adapter.verify_webhook(
            {"_signature": signature, "_timestamp": timestamp, "_body": raw_body},
            secret=public_key,
        )
        if not verified:
            return Response(status_code=401)

    body = json.loads(raw_body)

    # Handle Discord PING verification
    pong = adapter.handle_ping(body)
    if pong is not None:
        return pong

    message = adapter.parse_inbound(body)
    if not message:
        return Response(status_code=200)

    # For interactions, send deferred response first (Discord requires <3s ack)
    # Then process in background
    if dedup.is_duplicate(connection_id, message.platform_message_id):
        return {"type": 5}  # DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE

    user_key = f"user:{connection_id}:{message.platform_user_id}"
    if rate_limiter.is_rate_limited(user_key, max_requests=10, window_seconds=60):
        return {"type": 5}

    asyncio.create_task(process_message("discord", connection_id, message,
                                         interaction_token=body.get("token"),
                                         application_id=body.get("application_id")))
    return {"type": 5}  # DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE


# ── Teams ────────────────────────────────────────────────────────

@app.post("/webhook/teams/{connection_id}")
async def teams_webhook(connection_id: str, request: Request):
    body = await request.json()
    adapter = get_adapter("teams")
    message = adapter.parse_inbound(body)
    if not message:
        return Response(status_code=200)

    # Store service_url from activity for reply routing
    service_url = body.get("serviceUrl", "")

    if dedup.is_duplicate(connection_id, message.platform_message_id):
        return Response(status_code=200)

    user_key = f"user:{connection_id}:{message.platform_user_id}"
    if rate_limiter.is_rate_limited(user_key, max_requests=10, window_seconds=60):
        return Response(status_code=200)

    asyncio.create_task(process_message("teams", connection_id, message,
                                         service_url=service_url))
    return Response(status_code=200)


# ── WhatsApp ─────────────────────────────────────────────────────

@app.get("/webhook/whatsapp/{connection_id}")
async def whatsapp_verify(connection_id: str,
                          hub_mode: str = Query("", alias="hub.mode"),
                          hub_token: str = Query("", alias="hub.verify_token"),
                          hub_challenge: str = Query("", alias="hub.challenge")):
    """Meta webhook verification GET challenge."""
    conn = await get_connection_cached(connection_id)
    if not conn:
        return Response(status_code=404)

    adapter = get_adapter("whatsapp")
    verify_token = conn.get("config", {}).get("verify_token", "")
    result = adapter.handle_verification_challenge(hub_mode, hub_token, hub_challenge, verify_token)
    if result is not None:
        return Response(content=result, media_type="text/plain")
    return Response(status_code=403)


@app.post("/webhook/whatsapp/{connection_id}")
async def whatsapp_webhook(connection_id: str, request: Request):
    raw_body = await request.body()
    adapter = get_adapter("whatsapp")

    # Verify WhatsApp webhook signature
    conn = await get_connection_cached(connection_id)
    app_secret = conn.get("config", {}).get("app_secret", "") if conn else ""
    if app_secret:
        hub_signature = request.headers.get("X-Hub-Signature-256", "")
        verified = adapter.verify_webhook(
            {}, secret=app_secret, signature=hub_signature, body=raw_body,
        )
        if not verified:
            return Response(status_code=401)

    body = json.loads(raw_body)
    message = adapter.parse_inbound(body)
    if not message:
        return Response(status_code=200)
    return await handle_platform_webhook("whatsapp", connection_id, message)


# ── Task callback (all platforms) ────────────────────────────────

@app.post("/internal/task-callback/{connection_id}/{chat_id}")
async def task_callback(connection_id: str, chat_id: str, request: Request):
    body = await request.json()
    conn = await get_connection_cached(connection_id)
    if not conn:
        return Response(status_code=404)

    platform = conn.get("platform", "telegram")
    bot_token = conn.get("bot_token_decrypted", "")
    text = body.get("result", "")
    if not text:
        artifacts = body.get("artifacts", [])
        text = artifacts[0].get("content", "No response") if artifacts else "No response"

    # Send response via platform adapter
    adapter = get_adapter(platform)
    if platform == "whatsapp":
        phone_number_id = conn.get("config", {}).get("phone_number_id", "")
        await adapter.send_message(bot_token, chat_id, text, phone_number_id=phone_number_id)
    elif platform == "teams":
        service_url = conn.get("config", {}).get("last_service_url", "")
        await adapter.send_message(bot_token, chat_id, text, service_url=service_url)
    elif platform == "discord":
        # Discord followup uses interaction token stored in config
        interaction_token = conn.get("config", {}).get("last_interaction_token", "")
        application_id = conn.get("config", {}).get("application_id", "")
        if interaction_token and application_id:
            await adapter.send_followup(application_id, interaction_token, text)
        else:
            await adapter.send_message(bot_token, chat_id, text)
    else:
        await adapter.send_message(bot_token, chat_id, text)

    # Log outbound message
    await billing.log_message(connection_id, {
        "platform_user_id": "agent",
        "platform_message_id": body.get("task_id", ""),
        "direction": "outbound",
        "message_text": text[:500],
        "task_id": body.get("task_id"),
        "credits_charged": body.get("credits_used", 0),
        "response_time_ms": body.get("latency_ms", 0),
    })

    return Response(status_code=200)


# ── Background message processing ───────────────────────────────

async def process_message(platform: str, connection_id: str, message,
                          interaction_token: str = "", application_id: str = "",
                          service_url: str = ""):
    """Background task: check credits, create task, send typing."""
    try:
        conn = await get_connection_cached(connection_id)
        if not conn:
            logger.error("Connection %s not found", connection_id)
            return

        if conn.get("status") != "active":
            logger.info("Connection %s is %s, skipping", connection_id, conn.get("status"))
            return

        owner_id = conn.get("owner_id", "")
        agent_id = conn.get("agent_id", "")
        skill_id = conn.get("skill_id")
        bot_token = conn.get("bot_token_decrypted", "")

        # Check daily credit limit
        if conn.get("daily_credit_limit"):
            today_usage = await billing.get_today_usage(connection_id)
            if today_usage >= conn["daily_credit_limit"]:
                if conn.get("pause_on_limit"):
                    await billing.update_connection_status(connection_id, "paused", "daily_limit")
                adapter = get_adapter(platform)
                await adapter.send_message(bot_token, message.chat_id, "Service paused — daily limit reached.")
                return

        # Send typing indicator
        adapter = get_adapter(platform)
        if platform == "whatsapp":
            phone_number_id = conn.get("config", {}).get("phone_number_id", "")
            await adapter.send_typing(bot_token, message.chat_id, phone_number_id=phone_number_id)
        elif platform == "teams":
            await adapter.send_typing(bot_token, message.chat_id)
        elif platform == "discord":
            await adapter.send_typing(bot_token, message.chat_id)
        else:
            await adapter.send_typing(bot_token, message.chat_id)

        # WhatsApp surcharge check
        extra_credits = 0
        if platform == "whatsapp":
            surcharge = adapter.get_surcharge(connection_id, message.platform_user_id)
            if surcharge > 0:
                adapter.open_conversation_window(connection_id, message.platform_user_id)
                extra_credits = surcharge

        # Create task with callback
        callback_url = f"{GATEWAY_URL}/internal/task-callback/{connection_id}/{message.chat_id}"
        task = await billing.create_task(
            agent_id=agent_id,
            skill_id=skill_id,
            message=message.text,
            owner_id=owner_id,
            callback_url=callback_url,
            idempotency_key=message.platform_message_id,
        )

        if not task:
            logger.error("Failed to create task for connection %s", connection_id)
            error_msg = "Sorry, I couldn't process your request right now."
            if platform == "whatsapp":
                phone_number_id = conn.get("config", {}).get("phone_number_id", "")
                await adapter.send_message(bot_token, message.chat_id, error_msg, phone_number_id=phone_number_id)
            elif platform == "discord" and interaction_token and application_id:
                await adapter.send_followup(application_id, interaction_token, error_msg)
            else:
                await adapter.send_message(bot_token, message.chat_id, error_msg)
            return

        # Log inbound message
        await billing.log_message(connection_id, {
            "platform_user_id": message.platform_user_id,
            "platform_message_id": message.platform_message_id,
            "platform_chat_id": message.chat_id,
            "direction": "inbound",
            "message_text": message.text[:500],
            "task_id": task.get("id"),
            "credits_charged": extra_credits,
        })

    except Exception as e:
        logger.exception("Error processing message for %s: %s", connection_id, e)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
