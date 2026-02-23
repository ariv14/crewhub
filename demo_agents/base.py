"""Shared A2A protocol handler for demo agents.

Provides a factory function that creates a FastAPI app implementing the
Google A2A (Agent-to-Agent) protocol with:
  - GET  /.well-known/agent-card.json  -- agent card discovery
  - POST /                             -- JSON-RPC 2.0 dispatch
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


# ---------------------------------------------------------------------------
# Types used by handler functions
# ---------------------------------------------------------------------------

class MessagePart:
    """Lightweight mirror of the marketplace MessagePart schema."""

    def __init__(self, type: str, content: str | None = None, data: dict | None = None, mime_type: str | None = None):
        self.type = type
        self.content = content
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

    agent_card = {
        "name": name,
        "description": description,
        "url": f"http://localhost:{port}",
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
            skill_id = params.get("skill_id") or _default_skill_id()
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
