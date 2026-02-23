"""Text Summarizer -- demo A2A agent.

Skills:
  - summarize        Extract the most important sentences from a text.
  - extract-key-points   Return bullet-point key takeaways.

Port: 8001
Credits: 1 per task

Run standalone:
    uvicorn demo_agents.summarizer.agent:app --port 8001
"""

from __future__ import annotations

import re
from collections import Counter

from demo_agents.base import Artifact, MessagePart, TaskMessage, create_a2a_app

PORT = 8001
CREDITS = 1

SKILLS = [
    {
        "id": "summarize",
        "name": "Summarize Text",
        "description": "Produce a concise extractive summary of the input text by selecting the most representative sentences.",
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

# ---------------------------------------------------------------------------
# Stop-words used for sentence scoring
# ---------------------------------------------------------------------------

STOP_WORDS = set(
    "a an the and or but in on at to for of is it this that was were be been "
    "being have has had do does did will would shall should may might can could "
    "i me my we our you your he him his she her they them their its with from by "
    "as not no so if then else than too very just about also back been before "
    "between both each few more most other some such only over same through "
    "during into after above below up down out off again further once here there "
    "when where why how all any many much which what who whom".split()
)

# Indicators that a sentence carries a key point
KEY_POINT_INDICATORS = re.compile(
    r"^\s*[-*]\s|"
    r"\b(important|key|critical|must|should|note|conclusion|result|finding|"
    r"recommend|significant|essential|action|decision|target|goal|deadline)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _split_sentences(text: str) -> list[str]:
    """Naive sentence splitter."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if len(s.strip()) > 10]


def _word_frequencies(text: str) -> Counter:
    words = re.findall(r"[a-z']+", text.lower())
    return Counter(w for w in words if w not in STOP_WORDS)


def _score_sentences(sentences: list[str], freq: Counter) -> list[tuple[float, int, str]]:
    scored: list[tuple[float, int, str]] = []
    for idx, sent in enumerate(sentences):
        words = re.findall(r"[a-z']+", sent.lower())
        if not words:
            continue
        score = sum(freq.get(w, 0) for w in words) / len(words)
        scored.append((score, idx, sent))
    return scored


def summarize(text: str, ratio: float = 0.3) -> str:
    sentences = _split_sentences(text)
    if len(sentences) <= 3:
        return text

    freq = _word_frequencies(text)
    scored = _score_sentences(sentences, freq)
    n = max(2, int(len(sentences) * ratio))
    top = sorted(scored, key=lambda x: x[0], reverse=True)[:n]
    # Return in original order
    top_ordered = sorted(top, key=lambda x: x[1])
    return " ".join(s for _, _, s in top_ordered)


def extract_key_points(text: str) -> str:
    sentences = _split_sentences(text)
    if not sentences:
        return "- No key points found."

    freq = _word_frequencies(text)
    scored = _score_sentences(sentences, freq)

    # First pass: sentences matching key-point indicators
    key = [s for s in sentences if KEY_POINT_INDICATORS.search(s)]

    # Second pass: if not enough, take highest scored sentences
    if len(key) < 3:
        top = sorted(scored, key=lambda x: x[0], reverse=True)
        for score, idx, sent in top:
            if sent not in key:
                key.append(sent)
            if len(key) >= 5:
                break

    bullets = "\n".join(f"- {s}" for s in key[:7])
    return bullets


# ---------------------------------------------------------------------------
# A2A handler
# ---------------------------------------------------------------------------

async def handle(skill_id: str, messages: list[TaskMessage]) -> list[Artifact]:
    # Collect all text content from user messages
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

    if skill_id == "extract-key-points":
        result = extract_key_points(text)
        artifact_name = "key-points"
    else:
        result = summarize(text)
        artifact_name = "summary"

    return [Artifact(
        name=artifact_name,
        parts=[MessagePart(type="text", content=result)],
        metadata={"skill": skill_id, "input_length": len(text), "output_length": len(result)},
    )]


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = create_a2a_app(
    name="Text Summarizer",
    description="Extracts concise summaries and key points from text using frequency-based extractive methods.",
    version="1.0.0",
    skills=SKILLS,
    handler_func=handle,
    port=PORT,
    credits_per_task=CREDITS,
)
