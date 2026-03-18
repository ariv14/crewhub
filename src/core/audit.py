# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Audit logging utility for SOC 2 compliance."""
import json
import logging
from typing import Any, Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


async def audit_log(
    db: AsyncSession,
    *,
    action: str,
    actor_user_id: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    old_value: Any = None,
    new_value: Any = None,
    request: Optional[Request] = None,
) -> None:
    """Write an immutable audit log entry. Call within the same DB transaction as the action."""
    entry = AuditLog(
        action=action,
        actor_user_id=actor_user_id,
        target_type=target_type,
        target_id=str(target_id) if target_id else None,
        old_value=json.dumps(old_value, default=str) if old_value is not None else None,
        new_value=json.dumps(new_value, default=str) if new_value is not None else None,
        ip_address=_get_client_ip(request) if request else None,
        user_agent=request.headers.get("user-agent", "")[:500] if request else None,
    )
    db.add(entry)
    logger.info(
        "audit action=%s actor=%s target=%s/%s",
        action, actor_user_id, target_type, target_id,
    )


def _get_client_ip(request: Request) -> Optional[str]:
    """Extract real client IP from proxy headers."""
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None
