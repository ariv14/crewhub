"""Reputation service -- calculate and manage agent reputation scores."""

import math
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent import Agent
from src.models.task import Task, TaskStatus


class ReputationService:
    """Calculates and maintains agent reputation scores."""

    # Reputation component weights
    W_SUCCESS = 0.30
    W_QUALITY = 0.25
    W_RATING = 0.20
    W_RELIABILITY = 0.15
    W_VOLUME = 0.10

    # Decay rate per week of inactivity
    DECAY_RATE_PER_WEEK = 0.02

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Update reputation
    # ------------------------------------------------------------------

    async def update_reputation(self, agent_id: UUID) -> float:
        """Recalculate and store the reputation score for an agent.

        Formula:
            0.30 * success_rate
          + 0.25 * avg_quality (normalized to 0-1)
          + 0.20 * avg_rating  (normalized to 0-1, scale 1-5)
          + 0.15 * reliability
          + 0.10 * volume_factor

        volume_factor = min(1.0, log(total_tasks + 1) / log(100))
        """
        agent = await self.db.get(Agent, agent_id)
        if not agent:
            return 0.0

        # Gather task statistics
        completed_stmt = select(func.count()).where(
            Task.provider_agent_id == agent_id,
            Task.status == TaskStatus.COMPLETED,
        )
        total_terminal_stmt = select(func.count()).where(
            Task.provider_agent_id == agent_id,
            Task.status.in_([
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELED,
                TaskStatus.REJECTED,
            ]),
        )
        avg_quality_stmt = select(func.avg(Task.quality_score)).where(
            Task.provider_agent_id == agent_id,
            Task.quality_score.isnot(None),
        )
        avg_rating_stmt = select(func.avg(Task.client_rating)).where(
            Task.provider_agent_id == agent_id,
            Task.client_rating.isnot(None),
        )
        failed_stmt = select(func.count()).where(
            Task.provider_agent_id == agent_id,
            Task.status == TaskStatus.FAILED,
        )

        completed = (await self.db.execute(completed_stmt)).scalar_one()
        total_terminal = (await self.db.execute(total_terminal_stmt)).scalar_one()
        avg_quality = (await self.db.execute(avg_quality_stmt)).scalar_one()
        avg_rating = (await self.db.execute(avg_rating_stmt)).scalar_one()
        failed = (await self.db.execute(failed_stmt)).scalar_one()

        # success_rate
        success_rate = (completed / total_terminal) if total_terminal > 0 else 0.0

        # avg_quality normalized to 0-1 (assuming quality_score is 0-5)
        quality_norm = (float(avg_quality) / 5.0) if avg_quality else 0.0

        # avg_rating normalized to 0-1 (rating scale 1-5)
        rating_norm = ((float(avg_rating) - 1.0) / 4.0) if avg_rating else 0.0

        # reliability = 1 - (failed / total_terminal)
        reliability = (1.0 - (failed / total_terminal)) if total_terminal > 0 else 0.0

        # volume_factor = min(1.0, log(total_tasks + 1) / log(100))
        total_tasks = completed + failed
        volume_factor = min(1.0, math.log(total_tasks + 1) / math.log(100))

        # Composite score (0-1 scale, stored as 0-5)
        raw = (
            self.W_SUCCESS * success_rate
            + self.W_QUALITY * quality_norm
            + self.W_RATING * rating_norm
            + self.W_RELIABILITY * reliability
            + self.W_VOLUME * volume_factor
        )
        score = round(raw * 5.0, 2)  # scale to 0-5

        agent.reputation_score = score
        agent.success_rate = success_rate
        agent.total_tasks_completed = completed

        # Auto-promote verification level based on eval performance
        self._auto_promote_verification(agent, completed, success_rate, quality_norm, score)

        await self.db.commit()

        return score

    @staticmethod
    def _auto_promote_verification(
        agent: "Agent",
        completed: int,
        success_rate: float,
        quality_norm: float,
        score: float,
    ) -> None:
        """Auto-promote verification tier based on eval performance.

        3 tiers (progressive — never demote):
          new → verified: ≥3 tasks, quality ≥ 0.6 (3.0/5), success ≥ 80%
          verified → certified: ≥25 tasks, quality ≥ 0.8 (4.0/5), success ≥ 95%, reputation ≥ 3.5
        """
        from src.models.agent import VerificationLevel

        current_str = agent.verification_level.value if hasattr(agent.verification_level, "value") else str(agent.verification_level)
        # Map legacy values to new tiers
        legacy_map = {"unverified": "new", "self_tested": "verified", "namespace": "verified", "quality": "certified", "audit": "certified"}
        current_str = legacy_map.get(current_str, current_str)

        # new → verified
        if current_str == "new" and completed >= 3 and quality_norm >= 0.6 and success_rate >= 0.8:
            agent.verification_level = VerificationLevel.VERIFIED

        # verified → certified
        if current_str == "verified" and completed >= 25 and quality_norm >= 0.8 and success_rate >= 0.95 and score >= 3.5:
            agent.verification_level = VerificationLevel.CERTIFIED

    # ------------------------------------------------------------------
    # Decay
    # ------------------------------------------------------------------

    async def apply_decay(self, agent_id: UUID, weeks_inactive: int) -> float:
        """Apply 2% decay per week of inactivity to the agent's reputation."""
        agent = await self.db.get(Agent, agent_id)
        if not agent:
            return 0.0

        decay_factor = (1.0 - self.DECAY_RATE_PER_WEEK) ** weeks_inactive
        new_score = round(agent.reputation_score * decay_factor, 2)
        agent.reputation_score = new_score
        await self.db.commit()

        return new_score

    # ------------------------------------------------------------------
    # Verification requirements
    # ------------------------------------------------------------------

    async def get_verification_requirements(self, level: str) -> dict:
        """Return the requirements for each verification tier."""
        tiers = {
            "verified": {
                "level": "verified",
                "description": "Agent is eval'd and working. Gets normal search ranking.",
                "requirements": [
                    "Complete at least 3 tasks",
                    "AI quality score ≥ 3.0/5",
                    "Success rate ≥ 80%",
                ],
                "min_reputation": 0.0,
                "min_tasks": 3,
            },
            "certified": {
                "level": "certified",
                "description": "Top-tier agent. Featured placement and priority ranking.",
                "requirements": [
                    "Complete at least 25 tasks",
                    "AI quality score ≥ 4.0/5",
                    "Success rate ≥ 95%",
                    "Reputation score ≥ 3.5/5",
                ],
                "min_reputation": 3.5,
                "min_tasks": 25,
            },
        }

        if level not in tiers:
            return {
                "error": f"Unknown verification level: {level}",
                "available_levels": list(tiers.keys()),
            }

        return tiers[level]
