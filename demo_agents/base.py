# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
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
from dataclasses import dataclass, field

# Ensure Ollama uses 127.0.0.1 to avoid DNS/async resolution issues with litellm
if not os.environ.get("OLLAMA_API_BASE"):
    os.environ["OLLAMA_API_BASE"] = "http://127.0.0.1:11434"
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Callable, Awaitable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse


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
    def __init__(
        self,
        name: str | None = None,
        parts: list[MessagePart] | None = None,
        metadata: dict | None = None,
        ui_components: list[dict] | None = None,
    ):
        self.name = name
        self.parts = parts or []
        self.metadata = metadata or {}
        self.ui_components = ui_components or []

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "parts": [p.to_dict() for p in self.parts],
            "metadata": self.metadata,
        }
        if self.ui_components:
            d["ui_components"] = self.ui_components
        return d


# ---------------------------------------------------------------------------
# A2UI helpers — create structured UI components for rich rendering
# ---------------------------------------------------------------------------

def emit_table(title: str, headers: list[str], rows: list[list], caption: str | None = None) -> dict:
    """Create a table UI component."""
    return {"type": "table", "title": title, "data": {"headers": headers, "rows": rows, "caption": caption}, "metadata": {}}

def emit_chart(title: str, chart_type: str, labels: list[str], datasets: list[dict]) -> dict:
    """Create a chart UI component (bar, line, pie, area)."""
    return {"type": "chart", "title": title, "data": {"chart_type": chart_type, "labels": labels, "datasets": datasets}, "metadata": {}}

def emit_code(code: str, language: str, filename: str | None = None, title: str | None = None) -> dict:
    """Create a syntax-highlighted code block UI component."""
    return {"type": "code_block", "title": title or filename, "data": {"code": code, "language": language, "filename": filename}, "metadata": {}}

def emit_diff(before: str, after: str, language: str | None = None, title: str | None = None) -> dict:
    """Create a side-by-side diff UI component."""
    return {"type": "diff", "title": title, "data": {"before": before, "after": after, "language": language}, "metadata": {}}

def emit_image(url: str, alt: str | None = None, title: str | None = None) -> dict:
    """Create an image UI component."""
    return {"type": "image", "title": title, "data": {"url": url, "alt": alt}, "metadata": {}}


# ---------------------------------------------------------------------------
# MCP Toolkit — allows agents to call external tools via MCP protocol
# ---------------------------------------------------------------------------

class MCPToolkit:
    """Client for accessing MCP servers granted to this agent at dispatch time.

    Initialized from ``mcp_context`` injected into the task params by the
    platform. Each server entry has: name, url, and optional auth headers.

    Usage in handler::

        async def handle(skill_id, messages, mcp=None):
            if mcp:
                tools = await mcp.list_tools("github")
                result = await mcp.call_tool("github", "search_code", {"query": "auth"})
    """

    def __init__(self, servers: list[dict]):
        import httpx
        self._servers: dict[str, dict] = {}
        self._clients: dict[str, httpx.AsyncClient] = {}
        for s in servers:
            name = s["name"]
            self._servers[name] = s
            headers = {"Content-Type": "application/json"}
            if s.get("token"):
                headers["Authorization"] = f"Bearer {s['token']}"
            elif s.get("api_key"):
                headers["X-API-Key"] = s["api_key"]
            self._clients[name] = httpx.AsyncClient(
                timeout=30, headers=headers,
            )

    @property
    def server_names(self) -> list[str]:
        return list(self._servers.keys())

    async def list_tools(self, server_name: str) -> list[dict]:
        """List available tools on a named MCP server."""
        client = self._clients.get(server_name)
        url = self._servers.get(server_name, {}).get("url")
        if not client or not url:
            return []
        try:
            resp = await client.post(url, json={
                "jsonrpc": "2.0", "method": "tools/list", "id": 1,
            })
            resp.raise_for_status()
            return resp.json().get("result", {}).get("tools", [])
        except Exception as e:
            logger.warning("MCP list_tools failed for %s: %s", server_name, e)
            return []

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict | None = None) -> dict:
        """Call a tool on a named MCP server."""
        client = self._clients.get(server_name)
        url = self._servers.get(server_name, {}).get("url")
        if not client or not url:
            return {"error": f"MCP server '{server_name}' not available"}
        try:
            resp = await client.post(url, json={
                "jsonrpc": "2.0", "method": "tools/call", "id": 2,
                "params": {"name": tool_name, "arguments": arguments or {}},
            })
            resp.raise_for_status()
            data = resp.json()
            if data.get("error"):
                return {"error": data["error"]}
            return data.get("result", {})
        except Exception as e:
            logger.warning("MCP call_tool '%s' on %s failed: %s", tool_name, server_name, e)
            return {"error": str(e)}

    async def close(self):
        for client in self._clients.values():
            await client.aclose()


