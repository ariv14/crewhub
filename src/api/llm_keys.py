# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""LLM API key management endpoints.

Users can store their own API keys (encrypted) for embedding providers.
These keys are used when an agent overrides the platform embedding config.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_user
from src.core.encryption import decrypt_value, encrypt_value
from src.database import get_db
from src.models.user import User
from src.schemas.agent import VALID_EMBEDDING_PROVIDERS

router = APIRouter(prefix="/llm-keys", tags=["llm-keys"])


class LLMKeySet(BaseModel):
    """Set an API key for a provider."""

    provider: str = Field(max_length=20)
    api_key: str = Field(min_length=1, max_length=500)


class LLMKeyResponse(BaseModel):
    provider: str
    is_set: bool
    masked_key: str  # e.g. "sk-...abc"


class LLMKeysListResponse(BaseModel):
    keys: list[LLMKeyResponse]


async def _get_user(db: AsyncSession, current_user: dict) -> User:
    firebase_uid = current_user.get("firebase_uid")
    if firebase_uid:
        result = await db.execute(
            select(User).where(User.firebase_uid == firebase_uid)
        )
    else:
        result = await db.execute(
            select(User).where(User.id == UUID(current_user["id"]))
        )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _mask_key(key: str) -> str:
    """Show first 4 and last 3 characters of a key."""
    if len(key) <= 10:
        return key[:2] + "..." + key[-2:]
    return key[:4] + "..." + key[-3:]


@router.get("/", response_model=LLMKeysListResponse)
async def list_llm_keys(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> LLMKeysListResponse:
    """List all configured LLM API keys (masked) for the current user."""
    user = await _get_user(db, current_user)
    stored = user.llm_api_keys or {}

    keys = []
    for provider in sorted(VALID_EMBEDDING_PROVIDERS):
        encrypted = stored.get(provider, "")
        if encrypted:
            decrypted = decrypt_value(encrypted)
            keys.append(LLMKeyResponse(
                provider=provider,
                is_set=bool(decrypted),
                masked_key=_mask_key(decrypted) if decrypted else "",
            ))
        else:
            keys.append(LLMKeyResponse(provider=provider, is_set=False, masked_key=""))

    return LLMKeysListResponse(keys=keys)


@router.put("/{provider}", response_model=LLMKeyResponse)
async def set_llm_key(
    provider: str,
    data: LLMKeySet,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> LLMKeyResponse:
    """Store (or update) an encrypted LLM API key for a provider."""
    provider = provider.lower()
    if provider not in VALID_EMBEDDING_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider. Must be one of: {', '.join(sorted(VALID_EMBEDDING_PROVIDERS))}",
        )

    user = await _get_user(db, current_user)
    stored = dict(user.llm_api_keys or {})
    stored[provider] = encrypt_value(data.api_key)
    user.llm_api_keys = stored
    await db.commit()

    return LLMKeyResponse(
        provider=provider,
        is_set=True,
        masked_key=_mask_key(data.api_key),
    )


@router.delete("/{provider}")
async def delete_llm_key(
    provider: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Remove an LLM API key for a provider."""
    provider = provider.lower()
    user = await _get_user(db, current_user)
    stored = dict(user.llm_api_keys or {})

    if provider in stored:
        del stored[provider]
        user.llm_api_keys = stored
        await db.commit()

    return {"detail": f"Key for '{provider}' removed"}
