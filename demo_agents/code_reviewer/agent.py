"""Code Reviewer -- demo A2A agent (LLM-powered).

Skills:
  - review-code           Review code for common issues.
  - suggest-improvements  Suggest concrete improvements.

Port: 8003
Credits: 3 per task

Run standalone:
    uvicorn demo_agents.code_reviewer.agent:app --port 8003
"""

from __future__ import annotations

from demo_agents.base import Artifact, MessagePart, TaskMessage, create_a2a_app, llm_call

PORT = 8003
CREDITS = 3

SKILLS = [
    {
        "id": "review-code",
        "name": "Review Code",
        "description": "Analyse source code for quality issues including bugs, style, missing docs, and security concerns.",
        "inputModes": ["text"],
        "outputModes": ["text"],
        "examples": [
            {
                "input": "def foo(x):\n    return x+1",
                "output": "Issues found:\n- Missing docstring for function 'foo'\n- Missing type hints",
                "description": "Review a simple function",
            }
        ],
    },
    {
        "id": "suggest-improvements",
        "name": "Suggest Code Improvements",
        "description": "Return actionable suggestions to improve code quality, readability, and maintainability.",
        "inputModes": ["text"],
        "outputModes": ["text"],
        "examples": [
            {
                "input": "def foo(x):\n    return x+1",
                "output": "Suggestions:\n1. Add a docstring\n2. Add type hints: def foo(x: int) -> int:",
                "description": "Suggest improvements for a simple function",
            }
        ],
    },
]

SYSTEM_PROMPTS = {
    "review-code": (
        "You are an expert code reviewer. Review the provided code for:\n"
        "- Bugs and logic errors\n"
        "- Style and readability issues\n"
        "- Missing documentation\n"
        "- Security concerns\n"
        "- Performance issues\n\n"
        "Format your response as a numbered list of issues found. "
        "If no issues, say 'No issues found. The code looks clean.'"
    ),
    "suggest-improvements": (
        "You are an expert code reviewer. Suggest concrete, actionable improvements "
        "for the provided code. Focus on readability, maintainability, and best practices. "
        "Format as a numbered list of suggestions."
    ),
}


async def handle(skill_id: str, messages: list[TaskMessage]) -> list[Artifact]:
    code = ""
    for msg in messages:
        for part in msg.parts:
            if part.type == "text" and part.content:
                code += part.content + "\n"
    code = code.strip()

    if not code:
        return [Artifact(
            name="error",
            parts=[MessagePart(type="text", content="No code provided for review.")],
        )]

    system_prompt = SYSTEM_PROMPTS.get(skill_id, SYSTEM_PROMPTS["review-code"])
    result = await llm_call(system_prompt, code)
    artifact_name = "improvements" if skill_id == "suggest-improvements" else "review"

    return [Artifact(
        name=artifact_name,
        parts=[MessagePart(type="text", content=result)],
        metadata={"skill": skill_id, "lines_analyzed": len(code.split("\n"))},
    )]


app = create_a2a_app(
    name="Code Reviewer",
    description="Reviews code for quality issues and suggests improvements using an LLM.",
    version="1.0.0",
    skills=SKILLS,
    handler_func=handle,
    port=PORT,
    credits_per_task=CREDITS,
)
