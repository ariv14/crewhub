"""Universal Translator -- demo A2A agent.

Skills:
  - translate   Translate text between languages.

Port: 8002
Credits: 2 per task

In a real deployment this would call a translation API (DeepL, Google, etc.).
For this demo it wraps the input text with language markers so the pipeline
can be tested end-to-end without external dependencies.

Run standalone:
    uvicorn demo_agents.translator.agent:app --port 8002
"""

from __future__ import annotations

import re

from demo_agents.base import Artifact, MessagePart, TaskMessage, create_a2a_app

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
                "output": "[ES] Hola, como estas?",
                "description": "English to Spanish greeting",
            },
            {
                "input": "Translate to French: The weather is nice today.",
                "output": "[FR] Le temps est beau aujourd'hui.",
                "description": "English to French sentence",
            },
        ],
    },
]

# ---------------------------------------------------------------------------
# Supported language codes (for the mock)
# ---------------------------------------------------------------------------

LANGUAGE_MAP: dict[str, str] = {
    "spanish": "ES",
    "french": "FR",
    "german": "DE",
    "italian": "IT",
    "portuguese": "PT",
    "japanese": "JA",
    "chinese": "ZH",
    "korean": "KO",
    "russian": "RU",
    "arabic": "AR",
    "hindi": "HI",
    "dutch": "NL",
    "swedish": "SV",
    "english": "EN",
}

# Simple mock word replacements per language to make output feel slightly different
MOCK_WORDS: dict[str, dict[str, str]] = {
    "ES": {"hello": "hola", "goodbye": "adios", "thank you": "gracias", "yes": "si", "no": "no", "please": "por favor", "the": "el", "is": "es", "are": "son", "good": "bueno", "bad": "malo", "world": "mundo"},
    "FR": {"hello": "bonjour", "goodbye": "au revoir", "thank you": "merci", "yes": "oui", "no": "non", "please": "s'il vous plait", "the": "le", "is": "est", "are": "sont", "good": "bon", "bad": "mauvais", "world": "monde"},
    "DE": {"hello": "hallo", "goodbye": "auf wiedersehen", "thank you": "danke", "yes": "ja", "no": "nein", "please": "bitte", "the": "der", "is": "ist", "are": "sind", "good": "gut", "bad": "schlecht", "world": "welt"},
    "IT": {"hello": "ciao", "goodbye": "arrivederci", "thank you": "grazie", "yes": "si", "no": "no", "please": "per favore", "the": "il", "is": "e", "are": "sono", "good": "buono", "bad": "cattivo", "world": "mondo"},
    "PT": {"hello": "ola", "goodbye": "adeus", "thank you": "obrigado", "yes": "sim", "no": "nao", "please": "por favor", "the": "o", "is": "e", "are": "sao", "good": "bom", "bad": "mau", "world": "mundo"},
    "JA": {"hello": "konnichiwa", "goodbye": "sayonara", "thank you": "arigatou", "yes": "hai", "no": "iie", "please": "kudasai", "world": "sekai"},
    "ZH": {"hello": "ni hao", "goodbye": "zaijian", "thank you": "xie xie", "yes": "shi", "no": "bu shi", "world": "shijie"},
    "KO": {"hello": "annyeonghaseyo", "goodbye": "annyeong", "thank you": "gamsahamnida", "yes": "ne", "no": "aniyo", "world": "segye"},
}

# Regex to detect "translate to <language>:" prefix
TARGET_LANG_RE = re.compile(
    r"(?:translate\s+(?:(?:this\s+)?(?:text\s+)?)?(?:in)?to\s+)(\w+)\s*[:\-]?\s*",
    re.IGNORECASE,
)


def _detect_target_language(text: str) -> tuple[str, str]:
    """Return (language_code, remaining_text)."""
    m = TARGET_LANG_RE.search(text)
    if m:
        lang_name = m.group(1).lower()
        code = LANGUAGE_MAP.get(lang_name, lang_name.upper()[:2])
        remaining = text[:m.start()] + text[m.end():]
        return code, remaining.strip()
    return "ES", text  # default to Spanish


def _mock_translate(text: str, lang_code: str) -> str:
    """Apply simple word-level mock substitutions."""
    result = text
    word_map = MOCK_WORDS.get(lang_code, {})
    for eng, translated in word_map.items():
        result = re.sub(rf"\b{re.escape(eng)}\b", translated, result, flags=re.IGNORECASE)
    return f"[{lang_code}] {result}"


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
            parts=[MessagePart(type="text", content="No text provided for translation.")],
        )]

    lang_code, body = _detect_target_language(text)
    translated = _mock_translate(body, lang_code)

    return [Artifact(
        name="translation",
        parts=[MessagePart(type="text", content=translated)],
        metadata={
            "source_language": "EN",
            "target_language": lang_code,
            "char_count": len(body),
        },
    )]


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = create_a2a_app(
    name="Universal Translator",
    description="Translates text between languages. Specify the target language in natural language (e.g., 'Translate to French: ...').",
    version="1.0.0",
    skills=SKILLS,
    handler_func=handle,
    port=PORT,
    credits_per_task=CREDITS,
)
