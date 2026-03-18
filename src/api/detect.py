# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Agent detection endpoint — fetch and parse a remote agent card."""

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException

from src.core.rate_limiter import rate_limit_by_ip
from src.core.url_validator import validate_public_url
from src.schemas.detect import DetectRequest, DetectedSkill, DetectResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/detect", response_model=DetectResponse, dependencies=[Depends(rate_limit_by_ip)])
async def detect_agent(
    data: DetectRequest,
) -> DetectResponse:
    """Auto-detect an agent by fetching its .well-known/agent-card.json."""

    validate_public_url(data.url)
    base_url = data.url.rstrip("/")
    card_url = base_url + "/.well-known/agent-card.json"

    # Fetch the agent card
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(card_url)
    except httpx.TimeoutException:
        raise HTTPException(status_code=400, detail="Endpoint timed out (10s)")
    except httpx.ConnectError:
        raise HTTPException(status_code=400, detail="Could not reach endpoint")
    except httpx.HTTPError:
        raise HTTPException(status_code=400, detail="Could not reach endpoint")

    if resp.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=f"Endpoint returned HTTP {resp.status_code}",
        )

    try:
        card = resp.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Agent card is not valid JSON")

    if not isinstance(card, dict):
        raise HTTPException(status_code=400, detail="Agent card is not valid JSON")

    # Validate required field
    name = card.get("name")
    if not name:
        raise HTTPException(
            status_code=400,
            detail="Agent card missing required field: name",
        )

    # Extract fields with defaults
    description = card.get("description", "")
    version = card.get("version", "1.0.0")
    url = card.get("url", base_url)
    capabilities = card.get("capabilities", {})

    warnings: list[str] = []
    if not description:
        warnings.append("Missing description")

    # Parse skills
    raw_skills = card.get("skills", [])
    skills: list[DetectedSkill] = []
    if not raw_skills:
        warnings.append("No skills found")

    for s in raw_skills:
        if not isinstance(s, dict):
            continue
        skill_key = s.get("id", s.get("skill_key", ""))
        skill_name = s.get("name", skill_key)
        skill_desc = s.get("description", "")
        input_modes = s.get("inputModes", s.get("input_modes", ["text"]))
        output_modes = s.get("outputModes", s.get("output_modes", ["text"]))
        if skill_key:
            skills.append(
                DetectedSkill(
                    skill_key=skill_key,
                    name=skill_name,
                    description=skill_desc,
                    input_modes=input_modes,
                    output_modes=output_modes,
                )
            )

    # Build suggested registration payload (AgentCreate-compatible)
    suggested_registration = {
        "name": name,
        "description": description or f"Agent: {name}",
        "version": version,
        "endpoint": base_url,
        "capabilities": capabilities,
        "skills": [
            {
                "skill_key": sk.skill_key,
                "name": sk.name,
                "description": sk.description or f"Skill: {sk.name}",
                "input_modes": sk.input_modes,
                "output_modes": sk.output_modes,
                "examples": [],
                "avg_credits": 0,
                "avg_latency_ms": 0,
            }
            for sk in skills
        ],
        "security_schemes": card.get("securitySchemes", []),
        "category": "general",
        "tags": [],
        "pricing": {
            "license_type": "open",
            "tiers": [],
            "model": "per_task",
            "credits": 1,
            "trial_days": None,
            "trial_task_limit": None,
        },
        "accepted_payment_methods": ["credits"],
    }

    return DetectResponse(
        name=name,
        description=description,
        url=url,
        version=version,
        capabilities=capabilities,
        skills=skills,
        suggested_registration=suggested_registration,
        card_url=card_url,
        warnings=warnings,
    )
