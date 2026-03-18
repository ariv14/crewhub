"""CrewHub Multi-Channel Gateway — FastAPI app."""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from config import PORT, GATEWAY_URL
from dedup import dedup
from rate_limiter import rate_limiter
from gateway import billing

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("gateway")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Gateway starting — URL: %s", GATEWAY_URL)
    yield
    logger.info("Gateway shutting down")

app = FastAPI(title="CrewHub Gateway", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Connection config cache (TTL 60s)
_connection_cache: dict[str, tuple[dict, float]] = {}
CACHE_TTL = 60

async def get_connection_cached(connection_id: str) -> dict | None:
    import time
    cached = _connection_cache.get(connection_id)
    if cached and time.time() - cached[1] < CACHE_TTL:
        return cached[0]
    conn = await billing.get_connection(connection_id)
    if conn:
        _connection_cache[connection_id] = (conn, time.time())
    return conn


@app.get("/health")
async def health():
    return {"status": "ok", "service": "crewhub-gateway"}


# Telegram webhook
@app.post("/webhook/telegram/{connection_id}")
async def telegram_webhook(connection_id: str, request: Request):
    from adapters.telegram import TelegramAdapter

    body = await request.json()
    adapter = TelegramAdapter()

    # Parse message
    message = adapter.parse_inbound(body)
    if not message:
        return Response(status_code=200)

    # Dedup
    if dedup.is_duplicate(connection_id, message.platform_message_id):
        return Response(status_code=200)

    # Rate limit end-user (10 msg/min)
    user_key = f"user:{connection_id}:{message.platform_user_id}"
    if rate_limiter.is_rate_limited(user_key, max_requests=10, window_seconds=60):
        return Response(status_code=200)

    # Ack immediately, process in background
    asyncio.create_task(process_message("telegram", connection_id, message))
    return Response(status_code=200)


# Task callback (called by CrewHub when agent completes)
@app.post("/internal/task-callback/{connection_id}/{chat_id}")
async def task_callback(connection_id: str, chat_id: str, request: Request):
    body = await request.json()
    conn = await get_connection_cached(connection_id)
    if not conn:
        return Response(status_code=404)

    # Get adapter and send response
    platform = conn.get("platform", "telegram")
    if platform == "telegram":
        from adapters.telegram import TelegramAdapter
        adapter = TelegramAdapter()
        text = body.get("result", body.get("artifacts", [{}])[0].get("content", "No response"))
        bot_token = conn.get("bot_token_decrypted", "")
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


async def process_message(platform: str, connection_id: str, message):
    """Background task: check credits, create task, send typing."""
    try:
        conn = await get_connection_cached(connection_id)
        if not conn:
            logger.error("Connection %s not found", connection_id)
            return

        # Check if connection is active
        if conn.get("status") != "active":
            logger.info("Connection %s is %s, skipping", connection_id, conn.get("status"))
            return

        owner_id = conn.get("owner_id", "")
        agent_id = conn.get("agent_id", "")
        skill_id = conn.get("skill_id")

        # Send typing indicator
        if platform == "telegram":
            from adapters.telegram import TelegramAdapter
            adapter = TelegramAdapter()
            bot_token = conn.get("bot_token_decrypted", "")
            await adapter.send_typing(bot_token, message.chat_id)

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
            if platform == "telegram":
                await adapter.send_message(bot_token, message.chat_id, "Sorry, I couldn't process your request right now.")
            return

        # Log inbound message
        await billing.log_message(connection_id, {
            "platform_user_id": message.platform_user_id,
            "platform_message_id": message.platform_message_id,
            "platform_chat_id": message.chat_id,
            "direction": "inbound",
            "message_text": message.text[:500],
            "task_id": task.get("id"),
        })

    except Exception as e:
        logger.exception("Error processing message for %s: %s", connection_id, e)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
