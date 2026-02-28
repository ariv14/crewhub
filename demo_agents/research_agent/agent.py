"""Research Agent -- demo A2A agent with LLM + real A2A delegation.

Skills:
  - research-topic   Research a topic and compile a structured report.

Port: 8005
Credits: 10 per task

Demonstrates:
  1. LLM-powered report generation
  2. Discovery of other agents via marketplace API
  3. A2A protocol delegation to translator/summarizer

Run standalone:
    uvicorn demo_agents.research_agent.agent:app --port 8005
"""

from __future__ import annotations

import os
import re
import uuid

import httpx

from demo_agents.base import Artifact, MessagePart, TaskMessage, create_a2a_app, llm_call

PORT = 8005
CREDITS = 10
MARKETPLACE_API = os.environ.get("CREWHUB_API_URL", "http://localhost:8080") + "/api/v1"

SKILLS = [
    {
        "id": "research-topic",
        "name": "Research Topic",
        "description": (
            "Research a topic and compile a structured report with sections "
            "for overview, key findings, and analysis. If the request mentions "
            "translating the report into another language, the agent will "
            "discover and delegate to a translation agent via the marketplace."
        ),
        "inputModes": ["text"],
        "outputModes": ["text"],
        "examples": [
            {
                "input": "Research the impact of AI on healthcare",
                "output": "# AI in Healthcare\n\n## Overview\n...",
                "description": "Research report on a technology topic",
            },
            {
                "input": "Research renewable energy and translate to Spanish",
                "output": "# Energia Renovable\n...",
                "description": "Research report with translation delegation",
            },
        ],
    },
]

KNOWN_LANGUAGES = {
    "spanish", "french", "german", "italian", "portuguese",
    "japanese", "chinese", "korean", "russian", "arabic",
    "hindi", "dutch", "swedish", "english",
}

LANGUAGE_RE = re.compile(
    r"(?:translate\s+(?:to|into)|in\s+)(\w+)",
    re.IGNORECASE,
)

RESEARCH_SYSTEM_PROMPT = (
    "You are a research analyst. Write a structured research report on the given topic.\n\n"
    "Format your report with these sections:\n"
    "# Research Report: [Topic]\n\n"
    "## Overview\n[2-3 paragraphs]\n\n"
    "## Key Findings\n[Numbered list of 4-5 findings]\n\n"
    "## Analysis\n[2-3 paragraphs with actionable insights]\n\n"
    "## Conclusion\n[1 paragraph summary]\n\n"
    "Be informative, specific, and cite concrete examples where possible."
)


def _detect_translation_request(text: str) -> str | None:
    """Return the target language if the user wants translation, else None."""
    m = LANGUAGE_RE.search(text)
    if m:
        lang = m.group(1).lower()
        if lang in KNOWN_LANGUAGES:
            return lang
    lower = text.lower()
    if "translate" in lower:
        for lang in KNOWN_LANGUAGES:
            if lang in lower:
                return lang
    return None


def _strip_translation_from_topic(text: str) -> str:
    """Remove translation instructions from the research topic."""
    topic = re.sub(
        r"(?:and\s+)?(?:also\s+)?translate\s+(?:it\s+)?(?:to|into)\s+\w+",
        "", text, flags=re.IGNORECASE,
    ).strip().rstrip(",. ")
    topic = re.sub(r"\s+in\s+\w+\s*$", "", topic, flags=re.IGNORECASE).strip()
    return topic


async def _discover_agent(query: str, name_contains: str) -> str | None:
    """Find an agent endpoint via marketplace discovery API."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{MARKETPLACE_API}/discover/",
                json={"query": query, "mode": "keyword", "limit": 5},
            )
            if resp.status_code == 200:
                for match in resp.json().get("matches", []):
                    agent = match.get("agent", {})
                    if name_contains in agent.get("name", "").lower():
                        return agent.get("endpoint")

            resp = await client.get(f"{MARKETPLACE_API}/agents/")
            if resp.status_code == 200:
                for agent in resp.json().get("agents", []):
                    if name_contains in agent.get("name", "").lower():
                        return agent.get("endpoint")
    except httpx.HTTPError:
        pass
    return None


async def _delegate_a2a(endpoint: str, skill_id: str, text: str) -> str | None:
    """Send a task to another agent via A2A protocol."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "jsonrpc": "2.0",
                "method": "tasks/send",
                "id": str(uuid.uuid4()),
                "params": {
                    "id": str(uuid.uuid4()),
                    "skill_id": skill_id,
                    "messages": [
                        {
                            "role": "user",
                            "parts": [{"type": "text", "content": text}],
                        }
                    ],
                },
            }
            resp = await client.post(f"{endpoint}/", json=payload)
            if resp.status_code == 200:
                result = resp.json().get("result", {})
                artifacts = result.get("artifacts", [])
                if artifacts:
                    parts = artifacts[0].get("parts", [])
                    if parts:
                        return parts[0].get("content")
    except httpx.HTTPError:
        pass
    return None


async def handle(skill_id: str, messages: list[TaskMessage]) -> list[Artifact]:
    text = ""
    for msg in messages:
        for part in msg.parts:
            if part.type == "text" and part.content:
                text += part.content + "\n"
    text = text.strip()

    if not text:
        return [Artifact(
            name="error",
            parts=[MessagePart(type="text", content="No research topic provided.")],
        )]

    target_language = _detect_translation_request(text)
    topic = _strip_translation_from_topic(text) if target_language else text

    delegation_log: list[str] = []

    # Step 1: Generate research report via LLM
    delegation_log.append(f"Researching topic: {topic}")
    report = await llm_call(RESEARCH_SYSTEM_PROMPT, f"Research topic: {topic}")
    delegation_log.append("Research report generated via LLM.")

    artifacts: list[Artifact] = [
        Artifact(
            name="research-report",
            parts=[MessagePart(type="text", content=report)],
            metadata={"topic": topic, "language": "en"},
        ),
    ]

    # Step 2: If translation requested, discover and delegate via A2A
    if target_language:
        delegation_log.append(f"Translation to {target_language} requested.")

        # Try marketplace discovery
        translator_endpoint = await _discover_agent("translate", "translat")

        if translator_endpoint:
            delegation_log.append(f"Discovered translator at: {translator_endpoint}")
        else:
            # Fallback to well-known port
            translator_endpoint = "http://localhost:8002"
            delegation_log.append("Marketplace discovery unavailable, trying localhost:8002.")

        translated = await _delegate_a2a(
            translator_endpoint, "translate",
            f"Translate to {target_language}: {report}",
        )

        if translated:
            delegation_log.append("Translation completed via A2A delegation.")
            artifacts.append(Artifact(
                name="translated-report",
                parts=[MessagePart(type="text", content=translated)],
                metadata={
                    "topic": topic,
                    "language": target_language,
                    "delegated_to": "Universal Translator",
                },
            ))
        else:
            delegation_log.append("Translation delegation failed. Returning English report only.")

    artifacts.append(Artifact(
        name="delegation-log",
        parts=[MessagePart(type="text", content="\n".join(delegation_log))],
        metadata={"type": "delegation-log"},
    ))

    return artifacts


app = create_a2a_app(
    name="Research Agent",
    description=(
        "Researches a topic and compiles a structured report using an LLM. "
        "Demonstrates A2A delegation by discovering and using other marketplace agents."
    ),
    version="1.0.0",
    skills=SKILLS,
    handler_func=handle,
    port=PORT,
    credits_per_task=CREDITS,
)
