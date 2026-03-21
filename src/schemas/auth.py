# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
import re
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(max_length=100)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = re.sub(r"<[^>]*>", "", v).strip()
        if not v:
            raise ValueError("Name cannot be empty or only HTML tags")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str
    is_active: bool
    is_admin: bool = False
    onboarding_completed: bool = False
    account_tier: str = "free"
    daily_spend_limit: float | None = None
    interests: list[str] = []
    created_at: datetime


class OnboardingComplete(BaseModel):
    name: str | None = Field(None, max_length=100)
    interests: list[str] = []

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = re.sub(r"<[^>]*>", "", v).strip()
        if not v:
            raise ValueError("Name cannot be empty or only HTML tags")
        return v


class UserUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    email: EmailStr | None = None
    daily_spend_limit: float | None = Field(None, ge=0, le=100_000)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        # Strip HTML tags to prevent stored XSS
        v = re.sub(r"<[^>]*>", "", v).strip()
        if not v:
            raise ValueError("Name cannot be empty or only HTML tags")
        return v


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ApiKeyCreate(BaseModel):
    name: str


class ApiKeyResponse(BaseModel):
    key: str
    name: str
    created_at: datetime
