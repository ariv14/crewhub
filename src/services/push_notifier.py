# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Push notification service for A2A protocol.

When a task status changes and the task has a registered callback_url,
this service POSTs a JSON-RPC notification to that URL.
"""

import logging

from src.schemas.a2a import JsonRpcRequest
from src.schemas.agent import _validate_public_url

logger = logging.getLogger(__name__)

PUSH_TIMEOUT = 10  # seconds


def _get_gateway_key() -> str:
    from src.config import settings
    return settings.gateway_service_key or ""
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 4]  # seconds between retries


def validate_callback_url(url: str) -> str:
    """Validate that a callback URL is safe (no SSRF to private IPs)."""
    return _validate_public_url(url)


async def send_push_notification(
    callback_url: str,
    task_id: str,
    status: str,
    artifacts: list | None = None,
) -> bool:
    """POST a JSON-RPC notification to the caller's callback URL.

    Validates the URL against SSRF, retries up to 3 times with exponential
    backoff on failure. Returns True on success, False on failure.
    """
    # SSRF protection: reject private/internal IPs
    try:
        validate_callback_url(callback_url)
    except ValueError as e:
        logger.warning(f"Push notification blocked for task {task_id}: {e}")
        return False

    payload = JsonRpcRequest(
        method="tasks/statusUpdate",
        params={
            "id": task_id,
            "status": status,
            "artifacts": artifacts or [],
        },
    )

    import asyncio

    import json as json_mod

    for attempt in range(MAX_RETRIES):
        try:
            # Use urllib (stdlib) instead of httpx — bypasses HF Spaces DNS issues
            import urllib.request
            import ssl
            data = json_mod.dumps(payload.model_dump()).encode()
            req = urllib.request.Request(
                callback_url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "X-Gateway-Key": _get_gateway_key(),
                },
            )
            ctx = ssl.create_default_context()
            await asyncio.to_thread(
                lambda: urllib.request.urlopen(req, timeout=PUSH_TIMEOUT, context=ctx).read()
            )
            logger.info(f"Push notification sent for task {task_id} → {callback_url}")
            return True
        except Exception as e:
            logger.warning(
                f"Push notification attempt {attempt + 1}/{MAX_RETRIES} error for task {task_id}: {e}"
            )

        # Wait before retry (unless this was the last attempt)
        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(RETRY_BACKOFF[attempt])

    logger.error(f"Push notification failed after {MAX_RETRIES} attempts for task {task_id}")
    return False
