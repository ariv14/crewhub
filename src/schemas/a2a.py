from typing import Any, Optional

from pydantic import BaseModel, Field

from src.schemas.task import TaskMessage


class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: dict = {}
    id: Optional[str | int] = None


class JsonRpcResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[dict] = None
    id: Optional[str | int] = None


class SendMessageParams(BaseModel):
    message: TaskMessage


class GetTaskParams(BaseModel):
    id: str


class CancelTaskParams(BaseModel):
    id: str


# ---------------------------------------------------------------------------
# A2A Server-Side SSE Event Types
# ---------------------------------------------------------------------------


class SendTaskParams(BaseModel):
    """Parameters for tasks/send and tasks/sendSubscribe."""
    id: Optional[str] = Field(None, description="Client-assigned task ID")
    message: TaskMessage
    pushNotification: Optional[dict] = Field(None, description="Push notification config with url")


class TaskStatusUpdateEvent(BaseModel):
    """SSE event: task status changed."""
    id: str
    status: str
    final: bool = False
    metadata: dict = {}


class TaskArtifactUpdateEvent(BaseModel):
    """SSE event: new artifact available."""
    id: str
    artifact: dict


class PushNotificationConfig(BaseModel):
    """Push notification endpoint configuration."""
    url: str = Field(max_length=2048)
    token: Optional[str] = Field(None, max_length=500, description="Auth token for the callback")


# ---------------------------------------------------------------------------
# JSON-RPC Error Codes (A2A spec)
# ---------------------------------------------------------------------------

JSONRPC_PARSE_ERROR = -32700
JSONRPC_INVALID_REQUEST = -32600
JSONRPC_METHOD_NOT_FOUND = -32601
JSONRPC_INVALID_PARAMS = -32602
JSONRPC_INTERNAL_ERROR = -32603
JSONRPC_TASK_NOT_FOUND = -32001
JSONRPC_TASK_NOT_CANCELABLE = -32002
