"""Creator Agent — universal executor that role-plays as any specialist.

Receives a system_prompt via task metadata and uses it to role-play as
the specified specialist. This is the engine behind "Create an Agent" —
one deployment handles all community-created agents.

Skills:
  - custom-execute    Execute a task as any specialist (system_prompt in metadata)

Port: 8004
Credits: 0 (billing handled by marketplace)

Run standalone:
    uvicorn demo_agents.creator.agent:app --port 8004
"""

from __future__ import annotations

from demo_agents.base import Artifact, MessagePart, TaskMessage, create_a2a_app, llm_call

PORT = 8004
CREDITS = 0  # Marketplace handles credit billing

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful, knowledgeable AI assistant. Provide thorough, "
    "well-structured, and actionable responses. If the user's request "
    "requires domain expertise, apply best practices and established "
    "methodologies. Always explain your reasoning."
)

SKILLS = [
    {
        "id": "custom-execute",
        "name": "Custom Agent Executor",
        "description": "Execute any task using a dynamically provided specialist persona.",
        "inputModes": ["text"],
        "outputModes": ["text"],
    },
]


async def handle(skill_id: str, messages: list[TaskMessage]) -> list[Artifact]:
    """Handle a task by role-playing as the specialist defined in metadata."""
    # Extract user message text
    text = ""
    system_prompt = DEFAULT_SYSTEM_PROMPT
    metadata = {}

    for msg in messages:
        for part in msg.parts:
            if part.type == "text" and part.content:
                text += part.content + "\n"
            # Check for metadata containing system_prompt
            if part.data and isinstance(part.data, dict):
                metadata.update(part.data)

    text = text.strip()

    if not text:
        return [Artifact(
            name="error",
            parts=[MessagePart(type="text", content="No input text provided.")],
        )]

    # Use system_prompt from metadata if provided
    if metadata.get("system_prompt"):
        system_prompt = metadata["system_prompt"]

    result = await llm_call(system_prompt, text)

    return [Artifact(
        name="custom-response",
        parts=[MessagePart(type="text", content=result)],
        metadata={"skill": skill_id, "custom_agent": True},
    )]


app = create_a2a_app(
    name="Creator Agent",
    description="Universal AI executor — role-plays as any specialist using dynamic personas.",
    version="1.0.0",
    skills=SKILLS,
    handler_func=handle,
    port=PORT,
    credits_per_task=CREDITS,
)
