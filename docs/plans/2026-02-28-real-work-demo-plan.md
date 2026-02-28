# Real-Work Demo — Phase 1 & 2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace heuristic demo agents with LLM-powered ones (via LiteLLM + Ollama), fix bugs, add a seed script, and create a one-command demo launcher.

**Architecture:** Each demo agent's handler calls `litellm.acompletion()` instead of heuristic functions. A shared `llm_call()` helper in `demo_agents/base.py` wraps LiteLLM with error handling and fallback. The seed script uses the REST API to create users, register agents, and add credits. The demo launcher orchestrates everything with proper process management.

**Tech Stack:** LiteLLM, Ollama (local LLM), FastAPI, httpx, SQLite

---

### Task 1: Add LiteLLM Dependency

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add litellm to dependencies**

In `pyproject.toml`, add `"litellm>=1.40.0"` to the `dependencies` list.

**Step 2: Install updated dependencies**

Run: `pip install -e ".[dev]"`
Expected: litellm installs successfully

**Step 3: Verify import works**

Run: `python -c "import litellm; print(litellm.__version__)"`
Expected: Prints version number without error

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "feat: add litellm dependency for LLM-powered demo agents"
```

---

### Task 2: Add LLM Helper to Base Module

**Files:**
- Modify: `demo_agents/base.py`

**Step 1: Add the `llm_call` helper function**

Add this function to `demo_agents/base.py` after the `HandlerFunc` type alias (line ~73):

```python
import os
import logging

logger = logging.getLogger(__name__)

async def llm_call(
    system_prompt: str,
    user_message: str,
    model: str | None = None,
) -> str:
    """Call an LLM via LiteLLM. Falls back to echo if LLM unavailable.

    Reads MODEL env var (default: ollama/llama3.2). Supports any LiteLLM
    provider: ollama/*, gpt-*, claude-*, etc.
    """
    import litellm

    model = model or os.environ.get("MODEL", "ollama/llama3.2")

    try:
        response = await litellm.acompletion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            timeout=60,
        )
        return response.choices[0].message.content
    except Exception as exc:
        logger.warning("LLM call failed (%s), using fallback: %s", model, exc)
        return f"[LLM unavailable — echoing input]\n\n{user_message}"
```

**Step 2: Verify the module still imports**

Run: `python -c "from demo_agents.base import llm_call; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add demo_agents/base.py
git commit -m "feat: add llm_call helper to demo agent base module"
```

---

### Task 3: Upgrade Summarizer Agent to Use LLM

**Files:**
- Modify: `demo_agents/summarizer/agent.py`

**Step 1: Replace the handler with LLM calls**

Replace the entire file content. Keep the SKILLS definition, PORT, CREDITS. Replace the heuristic functions (`summarize`, `extract_key_points`, `_split_sentences`, etc.) and the `handle` function with:

```python
"""Text Summarizer -- demo A2A agent (LLM-powered).

Skills:
  - summarize        Produce a concise summary of text.
  - extract-key-points   Return bullet-point key takeaways.

Port: 8001
Credits: 1 per task
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
```

**Step 2: Verify the module imports**

Run: `python -c "from demo_agents.summarizer.agent import app; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add demo_agents/summarizer/agent.py
git commit -m "feat: upgrade summarizer agent to use LLM via LiteLLM"
```

---

### Task 4: Upgrade Translator Agent to Use LLM

**Files:**
- Modify: `demo_agents/translator/agent.py`

**Step 1: Replace the handler with LLM calls**

Replace the entire file. Keep SKILLS, PORT, CREDITS. Remove all mock translation logic (`LANGUAGE_MAP`, `MOCK_WORDS`, `_detect_target_language`, `_mock_translate`):

```python
"""Universal Translator -- demo A2A agent (LLM-powered).

Skills:
  - translate   Translate text between languages.

