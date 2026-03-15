# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Load personality definitions from downloaded markdown files.

Each personality .md file has YAML frontmatter (name, description) and a
markdown body that becomes the LLM system prompt.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

MAX_PROMPT_CHARS = int(os.environ.get("MAX_PROMPT_CHARS", "6000"))

PERSONALITIES_DIR = Path(__file__).resolve().parent / "personalities"

CLOSING_INSTRUCTION = (
    "\n\nRespond helpfully and concisely based on your expertise above. "
    "Focus on actionable, practical advice."
)


@dataclass
class PersonalityDef:
    skill_id: str
    name: str
    description: str
    system_prompt: str


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown. Returns (metadata, body)."""
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    meta = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return meta, parts[2].strip()


def _truncate_prompt(body: str, max_chars: int) -> str:
    """Truncate prompt to max_chars, preserving section structure.

    Strips large code blocks first, then truncates at a section boundary.
    """
    # Strip fenced code blocks (they consume tokens but add little personality)
    body = re.sub(r"```[\s\S]*?```", "[code example omitted]", body)

    if len(body) <= max_chars:
        return body

    # Truncate at the last section header before the limit
    truncated = body[:max_chars]
    last_header = truncated.rfind("\n## ")
    if last_header > max_chars // 2:
        truncated = truncated[:last_header]

    return truncated.rstrip()


def _derive_skill_id(filename: str, division: str) -> str:
    """Derive skill_id from filename by stripping division prefix + .md."""
    stem = filename.removesuffix(".md")
    prefix = division + "-"
    if stem.startswith(prefix):
        return stem[len(prefix):]
    return stem


def load_division(division: str) -> dict[str, PersonalityDef]:
    """Load all personality definitions for a division.

    Returns {skill_id: PersonalityDef} mapping.
    """
    div_dir = PERSONALITIES_DIR / division
    if not div_dir.is_dir():
        raise FileNotFoundError(f"Division directory not found: {div_dir}")

    personalities: dict[str, PersonalityDef] = {}
    for md_file in sorted(div_dir.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(content)

        skill_id = _derive_skill_id(md_file.name, division)
        name = meta.get("name", skill_id.replace("-", " ").title())
        description = meta.get("description", "")

        system_prompt = _truncate_prompt(body, MAX_PROMPT_CHARS) + CLOSING_INSTRUCTION

        personalities[skill_id] = PersonalityDef(
            skill_id=skill_id,
            name=name,
            description=description,
            system_prompt=system_prompt,
        )

    return personalities
