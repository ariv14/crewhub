# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Eval service -- LLM-as-judge quality scoring for completed tasks."""

import json
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings

logger = logging.getLogger(__name__)

EVAL_RUBRIC = """\
You are an impartial quality evaluator for AI agent task responses.

Given the user's request and the agent's response, score the response on three dimensions:
1. **Relevance** (0-5): Does the response address what was asked?
2. **Completeness** (0-5): Does it cover the full scope of the request?
3. **Coherence** (0-5): Is it well-structured, clear, and internally consistent?

Respond ONLY with a JSON object (no markdown, no explanation):
{"relevance": <int>, "completeness": <int>, "coherence": <int>}
"""


class EvalService:
    """Scores task responses using an LLM-as-judge approach."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def score_response(self, task_id: UUID | str) -> float | None:
        """Score a completed task's response quality.

        Returns the quality_score (0-5 float) or None if scoring fails.
        Updates the task's quality_score column in the database.
        """
        if not settings.eval_enabled:
            return None

        from src.models.task import Task
        from sqlalchemy import select

        # Use select() instead of db.get() for SQLite UUID compatibility
        if isinstance(task_id, str):
            task_id = UUID(task_id)
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalars().first()
        if not task:
            logger.warning("Eval: task %s not found", task_id)
            return None

        # Extract input text from messages
        input_text = self._extract_text(task.messages or [], role="user")
        if not input_text:
            logger.info("Eval: no user messages for task %s", task_id)
            return None

        # Extract output text from artifacts
        output_text = self._extract_artifact_text(task.artifacts or [])
        if not output_text:
            logger.info("Eval: no artifacts for task %s", task_id)
            return None

        # Call LLM for scoring
        try:
            scores = await self._call_llm_judge(input_text, output_text)
            if scores is None:
                return None

            quality_score = (
                scores["relevance"] + scores["completeness"] + scores["coherence"]
            ) / 3.0

            # Clamp to 0-5
            quality_score = max(0.0, min(5.0, quality_score))

            task.quality_score = quality_score
            task.eval_model = settings.eval_llm_model
            task.eval_relevance = float(scores["relevance"])
            task.eval_completeness = float(scores["completeness"])
            task.eval_coherence = float(scores["coherence"])
            await self.db.commit()

            logger.info(
                "Eval: task %s scored %.2f (R=%d C=%d H=%d) model=%s",
                task_id, quality_score,
                scores["relevance"], scores["completeness"], scores["coherence"],
                settings.eval_llm_model,
            )
            return quality_score

        except Exception:
            logger.exception("Eval: scoring failed for task %s", task_id)
            return None

    async def _call_llm_judge(
        self, input_text: str, output_text: str
    ) -> dict | None:
        """Call the eval LLM model and parse the JSON scores.

        Uses the configured eval model (default: Gemini Flash) with fallback
        to the multi-provider backend router if the primary model fails.
        """
        try:
            from litellm import acompletion
        except ImportError:
            logger.warning("Eval: litellm not installed, skipping scoring")
            return None

        # Truncate to avoid excessive token usage
        input_text = input_text[:4000]
        output_text = output_text[:8000]

        prompt = (
            f"## User Request\n{input_text}\n\n"
            f"## Agent Response\n{output_text}"
        )

        try:
            # Try configured eval model first (Gemini Flash — separate budget)
            response = await acompletion(
                model=settings.eval_llm_model,
                messages=[
                    {"role": "system", "content": EVAL_RUBRIC},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=100,
            )

            content = response.choices[0].message.content.strip()
            # Parse JSON from response (handle potential markdown wrapping)
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0]
            scores = json.loads(content)

            # Validate
            for key in ("relevance", "completeness", "coherence"):
                val = scores.get(key)
                if not isinstance(val, (int, float)) or val < 0 or val > 5:
                    logger.warning("Eval: invalid score %s=%s", key, val)
                    return None

            return scores

        except json.JSONDecodeError:
            logger.warning("Eval: failed to parse LLM response as JSON")
            return None
        except Exception:
            logger.warning("Eval: primary model (%s) failed, trying router fallback", settings.eval_llm_model)
            try:
                from src.core.llm_router import completion
                content = await completion(
                    messages=[
                        {"role": "system", "content": EVAL_RUBRIC},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.0,
                    max_tokens=100,
                )
                content = content.strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[-1].rsplit("```", 1)[0]
                scores = json.loads(content)
                for key in ("relevance", "completeness", "coherence"):
                    val = scores.get(key)
                    if not isinstance(val, (int, float)) or val < 0 or val > 5:
                        return None
                return scores
            except Exception:
                logger.exception("Eval: router fallback also failed")
                return None

    @staticmethod
    def _extract_text(messages: list[dict], role: str = "user") -> str:
        """Extract text content from messages with a specific role."""
        texts = []
        for msg in messages:
            if msg.get("role") != role:
                continue
            for part in msg.get("parts", []):
                content = part.get("content") or part.get("text")
                if content and part.get("type", "text") == "text":
                    texts.append(content)
        return "\n".join(texts)

    @staticmethod
    def _extract_artifact_text(artifacts: list[dict]) -> str:
        """Extract text content from task artifacts."""
        texts = []
        for artifact in artifacts:
            for part in artifact.get("parts", []):
                content = part.get("content") or part.get("text")
                if content and part.get("type", "text") == "text":
                    texts.append(content)
        return "\n".join(texts)