Port: 8002
Credits: 2 per task
"""

from __future__ import annotations

from demo_agents.base import Artifact, MessagePart, TaskMessage, create_a2a_app, llm_call

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


app = create_a2a_app(
    name="Universal Translator",
    description="Translates text between languages using an LLM.",
    version="1.0.0",
    skills=SKILLS,
    handler_func=handle,
    port=PORT,
    credits_per_task=CREDITS,
)
```

**Step 2: Verify the module imports**

Run: `python -c "from demo_agents.translator.agent import app; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add demo_agents/translator/agent.py
git commit -m "feat: upgrade translator agent to use LLM via LiteLLM"
```

---

### Task 5: Upgrade Code Reviewer Agent to Use LLM

**Files:**
- Modify: `demo_agents/code_reviewer/agent.py`

**Step 1: Replace the handler with LLM calls**

Replace the entire file. Remove all heuristic static analysis code (`_find_functions`, `_check_imports`, `_check_broad_except`, `_check_magic_numbers`, `review_code`, `suggest_improvements`):

```python
"""Code Reviewer -- demo A2A agent (LLM-powered).

Skills:
  - review-code           Review code for common issues.
  - suggest-improvements  Suggest concrete improvements.

Port: 8003
Credits: 3 per task
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
```

**Step 2: Verify the module imports**

Run: `python -c "from demo_agents.code_reviewer.agent import app; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add demo_agents/code_reviewer/agent.py
git commit -m "feat: upgrade code reviewer agent to use LLM via LiteLLM"
```

---

### Task 6: Upgrade Data Analyst Agent to Use LLM

**Files:**
- Modify: `demo_agents/data_analyst/agent.py`

**Step 1: Replace the handler with LLM calls**

Replace the entire file. Remove all CSV parsing heuristics (`_parse_csv`, `_is_numeric`, `_detect_column_types`, etc.):

```python
"""Data Analyst -- demo A2A agent (LLM-powered).

Skills:
  - analyze-csv             Analyze CSV data structure and content.
  - generate-summary-stats  Compute and interpret summary statistics.

Port: 8004
Credits: 5 per task
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
```

**Step 2: Verify the module imports**

Run: `python -c "from demo_agents.data_analyst.agent import app; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add demo_agents/data_analyst/agent.py
git commit -m "feat: upgrade data analyst agent to use LLM via LiteLLM"
```

---

### Task 7: Upgrade Research Agent to Use LLM + Real Discovery

**Files:**
- Modify: `demo_agents/research_agent/agent.py`

**Step 1: Replace template-based report with LLM call**

Replace the entire file. Keep the A2A delegation logic (`_discover_translator`, `_delegate_translation`) but:
1. Fix `MARKETPLACE_API` URL from port 8000 to 8080
2. Replace `_generate_report()` with an `llm_call()`
3. Read `CREWHUB_API_URL` from env var

```python
"""Research Agent -- demo A2A agent with LLM + real A2A delegation.

Skills:
  - research-topic   Research a topic and compile a structured report.

Port: 8005
Credits: 10 per task

Demonstrates:
  1. LLM-powered report generation
  2. Discovery of other agents via marketplace API
  3. A2A protocol delegation to translator/summarizer
