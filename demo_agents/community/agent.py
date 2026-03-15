# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Community Toolkit -- free utility agent with 5 daily-use skills.

Skills:
  - quick-summarize    Summarize any text in 2-3 sentences
  - fix-grammar        Fix grammar, spelling, improve clarity
  - format-json        Format/validate/convert JSON, YAML, CSV
  - eli5               Explain any concept simply
  - draft-email        Draft professional email from bullet points

Port: 8003
Credits: 0 (free / open-source)

Run standalone:
    uvicorn demo_agents.community.agent:app --port 8003
"""

from __future__ import annotations

from demo_agents.base import Artifact, MessagePart, TaskMessage, create_a2a_app, llm_call

PORT = 8003
CREDITS = 0

SKILLS = [
    {
        "id": "quick-summarize",
        "name": "Quick Summarizer",
        "description": "Summarize any text in 2-3 clear sentences.",
        "inputModes": ["text"],
        "outputModes": ["text"],
        "examples": [
            {
                "input": "A lengthy article about renewable energy trends...",
                "output": "Renewable energy adoption surged 30% in 2025, led by solar and wind. Battery storage costs dropped below $100/kWh, making grid-scale storage viable.",
                "description": "Summarize a news article",
            }
        ],
    },
    {
        "id": "fix-grammar",
        "name": "Grammar Fixer",
        "description": "Fix grammar, spelling, and improve clarity while preserving meaning.",
        "inputModes": ["text"],
        "outputModes": ["text"],
        "examples": [
            {
                "input": "Their going to the store becuz they needs milk and also bread to.",
                "output": "They're going to the store because they need milk and bread too.",
                "description": "Fix common grammar mistakes",
            }
        ],
    },
    {
        "id": "format-json",
        "name": "JSON Formatter",
        "description": "Format, validate, or convert between JSON, YAML, and CSV.",
        "inputModes": ["text"],
        "outputModes": ["text"],
        "examples": [
            {
                "input": '{"name":"Alice","age":30,"skills":["python","sql"]}',
                "output": '{\n  "name": "Alice",\n  "age": 30,\n  "skills": [\n    "python",\n    "sql"\n  ]\n}',
                "description": "Pretty-print minified JSON",
            }
        ],
    },
    {
        "id": "eli5",
        "name": "ELI5 Explainer",
        "description": "Explain any concept in simple terms anyone can understand.",
        "inputModes": ["text"],
        "outputModes": ["text"],
        "examples": [
            {
                "input": "How does HTTPS encryption work?",
                "output": "Imagine you and a friend have a secret language only you two understand. HTTPS is like that — your browser and a website agree on a secret code before talking, so nobody listening in can understand what you're saying.",
                "description": "Explain a technical concept simply",
            }
        ],
    },
    {
        "id": "draft-email",
        "name": "Email Writer",
        "description": "Draft a professional email from bullet points or rough notes.",
        "inputModes": ["text"],
        "outputModes": ["text"],
        "examples": [
            {
                "input": "- meeting moved to Thursday\n- same time 2pm\n- room changed to 4B\n- bring laptop",
                "output": "Subject: Meeting Rescheduled to Thursday\n\nHi team,\n\nQuick update — our meeting has been moved to Thursday at 2:00 PM. We'll be in Room 4B instead. Please bring your laptops.\n\nThanks!",
                "description": "Turn bullet points into a professional email",
            }
        ],
    },
]

SYSTEM_PROMPTS = {
    "quick-summarize": (
        "You are a concise text summarizer. Summarize the input in 2-3 clear sentences. "
        "Focus on the most important information. Be direct and informative."
    ),
    "fix-grammar": (
        "You are a grammar and writing assistant. Fix all grammar, spelling, and punctuation errors. "
        "Improve clarity and readability while preserving the original meaning and tone. "
        "Return only the corrected text without explanations."
    ),
    "format-json": (
        "You are a data formatting assistant. When given JSON, pretty-print it with 2-space indentation. "
        "When given YAML, convert to formatted JSON. When given CSV, convert to a JSON array of objects. "
        "If the input is malformed, explain the error and suggest a fix. "
        "Return only the formatted output without explanations unless there's an error."
    ),
    "eli5": (
        "You are an ELI5 (Explain Like I'm 5) expert. Explain the given concept in simple, everyday language. "
        "Use analogies and examples that anyone can understand. Avoid jargon. "
        "Keep your explanation to 2-4 sentences."
    ),
    "draft-email": (
        "You are a professional email writer. Given bullet points, rough notes, or a brief description, "
        "draft a clear, professional email. Include an appropriate subject line. "
        "Match the tone to the content — formal for business, friendly for team updates. "
        "Keep it concise."
    ),
}


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
            parts=[MessagePart(type="text", content="No input text provided.")],
        )]

    system_prompt = SYSTEM_PROMPTS.get(skill_id, SYSTEM_PROMPTS["quick-summarize"])
    result = await llm_call(system_prompt, text)

    return [Artifact(
        name=skill_id,
        parts=[MessagePart(type="text", content=result)],
        metadata={"skill": skill_id, "input_length": len(text), "output_length": len(result)},
    )]


app = create_a2a_app(
    name="Community Toolkit",
    description="Free utility agents for everyday tasks — summarize, fix grammar, format JSON, explain concepts, and draft emails.",
    version="1.0.0",
    skills=SKILLS,
    handler_func=handle,
    port=PORT,
    credits_per_task=CREDITS,
)
