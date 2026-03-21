import asyncio
import hashlib
import logging
import re
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from config import settings
from crewhub_client import CrewHubClient
from rate_limiter import InMemoryRateLimiter
from dedup import MessageDedup
from billing import check_and_charge
from adapters import get_adapter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("gateway")

# Global instances
client: CrewHubClient | None = None
rate_limiter = InMemoryRateLimiter(max_requests=10, window_seconds=60)
dedup = MessageDedup(ttl=300)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    if not settings.gateway_service_key:
        logger.error("GATEWAY_SERVICE_KEY not set — gateway will not function")
    client = CrewHubClient()
    logger.info("Gateway started — CrewHub API: %s", settings.crewhub_api_url)
    yield
    if client and client._client:
        await client._client.aclose()
    logger.info("Gateway stopped")

app = FastAPI(title="CrewHub Gateway", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "crewhub-gateway"}


@app.post("/webhook/telegram/{connection_id}")
async def telegram_webhook(connection_id: str, request: Request):
    """Receive Telegram webhook — acknowledge immediately, process async."""
    # Read raw bytes first (needed for signature verification), then parse JSON
    body_bytes = await request.body()
    import json
    try:
        body = json.loads(body_bytes)
    except Exception:
        return JSONResponse(status_code=400, content={"detail": "Invalid JSON"})

    adapter = get_adapter("telegram")

    # Verify webhook signature using per-connection secret derived from gateway_service_key
    # The same derivation is used when calling Telegram's setWebhook (see channel_service.py)
    headers = dict(request.headers)
    webhook_secret = ""
    if settings.gateway_service_key:
        webhook_secret = hashlib.sha256(
            f"{settings.gateway_service_key}:{connection_id}".encode()
        ).hexdigest()[:32]
    if not adapter.verify_webhook(body_bytes, headers, webhook_secret):
        logger.warning("Telegram webhook signature mismatch for connection %s — rejecting", connection_id)
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

    # Parse the message
    message = adapter.parse_inbound(body)
    if not message:
        return adapter.ack_response()

    # Deduplicate
    if dedup.is_duplicate(connection_id, message.platform_message_id):
        return adapter.ack_response()

    # Rate limit per end-user
    if rate_limiter.is_limited(f"{connection_id}:{message.platform_user_id}"):
        return adapter.ack_response()

    # Acknowledge immediately — Telegram requires response within 3 seconds
    asyncio.create_task(process_message("telegram", connection_id, message))
    return adapter.ack_response()


async def process_message(platform: str, connection_id: str, message):
    """Background processing after webhook acknowledgement."""
    try:
        adapter = get_adapter(platform)

        # Get connection config (cached 60s)
        connection = await client.get_connection(connection_id)
        if not connection or connection.get("status") != "active":
            logger.warning("Connection %s not found or inactive", connection_id)
            return

        bot_token = connection.get("bot_token", "")

        # Send typing indicator while processing
        await adapter.send_typing(bot_token, message.platform_chat_id)

        # Check credits + charge atomically
        surcharge = 2.0 if platform == "whatsapp" else 0.0
        ok, error = await check_and_charge(client, connection, message.text, surcharge)
        if not ok:
            error_msgs = {
                "daily_limit": "Daily message limit reached. Service will resume tomorrow.",
                "credit_exhausted": "Service temporarily unavailable.",
                "insufficient_balance": "Service temporarily unavailable.",
            }
            await adapter.send_message(bot_token, message.platform_chat_id,
                                       error_msgs.get(error, "Service temporarily unavailable."))
            return

        # Log inbound message
        await client.log_message({
            "connection_id": connection_id,
            "platform_user_id": message.platform_user_id,
            "platform_message_id": message.platform_message_id,
            "platform_chat_id": message.platform_chat_id,
            "direction": "inbound",
            "message_text": message.text,
            "media_type": message.media_type,
        })

        # Create task with callback URL
        callback_url = f"{settings.gateway_public_url}/internal/task-callback/{connection_id}/{message.platform_chat_id}"
        task = await client.create_task(
            agent_id=str(connection["agent_id"]),
            skill_id=str(connection["skill_id"]) if connection.get("skill_id") else None,
            message=message.text,
            owner_id=str(connection["owner_id"]),
            callback_url=callback_url,
        )

        if "error" in task:
            logger.error("Task creation failed: %s", task["error"])
            await adapter.send_message(bot_token, message.platform_chat_id,
                                       "Sorry, I couldn't process your request. Please try again.")
            return

        logger.info("Task %s created for connection %s", task.get("id"), connection_id)

    except Exception as e:
        logger.exception("Error processing message for connection %s: %s", connection_id, e)


@app.post("/internal/task-callback/{connection_id}/{chat_id}")
async def task_callback(connection_id: str, chat_id: str, request: Request):
    """Receive task completion callback from CrewHub backend."""
    # Verify shared secret
    gateway_key = request.headers.get("X-Gateway-Key", "")
    if not settings.gateway_service_key or gateway_key != settings.gateway_service_key:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

    body = await request.json()

    # Get connection to find platform + bot token
    connection = await client.get_connection(connection_id)
    if not connection:
        logger.warning("Callback for unknown connection %s", connection_id)
        return {"status": "connection_not_found"}

    adapter = get_adapter(connection["platform"])
    bot_token = connection.get("bot_token", "")

    # Extract response text from task result
    # The callback body has: {task_id, status, artifacts: [{parts: [{type: "text", content: "..."}]}]}
    response_text = "Task completed."
    artifacts = body.get("artifacts", [])
    if artifacts:
        parts = artifacts[0].get("parts", [])
        for part in parts:
            if part.get("type") == "text" and part.get("content"):
                response_text = part["content"]
                break

    # Send response to platform
    success = await adapter.send_message(bot_token, chat_id, response_text)

    # Log outbound message
    await client.log_message({
        "connection_id": connection_id,
        "platform_user_id": "agent",
        "platform_message_id": f"cb-{body.get('task_id', 'unknown')}",
        "platform_chat_id": chat_id,
        "direction": "outbound",
        "message_text": response_text[:500],
        "task_id": body.get("task_id"),
        "credits_charged": body.get("credits_used", 0),
        "response_time_ms": body.get("latency_ms"),
    })

    return {"status": "delivered" if success else "delivery_failed"}
