# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Data Analyst -- demo A2A agent (LLM-powered).

Skills:
  - analyze-csv             Analyze CSV data structure and content.
  - generate-summary-stats  Compute and interpret summary statistics.

Port: 8004
Credits: 5 per task

Run standalone:
    uvicorn demo_agents.data_analyst.agent:app --port 8004
"""

from __future__ import annotations

from demo_agents.base import Artifact, MessagePart, TaskMessage, create_a2a_app, llm_call

PORT = 8004
CREDITS = 5

SKILLS = [
    {
        "id": "analyze-csv",
        "name": "Analyze CSV Data",
        "description": "Parse CSV text and return a structural overview with insights.",
        "inputModes": ["text"],
        "outputModes": ["text"],
        "examples": [
            {
                "input": "name,age,salary\nAlice,30,50000\nBob,25,45000",
                "output": "Dataset has 2 rows and 3 columns...",
                "description": "Analyze a small CSV",
            }
        ],
    },
    {
        "id": "generate-summary-stats",
        "name": "Generate Summary Statistics",
        "description": "Compute and explain summary statistics for each column in a CSV dataset.",
        "inputModes": ["text"],
        "outputModes": ["text"],
        "examples": [
            {
                "input": "name,age,salary\nAlice,30,50000\nBob,25,45000\nCarol,35,60000",
                "output": "age: mean=30.0, median=30.0...",
                "description": "Summary stats for a small dataset",
            }
        ],
    },
]

SYSTEM_PROMPTS = {
    "analyze-csv": (
        "You are a data analyst. Analyze the provided CSV data.\n"
        "Report:\n"
        "- Number of rows and columns\n"
        "- Column names and detected types (numeric, text, date, etc.)\n"
        "- Key observations about the data\n"
        "- Any data quality issues (missing values, outliers, etc.)\n\n"
        "Be concise but thorough."
    ),
    "generate-summary-stats": (
        "You are a data analyst. Compute and report summary statistics for the provided CSV data.\n"
        "For numeric columns: count, mean, median, std, min, max.\n"
        "For text columns: count, unique values, most common.\n"
        "Include brief interpretive notes about what the statistics reveal."
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
            parts=[MessagePart(type="text", content="No CSV data provided.")],
        )]

    system_prompt = SYSTEM_PROMPTS.get(skill_id, SYSTEM_PROMPTS["analyze-csv"])
    result = await llm_call(system_prompt, text)
    artifact_name = "summary-stats" if skill_id == "generate-summary-stats" else "csv-analysis"

    return [Artifact(
        name=artifact_name,
        parts=[MessagePart(type="text", content=result)],
        metadata={"skill": skill_id},
    )]


app = create_a2a_app(
    name="Data Analyst",
    description="Analyzes CSV data and computes summary statistics using an LLM.",
    version="1.0.0",
    skills=SKILLS,
    handler_func=handle,
    port=PORT,
    credits_per_task=CREDITS,
)
