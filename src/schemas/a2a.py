from typing import Any, Optional

from pydantic import BaseModel

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
