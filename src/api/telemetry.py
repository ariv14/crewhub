"""Telemetry API — fire-and-forget event logging."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.services.telemetry import TelemetryService

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


class TelemetryEventCreate(BaseModel):
    name: str
    properties: Optional[dict] = None


class TelemetryBatchCreate(BaseModel):
    events: list[TelemetryEventCreate]


@router.post("/events", status_code=202)
async def log_events(
    data: TelemetryBatchCreate,
    db: AsyncSession = Depends(get_db),
):
    """Log a batch of telemetry events (fire-and-forget)."""
    # Optional: extract user from auth header if present
    user_id = None
    try:
        from src.api.deps import get_current_user_optional
        # Not enforcing auth — telemetry is best-effort
    except Exception:
        pass

    service = TelemetryService(db)
    count = await service.log_batch(
        events=[e.model_dump() for e in data.events],
        user_id=user_id,
    )
    await db.commit()
    return {"accepted": count}