"""

from __future__ import annotations

import os
import re
import uuid

import httpx

from demo_agents.base import Artifact, MessagePart, TaskMessage, create_a2a_app, llm_call

PORT = 8005
CREDITS = 10
MARKETPLACE_API = os.environ.get("CREWHUB_API_URL", "http://localhost:8080") + "/api/v1"

SKILLS = [
    {
        "id": "research-topic",
        "name": "Research Topic",
        "description": (
            "Research a topic and compile a structured report with sections "
            "for overview, key findings, and analysis. If the request mentions "
            "translating the report into another language, the agent will "
            "discover and delegate to a translation agent via the marketplace."
        ),
        "inputModes": ["text"],
        "outputModes": ["text"],
        "examples": [
            {
                "input": "Research the impact of AI on healthcare",
                "output": "# AI in Healthcare\n\n## Overview\n...",
                "description": "Research report on a technology topic",
            },
            {
                "input": "Research renewable energy and translate to Spanish",
                "output": "# Energia Renovable\n...",
                "description": "Research report with translation delegation",
            },
        ],
    },
]

KNOWN_LANGUAGES = {
    "spanish", "french", "german", "italian", "portuguese",
    "japanese", "chinese", "korean", "russian", "arabic",
    "hindi", "dutch", "swedish", "english",
}

LANGUAGE_RE = re.compile(
    r"(?:translate\s+(?:to|into)|in\s+)(\w+)",
    re.IGNORECASE,
)

RESEARCH_SYSTEM_PROMPT = (
    "You are a research analyst. Write a structured research report on the given topic.\n\n"
    "Format your report with these sections:\n"
    "# Research Report: [Topic]\n\n"
    "## Overview\n[2-3 paragraphs]\n\n"
    "## Key Findings\n[Numbered list of 4-5 findings]\n\n"
    "## Analysis\n[2-3 paragraphs with actionable insights]\n\n"
    "## Conclusion\n[1 paragraph summary]\n\n"
    "Be informative, specific, and cite concrete examples where possible."
)


def _detect_translation_request(text: str) -> str | None:
    m = LANGUAGE_RE.search(text)
    if m:
        lang = m.group(1).lower()
        if lang in KNOWN_LANGUAGES:
            return lang
    lower = text.lower()
    if "translate" in lower:
        for lang in KNOWN_LANGUAGES:
            if lang in lower:
                return lang
    return None


def _strip_translation_from_topic(text: str) -> str:
    topic = re.sub(
        r"(?:and\s+)?(?:also\s+)?translate\s+(?:it\s+)?(?:to|into)\s+\w+",
        "", text, flags=re.IGNORECASE,
    ).strip().rstrip(",. ")
    topic = re.sub(r"\s+in\s+\w+\s*$", "", topic, flags=re.IGNORECASE).strip()
    return topic


async def _discover_agent(query: str, name_contains: str) -> str | None:
    """Find an agent endpoint via marketplace discovery API."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{MARKETPLACE_API}/discover/",
                json={"query": query, "mode": "keyword", "limit": 5},
            )
            if resp.status_code == 200:
                for match in resp.json().get("matches", []):
                    agent = match.get("agent", {})
                    if name_contains in agent.get("name", "").lower():
                        return agent.get("endpoint")

            resp = await client.get(f"{MARKETPLACE_API}/agents/")
            if resp.status_code == 200:
                for agent in resp.json().get("agents", []):
                    if name_contains in agent.get("name", "").lower():
                        return agent.get("endpoint")
    except httpx.HTTPError:
        pass
    return None


