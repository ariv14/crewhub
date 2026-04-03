# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Content Writer — workflow-ready agent for polished content creation.

Designed as the final step in a workflow pipeline. Takes raw input or
research findings and produces polished content with structured sections.

Skills:
  - write-article     Write a blog post or article with sections
  - write-summary     Create an executive summary from raw data/findings

Port: 8009
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

PORT = 8009
CREDITS = 5

SKILLS = [
    {
        "id": "write-article",
        "name": "Write Article",
        "description": (
            "Write a polished blog post or article with structured sections. "
            "Accepts raw notes, research findings, or a topic. Returns well-formatted "
            "content with a metadata table. Perfect as the final workflow step."
        ),
        "inputModes": ["text"],
        "outputModes": ["text"],
        "examples": [
            {"input": "Write an article about AI agent marketplaces based on these findings: ...", "output": "A polished article with intro, sections, and conclusion.", "description": "Article from research"},
            {"input": "Write a blog post about the future of MCP protocol", "output": "Engaging blog post with structured sections.", "description": "Topic-based article"},
        ],
    },
    {
        "id": "write-summary",
        "name": "Write Executive Summary",
        "description": (
            "Distill raw data, findings, or lengthy content into a crisp executive "
            "summary with key takeaways table. Ideal for workflow chains where "
            "upstream agents produce research that needs condensing."
        ),
        "inputModes": ["text"],
        "outputModes": ["text"],
        "examples": [
            {"input": "Summarize these research findings: ...", "output": "Executive summary with key takeaways table.", "description": "Summarize research"},
        ],
    },
]

ARTICLE_PROMPT = """You are a professional content writer. Write a polished, engaging article.

Return ONLY valid JSON (no other text):
{
  "title": "Article Title",
  "content": "Full article in markdown with ## headers for sections. Include an intro, 3-4 body sections, and a conclusion. Use **bold** for emphasis. 400-600 words.",
  "metadata_table": {
    "headers": ["Property", "Value"],
    "rows": [
      ["Word Count", "~500"],
      ["Reading Time", "~2 min"],
      ["Tone", "Professional/Informative"],
      ["Target Audience", "Tech professionals"],
      ["SEO Keywords", "keyword1, keyword2, keyword3"]
    ]
  }
}

IMPORTANT: Return ONLY valid JSON. The content field should be a single string with \\n for newlines."""

SUMMARY_PROMPT = """You are an executive communications expert. Create a crisp executive summary.

Return ONLY valid JSON (no other text):
{
  "summary": "3-5 paragraph executive summary in markdown. Clear, actionable, no fluff.",
  "takeaways_title": "Key Takeaways",
  "takeaways_headers": ["#", "Takeaway", "Impact", "Action Required"],
  "takeaways_rows": [
    ["1", "Key finding or insight", "High/Medium/Low", "What to do about it"],
    ["2", "Another key point", "High/Medium/Low", "Recommended action"]
  ]
}

Return 4-6 key takeaways. Be specific and actionable.
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

    prompt = ARTICLE_PROMPT if skill_id == "write-article" else SUMMARY_PROMPT
    raw = await llm_call(prompt, text)
    data = _extract_json(raw)

    if not data:
        return [Artifact(name="content", parts=[MessagePart(type="text", content=raw)], metadata={"skill": skill_id})]

    if skill_id == "write-article":
        content = data.get("content", "")
        title = data.get("title", "Article")
        meta = data.get("metadata_table", {})
        components = [emit_table("Article Metadata", meta.get("headers", []), meta.get("rows", []))] if meta.get("rows") else []
        return [Artifact(
            name=title,
            parts=[MessagePart(type="text", content=f"# {title}\n\n{content}")],
            metadata={"skill": skill_id},
            ui_components=components,
        )]
    else:
        summary = data.get("summary", "")
        components = [emit_table(
            data.get("takeaways_title", "Key Takeaways"),
            data.get("takeaways_headers", []),
            data.get("takeaways_rows", []),
        )]
        return [Artifact(
            name="executive-summary",
            parts=[MessagePart(type="text", content=summary)],
            metadata={"skill": skill_id},
            ui_components=components,
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

    yield StreamChunk(type="thinking", content="Writing..." if skill_id == "write-article" else "Summarizing...")

    prompt = ARTICLE_PROMPT if skill_id == "write-article" else SUMMARY_PROMPT
    accumulated = ""
    async for chunk in llm_call_streaming(prompt, text):
        accumulated += chunk
        yield StreamChunk(type="text", content=chunk)

    data = _extract_json(accumulated)
    if not data:
        yield StreamChunk(type="done", artifacts=[Artifact(name="content", parts=[MessagePart(type="text", content=accumulated)])])
        return

    artifacts = await handle(skill_id, messages)  # Reuse sync handler for artifact construction
    # Replace the LLM call result artifacts
    if skill_id == "write-article":
        content = data.get("content", "")
        title = data.get("title", "Article")
        meta = data.get("metadata_table", {})
        components = [emit_table("Article Metadata", meta.get("headers", []), meta.get("rows", []))] if meta.get("rows") else []
        yield StreamChunk(type="done", artifacts=[Artifact(
            name=title,
            parts=[MessagePart(type="text", content=f"# {title}\n\n{content}")],
            metadata={"skill": skill_id},
            ui_components=components,
        )])
    else:
        summary = data.get("summary", "")
        components = [emit_table(
            data.get("takeaways_title", "Key Takeaways"),
            data.get("takeaways_headers", []),
            data.get("takeaways_rows", []),
        )]
        yield StreamChunk(type="done", artifacts=[Artifact(
            name="executive-summary",
            parts=[MessagePart(type="text", content=summary)],
            metadata={"skill": skill_id},
            ui_components=components,
        )])


app = create_a2a_app(
    name="Content Writer",
    description="Write polished articles and executive summaries. Workflow-ready — chain after Researcher or Data Insights.",
    version="1.0.0",
    skills=SKILLS,
    handler_func=handle,
    port=PORT,
    credits_per_task=CREDITS,
    streaming_handler_func=handle_streaming,
)
