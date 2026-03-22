# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Pydantic schemas for multi-channel gateway."""

from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChannelCreate(BaseModel):
    platform: str = Field(pattern=r"^(telegram|slack|discord|teams|whatsapp)$")
    credentials: dict  # platform-specific tokens, never returned in responses
    bot_name: str = Field(max_length=200)
    agent_id: UUID
    skill_id: Optional[UUID] = None
    daily_credit_limit: Optional[int] = Field(None, ge=1)
    low_balance_threshold: int = Field(20, ge=1)
    pause_on_limit: bool = True


class ChannelUpdate(BaseModel):
    bot_name: Optional[str] = Field(None, max_length=200)
    agent_id: Optional[UUID] = None
    skill_id: Optional[UUID] = None
    daily_credit_limit: Optional[int] = Field(None, ge=0)  # 0 = unlimited
    low_balance_threshold: Optional[int] = Field(None, ge=1)
    pause_on_limit: Optional[bool] = None
    status: Optional[str] = Field(None, pattern=r"^(active|paused)$")


class ChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    platform: str
    bot_name: str
    agent_id: UUID
    skill_id: Optional[UUID] = None
    status: str
    paused_reason: Optional[str] = None
    daily_credit_limit: Optional[int] = None
    low_balance_threshold: int
    pause_on_limit: bool
    webhook_url: Optional[str] = None
    error_message: Optional[str] = None
    last_active_at: Optional[datetime] = None
    messages_today: int = 0  # computed field
    credits_used_today: Decimal = Decimal("0")  # computed field
    created_at: datetime
    updated_at: datetime


class ChannelListResponse(BaseModel):
    channels: list[ChannelResponse]
    total: int


class ChannelAnalytics(BaseModel):
    daily: list[dict] = []  # [{date, messages, credits}]
    total_messages: int = 0
    total_credits: float = 0


class ChannelTestResult(BaseModel):
    success: bool
    message: str
    latency_ms: Optional[int] = None


# ---------------------------------------------------------------------------
# Gateway-facing schemas (server-to-server, authenticated via X-Gateway-Key)
# ---------------------------------------------------------------------------

class GatewayChargeRequest(BaseModel):
    connection_id: UUID
    platform_user_id: str
    credits: float = Field(gt=0, le=100)
    daily_credit_limit: Optional[int] = None  # for server-side limit check


class GatewayChargeResponse(BaseModel):
    success: bool
    remaining_balance: float = 0
    today_usage: float = 0
    error: Optional[str] = None


class GatewayLogMessageRequest(BaseModel):
    connection_id: UUID
    platform_user_id: str
    platform_message_id: str
    platform_chat_id: Optional[str] = None
    direction: str = Field(pattern="^(inbound|outbound|system)$")
    message_text: str
    media_type: Optional[str] = None
    task_id: Optional[UUID] = None
    credits_charged: float = 0
    response_time_ms: Optional[int] = None
    error: Optional[str] = None


class HeartbeatConnectionStatus(BaseModel):
    connection_id: UUID
    status: Literal["active", "paused", "error", "disconnected"]
    error_message: str | None = Field(None, max_length=500)


class GatewayHeartbeatRequest(BaseModel):
    connections: list[HeartbeatConnectionStatus] = Field(max_length=100)


class GatewayCreateTaskRequest(BaseModel):
    """Task creation request from the gateway service.

    ``owner_id`` identifies whose credits will be reserved for the task.
    """

    owner_id: UUID
    provider_agent_id: UUID
    skill_id: str | None = Field(None, max_length=255)
    message: str = Field(max_length=10_000)
    callback_url: str | None = Field(None, max_length=2000)


class GatewayConnectionResponse(BaseModel):
    id: UUID
    owner_id: UUID
    platform: str
    bot_token: str
    webhook_secret: Optional[str] = None
    agent_id: UUID
    skill_id: Optional[UUID] = None
    status: str
    daily_credit_limit: Optional[int] = None
    pause_on_limit: bool = True
    low_balance_threshold: int = 20
    config: Optional[dict] = None
    blocked_users: list[str] = []


# ---------------------------------------------------------------------------
# Contact management schemas
# ---------------------------------------------------------------------------

class ChannelContactResponse(BaseModel):
    platform_user_id_hash: str
    message_count: int
    last_seen: datetime
    first_seen: datetime
    is_blocked: bool = False


class ChannelContactListResponse(BaseModel):
    contacts: list[ChannelContactResponse]
    total: int


class ChannelMessageResponse(BaseModel):
    id: UUID
    direction: str
    platform_user_id_hash: str
    message_text: str | None = None
    credits_charged: float
    response_time_ms: int | None = None
    created_at: datetime


class ChannelMessageListResponse(BaseModel):
    messages: list[ChannelMessageResponse]
    cursor: str | None = None
    has_more: bool = False


class AdminChannelResponse(ChannelResponse):
    owner_email: str = ""
    owner_name: str = ""
    owner_credit_balance: float = 0
    owner_account_tier: str = "free"


class ChannelAnalyticsResponse(BaseModel):
    daily: list[dict] = []
    total_messages: int = 0
    total_credits: float = 0
    avg_response_ms: float | None = None


class GDPRErasureResponse(BaseModel):
    deleted_messages: int
    user_hash: str
    channel_id: UUID


class AdminMessageAccessRequest(BaseModel):
    justification: Literal["abuse_report", "developer_support", "legal_request", "compliance_check"]
