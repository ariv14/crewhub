"""Shared A2A protocol handler for demo agents.

Provides a factory function that creates a FastAPI app implementing the
Google A2A (Agent-to-Agent) protocol with:
  - GET  /.well-known/agent-card.json  -- agent card discovery
  - POST /                             -- JSON-RPC 2.0 dispatch
"""

from __future__ import annotations

import logging
import os
import uuid

# Ensure Ollama uses 127.0.0.1 to avoid DNS/async resolution issues with litellm
if not os.environ.get("OLLAMA_API_BASE"):
    os.environ["OLLAMA_API_BASE"] = "http://127.0.0.1:11434"
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


# ---------------------------------------------------------------------------
# Types used by handler functions
# ---------------------------------------------------------------------------

class MessagePart:
    """Lightweight mirror of the marketplace MessagePart schema."""

    def __init__(self, type: str, content: str | None = None, data: dict | None = None, mime_type: str | None = None, text: str | None = None):
        self.type = type
        # A2A spec uses "text"; our internal convention uses "content". Accept both.
        self.content = content or text
        self.data = data
        self.mime_type = mime_type

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"type": self.type}
        if self.content is not None:
            d["content"] = self.content
        if self.data is not None:
            d["data"] = self.data
        if self.mime_type is not None:
            d["mime_type"] = self.mime_type
        return d


class TaskMessage:
    def __init__(self, role: str, parts: list[MessagePart]):
        self.role = role
        self.parts = parts

    @classmethod
    def from_dict(cls, d: dict) -> "TaskMessage":
        parts = [MessagePart(**p) for p in d.get("parts", [])]
        return cls(role=d["role"], parts=parts)

    def to_dict(self) -> dict:
        return {"role": self.role, "parts": [p.to_dict() for p in self.parts]}


class Artifact:
    def __init__(self, name: str | None = None, parts: list[MessagePart] | None = None, metadata: dict | None = None):
        self.name = name
        self.parts = parts or []
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "parts": [p.to_dict() for p in self.parts],
            "metadata": self.metadata,
        }


# Handler signature:
#   async def handler(skill_id: str, messages: list[TaskMessage]) -> list[Artifact]
HandlerFunc = Callable[[str, list[TaskMessage]], Awaitable[list[Artifact]]]

logger = logging.getLogger(__name__)


async def _ollama_call(
    model_name: str,
    system_prompt: str,
    user_message: str,
) -> str:
    """Call Ollama directly via httpx (bypasses LiteLLM async issues)."""
    import httpx

    base = os.environ.get("OLLAMA_API_BASE", "http://127.0.0.1:11434")
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    # connect quickly, but allow up to 5min for generation on slow hardware
    timeout = httpx.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{base}/api/chat",
            json={"model": model_name, "messages": messages, "stream": False},
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]


# ---------------------------------------------------------------------------
# Multi-provider LLM Router (built once at import time)
# ---------------------------------------------------------------------------

# Provider definitions: (env_var, model_string, rpm_limit)
_PROVIDER_DEFS = [
    ("GROQ_API_KEY", "groq/llama-3.3-70b-versatile", 30),
    ("CEREBRAS_API_KEY", "cerebras/llama-3.3-70b", 30),
    ("SAMBANOVA_API_KEY", "sambanova/Meta-Llama-3.3-70B-Instruct", 20),
    ("GEMINI_API_KEY", "gemini/gemini-2.0-flash", 15),
]

_router = None  # Lazy-initialized on first call


def _build_router():
    """Build a LiteLLM Router from available API keys. Returns None if no keys."""
    try:
        from litellm import Router
    except ImportError:
        return None

    model_list = []
    for env_var, model_str, rpm in _PROVIDER_DEFS:
        key = os.environ.get(env_var)
        if key:
            model_list.append({
                "model_name": "agent-llm",
                "litellm_params": {
                    "model": model_str,
                    "api_key": key,
                    "rpm": rpm,
                },
            })

    if not model_list:
        return None

    providers = [m["litellm_params"]["model"] for m in model_list]
    logger.info("LLM Router initialized with %d providers: %s", len(model_list), providers)

    return Router(
        model_list=model_list,
        num_retries=2,
        timeout=30,
        allowed_fails=3,
        cooldown_time=60,
        retry_after=1,
    )


async def llm_call(
    system_prompt: str,
    user_message: str,
    model: str | None = None,
) -> str:
    """Call an LLM with automatic multi-provider fallback.

    Uses LiteLLM Router to load-balance across available providers and
    automatically retry on 429/500 errors. Falls back to single-model
    call if MODEL env var is set explicitly, or echo if nothing works.
    """
    global _router
    explicit_model = model or os.environ.get("MODEL")

    # Ollama: bypass router entirely
    if explicit_model and explicit_model.lower().startswith("ollama/"):
        try:
            return await _ollama_call(explicit_model.split("/", 1)[1], system_prompt, user_message)
        except Exception as exc:
            logger.warning("Ollama call failed: %s: %s", type(exc).__name__, exc)
            return f"[LLM unavailable — echoing input]\n\n{user_message}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    # Try Router first (multi-provider with automatic failover)
    if _router is None:
        _router = _build_router() or False  # False = no keys available
    if _router:
        try:
            response = await _router.acompletion(model="agent-llm", messages=messages)
            return response.choices[0].message.content
        except Exception as exc:
            logger.warning("Router call failed: %s: %s", type(exc).__name__, exc)

    # Fallback: direct single-model call (if MODEL env var set)
    if explicit_model:
        try:
            import litellm
            response = await litellm.acompletion(
                model=explicit_model, messages=messages, timeout=60,
            )
            return response.choices[0].message.content
        except Exception as exc:
            logger.warning("Direct LLM call failed (%s): %s: %s", explicit_model, type(exc).__name__, exc)

    return f"[LLM unavailable — echoing input]\n\n{user_message}"


