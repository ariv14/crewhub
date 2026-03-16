# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Parameterized A2A agent for premium marketing divisions.

Each division (cro, copywriter, seo, launch, email, pricing) runs as a
separate HuggingFace Space using this same codebase, configured via the
DIVISION env var. Each skill within the division is routed by skill_id.

Based on marketingskills by Corey Haines (MIT licensed).

Run standalone:
    DIVISION=cro uvicorn demo_agents.marketing.marketing_agent:app --port 8010
"""

from __future__ import annotations

import os

from demo_agents.marketing.division_loader import load_division
from demo_agents.base import Artifact, MessagePart, TaskMessage, create_a2a_app, llm_call

DIVISION = os.environ.get("DIVISION", "cro")
PORT = int(os.environ.get("PORT", "7860"))
CREDITS = float(os.environ.get("CREDITS_PER_TASK", "20"))

# Human-readable metadata per division
DIVISION_META = {
    "cro": (
        "CRO Optimizer",
        "Conversion rate optimization expert: landing pages, signup flows, and onboarding optimization",
        20,
        [
            "Audit my landing page for conversion issues: https://example.com",
            "My signup page has a 2% conversion rate. How do I improve it?",
            "Review my onboarding flow and suggest improvements",
        ],
    ),
    "copywriter": (
        "Marketing Copywriter",
        "Expert conversion copywriter: headlines, landing page copy, and copy editing with the Seven Sweeps framework",
        20,
        [
            "Write a hero headline and subheadline for my SaaS product",
            "Rewrite this landing page copy to be more conversion-focused",
            "Edit this email for clarity, tone, and persuasion",
        ],
    ),
    "seo": (
        "SEO Auditor",
        "SEO expert: technical audits, AI search optimization, and schema markup implementation",
        25,
        [
            "Audit my site's SEO: https://example.com",
            "How do I optimize my content to get cited by ChatGPT and Perplexity?",
            "Generate schema markup for my SaaS product page",
        ],
    ),
    "launch": (
        "Launch Strategist",
        "Product launch expert: go-to-market strategy, Product Hunt launches, and creative marketing ideas",
        25,
        [
            "Plan my Product Hunt launch for next month",
            "I'm launching a new feature. Give me a go-to-market strategy",
            "Generate 10 creative marketing ideas for my developer tool",
        ],
    ),
    "email": (
        "Email Campaign Builder",
        "Email marketing expert: cold outreach, drip sequences, onboarding flows, and re-engagement campaigns",
        20,
        [
            "Write a 5-email onboarding drip sequence for new signups",
            "Draft a cold email to CTOs about my AI monitoring tool",
            "Create a re-engagement sequence for churned users",
        ],
    ),
    "pricing": (
        "Pricing Strategist",
        "Pricing and monetization expert: tier structures, value metrics, competitor positioning, and comparison pages",
        20,
        [
            "Help me price my SaaS product — currently freemium with 3 tiers",
            "Create a competitor comparison page for my product vs Notion",
            "Should I use per-seat, usage-based, or flat pricing?",
        ],
    ),
}

# Load division definition
_division_def = load_division(DIVISION)

# Build skills list from the division definition
SKILLS = [
    {
        "id": skill.skill_id,
        "name": skill.name,
        "description": skill.description,
        "inputModes": ["text"],
        "outputModes": ["text"],
    }
    for skill in _division_def.skills
]

div_name, div_desc, div_credits, div_starters = DIVISION_META.get(
    DIVISION,
    (DIVISION.title(), f"Marketing {DIVISION} agent", 20, []),
)

# Override credits from division metadata
CREDITS = float(os.environ.get("CREDITS_PER_TASK", str(div_credits)))


async def handle(skill_id: str, messages: list[TaskMessage]) -> list[Artifact]:
    """Handle a task by routing to the division's system prompt."""
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

    # All skills within a division share the same combined system prompt
    system_prompt = _division_def.system_prompt

    result = await llm_call(system_prompt, text)

    return [Artifact(
        name=f"{skill_id}-response",
        parts=[MessagePart(type="text", content=result)],
        metadata={"skill": skill_id, "division": DIVISION},
    )]


app = create_a2a_app(
    name=f"Marketing Pro: {div_name}",
    description=div_desc,
    version="1.0.0",
    skills=SKILLS,
    handler_func=handle,
    port=PORT,
    credits_per_task=CREDITS,
)
