"""Task delegation suggestion endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.discovery import _resolve_user_keys
from src.core.auth import get_current_user
from src.database import get_db
from src.schemas.suggestion import SuggestionRequest, SuggestionResponse
from src.services.task_broker import TaskBrokerService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/suggest", response_model=SuggestionResponse)
async def suggest_delegation(
    data: SuggestionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> SuggestionResponse:
    """Suggest the best agent and skill for a task message.

    Uses semantic search when an embedding API key is available,
    falls back to keyword matching otherwise.
    """
    user_keys, user_id, account_tier = await _resolve_user_keys(db, current_user)
    service = TaskBrokerService(db)
    return await service.suggest_delegation(
        message=data.message,
        category=data.category,
        tags=data.tags,
        max_credits=data.max_credits,
        limit=data.limit,
        user_llm_keys=user_keys,
        user_id=user_id,
        account_tier=account_tier,
    )
