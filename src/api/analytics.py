"""Analytics API — eval trends, agent performance metrics, and public stats."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import case, func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_db
from src.models.agent import Agent
from src.models.task import Task, TaskStatus
from src.models.transaction import Transaction, TransactionType

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ---------------------------------------------------------------------------
# Public platform stats (no auth, cached-friendly)
# ---------------------------------------------------------------------------


class PublicStats(BaseModel):
    total_agents: int
    total_skills: int
    total_categories: int
    tasks_completed: int
    avg_success_rate: float | None
    credits_earned_by_builders: float


@router.get("/public-stats", response_model=PublicStats)
async def get_public_stats(
    db: AsyncSession = Depends(get_db),
) -> PublicStats:
    """Public platform stats for landing page — no authentication required."""
    from src.models.skill import AgentSkill

    total_agents = (
        await db.execute(select(func.count(Agent.id)).where(Agent.status == "active"))
    ).scalar_one()

    total_skills = (await db.execute(select(func.count(AgentSkill.id)))).scalar_one()

    total_categories = (
        await db.execute(select(func.count(func.distinct(Agent.category))))
    ).scalar_one()

    tasks_completed = (
        await db.execute(
            select(func.count(Task.id)).where(Task.status == "completed")
        )
    ).scalar_one()

    # Success rate: completed / (completed + failed)
    tasks_failed = (
        await db.execute(
            select(func.count(Task.id)).where(Task.status == "failed")
        )
    ).scalar_one()
    total_finished = tasks_completed + tasks_failed
    avg_success_rate = round(tasks_completed / total_finished * 100, 1) if total_finished > 0 else None

    # Credits earned by developers (task payments received)
    earned_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.type == TransactionType.TASK_PAYMENT,
            Transaction.to_account_id.isnot(None),
        )
    )
    credits_earned = float(earned_result.scalar_one())

    return PublicStats(
        total_agents=total_agents,
        total_skills=total_skills,
        total_categories=total_categories,
        tasks_completed=tasks_completed,
        avg_success_rate=avg_success_rate,
        credits_earned_by_builders=credits_earned,
    )


class WeeklyTrend(BaseModel):
    week: str  # ISO week label e.g. "2026-W10"
    avg_quality: float | None
    avg_relevance: float | None
    avg_completeness: float | None
    avg_coherence: float | None
    avg_rating: float | None
    rating_count: int
    success_rate: float | None
    avg_latency_ms: float | None
    task_count: int


class AgentTrendsResponse(BaseModel):
    agent_id: str
    eval_model: str | None
    trends: list[WeeklyTrend]


class EvalModelsResponse(BaseModel):
    models: list["EvalModelInfo"]


class EvalModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    credits_per_eval: float
    is_default: bool


def _week_columns():
    """Return (year_col, week_col) compatible with both SQLite and PostgreSQL."""
    if "sqlite" in settings.database_url:
        yr = literal_column("CAST(strftime('%Y', created_at) AS INTEGER)").label("yr")
        wk = literal_column("CAST(strftime('%W', created_at) AS INTEGER)").label("wk")
    else:
        from sqlalchemy import extract
        yr = extract("isoyear", Task.created_at).label("yr")
        wk = extract("week", Task.created_at).label("wk")
    return yr, wk


# Platform-provided eval models
PLATFORM_EVAL_MODELS: list[EvalModelInfo] = [
    EvalModelInfo(
        id="groq/llama-3.3-70b-versatile",
        name="Llama 3.3 70B",
        provider="Groq",
        credits_per_eval=0,
        is_default=True,
    ),
    EvalModelInfo(
        id="groq/gemma2-9b-it",
        name="Gemma 2 9B",
        provider="Groq",
        credits_per_eval=0,
        is_default=False,
    ),
    EvalModelInfo(
        id="openai/gpt-4o-mini",
        name="GPT-4o Mini",
        provider="OpenAI",
        credits_per_eval=1,
        is_default=False,
    ),
    EvalModelInfo(
        id="openai/gpt-4o",
        name="GPT-4o",
        provider="OpenAI",
        credits_per_eval=2,
        is_default=False,
    ),
]


@router.get("/eval-models", response_model=EvalModelsResponse)
async def list_eval_models():
    """List available platform-provided eval models."""
    return EvalModelsResponse(models=PLATFORM_EVAL_MODELS)


@router.get("/agent/{agent_id}/trends", response_model=AgentTrendsResponse)
async def get_agent_trends(
    agent_id: UUID,
    weeks: int = Query(default=8, ge=1, le=52),
    db: AsyncSession = Depends(get_db),
):
    """Get weekly aggregated quality, success rate, and latency trends for an agent."""
    cutoff = datetime.now(timezone.utc) - timedelta(weeks=weeks)
    yr, wk = _week_columns()

    stmt = (
        select(
            yr,
            wk,
            func.avg(Task.quality_score).label("avg_quality"),
            func.avg(Task.eval_relevance).label("avg_relevance"),
            func.avg(Task.eval_completeness).label("avg_completeness"),
            func.avg(Task.eval_coherence).label("avg_coherence"),
            func.avg(Task.client_rating).label("avg_rating"),
            func.count(Task.client_rating).label("rating_cnt"),
            func.avg(
                case(
                    (Task.status == TaskStatus.COMPLETED, 1.0),
                    else_=0.0,
                )
            ).label("success_rate"),
            func.avg(Task.latency_ms).label("avg_latency"),
            func.count().label("cnt"),
        )
        .where(
            Task.provider_agent_id == agent_id,
            Task.created_at >= cutoff,
            Task.status.in_([TaskStatus.COMPLETED, TaskStatus.FAILED]),
        )
        .group_by("yr", "wk")
        .order_by("yr", "wk")
    )

    result = await db.execute(stmt)
    rows = result.all()

    # Get the most recent eval_model used for this agent
    model_stmt = (
        select(Task.eval_model)
        .where(
            Task.provider_agent_id == agent_id,
            Task.eval_model.isnot(None),
        )
        .order_by(Task.created_at.desc())
        .limit(1)
    )
    model_result = await db.execute(model_stmt)
    eval_model = model_result.scalar_one_or_none()

    trends = []
    for row in rows:
        y = int(row.yr) if row.yr else 0
        w = int(row.wk) if row.wk else 0
        trends.append(
            WeeklyTrend(
                week=f"{y}-W{w:02d}",
                avg_quality=round(float(row.avg_quality), 2) if row.avg_quality else None,
                avg_relevance=round(float(row.avg_relevance), 2) if row.avg_relevance else None,
                avg_completeness=round(float(row.avg_completeness), 2) if row.avg_completeness else None,
                avg_coherence=round(float(row.avg_coherence), 2) if row.avg_coherence else None,
                avg_rating=round(float(row.avg_rating), 2) if row.avg_rating else None,
                rating_count=int(row.rating_cnt) if row.rating_cnt else 0,
                success_rate=round(float(row.success_rate), 2) if row.success_rate is not None else None,
                avg_latency_ms=round(float(row.avg_latency), 0) if row.avg_latency else None,
                task_count=int(row.cnt),
            )
        )

    return AgentTrendsResponse(agent_id=str(agent_id), eval_model=eval_model, trends=trends)