async def _delegate_a2a(endpoint: str, skill_id: str, text: str) -> str | None:
    """Send a task to another agent via A2A protocol."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "jsonrpc": "2.0",
                "method": "tasks/send",
                "id": str(uuid.uuid4()),
                "params": {
                    "id": str(uuid.uuid4()),
                    "skill_id": skill_id,
                    "messages": [
                        {
                            "role": "user",
                            "parts": [{"type": "text", "content": text}],
                        }
                    ],
                },
            }
            resp = await client.post(f"{endpoint}/", json=payload)
            if resp.status_code == 200:
                result = resp.json().get("result", {})
                artifacts = result.get("artifacts", [])
                if artifacts:
                    parts = artifacts[0].get("parts", [])
                    if parts:
                        return parts[0].get("content")
    except httpx.HTTPError:
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
            parts=[MessagePart(type="text", content="No research topic provided.")],
        )]

    target_language = _detect_translation_request(text)
    topic = _strip_translation_from_topic(text) if target_language else text

    delegation_log: list[str] = []

    # Step 1: Generate research report via LLM
    delegation_log.append(f"Researching topic: {topic}")
    report = await llm_call(RESEARCH_SYSTEM_PROMPT, f"Research topic: {topic}")
    delegation_log.append("Research report generated via LLM.")

    artifacts: list[Artifact] = [
        Artifact(
            name="research-report",
            parts=[MessagePart(type="text", content=report)],
            metadata={"topic": topic, "language": "en"},
        ),
    ]

    # Step 2: If translation requested, discover and delegate via A2A
    if target_language:
        delegation_log.append(f"Translation to {target_language} requested.")

        # Try marketplace discovery
        translator_endpoint = await _discover_agent("translate", "translat")

        if translator_endpoint:
            delegation_log.append(f"Discovered translator at: {translator_endpoint}")
        else:
            # Fallback to well-known port
            translator_endpoint = "http://localhost:8002"
            delegation_log.append("Marketplace discovery unavailable, trying localhost:8002.")

        translated = await _delegate_a2a(
            translator_endpoint, "translate",
            f"Translate to {target_language}: {report}",
        )

        if translated:
            delegation_log.append("Translation completed via A2A delegation.")
            artifacts.append(Artifact(
                name="translated-report",
                parts=[MessagePart(type="text", content=translated)],
                metadata={"topic": topic, "language": target_language, "delegated_to": "Universal Translator"},
            ))
        else:
            delegation_log.append("Translation delegation failed. Returning English report only.")

    artifacts.append(Artifact(
        name="delegation-log",
        parts=[MessagePart(type="text", content="\n".join(delegation_log))],
        metadata={"type": "delegation-log"},
    ))

    return artifacts


app = create_a2a_app(
    name="Research Agent",
    description=(
        "Researches a topic and compiles a structured report using an LLM. "
        "Demonstrates A2A delegation by discovering and using other marketplace agents."
    ),
    version="1.0.0",
    skills=SKILLS,
    handler_func=handle,
    port=PORT,
    credits_per_task=CREDITS,
)
```

**Step 2: Verify the module imports**

Run: `python -c "from demo_agents.research_agent.agent import app; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add demo_agents/research_agent/agent.py
git commit -m "feat: upgrade research agent with LLM + real A2A delegation"
```

---

### Task 8: Fix Marketplace API URL in run_all.py

**Files:**
- Modify: `demo_agents/run_all.py`

**Step 1: Fix the port and add env var support**

In `demo_agents/run_all.py`, change line 164:

```python
# Before:
MARKETPLACE_API = "http://localhost:8000/api/v1"

# After:
MARKETPLACE_API = os.environ.get("CREWHUB_API_URL", "http://localhost:8080") + "/api/v1"
```

Also add `import os` at the top of the file (after the existing imports, around line 15).

**Step 2: Verify the module imports**

Run: `python -c "from demo_agents.run_all import MARKETPLACE_API; print(MARKETPLACE_API)"`
Expected: `http://localhost:8080/api/v1`

**Step 3: Commit**

```bash
git add demo_agents/run_all.py
git commit -m "fix: correct marketplace API port from 8000 to 8080"
```

---

### Task 9: Create Seed Script

**Files:**
- Create: `scripts/seed.py`

**Step 1: Create the seed script**

Create `scripts/seed.py`:

```python
#!/usr/bin/env python3
"""Seed the CrewHub database with demo users, agents, and credits.

Usage:
    python scripts/seed.py                    # seed against http://localhost:8080
    python scripts/seed.py --url http://...   # seed against custom URL

