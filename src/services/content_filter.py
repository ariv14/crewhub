# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Content moderation service — filters harmful input/output text.

Level 1: Regex blocklist (default, zero external calls).
Level 2: OpenAI Moderation API (free, requires OpenAI key).
"""

import logging
import re

from src.config import settings
from src.core.exceptions import ContentModerationError

logger = logging.getLogger(__name__)

# --- Level 1: Regex blocklist ---
# Patterns that indicate clearly harmful content. Kept intentionally conservative
# to avoid false positives — this is a safety net, not a content policy engine.
_BLOCKLIST_PATTERNS = [
    # Prompt injection attempts
    r"(?i)ignore\s+(all\s+)?previous\s+instructions",
    r"(?i)you\s+are\s+now\s+(a|an)\s+",
    r"(?i)system\s*:\s*",
    # Harmful content requests
    r"(?i)how\s+to\s+(make|build|create)\s+(a\s+)?(bomb|weapon|explosive)",
    r"(?i)(synthesize|manufacture)\s+(meth|fentanyl|ricin)",
    # PII extraction attempts
    r"(?i)(give|list|show)\s+me\s+(all\s+)?(user|customer)\s+(data|info|emails|passwords)",
]

_COMPILED_BLOCKLIST = [re.compile(p) for p in _BLOCKLIST_PATTERNS]


def check_input(text: str) -> None:
    """Check user input for moderation violations.

    Raises ContentModerationError if content is blocked.
    """
    if not settings.content_moderation_enabled:
        return

    if not text or not text.strip():
        return

    # Level 1: regex blocklist
    for pattern in _COMPILED_BLOCKLIST:
        if pattern.search(text):
            logger.warning("Content blocked by regex filter: pattern=%s", pattern.pattern)
            raise ContentModerationError(
                detail="Your message was blocked by our content policy. "
                "Please rephrase and try again."
            )

    # Level 2: OpenAI Moderation API (optional)
    if settings.content_moderation_level >= 2:
        _check_openai_moderation(text)


def check_output(text: str) -> None:
    """Check agent output for moderation violations.

    Raises ContentModerationError if content is blocked.
    """
    if not settings.content_moderation_enabled:
        return

    if not text or not text.strip():
        return

    # Only apply regex blocklist to outputs (level 1)
    for pattern in _COMPILED_BLOCKLIST:
        if pattern.search(text):
            logger.warning("Output blocked by regex filter: pattern=%s", pattern.pattern)
            raise ContentModerationError(
                detail="Agent response was blocked by our content policy."
            )


def _check_openai_moderation(text: str) -> None:
    """Call OpenAI Moderation API (synchronous, free endpoint)."""
    try:
        import httpx

        resp = httpx.post(
            "https://api.openai.com/v1/moderations",
            json={"input": text},
            headers={"Authorization": f"Bearer {_get_openai_key()}"},
            timeout=5.0,
        )
        if resp.status_code != 200:
            logger.warning("OpenAI moderation API returned %d", resp.status_code)
            return  # fail open — don't block on API errors

        data = resp.json()
        results = data.get("results", [])
        if results and results[0].get("flagged"):
            categories = [
                k for k, v in results[0].get("categories", {}).items() if v
            ]
            logger.warning("Content flagged by OpenAI moderation: %s", categories)
            raise ContentModerationError(
                detail="Your message was flagged by our content policy. "
                "Please rephrase and try again."
            )
    except ContentModerationError:
        raise
    except Exception as e:
        # Fail open — moderation API errors should not block requests
        logger.warning("OpenAI moderation check failed: %s", e)


def _get_openai_key() -> str:
    """Get OpenAI API key from platform config."""
    return settings.platform_embedding_key or ""
