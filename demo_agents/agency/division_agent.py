"""Parameterized A2A agent for an AI Agency division.

Each division (engineering, design, marketing, etc.) runs as a separate
HuggingFace Space using this same codebase, configured via DIVISION env var.
Each personality within the division becomes a skill.

Run standalone:
    DIVISION=engineering uvicorn demo_agents.agency.division_agent:app --port 8010
"""

from __future__ import annotations

import os

from demo_agents.agency.personality_loader import load_division
from demo_agents.base import Artifact, MessagePart, TaskMessage, create_a2a_app, llm_call

DIVISION = os.environ.get("DIVISION", "engineering")
PORT = int(os.environ.get("PORT", "7860"))
CREDITS = float(os.environ.get("CREDITS_PER_TASK", "2"))

# Human-readable metadata per division
DIVISION_META = {
    "engineering": ("Engineering Division", "Software engineering experts: backend, frontend, DevOps, AI, mobile, and prototyping"),
    "design": ("Design Division", "Design specialists: UI, UX, brand, visual storytelling, and creative direction"),
    "marketing": ("Marketing Division", "Marketing experts: content, social media, growth, app store optimization"),
    "product": ("Product Division", "Product management: feedback synthesis, sprint prioritization, trend research"),
    "project-management": ("Project Management Division", "Project management: scheduling, operations, production, experiment tracking"),
    "testing": ("Testing Division", "QA and testing: API testing, performance, evidence collection, workflow optimization"),
    "support": ("Support Division", "Support operations: analytics, finance, infrastructure, legal compliance"),
    "spatial-computing": ("Spatial Computing Division", "XR/spatial computing: visionOS, Metal, immersive experiences, cockpit interaction"),
    "specialized": ("Specialized Division", "Specialized agents: data analytics, orchestration, identity/trust, reporting"),
}

# Load personalities for this division
_personalities = load_division(DIVISION)

# Build skills list from loaded personalities
SKILLS = [
    {
        "id": p.skill_id,
        "name": p.name,
        "description": p.description,
        "inputModes": ["text"],
        "outputModes": ["text"],
    }
    for p in _personalities.values()
]

# Map skill_id → system_prompt for handler lookup
_prompts = {sid: p.system_prompt for sid, p in _personalities.items()}

div_name, div_desc = DIVISION_META.get(DIVISION, (DIVISION.title(), f"AI Agency {DIVISION} division"))


async def handle(skill_id: str, messages: list[TaskMessage]) -> list[Artifact]:
    """Handle a task by routing to the appropriate personality's system prompt."""
    # Extract text from messages
    text = ""
    for msg in messages:
        for part in msg.parts:
            if part.type == "text" and part.content:
                text += part.content + "\n"
    text = text.strip()

    if not text:
        return [Artifact(
            name="error",
            parts=[MessagePart(type="text", content="No input text provided.")],
        )]

    system_prompt = _prompts.get(skill_id)
    if not system_prompt:
        # Fall back to first skill if unknown skill_id
        first_sid = next(iter(_prompts))
        system_prompt = _prompts[first_sid]
        skill_id = first_sid

    result = await llm_call(system_prompt, text)

    return [Artifact(
        name=f"{skill_id}-response",
        parts=[MessagePart(type="text", content=result)],
        metadata={"skill": skill_id, "division": DIVISION},
    )]


app = create_a2a_app(
    name=f"AI Agency: {div_name}",
    description=div_desc,
    version="1.0.0",
    skills=SKILLS,
    handler_func=handle,
    port=PORT,
    credits_per_task=CREDITS,
)
