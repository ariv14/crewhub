# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""AI Researcher — workflow-ready agent for structured research and analysis.

Designed to be the first step in a workflow pipeline. Takes a research
question, produces structured findings as A2UI tables that downstream
agents (Content Writer, Data Insights) can consume.

Skills:
  - research-topic    Deep-dive research with structured findings
  - compare-options   Compare alternatives with pros/cons table

Port: 8008
Credits: 5 per task
"""

from __future__ import annotations

import json
import re

from demo_agents.base import (
    Artifact,
    MessagePart,
    StreamChunk,
    TaskMessage,
    create_a2a_app,
    emit_table,
    llm_call,
    llm_call_streaming,
)

PORT = 8008
CREDITS = 5

SKILLS = [
    {
        "id": "research-topic",
        "name": "Research Topic",
        "description": (
            "Deep-dive research on any topic. Returns structured findings with "
            "key facts, sources, and a summary table. Perfect as the first step "
            "in a workflow — feed results into Content Writer or Data Insights."
        ),
        "inputModes": ["text"],
        "outputModes": ["text"],
        "examples": [
            {"input": "Research the current state of AI agent marketplaces", "output": "Structured findings table with key players, market size, trends.", "description": "Market research"},
            {"input": "What are the best practices for building AI agents?", "output": "Table of best practices with descriptions and importance.", "description": "Best practices research"},
        ],
    },
    {
        "id": "compare-options",
        "name": "Compare Options",
        "description": (
            "Compare 2-5 alternatives side by side. Returns a detailed comparison "
            "table with criteria, scores, and a recommendation. Great for "
            "decision-making workflows."
        ),
        "inputModes": ["text"],
        "outputModes": ["text"],
        "examples": [
            {"input": "Compare React vs Vue vs Svelte for a new project", "output": "Comparison table with criteria scores and recommendation.", "description": "Framework comparison"},
        ],
    },
]

RESEARCH_PROMPT = """You are a thorough research analyst. Research the topic and return structured findings.

Return ONLY valid JSON (no other text):
{
  "summary": "2-3 sentence executive summary of findings",
  "table_title": "Title for the findings table",
  "headers": ["Finding", "Details", "Importance"],
  "rows": [
    ["finding 1", "details about it", "High/Medium/Low"],
    ["finding 2", "details about it", "High/Medium/Low"]
  ]
}

Return 5-8 rows of well-researched, specific findings. Be factual and concrete.
IMPORTANT: Return ONLY valid JSON."""

COMPARE_PROMPT = """You are a decision analysis expert. Compare the options the user asks about.

Return ONLY valid JSON (no other text):
{
  "summary": "2-3 sentence recommendation with reasoning",
  "table_title": "Comparison: [items being compared]",
  "headers": ["Criteria", "OPTION_1", "OPTION_2", "OPTION_3"],
  "rows": [
    ["Learning Curve", "Easy", "Medium", "Hard"],
    ["Performance", "Good", "Excellent", "Good"],
    ["Ecosystem", "Large", "Growing", "Small"]
  ]
}

Use 5-8 comparison criteria. Replace OPTION_1/2/3 with actual option names.
Adjust the number of option columns to match the user's request (2-5 options).
IMPORTANT: Return ONLY valid JSON."""


def _extract_json(text: str) -> dict | None:
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
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
        return [Artifact(name="error", parts=[MessagePart(type="text", content="No input provided.")])]

    prompt = RESEARCH_PROMPT if skill_id == "research-topic" else COMPARE_PROMPT
    raw = await llm_call(prompt, text)
    data = _extract_json(raw)

    if not data:
        return [Artifact(name="research", parts=[MessagePart(type="text", content=raw)], metadata={"skill": skill_id})]

    return [Artifact(
        name="research-findings" if skill_id == "research-topic" else "comparison",
        parts=[MessagePart(type="text", content=data.get("summary", ""))],
        metadata={"skill": skill_id},
        ui_components=[emit_table(data.get("table_title", "Findings"), data.get("headers", []), data.get("rows", []))],
    )]


async def handle_streaming(skill_id: str, messages: list[TaskMessage]):
    text = ""
    for msg in messages:
        for part in msg.parts:
            if part.type == "text" and part.content:
                text += part.content + "\n"
    text = text.strip()
    if not text:
        yield StreamChunk(type="error", content="No input provided.")
        return

    yield StreamChunk(type="thinking", content="Researching..." if skill_id == "research-topic" else "Comparing options...")

    prompt = RESEARCH_PROMPT if skill_id == "research-topic" else COMPARE_PROMPT
    accumulated = ""
    async for chunk in llm_call_streaming(prompt, text):
        accumulated += chunk
        yield StreamChunk(type="text", content=chunk)

    data = _extract_json(accumulated)
    if not data:
        yield StreamChunk(type="done", artifacts=[Artifact(name="research", parts=[MessagePart(type="text", content=accumulated)])])
        return

    yield StreamChunk(type="done", artifacts=[Artifact(
        name="research-findings" if skill_id == "research-topic" else "comparison",
        parts=[MessagePart(type="text", content=data.get("summary", ""))],
        metadata={"skill": skill_id},
        ui_components=[emit_table(data.get("table_title", "Findings"), data.get("headers", []), data.get("rows", []))],
    )])


app = create_a2a_app(
    name="AI Researcher",
    description="Deep research and comparison analysis with structured findings. Workflow-ready — chain with Content Writer or Data Insights.",
    version="1.0.0",
    skills=SKILLS,
    handler_func=handle,
    port=PORT,
    credits_per_task=CREDITS,
    streaming_handler_func=handle_streaming,
)
