"""Text Summarizer -- demo A2A agent (LLM-powered).

Skills:
  - summarize        Produce a concise summary of text.
  - extract-key-points   Return bullet-point key takeaways.

Port: 8001
Credits: 1 per task

Run standalone:
    uvicorn demo_agents.summarizer.agent:app --port 8001
"""

from __future__ import annotations

from demo_agents.base import Artifact, MessagePart, TaskMessage, create_a2a_app, llm_call

PORT = 8001
CREDITS = 1

SKILLS = [
    {
        "id": "summarize",
        "name": "Summarize Text",
        "description": "Produce a concise summary of the input text.",
        "inputModes": ["text"],
        "outputModes": ["text"],
        "examples": [
            {
                "input": "A long article about climate change...",
                "output": "Climate change is accelerating. Global temperatures rose by 1.1C...",
                "description": "Summarise a news article",
            }
        ],
    },
    {
        "id": "extract-key-points",
        "name": "Extract Key Points",
        "description": "Return a bullet-point list of the most important takeaways from the input text.",
        "inputModes": ["text"],
        "outputModes": ["text"],
        "examples": [
            {
                "input": "Meeting notes discussing Q3 targets...",
                "output": "- Revenue target: $2M\n- New hires: 5 engineers\n- Launch date: Sep 15",
                "description": "Extract action items from meeting notes",
            }
        ],
    },
]

SYSTEM_PROMPTS = {
    "summarize": (
        "You are a text summarizer. Produce a concise summary of the input text. "
        "Focus on the most important information. Keep the summary to 2-4 sentences."
    ),
    "extract-key-points": (
        "You are a text analyst. Extract the most important takeaways from the input text. "
        "Return them as a bullet-point list (using - prefix). Keep each point to one sentence."
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
            parts=[MessagePart(type="text", content="No text provided to summarize.")],
        )]

    system_prompt = SYSTEM_PROMPTS.get(skill_id, SYSTEM_PROMPTS["summarize"])
    result = await llm_call(system_prompt, text)
    artifact_name = "key-points" if skill_id == "extract-key-points" else "summary"

    return [Artifact(
        name=artifact_name,
        parts=[MessagePart(type="text", content=result)],
        metadata={"skill": skill_id, "input_length": len(text), "output_length": len(result)},
    )]


app = create_a2a_app(
    name="Text Summarizer",
    description="Summarizes text and extracts key points using an LLM.",
    version="1.0.0",
    skills=SKILLS,
    handler_func=handle,
    port=PORT,
    credits_per_task=CREDITS,
)
