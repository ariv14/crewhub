# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Universal Translator -- demo A2A agent (LLM-powered).

Skills:
  - translate   Translate text between languages.

Port: 8002
Credits: 2 per task

Run standalone:
    uvicorn demo_agents.translator.agent:app --port 8002
"""

from __future__ import annotations

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

PORT = 8002
CREDITS = 2

SKILLS = [
    {
        "id": "translate",
        "name": "Translate Text",
        "description": "Translate text from one language to another. Specify the target language in the message (e.g., 'Translate to Spanish: ...').",
        "inputModes": ["text"],
        "outputModes": ["text"],
        "examples": [
            {
                "input": "Translate to Spanish: Hello, how are you?",
                "output": "Hola, como estas?",
                "description": "English to Spanish greeting",
            },
            {
                "input": "Translate to French: The weather is nice today.",
                "output": "Le temps est beau aujourd'hui.",
                "description": "English to French sentence",
            },
        ],
    },
]

SYSTEM_PROMPT = (
    "You are a professional translator. Translate the text to the requested language. "
    "The user will specify the target language. Output ONLY the translated text, "
    "nothing else — no explanations, no notes."
)


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
            parts=[MessagePart(type="text", content="No text provided for translation.")],
        )]

    translated = await llm_call(SYSTEM_PROMPT, text)

    return [Artifact(
        name="translation",
        parts=[MessagePart(type="text", content=translated)],
        metadata={"skill": skill_id, "char_count": len(text)},
    )]


async def handle_streaming(skill_id: str, messages: list[TaskMessage]):
    """Streaming version — yields text chunks as the LLM generates them."""
    text = ""
    for msg in messages:
        for part in msg.parts:
            if part.type == "text" and part.content:
                text += part.content + "\n"
    text = text.strip()

    if not text:
        yield StreamChunk(type="error", content="No text provided for translation.")
        return

    yield StreamChunk(type="thinking", content="Translating...")

    accumulated = ""
    async for chunk in llm_call_streaming(SYSTEM_PROMPT, text):
        accumulated += chunk
        yield StreamChunk(type="text", content=chunk)

    # Emit final artifact with A2UI table showing translation stats
    yield StreamChunk(
        type="done",
        artifacts=[Artifact(
            name="translation",
            parts=[MessagePart(type="text", content=accumulated)],
            metadata={"skill": skill_id, "char_count": len(text), "streamed": True},
            ui_components=[
                emit_table(
                    "Translation Details",
                    ["Metric", "Value"],
                    [
                        ["Input Characters", str(len(text))],
                        ["Output Characters", str(len(accumulated))],
                        ["Ratio", f"{len(accumulated)/max(len(text),1):.2f}x"],
                        ["Streaming", "Yes"],
                    ],
                ),
            ],
        )],
    )


app = create_a2a_app(
    name="Universal Translator",
    description="Translates text between languages using an LLM.",
    version="1.0.0",
    skills=SKILLS,
    handler_func=handle,
    port=PORT,
    credits_per_task=CREDITS,
    streaming_handler_func=handle_streaming,
)
