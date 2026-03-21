# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Pydantic schemas for multi-channel gateway."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
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
    channel_id: UUID
    period_days: int
    daily_messages: list[dict]  # [{date, count}]
    daily_credits: list[dict]  # [{date, amount}]
    top_users: list[dict]  # [{platform_user_id, message_count}]
    cost_breakdown: dict  # {agent_processing, platform_surcharge, total, avg_per_message}


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
    message_text: str = ""
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


class GatewayHeartbeatRequest(BaseModel):
    connections: list[dict]


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