# In-memory task store shared within one process
_task_store: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_a2a_app(
    name: str,
    description: str,
    version: str,
    skills: list[dict],
    handler_func: HandlerFunc,
    port: int,
    credits_per_task: float = 1,
) -> FastAPI:
    """Create a FastAPI app that speaks the A2A protocol.

    Parameters
    ----------
    name:
        Human-readable agent name.
    description:
        Short description shown in the agent card.
    version:
        Semantic version string.
    skills:
        List of skill dicts following the A2A agent-card skill schema.
    handler_func:
        Async callable ``(skill_id, messages) -> list[Artifact]``.
    port:
        Port number the agent listens on (used for the agent card URL).
    credits_per_task:
        Credit cost advertised for every task handled by this agent.
    """

    app = FastAPI(title=name, version=version)

    # -- Agent card -----------------------------------------------------------

    # Use AGENT_URL env var when deployed (e.g. HF Spaces), else localhost
    base_url = os.environ.get("AGENT_URL", f"http://localhost:{port}")

    agent_card = {
        "name": name,
        "description": description,
        "url": base_url,
        "version": version,
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": False,
        },
        "skills": skills,
        "securitySchemes": [],
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text"],
        "pricing": {
            "model": "per_task",
            "credits": credits_per_task,
        },
    }

    @app.get("/.well-known/agent-card.json")
    async def get_agent_card():
        return agent_card

    # -- JSON-RPC 2.0 dispatch -----------------------------------------------

    @app.post("/")
    async def jsonrpc_dispatch(request: Request):
        body = await request.json()

        jsonrpc = body.get("jsonrpc", "2.0")
        method = body.get("method")
        params = body.get("params", {})
        req_id = body.get("id")

        if method == "tasks/send":
            return await _handle_send(params, req_id, jsonrpc)
        elif method == "tasks/get":
            return await _handle_get(params, req_id, jsonrpc)
        elif method == "tasks/cancel":
            return await _handle_cancel(params, req_id, jsonrpc)
        else:
            return _error_response(req_id, -32601, f"Method not found: {method}", jsonrpc)

    # -- tasks/send -----------------------------------------------------------

    async def _handle_send(params: dict, req_id: Any, jsonrpc: str):
        try:
            task_id = params.get("id") or str(uuid.uuid4())
            metadata = params.get("metadata", {})
            skill_id = params.get("skill_id") or metadata.get("skill_id") or _default_skill_id()
            raw_messages = params.get("message", params.get("messages", []))

            # Accept a single message dict or a list of messages
            if isinstance(raw_messages, dict):
                raw_messages = [raw_messages]
            messages = [TaskMessage.from_dict(m) for m in raw_messages]

            # Resolve skill_id from first message if caller put it there
            if not skill_id:
                skill_id = _default_skill_id()

            # Execute
            artifacts = await handler_func(skill_id, messages)

            task = {
                "id": task_id,
                "status": {"state": "completed"},
                "messages": [m.to_dict() for m in messages],
                "artifacts": [a.to_dict() for a in artifacts],
                "metadata": {
                    "credits_charged": credits_per_task,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                },
            }
            _task_store[task_id] = task

            return JSONResponse(content={
                "jsonrpc": jsonrpc,
                "id": req_id,
                "result": task,
            })
        except Exception as exc:
            return _error_response(req_id, -32000, str(exc), jsonrpc)

    # -- tasks/get ------------------------------------------------------------

    async def _handle_get(params: dict, req_id: Any, jsonrpc: str):
        task_id = params.get("id")
        task = _task_store.get(task_id)
        if task is None:
            return _error_response(req_id, -32001, f"Task not found: {task_id}", jsonrpc)
        return JSONResponse(content={
            "jsonrpc": jsonrpc,
            "id": req_id,
            "result": task,
        })

    # -- tasks/cancel ---------------------------------------------------------

    async def _handle_cancel(params: dict, req_id: Any, jsonrpc: str):
        task_id = params.get("id")
        task = _task_store.get(task_id)
        if task is None:
            return _error_response(req_id, -32001, f"Task not found: {task_id}", jsonrpc)
        task["status"] = {"state": "canceled"}
        return JSONResponse(content={
            "jsonrpc": jsonrpc,
            "id": req_id,
            "result": task,
        })

    # -- helpers --------------------------------------------------------------

    def _default_skill_id() -> str:
        if skills:
            return skills[0]["id"]
        return "default"

    def _error_response(req_id: Any, code: int, message: str, jsonrpc: str = "2.0"):
        return JSONResponse(content={
            "jsonrpc": jsonrpc,
            "id": req_id,
            "error": {"code": code, "message": message},
        })

    return app