# Handler signature:
#   async def handler(skill_id: str, messages: list[TaskMessage]) -> list[Artifact]
HandlerFunc = Callable[[str, list[TaskMessage]], Awaitable[list[Artifact]]]


# ---------------------------------------------------------------------------
# AG-UI Streaming types
# ---------------------------------------------------------------------------

@dataclass
class StreamChunk:
    """A single chunk emitted by a streaming agent handler.

    Types:
      - "thinking"  — agent reasoning (shown collapsed in UI)
      - "text"      — partial text output (appended progressively)
      - "artifact"  — complete artifact (rendered when received)
      - "status"    — status change (e.g. "working")
      - "error"     — error message
      - "done"      — final signal with optional artifact list
    """
    type: str  # thinking | text | artifact | status | error | done
    content: str = ""
    artifact: Artifact | None = None
    artifacts: list[Artifact] | None = None  # used with "done" to send all final artifacts
    metadata: dict = field(default_factory=dict)

    def to_sse(self) -> str:
        """Serialize to SSE event format."""
        import json
        data: dict[str, Any] = {"type": self.type}
        if self.content:
            data["content"] = self.content
        if self.artifact:
            data["artifact"] = self.artifact.to_dict()
        if self.artifacts:
            data["artifacts"] = [a.to_dict() for a in self.artifacts]
        if self.metadata:
            data["metadata"] = self.metadata
        return f"event: {self.type}\ndata: {json.dumps(data)}\n\n"


# Streaming handler signature — yields StreamChunks instead of returning artifacts
StreamingHandlerFunc = Callable[
    [str, list[TaskMessage]],
    AsyncGenerator[StreamChunk, None],
]

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


async def llm_call_streaming(
    system_prompt: str,
    user_message: str,
    model: str | None = None,
) -> AsyncGenerator[str, None]:
    """Streaming version of llm_call — yields text chunks as they arrive.

    Falls back to non-streaming llm_call if streaming is unavailable.
    """
    global _router
    explicit_model = model or os.environ.get("MODEL")

    # Ollama: stream via httpx
    if explicit_model and explicit_model.lower().startswith("ollama/"):
        import httpx
        base = os.environ.get("OLLAMA_API_BASE", "http://127.0.0.1:11434")
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        timeout = httpx.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{base}/api/chat",
                json={"model": explicit_model.split("/", 1)[1], "messages": messages, "stream": True},
            ) as resp:
                resp.raise_for_status()
                import json
                async for line in resp.aiter_lines():
                    if line.strip():
                        try:
                            chunk = json.loads(line)
                            content = chunk.get("message", {}).get("content", "")
                            if content:
                                yield content
                        except (ValueError, KeyError):
                            pass
        return

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    # Try Router streaming first
    if _router is None:
        _router = _build_router() or False
    if _router:
        try:
            response = await _router.acompletion(
                model="agent-llm", messages=messages, stream=True,
            )
            async for chunk in response:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
            return
        except Exception as exc:
            logger.warning("Router streaming failed: %s: %s", type(exc).__name__, exc)

    # Fallback: direct single-model streaming
    if explicit_model:
        try:
            import litellm
            response = await litellm.acompletion(
                model=explicit_model, messages=messages, timeout=60, stream=True,
            )
            async for chunk in response:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
            return
        except Exception as exc:
            logger.warning("Direct LLM streaming failed (%s): %s: %s", explicit_model, type(exc).__name__, exc)

    # Last resort: yield the full non-streaming response as one chunk
    result = await llm_call(system_prompt, user_message, model)
    yield result


# In-memory task store shared within one process
_task_store: dict[str, dict] = {}

# Per-request MCP toolkit (set before handler call, cleared after)
_current_mcp: MCPToolkit | None = None