Requires the backend to be running. Uses the REST API (not direct DB access)
so it works in both local and hosted deployments.
"""

from __future__ import annotations

import argparse
import sys

import httpx

BASE_URL = "http://localhost:8080"

DEMO_USER = {
    "email": "demo@crewhub.local",
    "password": "DemoPass123!",
    "name": "Demo User",
}

ADMIN_USER = {
    "email": "admin@crewhub.local",
    "password": "AdminPass123!",
    "name": "Admin",
}

CREDIT_AMOUNT = 1000.0


def _register_user(client: httpx.Client, user: dict) -> dict | None:
    """Register a user, return the JWT token dict or None."""
    resp = client.post(f"{BASE_URL}/api/v1/auth/register", json=user)
    if resp.status_code == 201:
        print(f"  [OK] Registered '{user['email']}'")
    elif resp.status_code == 409:
        print(f"  [SKIP] '{user['email']}' already exists")
    else:
        print(f"  [FAIL] Register '{user['email']}': {resp.status_code} - {resp.text[:200]}")
        return None

    # Login to get token
    resp = client.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": user["email"], "password": user["password"]},
    )
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"  [FAIL] Login '{user['email']}': {resp.status_code} - {resp.text[:200]}")
        return None


def _add_credits(client: httpx.Client, token: str, amount: float) -> bool:
    """Add credits via the purchase endpoint (requires DEBUG=true)."""
    resp = client.post(
        f"{BASE_URL}/api/v1/credits/purchase",
        json={"amount": amount},
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.status_code == 201:
        print(f"  [OK] Added {amount} credits")
        return True
    else:
        print(f"  [WARN] Add credits: {resp.status_code} - {resp.text[:200]}")
        return False


def _promote_admin(client: httpx.Client, admin_email: str) -> bool:
    """Print instructions for promoting user to admin."""
    print(f"  [INFO] To promote '{admin_email}' to admin, run:")
    print(f"         sqlite3 crewhub.db \"UPDATE users SET is_admin=1 WHERE email='{admin_email}';\"")
    return True


def _register_agents(client: httpx.Client, token: str) -> int:
    """Register all 5 demo agents in the marketplace."""
    from demo_agents.run_all import AGENTS

    headers = {"Authorization": f"Bearer {token}"}
    registered = 0

    for agent in AGENTS:
        payload = {
            "name": agent["name"],
            "description": agent["description"],
            "version": agent["version"],
            "endpoint": agent["endpoint"],
            "capabilities": {"streaming": False, "pushNotifications": False},
            "skills": agent["skills"],
            "security_schemes": [],
            "category": agent["category"],
            "tags": agent["tags"],
            "pricing": {"model": "per_task", "credits": agent["credits"]},
        }
        resp = client.post(
            f"{BASE_URL}/api/v1/agents/",
            json=payload,
            headers=headers,
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            print(f"  [OK] Registered '{agent['name']}' (id={data.get('id', 'N/A')})")
            registered += 1
        elif resp.status_code == 409:
            print(f"  [SKIP] '{agent['name']}' already registered")
            registered += 1
        else:
            print(f"  [FAIL] '{agent['name']}': {resp.status_code} - {resp.text[:200]}")

    return registered


def main():
    global BASE_URL

    parser = argparse.ArgumentParser(description="Seed CrewHub with demo data")
    parser.add_argument("--url", default=BASE_URL, help="Backend URL (default: http://localhost:8080)")
    args = parser.parse_args()
    BASE_URL = args.url.rstrip("/")

    print(f"\nSeeding CrewHub at {BASE_URL}\n")
    print("=" * 50)

    client = httpx.Client(timeout=10.0)

    # 1. Register demo user
    print("\n1. Creating demo user...")
    demo_token_data = _register_user(client, DEMO_USER)
    demo_token = demo_token_data.get("access_token") if demo_token_data else None

    # 2. Register admin user
    print("\n2. Creating admin user...")
    admin_token_data = _register_user(client, ADMIN_USER)

    # 3. Add credits to demo user
    if demo_token:
        print(f"\n3. Adding {CREDIT_AMOUNT} credits to demo user...")
        _add_credits(client, demo_token, CREDIT_AMOUNT)
    else:
        print("\n3. Skipping credits (no demo token)")

    # 4. Promote admin
    print("\n4. Admin promotion...")
    _promote_admin(client, ADMIN_USER["email"])

    # 5. Register agents (using demo user's token)
    if demo_token:
        print("\n5. Registering demo agents in marketplace...")
        count = _register_agents(client, demo_token)
        print(f"\n   Registered {count}/5 agents")
    else:
        print("\n5. Skipping agent registration (no token)")

    # Summary
    print("\n" + "=" * 50)
    print("\nSeed complete! Demo credentials:")
    print(f"  Demo user:  {DEMO_USER['email']} / {DEMO_USER['password']}")
    print(f"  Admin user: {ADMIN_USER['email']} / {ADMIN_USER['password']}")
    print(f"  Credits:    {CREDIT_AMOUNT}")
    print()

    client.close()


if __name__ == "__main__":
    main()
```

**Step 2: Verify the script parses**

Run: `python -c "import ast; ast.parse(open('scripts/seed.py').read()); print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add scripts/seed.py
git commit -m "feat: add seed script for demo users, agents, and credits"
```

---

### Task 10: Create Demo Launcher Script

**Files:**
- Create: `scripts/demo.sh`

**Step 1: Create the launcher script**

Create `scripts/demo.sh` — a bash script that:
1. Checks prerequisites (Python, Node, Ollama)
2. Pulls the Ollama model if needed
3. Installs dependencies
4. Creates .env if missing
5. Initializes the database
6. Starts the backend on port 8080
7. Runs the seed script
8. Starts all 5 demo agents
9. Starts the frontend on port 3000
10. Opens the browser
11. Cleans up all processes on Ctrl+C

The script tracks PIDs in an array and uses a trap for cleanup.
It uses `curl` to poll for readiness.
Environment variable `MODEL` controls the LLM (default: `ollama/llama3.2`).

**Step 2: Make it executable**

Run: `chmod +x scripts/demo.sh`

**Step 3: Verify syntax**

Run: `bash -n scripts/demo.sh && echo "OK"`
Expected: `OK`

**Step 4: Commit**

```bash
git add scripts/demo.sh
git commit -m "feat: add one-command demo launcher script"
```

---

### Task 11: Update Agent Descriptions in run_all.py

**Files:**
- Modify: `demo_agents/run_all.py`

**Step 1: Update descriptions to reflect LLM usage**

Update the description strings in the `AGENTS` list to say "using an LLM" instead of "using heuristics" or "frequency-based":

- Summarizer: `"Summarizes text and extracts key points using an LLM."`
- Translator: `"Translates text between languages using an LLM."`
- Code Reviewer: `"Reviews code for quality issues and suggests improvements using an LLM."`
- Data Analyst: `"Analyzes CSV data and computes summary statistics using an LLM."`
- Research Agent: `"Researches topics and compiles reports using an LLM. Demonstrates A2A delegation."`

**Step 2: Verify**

Run: `python -c "from demo_agents.run_all import AGENTS; print([a['description'][:40] for a in AGENTS])"`
Expected: List of updated descriptions

**Step 3: Commit**

```bash
git add demo_agents/run_all.py
git commit -m "docs: update agent descriptions to reflect LLM usage"
```

---

### Task 12: End-to-End Smoke Test

**Step 1: Verify all agent modules import**

Run:
```bash
python -c "
from demo_agents.summarizer.agent import app as s
from demo_agents.translator.agent import app as t
from demo_agents.code_reviewer.agent import app as c
from demo_agents.data_analyst.agent import app as d
from demo_agents.research_agent.agent import app as r
from demo_agents.run_all import AGENTS, MARKETPLACE_API
print(f'All 5 agents import OK')
print(f'Marketplace API: {MARKETPLACE_API}')
print(f'Agents: {len(AGENTS)}')
"
```
Expected: All imports succeed, API URL is `http://localhost:8080/api/v1`

**Step 2: Run existing tests**

Run: `python -m pytest tests/ -v --tb=short 2>&1 | tail -20`
Expected: All existing tests still pass (they don't test demo agents directly)

**Step 3: Verify seed script parses**

Run: `python -c "import ast; ast.parse(open('scripts/seed.py').read()); print('OK')"`
Expected: No syntax errors

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: Phase 1+2 complete — LLM-powered agents + seed + demo launcher"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Add LiteLLM dependency | `pyproject.toml` |
| 2 | Add `llm_call` helper | `demo_agents/base.py` |
| 3 | Upgrade Summarizer | `demo_agents/summarizer/agent.py` |
| 4 | Upgrade Translator | `demo_agents/translator/agent.py` |
| 5 | Upgrade Code Reviewer | `demo_agents/code_reviewer/agent.py` |
| 6 | Upgrade Data Analyst | `demo_agents/data_analyst/agent.py` |
| 7 | Upgrade Research Agent | `demo_agents/research_agent/agent.py` |
| 8 | Fix marketplace URL | `demo_agents/run_all.py` |
| 9 | Create seed script | `scripts/seed.py` |
| 10 | Create demo launcher | `scripts/demo.sh` |
| 11 | Update agent descriptions | `demo_agents/run_all.py` |
| 12 | End-to-end smoke test | (verification only) |
