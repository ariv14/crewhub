"""Research Agent -- demo A2A agent that demonstrates A2A delegation.

Skills:
  - research-topic   Research a topic and compile a structured report.

Port: 8005
Credits: 10 per task

This agent demonstrates the core A2A value proposition: when the user's
request mentions translation or a specific language, the Research Agent
discovers the Universal Translator agent via the marketplace discovery API
and delegates a translation sub-task using the A2A protocol.

Run standalone:
    uvicorn demo_agents.research_agent.agent:app --port 8005
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

import httpx

from demo_agents.base import Artifact, MessagePart, TaskMessage, create_a2a_app

PORT = 8005
CREDITS = 10
MARKETPLACE_API = "http://localhost:8000/api/v1"

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
                "output": "# AI in Healthcare\n\n## Overview\n...\n## Key Findings\n...\n## Analysis\n...",
                "description": "Research report on a technology topic",
            },
            {
                "input": "Research renewable energy and translate to Spanish",
                "output": "[ES] # Energia Renovable\n...",
                "description": "Research report with translation delegation",
            },
        ],
    },
]

# ---------------------------------------------------------------------------
# Language detection in request
# ---------------------------------------------------------------------------

LANGUAGE_RE = re.compile(
    r"(?:translate\s+(?:to|into)|in\s+)(\w+)",
    re.IGNORECASE,
)

KNOWN_LANGUAGES = {
    "spanish", "french", "german", "italian", "portuguese",
    "japanese", "chinese", "korean", "russian", "arabic",
    "hindi", "dutch", "swedish", "english",
}


def _detect_translation_request(text: str) -> str | None:
    """Return the target language if the user wants translation, else None."""
    m = LANGUAGE_RE.search(text)
    if m:
        lang = m.group(1).lower()
        if lang in KNOWN_LANGUAGES:
            return lang
    # Also check for explicit keywords
    lower = text.lower()
    if "translate" in lower:
        for lang in KNOWN_LANGUAGES:
            if lang in lower:
                return lang
    return None


# ---------------------------------------------------------------------------
# Report generation (simulated research)
# ---------------------------------------------------------------------------

def _generate_report(topic: str) -> str:
    """Generate a structured research report on the topic.

    In a real agent this would call an LLM or search engine. Here we produce
    a deterministic template-based report so the demo works offline.
    """
    topic_title = topic.strip().rstrip(".").title()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return f"""# Research Report: {topic_title}

Generated: {timestamp}

## Overview

{topic_title} is a rapidly evolving area that has garnered significant attention
from researchers, industry practitioners, and policymakers alike. This report
provides a structured overview of the current state, key findings, and
forward-looking analysis.

## Key Findings

1. **Growing Adoption**: {topic_title} adoption has accelerated across multiple
   sectors, with a notable increase in investment and research output over the
   past five years.

2. **Technical Advances**: Recent breakthroughs have addressed several
   long-standing challenges, making {topic_title} more practical and accessible
   for mainstream applications.

3. **Economic Impact**: Studies estimate that {topic_title} could contribute
   significantly to economic growth, with projected market size reaching
   substantial figures within the next decade.

4. **Challenges Remain**: Despite progress, challenges including scalability,
   standardization, ethical considerations, and workforce readiness continue
   to require attention.

5. **Regulatory Landscape**: Governments worldwide are developing frameworks
   to govern {topic_title}, balancing innovation incentives with safety and
   fairness requirements.

## Analysis

The trajectory of {topic_title} suggests a maturation phase where early
experimental approaches are giving way to production-grade solutions. Key
success factors include cross-disciplinary collaboration, investment in
foundational infrastructure, and proactive engagement with stakeholders.

Organizations looking to leverage {topic_title} should focus on:
- Building internal expertise and talent pipelines
- Starting with well-scoped pilot projects before scaling
- Establishing governance frameworks early
- Engaging with the broader ecosystem for standards alignment

## Conclusion

{topic_title} represents both a significant opportunity and a complex challenge.
Stakeholders who take a measured, strategic approach are likely to realize the
greatest long-term benefits.

