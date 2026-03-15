# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Push notification service for A2A protocol.

When a task status changes and the task has a registered callback_url,
this service POSTs a JSON-RPC notification to that URL.
"""

import logging

import httpx

from src.schemas.a2a import JsonRpcRequest
from src.schemas.agent import _validate_public_url

logger = logging.getLogger(__name__)

PUSH_TIMEOUT = 10  # seconds
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

    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=PUSH_TIMEOUT) as client:
                response = await client.post(
                    callback_url,
                    json=payload.model_dump(),
                    headers={"Content-Type": "application/json"},
                )
                if response.status_code < 300:
                    logger.info(f"Push notification sent for task {task_id} → {callback_url}")
                    return True
                else:
                    logger.warning(
                        f"Push notification attempt {attempt + 1}/{MAX_RETRIES} failed for task {task_id}: "
                        f"HTTP {response.status_code} from {callback_url}"
                    )
        except Exception as e:
            logger.warning(
                f"Push notification attempt {attempt + 1}/{MAX_RETRIES} error for task {task_id}: {e}"
            )

        # Wait before retry (unless this was the last attempt)
        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(RETRY_BACKOFF[attempt])

    logger.error(f"Push notification failed after {MAX_RETRIES} attempts for task {task_id}")
    return False
