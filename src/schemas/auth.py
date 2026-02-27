from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str
    is_active: bool
    is_admin: bool = False
    created_at: datetime


class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ApiKeyCreate(BaseModel):
    name: str


class ApiKeyResponse(BaseModel):
    key: str
    name: str
    created_at: datetime
