# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Data Insights Agent — A2UI showcase for tables and charts.

Skills:
  - analyze-data     Analyze data and return structured tables
  - compare-metrics  Compare metrics with visual charts

Port: 8005
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
    emit_chart,
    emit_table,
    llm_call,
    llm_call_streaming,
)

PORT = 8005
CREDITS = 5

SKILLS = [
    {
        "id": "analyze-data",
        "name": "Analyze Data",
        "description": (
            "Analyze any topic and return structured data as a rich table. "
            "Ask about market trends, comparisons, rankings, stats — anything data-driven."
        ),
        "inputModes": ["text"],
        "outputModes": ["text"],
        "examples": [
            {
                "input": "Compare the top 5 programming languages by popularity in 2026",
                "output": "A table comparing Python, JavaScript, TypeScript, Go, and Rust with metrics.",
                "description": "Language comparison with structured table",
            },
        ],
    },
    {
        "id": "compare-metrics",
        "name": "Compare Metrics",
        "description": (
            "Compare items with visual charts. Returns bar, line, or pie charts "
            "alongside analysis. Great for market share, growth trends, feature comparisons."
        ),
        "inputModes": ["text"],
        "outputModes": ["text"],
        "examples": [
            {
                "input": "Show cloud provider market share: AWS, Azure, GCP",
                "output": "A pie chart showing market share distribution with analysis.",
                "description": "Cloud market share visualization",
            },
        ],
    },
]

TABLE_SYSTEM_PROMPT = """You are a data analyst. Analyze the user's request and return structured data.

You MUST return your response in this exact JSON format (no other text before or after):
{
  "summary": "Brief 1-2 sentence analysis",
  "table_title": "Title for the data table",
  "headers": ["Column1", "Column2", "Column3"],
  "rows": [
    ["row1-val1", "row1-val2", "row1-val3"],
    ["row2-val1", "row2-val2", "row2-val3"]
  ]
}

Return 4-8 rows of realistic data. Make values specific and numeric where appropriate.
IMPORTANT: Return ONLY valid JSON, no markdown, no code fences, no explanation before or after."""

CHART_SYSTEM_PROMPT = """You are a data visualization expert. The user wants to compare metrics visually.

You MUST return your response in this exact JSON format (no other text before or after):
{
  "summary": "Brief 1-2 sentence analysis of the comparison",
  "chart_title": "Title for the chart",
  "chart_type": "bar",
  "labels": ["Item1", "Item2", "Item3"],
  "datasets": [
    {"label": "Metric Name", "values": [65, 25, 10]}
  ]
}

chart_type must be one of: "bar", "line", "pie", "area".
Use "pie" for market share/proportions. Use "bar" for comparisons. Use "line" for trends over time.
Use 3-8 data points. Make values realistic and specific.
IMPORTANT: Return ONLY valid JSON, no markdown, no code fences, no explanation before or after."""


def _extract_json(text: str) -> dict | None:
    """Best-effort JSON extraction from LLM output."""
    # Try direct parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    # Try extracting from code fences
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    # Try finding first { ... } block
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
        return [Artifact(
            name="error",
            parts=[MessagePart(type="text", content="No input provided.")],
        )]

    if skill_id == "analyze-data":
        prompt = TABLE_SYSTEM_PROMPT
    else:
        prompt = CHART_SYSTEM_PROMPT

    raw = await llm_call(prompt, text)
    data = _extract_json(raw)

    if not data:
        return [Artifact(
            name="analysis",
            parts=[MessagePart(type="text", content=raw)],
            metadata={"skill": skill_id, "parse_error": True},
        )]

    if skill_id == "analyze-data":
        summary = data.get("summary", "Analysis complete.")
        components = [
            emit_table(
                data.get("table_title", "Data Analysis"),
                data.get("headers", []),
                data.get("rows", []),
            ),
        ]
    else:
        summary = data.get("summary", "Comparison complete.")
        components = [
            emit_chart(
                data.get("chart_title", "Metrics Comparison"),
                data.get("chart_type", "bar"),
                data.get("labels", []),
                data.get("datasets", []),
            ),
        ]

    return [Artifact(
        name="data-analysis" if skill_id == "analyze-data" else "metrics-chart",
        parts=[MessagePart(type="text", content=summary)],
        metadata={"skill": skill_id},
        ui_components=components,
    )]


async def handle_streaming(skill_id: str, messages: list[TaskMessage]):
    """Streaming version — shows thinking then emits rich components."""
    text = ""
    for msg in messages:
        for part in msg.parts:
            if part.type == "text" and part.content:
                text += part.content + "\n"
    text = text.strip()

    if not text:
        yield StreamChunk(type="error", content="No input provided.")
        return

    yield StreamChunk(type="thinking", content="Analyzing data and generating structured output...")

    if skill_id == "analyze-data":
        prompt = TABLE_SYSTEM_PROMPT
    else:
        prompt = CHART_SYSTEM_PROMPT

    # Stream the LLM response
    accumulated = ""
    async for chunk in llm_call_streaming(prompt, text):
        accumulated += chunk
        yield StreamChunk(type="text", content=chunk)

    # Parse the accumulated JSON
    data = _extract_json(accumulated)

    if not data:
        yield StreamChunk(
            type="done",
            artifacts=[Artifact(
                name="analysis",
                parts=[MessagePart(type="text", content=accumulated)],
                metadata={"skill": skill_id, "parse_error": True},
            )],
        )
        return

    if skill_id == "analyze-data":
        summary = data.get("summary", "Analysis complete.")
        components = [
            emit_table(
                data.get("table_title", "Data Analysis"),
                data.get("headers", []),
                data.get("rows", []),
            ),
        ]
    else:
        summary = data.get("summary", "Comparison complete.")
        components = [
            emit_chart(
                data.get("chart_title", "Metrics Comparison"),
                data.get("chart_type", "bar"),
                data.get("labels", []),
                data.get("datasets", []),
            ),
        ]

    yield StreamChunk(
        type="done",
        artifacts=[Artifact(
            name="data-analysis" if skill_id == "analyze-data" else "metrics-chart",
            parts=[MessagePart(type="text", content=summary)],
            metadata={"skill": skill_id},
            ui_components=components,
        )],
    )


app = create_a2a_app(
    name="Data Insights",
    description="Analyze data and visualize metrics with rich tables and charts.",
    version="1.0.0",
    skills=SKILLS,
    handler_func=handle,
    port=PORT,
    credits_per_task=CREDITS,
    streaming_handler_func=handle_streaming,
)
