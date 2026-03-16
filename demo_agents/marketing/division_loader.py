# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Load marketing division definitions from markdown files.

Each division .md file has YAML frontmatter (name, description, skills) and a
markdown body that becomes the combined LLM system prompt.

Skills are listed in the frontmatter as a YAML list with id, name, and
description fields. The body contains the merged system prompt from
multiple marketingskills SKILL.md sources.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

MAX_PROMPT_CHARS = int(os.environ.get("MAX_PROMPT_CHARS", "6000"))

DIVISIONS_DIR = Path(__file__).resolve().parent / "divisions"

CLOSING_INSTRUCTION = (
    "\n\nRespond helpfully and concisely based on your expertise above. "
    "Focus on actionable, practical advice. Provide specific frameworks, "
    "checklists, and examples the user can apply immediately."
)

ATTRIBUTION = (
    "\n\n---\n*Powered by marketingskills by Corey Haines (MIT licensed)*"
)


@dataclass
class SkillDef:
    skill_id: str
    name: str
    description: str


@dataclass
class DivisionDef:
    name: str
    description: str
    skills: list[SkillDef] = field(default_factory=list)
    system_prompt: str = ""


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown. Returns (metadata, body)."""
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    meta: dict = {}
    current_key = None
    current_list: list | None = None

    for line in parts[1].strip().splitlines():
        stripped = line.strip()
        if stripped.startswith("- ") and current_list is not None:
            # Parse list item — could be a dict-like entry
            item_str = stripped[2:].strip()
            if ":" in item_str and not item_str.startswith('"'):
                # Simple key: value on one line within a list item
                item_dict = {}
                # Re-parse the whole list item block
                key, _, val = item_str.partition(":")
                item_dict[key.strip()] = val.strip().strip('"')
                current_list.append(item_dict)
            else:
                current_list.append(item_str)
        elif ":" in line and not line.startswith(" "):
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if value:
                meta[key] = value
                current_key = key
                current_list = None
            else:
                # Start of a list or nested structure
                current_key = key
                current_list = []
                meta[key] = current_list
        elif current_list is not None and line.startswith("    "):
            # Continuation of a list item (indented key: value)
            stripped = line.strip()
            if ":" in stripped and current_list:
                key, _, val = stripped.partition(":")
                last_item = current_list[-1]
                if isinstance(last_item, dict):
                    last_item[key.strip()] = val.strip().strip('"')

    return meta, parts[2].strip()


def _truncate_prompt(body: str, max_chars: int) -> str:
    """Truncate prompt to max_chars, preserving section structure."""
    # Strip fenced code blocks (they consume tokens but add little value)
    body = re.sub(r"```[\s\S]*?```", "[code example omitted]", body)

    if len(body) <= max_chars:
        return body

    # Truncate at the last section header before the limit
    truncated = body[:max_chars]
    last_header = truncated.rfind("\n## ")
    if last_header > max_chars // 2:
        truncated = truncated[:last_header]

    return truncated.rstrip()


def load_division(division: str) -> DivisionDef:
    """Load a division definition from its markdown file.

    Returns a DivisionDef with name, description, skills list, and system_prompt.
    """
    div_file = DIVISIONS_DIR / f"{division}.md"
    if not div_file.is_file():
        raise FileNotFoundError(f"Division file not found: {div_file}")

    content = div_file.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(content)

    name = meta.get("name", division.replace("-", " ").title())
    description = meta.get("description", f"Marketing {division} agent")

    # Parse skills from frontmatter
    skills = []
    raw_skills = meta.get("skills", [])
    if isinstance(raw_skills, list):
        for item in raw_skills:
            if isinstance(item, dict):
                skills.append(SkillDef(
                    skill_id=item.get("id", ""),
                    name=item.get("name", ""),
                    description=item.get("description", ""),
                ))

    system_prompt = _truncate_prompt(body, MAX_PROMPT_CHARS) + CLOSING_INSTRUCTION

    return DivisionDef(
        name=name,
        description=description,
        skills=skills,
        system_prompt=system_prompt,
    )
