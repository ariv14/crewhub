import re
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str

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
    name: str | None = None
    interests: list[str] = []


class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    daily_spend_limit: float | None = Field(None, ge=0, le=100_000)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ApiKeyCreate(BaseModel):
    name: str


class ApiKeyResponse(BaseModel):
    key: str
    name: str
    created_at: datetime
