# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""ANP (Agent Network Protocol) endpoints.

Serves DID documents, agent descriptions in JSON-LD format,
and the well-known agent-descriptions discovery endpoint.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.did import agent_did, build_agent_description, build_did_document
from src.database import get_db
from src.models.agent import Agent, AgentStatus
from src.services.registry import RegistryService

from sqlalchemy import select

router = APIRouter(tags=["anp"])


@router.get("/agents/{agent_id}/did.json")
async def get_did_document(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Serve the W3C DID document for an agent.

    Returns a DID Core compliant JSON document with the agent's public key,
    authentication method, and service endpoints.
    """
    service = RegistryService(db)
    try:
        agent = await service.get_agent(agent_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Agent not found")

    if not getattr(agent, "did_public_key", None):
        raise HTTPException(status_code=404, detail="Agent has no DID identity")

    doc = build_did_document(
        agent_id=agent.id,
        public_key=agent.did_public_key,
        endpoint=agent.endpoint,
    )
    return doc


@router.get("/agents/{agent_id}/description")
async def get_agent_description(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Serve the JSON-LD agent description (ANP Agent Description Protocol).

    Returns metadata, capabilities, interface specs, and security bindings.
    """
    service = RegistryService(db)
    try:
        agent = await service.get_agent(agent_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Agent not found")

    skills = [
        {
            "name": s.name,
            "description": s.description,
            "input_modes": s.input_modes,
            "output_modes": s.output_modes,
        }
        for s in agent.skills
    ]

    description = build_agent_description(
        agent_id=agent.id,
        name=agent.name,
        description=agent.description or "",
        skills=skills,
        endpoint=agent.endpoint,
        mcp_server_url=getattr(agent, "mcp_server_url", None),
    )
    return description


@router.get("/.well-known/agent-descriptions")
async def well_known_agent_descriptions(
    db: AsyncSession = Depends(get_db),
):
    """JSON-LD CollectionPage listing all active agents' description URLs.

    This is the ANP discovery endpoint that allows agents to find other
    agents on this platform.
    """
    stmt = (
        select(Agent.id, Agent.name, Agent.description)
        .where(Agent.status == AgentStatus.ACTIVE)
        .order_by(Agent.created_at.desc())
        .limit(100)
    )
    result = await db.execute(stmt)
    agents = result.all()

    base_url = "https://api.crewhubai.com/api/v1"
    items = []
    for agent_row in agents:
        aid = str(agent_row[0])
        items.append({
            "@type": "SoftwareAgent",
            "identifier": agent_did(agent_row[0]),
            "name": agent_row[1],
            "description": (agent_row[2] or "")[:200],
            "url": f"{base_url}/agents/{aid}/description",
            "didDocument": f"{base_url}/agents/{aid}/did.json",
        })

    return {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "CrewHub Agent Directory",
        "numberOfItems": len(items),
        "itemListElement": items,
    }
