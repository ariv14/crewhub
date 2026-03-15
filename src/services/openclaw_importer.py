# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""OpenClaw skill importer — fetch, parse, and register external skills."""

import re
import time
from datetime import datetime, timezone
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ConflictError, MarketplaceError
from src.models.agent import Agent, AgentStatus, VerificationLevel
from src.models.skill import AgentSkill
from src.schemas.agent import PricingModel

MAX_MANIFEST_BYTES = 100_000
_import_counts: dict[str, list[float]] = {}
MAX_IMPORTS_PER_HOUR = 10


class OpenClawImporter:
    """Imports OpenClaw skills from external registries as CrewHub agents."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def sanitize_text(text: str, max_length: int = 10000) -> str:
        """Strip HTML tags, script content, and truncate to max length."""
        # Remove <script> tags and their content first
        clean = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL)
        # Remove remaining HTML tags
        clean = re.sub(r"<[^>]+>", "", clean)
        clean = re.sub(r"javascript:", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean[:max_length]

    @staticmethod
    def parse_manifest(content: str) -> dict:
        """Parse an OpenClaw skill manifest (markdown format) into structured data."""
        lines = content.strip().split("\n")
        result = {
            "name": "Imported Skill",
            "description": "",
            "endpoint": "",
            "input_modes": ["text"],
            "output_modes": ["text"],
        }

        # Name from first heading
        for line in lines:
            if line.startswith("# "):
                result["name"] = line.lstrip("# ").strip()
                break

        # Description: text between first heading and next section
        in_desc = False
        desc_lines = []
        for line in lines:
            if line.startswith("# ") and not in_desc:
                in_desc = True
                continue
            if in_desc:
                if line.startswith("## "):
                    break
                desc_lines.append(line)
        result["description"] = OpenClawImporter.sanitize_text(
            "\n".join(desc_lines).strip()
        )

        # Section parsing
        in_section = None
        for line in lines:
            lower = line.lower().strip()
            if lower.startswith("## endpoint"):
                in_section = "endpoint"
                continue
            elif lower.startswith("## input"):
                in_section = "input_modes"
                continue
            elif lower.startswith("## output"):
                in_section = "output_modes"
                continue
            elif lower.startswith("## "):
                in_section = None
                continue

            stripped = line.strip()
            if not stripped:
                continue

            if in_section == "endpoint" and stripped.startswith("http"):
                result["endpoint"] = stripped
            elif in_section == "input_modes":
                result["input_modes"] = [m.strip() for m in stripped.split(",") if m.strip()]
            elif in_section == "output_modes":
                result["output_modes"] = [m.strip() for m in stripped.split(",") if m.strip()]

        return result

    async def _check_rate_limit(self, user_id: UUID) -> None:
        """Enforce import rate limit: max N imports per user per hour."""
        key = str(user_id)
        now = time.time()
        hour_ago = now - 3600

        if key not in _import_counts:
            _import_counts[key] = []

        _import_counts[key] = [t for t in _import_counts[key] if t > hour_ago]

        if len(_import_counts[key]) >= MAX_IMPORTS_PER_HOUR:
            raise MarketplaceError(
                status_code=429,
                detail=f"Import rate limit exceeded ({MAX_IMPORTS_PER_HOUR} per hour)"
            )

        _import_counts[key].append(now)

    async def _check_duplicate(self, endpoint: str) -> None:
        """Reject if an agent with this endpoint already exists."""
        stmt = select(Agent).where(Agent.endpoint == endpoint)
        result = await self.db.execute(stmt)
        if result.scalars().first():
            raise ConflictError(detail=f"An agent with endpoint '{endpoint}' already exists")

    async def fetch_manifest(self, url: str) -> str:
        """Fetch skill manifest from allowed registry, with streaming size limit."""
        from src.schemas.agent import _validate_public_url
        _validate_public_url(url, allow_debug_bypass=False)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                async with client.stream("GET", url, follow_redirects=True) as resp:
                    resp.raise_for_status()
                    chunks = []
                    total = 0
                    async for chunk in resp.aiter_bytes():
                        total += len(chunk)
                        if total > MAX_MANIFEST_BYTES:
                            raise MarketplaceError(
                                status_code=400,
                                detail=f"Manifest too large (>{MAX_MANIFEST_BYTES} bytes)"
                            )
                        chunks.append(chunk)
                    return b"".join(chunks).decode()
        except httpx.HTTPError as e:
            raise MarketplaceError(
                status_code=400,
                detail=f"Failed to fetch manifest from {url}: {str(e)}"
            )

    async def import_skill(
        self,
        skill_url: str,
        pricing: PricingModel,
        category: str,
        tags: list[str],
        owner_id: UUID,
    ) -> Agent:
        """Full import flow: fetch, parse, validate, register."""
        await self._check_rate_limit(owner_id)

        content = await self.fetch_manifest(skill_url)
        parsed = self.parse_manifest(content)

        endpoint = parsed.get("endpoint", "")
        if endpoint:
            from src.schemas.agent import _validate_public_url
            _validate_public_url(endpoint)
        else:
            raise MarketplaceError(status_code=400, detail="Manifest has no endpoint URL")

        await self._check_duplicate(endpoint)

        name = self.sanitize_text(parsed["name"], max_length=255)
        description = self.sanitize_text(parsed["description"], max_length=10000)

        agent = Agent(
            owner_id=owner_id,
            name=name,
            description=description,
            version="1.0.0",
            endpoint=endpoint,
            capabilities={},
            security_schemes=[],
            category=category,
            tags=tags,
            pricing=pricing.model_dump(),
            license_type=pricing.license_type.value,
            sla={},
            embedding_config={},
            accepted_payment_methods=["credits"],
            metadata_={
                "source": "openclaw",
                "source_url": skill_url,
                "imported_at": datetime.now(timezone.utc).isoformat(),
            },
            status=AgentStatus.INACTIVE,
            verification_level=VerificationLevel.NEW,
        )
        self.db.add(agent)
        await self.db.flush()

        skill = AgentSkill(
            agent_id=agent.id,
            skill_key=re.sub(r"[^a-z0-9-]", "-", name.lower())[:100],
            name=name,
            description=description,
            input_modes=parsed.get("input_modes", ["text"]),
            output_modes=parsed.get("output_modes", ["text"]),
            examples=[],
            avg_credits=pricing.credits,
            avg_latency_ms=0,
        )
        self.db.add(skill)

        await self.db.commit()
        await self.db.refresh(agent)
        return agent