---
*Report compiled by Research Agent v1.0.0*
"""


# ---------------------------------------------------------------------------
# A2A delegation helpers
# ---------------------------------------------------------------------------

async def _discover_translator() -> str | None:
    """Find the Universal Translator agent endpoint via the marketplace API.

    Returns the agent's A2A endpoint URL, or None if unavailable.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Try the discovery search endpoint
            resp = await client.post(
                f"{MARKETPLACE_API}/discover/",
                json={
                    "query": "translate",
                    "mode": "keyword",
                    "limit": 5,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                for match in data.get("matches", []):
                    agent = match.get("agent", {})
                    if "translat" in agent.get("name", "").lower():
                        return agent.get("endpoint")

            # Fallback: list agents and find translator
            resp = await client.get(f"{MARKETPLACE_API}/agents/")
            if resp.status_code == 200:
                data = resp.json()
                for agent in data.get("agents", []):
                    if "translat" in agent.get("name", "").lower():
                        return agent.get("endpoint")
    except httpx.HTTPError:
        pass

    return None


async def _delegate_translation(endpoint: str, text: str, target_language: str) -> str | None:
    """Send a translation task to the translator agent via A2A protocol."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            payload = {
                "jsonrpc": "2.0",
                "method": "tasks/send",
                "id": str(uuid.uuid4()),
                "params": {
                    "id": str(uuid.uuid4()),
                    "skill_id": "translate",
                    "messages": [
                        {
                            "role": "user",
                            "parts": [
                                {
                                    "type": "text",
                                    "content": f"Translate to {target_language}: {text}",
                                }
                            ],
                        }
                    ],
                },
            }
            resp = await client.post(f"{endpoint}/", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                result = data.get("result", {})
                artifacts = result.get("artifacts", [])
                if artifacts:
                    parts = artifacts[0].get("parts", [])
                    if parts:
                        return parts[0].get("content")
    except httpx.HTTPError:
        pass
    return None


async def _try_direct_translator(text: str, target_language: str) -> str | None:
    """Try the translator agent directly at the well-known port."""
    return await _delegate_translation("http://localhost:8002", text, target_language)


# ---------------------------------------------------------------------------
# A2A handler
# ---------------------------------------------------------------------------

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

    # Strip translation instructions from the topic for report generation
    target_language = _detect_translation_request(text)
    topic = text
    if target_language:
        # Remove the translation part from the topic
        topic = re.sub(
            r"(?:and\s+)?(?:also\s+)?translate\s+(?:it\s+)?(?:to|into)\s+\w+",
            "",
            topic,
            flags=re.IGNORECASE,
        ).strip().rstrip(",. ")
        topic = re.sub(
            r"\s+in\s+\w+\s*$",
            "",
            topic,
            flags=re.IGNORECASE,
        ).strip()

    # Step 1: Generate the report
    report = _generate_report(topic)

    artifacts: list[Artifact] = [
        Artifact(
            name="research-report",
            parts=[MessagePart(type="text", content=report)],
            metadata={"topic": topic, "language": "en"},
        ),
    ]

    # Step 2: If translation requested, delegate via A2A
    if target_language:
        delegation_log: list[str] = []
        translated = None

        # Try marketplace discovery first
        delegation_log.append(f"Translation to {target_language} requested.")
        translator_endpoint = await _discover_translator()

        if translator_endpoint:
            delegation_log.append(f"Discovered translator at: {translator_endpoint}")
            translated = await _delegate_translation(translator_endpoint, report, target_language)
        else:
            delegation_log.append("Marketplace discovery unavailable, trying direct connection.")

        # Fallback: direct connection to translator on well-known port
        if translated is None:
            translated = await _try_direct_translator(report, target_language)
            if translated:
                delegation_log.append("Connected directly to translator at localhost:8002.")

        if translated:
            delegation_log.append("Translation completed successfully via A2A delegation.")
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


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = create_a2a_app(
    name="Research Agent",
    description=(
        "Researches a topic and compiles a structured report. Demonstrates "
        "A2A delegation by discovering and using other marketplace agents "
        "(e.g., the Universal Translator) for sub-tasks."
    ),
    version="1.0.0",
    skills=SKILLS,
    handler_func=handle,
    port=PORT,
    credits_per_task=CREDITS,
)
