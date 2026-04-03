# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Code Assistant Agent — A2UI showcase for code blocks and diffs.

Skills:
  - generate-code  Generate code with syntax-highlighted output
  - review-code    Review code and suggest improvements as diffs

Port: 8006
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
    emit_code,
    emit_diff,
    llm_call,
    llm_call_streaming,
)

PORT = 8006
CREDITS = 5

SKILLS = [
    {
        "id": "generate-code",
        "name": "Generate Code",
        "description": (
            "Generate code snippets with syntax highlighting. "
            "Specify the language and what you need — functions, classes, scripts, configs."
        ),
        "inputModes": ["text"],
        "outputModes": ["text"],
        "examples": [
            {
                "input": "Write a Python function to calculate fibonacci numbers with memoization",
                "output": "A syntax-highlighted Python function with explanation.",
                "description": "Python fibonacci generator",
            },
        ],
    },
    {
        "id": "review-code",
        "name": "Review & Improve Code",
        "description": (
            "Review code and suggest improvements. Returns a side-by-side diff "
            "showing the original and improved version with explanation."
        ),
        "inputModes": ["text"],
        "outputModes": ["text"],
        "examples": [
            {
                "input": "Review this Python code: def add(a,b): return a+b",
                "output": "A diff showing the original vs improved code with type hints and docstring.",
                "description": "Simple function improvement",
            },
        ],
    },
]

GENERATE_SYSTEM_PROMPT = """You are an expert programmer. Generate clean, well-documented code.

You MUST return your response in this exact JSON format (no other text before or after):
{
  "explanation": "Brief explanation of what the code does and design choices",
  "language": "python",
  "filename": "example.py",
  "code": "def fibonacci(n):\\n    pass"
}

Use proper indentation (\\n for newlines, spaces for indentation in the code string).
The code should be complete, runnable, and follow best practices.
IMPORTANT: Return ONLY valid JSON, no markdown, no code fences, no text before or after."""

REVIEW_SYSTEM_PROMPT = """You are a senior code reviewer. Review the user's code and suggest improvements.

You MUST return your response in this exact JSON format (no other text before or after):
{
  "explanation": "What was improved and why",
  "language": "python",
  "before": "original code here",
  "after": "improved code here"
}

Keep the improved version functionally equivalent but better: add type hints, docstrings,
error handling, better naming, or performance improvements as appropriate.
Use \\n for newlines in the code strings.
IMPORTANT: Return ONLY valid JSON, no markdown, no code fences, no text before or after."""


def _extract_json(text: str) -> dict | None:
    """Best-effort JSON extraction from LLM output."""
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
        return [Artifact(
            name="error",
            parts=[MessagePart(type="text", content="No input provided.")],
        )]

    if skill_id == "generate-code":
        prompt = GENERATE_SYSTEM_PROMPT
    else:
        prompt = REVIEW_SYSTEM_PROMPT

    raw = await llm_call(prompt, text)
    data = _extract_json(raw)

    if not data:
        return [Artifact(
            name="code-output",
            parts=[MessagePart(type="text", content=raw)],
            metadata={"skill": skill_id, "parse_error": True},
        )]

    explanation = data.get("explanation", "")
    language = data.get("language", "python")

    if skill_id == "generate-code":
        components = [
            emit_code(
                data.get("code", ""),
                language,
                filename=data.get("filename"),
                title="Generated Code",
            ),
        ]
    else:
        components = [
            emit_diff(
                data.get("before", ""),
                data.get("after", ""),
                language=language,
                title="Code Improvements",
            ),
        ]

    return [Artifact(
        name="generated-code" if skill_id == "generate-code" else "code-review",
        parts=[MessagePart(type="text", content=explanation)],
        metadata={"skill": skill_id, "language": language},
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

    if skill_id == "generate-code":
        yield StreamChunk(type="thinking", content="Generating code...")
        prompt = GENERATE_SYSTEM_PROMPT
    else:
        yield StreamChunk(type="thinking", content="Reviewing code and preparing improvements...")
        prompt = REVIEW_SYSTEM_PROMPT

    accumulated = ""
    async for chunk in llm_call_streaming(prompt, text):
        accumulated += chunk
        yield StreamChunk(type="text", content=chunk)

    data = _extract_json(accumulated)

    if not data:
        yield StreamChunk(
            type="done",
            artifacts=[Artifact(
                name="code-output",
                parts=[MessagePart(type="text", content=accumulated)],
                metadata={"skill": skill_id, "parse_error": True},
            )],
        )
        return

    explanation = data.get("explanation", "")
    language = data.get("language", "python")

    if skill_id == "generate-code":
        components = [
            emit_code(
                data.get("code", ""),
                language,
                filename=data.get("filename"),
                title="Generated Code",
            ),
        ]
    else:
        components = [
            emit_diff(
                data.get("before", ""),
                data.get("after", ""),
                language=language,
                title="Code Improvements",
            ),
        ]

    yield StreamChunk(
        type="done",
        artifacts=[Artifact(
            name="generated-code" if skill_id == "generate-code" else "code-review",
            parts=[MessagePart(type="text", content=explanation)],
            metadata={"skill": skill_id, "language": language},
            ui_components=components,
        )],
    )


app = create_a2a_app(
    name="Code Assistant",
    description="Generate code and review improvements with syntax highlighting and diffs.",
    version="1.0.0",
    skills=SKILLS,
    handler_func=handle,
    port=PORT,
    credits_per_task=CREDITS,
    streaming_handler_func=handle_streaming,
)
