"""Data Analyst -- demo A2A agent.

Skills:
  - analyze-csv             Parse CSV data and describe its structure.
  - generate-summary-stats  Compute per-column summary statistics.

Port: 8004
Credits: 5 per task

Parses CSV from text input using only the Python standard library so that
the demo has zero heavyweight dependencies.

Run standalone:
    uvicorn demo_agents.data_analyst.agent:app --port 8004
"""

from __future__ import annotations

import csv
import io
import json
import math
from collections import defaultdict

from demo_agents.base import Artifact, MessagePart, TaskMessage, create_a2a_app

PORT = 8004
CREDITS = 5

SKILLS = [
    {
        "id": "analyze-csv",
        "name": "Analyze CSV Data",
        "description": "Parse CSV text and return a structural overview: column names, types, row count, and sample rows.",
        "inputModes": ["text"],
        "outputModes": ["text", "data"],
        "examples": [
            {
                "input": "name,age,salary\nAlice,30,50000\nBob,25,45000",
                "output": "Columns: name (text), age (numeric), salary (numeric)\nRows: 2",
                "description": "Analyze a small CSV",
            }
        ],
    },
    {
        "id": "generate-summary-stats",
        "name": "Generate Summary Statistics",
        "description": "Compute mean, median, standard deviation, min, and max for each numeric column in a CSV dataset.",
        "inputModes": ["text"],
        "outputModes": ["text", "data"],
        "examples": [
            {
                "input": "name,age,salary\nAlice,30,50000\nBob,25,45000\nCarol,35,60000",
                "output": "age: mean=30.0, median=30.0, std=5.0, min=25, max=35\nsalary: mean=51666.7, median=50000.0, std=7637.6, min=45000, max=60000",
                "description": "Summary stats for a small dataset",
            }
        ],
    },
]


# ---------------------------------------------------------------------------
# CSV parsing helpers
# ---------------------------------------------------------------------------

def _parse_csv(text: str) -> tuple[list[str], list[list[str]]]:
    """Return (headers, rows) from CSV text."""
    reader = csv.reader(io.StringIO(text.strip()))
    rows = list(reader)
    if not rows:
        return [], []
    headers = [h.strip() for h in rows[0]]
    data = rows[1:]
    return headers, data


def _is_numeric(value: str) -> bool:
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def _detect_column_types(headers: list[str], rows: list[list[str]]) -> dict[str, str]:
    """Classify each column as 'numeric' or 'text'."""
    types: dict[str, str] = {}
    for col_idx, header in enumerate(headers):
        values = [r[col_idx].strip() for r in rows if col_idx < len(r) and r[col_idx].strip()]
        if values and all(_is_numeric(v) for v in values):
            types[header] = "numeric"
        else:
            types[header] = "text"
    return types


def _numeric_values(col_idx: int, rows: list[list[str]]) -> list[float]:
    vals: list[float] = []
    for r in rows:
        if col_idx < len(r) and r[col_idx].strip():
            try:
                vals.append(float(r[col_idx]))
            except ValueError:
                pass
    return vals


def _median(values: list[float]) -> float:
    s = sorted(values)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    if n % 2 == 0:
        return (s[mid - 1] + s[mid]) / 2
    return s[mid]


def _std(values: list[float], mean: float) -> float:
    if len(values) < 2:
        return 0.0
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


# ---------------------------------------------------------------------------
# Skill logic
# ---------------------------------------------------------------------------

def analyze_csv(text: str) -> tuple[dict, str]:
    """Return (structured_data, formatted_text)."""
    headers, rows = _parse_csv(text)
    if not headers:
        return {"error": "No valid CSV data found."}, "Error: No valid CSV data found."

    col_types = _detect_column_types(headers, rows)
    sample = rows[:5]

    data = {
        "columns": [{"name": h, "type": col_types.get(h, "text")} for h in headers],
        "row_count": len(rows),
        "column_count": len(headers),
        "sample_rows": [dict(zip(headers, r)) for r in sample],
    }

    lines = [
        f"Dataset overview:",
        f"  Rows: {len(rows)}",
        f"  Columns: {len(headers)}",
        "",
        "Column details:",
    ]
    for h in headers:
        lines.append(f"  - {h} ({col_types.get(h, 'text')})")

    if sample:
        lines.append("")
        lines.append(f"First {len(sample)} row(s):")
        for i, row in enumerate(sample):
            vals = ", ".join(f"{h}={row[j] if j < len(row) else 'N/A'}" for j, h in enumerate(headers))
            lines.append(f"  [{i + 1}] {vals}")

    return data, "\n".join(lines)


def generate_summary_stats(text: str) -> tuple[dict, str]:
    """Return (structured_stats, formatted_text)."""
    headers, rows = _parse_csv(text)
    if not headers:
        return {"error": "No valid CSV data found."}, "Error: No valid CSV data found."

    col_types = _detect_column_types(headers, rows)
    stats: dict[str, dict] = {}
    lines: list[str] = ["Summary statistics (numeric columns):", ""]

    for col_idx, header in enumerate(headers):
        if col_types.get(header) != "numeric":
            continue

        values = _numeric_values(col_idx, rows)
        if not values:
            continue

        mean = sum(values) / len(values)
        med = _median(values)
        std = _std(values, mean)
        mn = min(values)
        mx = max(values)

        col_stats = {
            "count": len(values),
            "mean": round(mean, 4),
            "median": round(med, 4),
            "std": round(std, 4),
            "min": round(mn, 4),
            "max": round(mx, 4),
        }
        stats[header] = col_stats

        lines.append(f"  {header}:")
        lines.append(f"    count  = {col_stats['count']}")
        lines.append(f"    mean   = {col_stats['mean']}")
        lines.append(f"    median = {col_stats['median']}")
        lines.append(f"    std    = {col_stats['std']}")
        lines.append(f"    min    = {col_stats['min']}")
        lines.append(f"    max    = {col_stats['max']}")
        lines.append("")

    # Text column summaries
    text_cols = [h for h in headers if col_types.get(h) == "text"]
    if text_cols:
        lines.append("Text columns:")
        for col_idx, header in enumerate(headers):
            if col_types.get(header) != "text":
                continue
            values = [r[col_idx].strip() for r in rows if col_idx < len(r) and r[col_idx].strip()]
            unique = len(set(values))
            stats[header] = {
                "type": "text",
                "count": len(values),
                "unique": unique,
                "sample": values[:3],
            }
            lines.append(f"  {header}: {len(values)} values, {unique} unique")

    if not stats:
        return {"message": "No numeric columns found."}, "No numeric columns found in the dataset."

    return stats, "\n".join(lines)


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
            parts=[MessagePart(type="text", content="No CSV data provided.")],
        )]

    if skill_id == "generate-summary-stats":
        data, formatted = generate_summary_stats(text)
        artifact_name = "summary-stats"
    else:
        data, formatted = analyze_csv(text)
        artifact_name = "csv-analysis"

    return [
        Artifact(
            name=f"{artifact_name}-text",
            parts=[MessagePart(type="text", content=formatted)],
            metadata={"skill": skill_id},
        ),
        Artifact(
            name=f"{artifact_name}-data",
            parts=[MessagePart(type="data", data=data, mime_type="application/json")],
            metadata={"skill": skill_id},
        ),
    ]


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = create_a2a_app(
    name="Data Analyst",
    description="Parses CSV data and computes summary statistics including mean, median, standard deviation, min, and max for numeric columns.",
    version="1.0.0",
    skills=SKILLS,
    handler_func=handle,
    port=PORT,
    credits_per_task=CREDITS,
)