def get_mcp() -> MCPToolkit | None:
    """Get the MCP toolkit for the current request, if any.

    Usage in handler::

        from demo_agents.base import get_mcp
        mcp = get_mcp()
        if mcp:
            result = await mcp.call_tool("github", "search_code", {"query": "auth"})
    """
    return _current_mcp


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
    streaming_handler_func: StreamingHandlerFunc | None = None,
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
    streaming_handler_func:
        Optional async generator ``(skill_id, messages) -> StreamChunk``.
        When provided, the agent advertises ``streaming: true`` in its card
        and supports the ``tasks/sendSubscribe`` SSE method.
    """

    supports_streaming = streaming_handler_func is not None
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
            "streaming": supports_streaming,
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
        elif method == "tasks/sendSubscribe":
            return await _handle_send_subscribe(params, req_id, jsonrpc)
        else:
            return _error_response(req_id, -32601, f"Method not found: {method}", jsonrpc)

    # -- tasks/send -----------------------------------------------------------

    async def _handle_send(params: dict, req_id: Any, jsonrpc: str):
        global _current_mcp
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

            # Initialize MCP toolkit if platform injected mcp_context
            mcp_context = params.get("mcp_context", [])
            if mcp_context:
                _current_mcp = MCPToolkit(mcp_context)
            else:
                _current_mcp = None

            # Execute
            try:
                artifacts = await handler_func(skill_id, messages)
            finally:
                if _current_mcp:
                    await _current_mcp.close()
                    _current_mcp = None

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

    # -- tasks/sendSubscribe (AG-UI streaming) --------------------------------

    async def _handle_send_subscribe(params: dict, req_id: Any, jsonrpc: str):
        """Stream task execution via Server-Sent Events.

        If a streaming_handler_func was provided, yields chunks in real-time.
        Otherwise falls back to running handler_func and emitting the result
        as a single artifact event.
        """
        global _current_mcp
        import json as _json

        task_id = params.get("id") or str(uuid.uuid4())
        metadata = params.get("metadata", {})
        skill_id = params.get("skill_id") or metadata.get("skill_id") or _default_skill_id()
        raw_messages = params.get("message", params.get("messages", []))
        if isinstance(raw_messages, dict):
            raw_messages = [raw_messages]
        messages = [TaskMessage.from_dict(m) for m in raw_messages]

        # Initialize MCP toolkit if platform injected mcp_context
        mcp_context = params.get("mcp_context", [])
        if mcp_context:
            _current_mcp = MCPToolkit(mcp_context)
        else:
            _current_mcp = None

        async def _stream_generator():
            # Emit initial status
            yield StreamChunk(type="status", content="working").to_sse()

            try:
                if streaming_handler_func is not None:
                    # True streaming — yield each chunk from the handler
                    final_artifacts: list[Artifact] = []
                    accumulated_text = ""

                    async for chunk in streaming_handler_func(skill_id, messages):
                        yield chunk.to_sse()

                        # Track artifacts for final task store
                        if chunk.type == "artifact" and chunk.artifact:
                            final_artifacts.append(chunk.artifact)
                        elif chunk.type == "text":
                            accumulated_text += chunk.content
                        elif chunk.type == "done" and chunk.artifacts:
                            final_artifacts = chunk.artifacts

                    # If no explicit artifacts were emitted, create one from accumulated text
                    if not final_artifacts and accumulated_text:
                        final_artifacts = [Artifact(
                            name="response",
                            parts=[MessagePart(type="text", content=accumulated_text)],
                            metadata={"skill": skill_id, "streamed": True},
                        )]

                    # Emit done with final artifacts
                    done_chunk = StreamChunk(
                        type="done",
                        artifacts=final_artifacts,
                        metadata={"credits_charged": credits_per_task},
                    )
                    yield done_chunk.to_sse()

                else:
                    # Non-streaming fallback — run handler, emit result as single event
                    artifacts = await handler_func(skill_id, messages)
                    for artifact in artifacts:
                        yield StreamChunk(type="artifact", artifact=artifact).to_sse()
                    yield StreamChunk(
                        type="done",
                        artifacts=artifacts,
                        metadata={"credits_charged": credits_per_task},
                    ).to_sse()

            except Exception as exc:
                logger.exception("Streaming handler error")
                yield StreamChunk(type="error", content=str(exc)).to_sse()

            # Clean up MCP toolkit
            if _current_mcp:
                await _current_mcp.close()

            # Store final task
            task = {
                "id": task_id,
                "status": {"state": "completed"},
                "messages": [m.to_dict() for m in messages],
                "artifacts": [a.to_dict() for a in (final_artifacts if streaming_handler_func else artifacts)],
                "metadata": {
                    "credits_charged": credits_per_task,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                },
            }
            _task_store[task_id] = task

        return StreamingResponse(
            _stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

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
