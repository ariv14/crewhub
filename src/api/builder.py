# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Builder API — auth bridge for Langflow iframe."""

import hashlib
import logging
import os
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.core.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/builder", tags=["builder"])

# Simple in-memory exchange code store (short-lived, single-use)
_exchange_codes: dict[str, dict] = {}

POOL_SPACES = [
    "https://arimatch1-crewhub-langflow-pool-02.hf.space",
    "https://arimatch1-crewhub-langflow-pool-03.hf.space",
]


class ExchangeCodeResponse(BaseModel):
    code: str
    expires_in: int
    builder_url: str


@router.post("/exchange-code", response_model=ExchangeCodeResponse)
async def create_exchange_code(
    current_user: dict = Depends(get_current_user),
):
    """Generate a short-lived exchange code for Langflow iframe auth."""
    user_id = current_user.get("id", "")

    # Generate opaque code
    raw = f"{user_id}:{time.time()}:{os.urandom(16).hex()}"
    code = hashlib.sha256(raw.encode()).hexdigest()[:32]

    # Store with 30s expiry
    _exchange_codes[code] = {
        "user_id": user_id,
        "created_at": time.time(),
        "used": False,
    }

    # Cleanup expired codes (older than 60s)
    now = time.time()
    expired = [k for k, v in _exchange_codes.items() if now - v["created_at"] > 60]
    for k in expired:
        del _exchange_codes[k]

    # Pick a pool Space (round-robin by user_id hash)
    pool_index = hash(user_id) % len(POOL_SPACES)
    builder_url = POOL_SPACES[pool_index]

    return ExchangeCodeResponse(
        code=code,
        expires_in=30,
        builder_url=builder_url,
    )


@router.post("/verify-code")
async def verify_exchange_code(code: str):
    """Verify an exchange code (called by Langflow middleware)."""
    entry = _exchange_codes.get(code)
    if not entry:
        raise HTTPException(status_code=401, detail="Invalid code")
    if entry["used"]:
        raise HTTPException(status_code=401, detail="Code already used")
    if time.time() - entry["created_at"] > 30:
        del _exchange_codes[code]
        raise HTTPException(status_code=401, detail="Code expired")

    entry["used"] = True
    return {"user_id": entry["user_id"], "status": "valid"}
