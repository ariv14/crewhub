"""External skill import endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_user
from src.database import get_db
from src.schemas.imports import OpenClawImportRequest, OpenClawImportResponse
from src.services.openclaw_importer import OpenClawImporter

router = APIRouter(prefix="/import", tags=["import"])


@router.post("/openclaw", response_model=OpenClawImportResponse, status_code=201)
async def import_openclaw_skill(
    data: OpenClawImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> OpenClawImportResponse:
    """Import an OpenClaw skill as a CrewHub agent.

    The imported agent starts as inactive and unverified.
    Requires authentication — the caller becomes the agent owner.
    """
    importer = OpenClawImporter(db)
    agent = await importer.import_skill(
        skill_url=data.skill_url,
        pricing=data.pricing,
        category=data.category,
        tags=data.tags,
        owner_id=UUID(current_user["id"]),
    )
    return OpenClawImportResponse(
        agent_id=str(agent.id),
        name=agent.name,
        status=agent.status.value if hasattr(agent.status, "value") else str(agent.status),
        source="openclaw",
        source_url=data.skill_url,
    )
