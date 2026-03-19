# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""A2A-to-Langflow adapter — routes JSON-RPC task requests to Langflow flows."""

import logging
import os

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.core.rate_limiter import rate_limit_by_ip

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/langflow", tags=["langflow"])

LANGFLOW_BASE = os.getenv("LANGFLOW_BASE_URL", "https://builder.crewhubai.com")


class LangflowRunRequest(BaseModel):
    """Simplified A2A-compatible request for Langflow flows."""
    jsonrpc: str = "2.0"
    method: str = "tasks/send"
    id: str | int | None = None
    params: dict | None = None


@router.post("/run/{flow_id}", dependencies=[Depends(rate_limit_by_ip)])
async def run_langflow(flow_id: str, body: LangflowRunRequest):
    """Execute a Langflow flow via A2A JSON-RPC interface.

    Accepts a JSON-RPC tasks/send request, extracts the message text,
    forwards it to Langflow, and returns an A2A-formatted response.
    """
    # Extract message text from A2A params
    text = ""
    try:
        message = body.params.get("message", {}) if body.params else {}
        parts = message.get("parts", [])
        if parts:
            part = parts[0] if isinstance(parts[0], dict) else {}
            text = part.get("content", "") or part.get("text", "")
    except (AttributeError, IndexError, TypeError):
        pass

    if not text:
        return {
            "jsonrpc": "2.0",
            "id": body.id,
            "error": {"code": -32602, "message": "No message text provided"},
        }

    # Call Langflow
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                f"{LANGFLOW_BASE}/api/v1/run/{flow_id}",
                json={
                    "input_value": text,
                    "output_type": "text",
                    "input_type": "text",
                },
            )

        if resp.status_code != 200:
            logger.warning("Langflow returned %d for flow %s", resp.status_code, flow_id)
            return {
                "jsonrpc": "2.0",
                "id": body.id,
                "error": {"code": -32000, "message": f"Langflow error: {resp.status_code}"},
            }

        data = resp.json()
        # Extract output text from Langflow response
        output = ""
        outputs = data.get("outputs", [])
        if outputs:
            results = outputs[0].get("outputs", [])
            if results:
                result_data = results[0].get("results", {})
                message_data = result_data.get("message", {})
                output = message_data.get("text", "") or str(message_data.get("data", ""))

        return {
            "jsonrpc": "2.0",
            "id": body.id,
            "result": {
                "status": "completed",
                "artifacts": [
                    {
                        "parts": [{"type": "text", "content": output or "No output from flow"}],
                    }
                ],
            },
        }

    except httpx.TimeoutException:
        return {
            "jsonrpc": "2.0",
            "id": body.id,
            "error": {"code": -32000, "message": "Langflow timeout (90s)"},
        }
    except Exception as e:
        logger.exception("Langflow proxy error for flow %s", flow_id)
        return {
            "jsonrpc": "2.0",
            "id": body.id,
            "error": {"code": -32000, "message": f"Proxy error: {type(e).__name__}"},
        }
