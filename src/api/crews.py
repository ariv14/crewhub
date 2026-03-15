# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""AgentCrew API — saved agent team compositions."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import resolve_db_user_id
from src.database import get_db
from src.schemas.crew import (
    CrewCreate,
    CrewListResponse,
    CrewResponse,
    CrewRunRequest,
    CrewRunResponse,
    CrewUpdate,
)
from src.services.crew_service import CrewService

router = APIRouter(prefix="/crews", tags=["crews"])


# --- Public endpoints (declared before {crew_id} to avoid path collision) ---


@router.get("/public", response_model=CrewListResponse)
async def list_public_crews(
    db: AsyncSession = Depends(get_db),
) -> CrewListResponse:
    """Browse public crews — no authentication required."""
    service = CrewService(db)
    crews, total = await service.list_public_crews()
    return CrewListResponse(crews=crews, total=total)


# --- Authenticated endpoints ---


@router.get("/", response_model=CrewListResponse)
async def list_my_crews(
    db: AsyncSession = Depends(get_db),
    owner_id: UUID = Depends(resolve_db_user_id),
) -> CrewListResponse:
    """List the current user's saved crews."""
    service = CrewService(db)
    crews, total = await service.list_my_crews(owner_id)
    return CrewListResponse(crews=crews, total=total)


@router.post("/", response_model=CrewResponse, status_code=201)
async def create_crew(
    data: CrewCreate,
    db: AsyncSession = Depends(get_db),
    owner_id: UUID = Depends(resolve_db_user_id),
) -> CrewResponse:
    """Create a new saved crew."""
    service = CrewService(db)
    crew = await service.create_crew(owner_id, data)
    return crew


@router.get("/{crew_id}", response_model=CrewResponse)
async def get_crew(
    crew_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> CrewResponse:
    """Get crew detail — public endpoint."""
    service = CrewService(db)
    return await service.get_crew(crew_id)


@router.put("/{crew_id}", response_model=CrewResponse)
async def update_crew(
    crew_id: UUID,
    data: CrewUpdate,
    db: AsyncSession = Depends(get_db),
    owner_id: UUID = Depends(resolve_db_user_id),
) -> CrewResponse:
    """Update a saved crew (name, members, visibility)."""
    service = CrewService(db)
    return await service.update_crew(crew_id, owner_id, data)


@router.delete("/{crew_id}", status_code=204)
async def delete_crew(
    crew_id: UUID,
    db: AsyncSession = Depends(get_db),
    owner_id: UUID = Depends(resolve_db_user_id),
) -> None:
    """Delete a saved crew."""
    service = CrewService(db)
    await service.delete_crew(crew_id, owner_id)


@router.post("/{crew_id}/run", response_model=CrewRunResponse)
async def run_crew(
    crew_id: UUID,
    data: CrewRunRequest,
    db: AsyncSession = Depends(get_db),
    owner_id: UUID = Depends(resolve_db_user_id),
) -> CrewRunResponse:
    """Execute a saved crew — creates one task per member."""
    service = CrewService(db)
    return await service.run_crew(crew_id, owner_id, data)


@router.post("/{crew_id}/clone", response_model=CrewResponse, status_code=201)
async def clone_crew(
    crew_id: UUID,
    db: AsyncSession = Depends(get_db),
    owner_id: UUID = Depends(resolve_db_user_id),
) -> CrewResponse:
    """Clone a public crew to your own collection."""
    service = CrewService(db)
    return await service.clone_crew(crew_id, owner_id)
