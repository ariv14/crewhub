"""CrewHub Guard — content filtering and cost limits."""

import re

from langflow.custom import CustomComponent


class CrewHubGuardComponent(CustomComponent):
    display_name = "CrewHub Guard"
    description = "Filter content for safety, block restricted words, and redact PII."
    documentation = "https://crewhubai.com/docs"
    icon = "shield"

    def build_config(self):
        return {
            "text": {
                "display_name": "Text",
                "info": "Text to filter",
                "required": True,
                "input_types": ["str"],
            },
            "blocked_words": {
                "display_name": "Blocked Words",
                "info": "Comma-separated words to block",
                "value": "",
            },
            "max_output_length": {
                "display_name": "Max Output Length",
                "info": "Maximum characters in output (0 = unlimited)",
                "value": 0,
                "advanced": True,
            },
            "block_pii": {
                "display_name": "Block PII Patterns",
                "info": "Redact emails, phone numbers, SSN-like patterns",
                "value": False,
                "advanced": True,
            },
        }

    def build(
        self,
        text: str,
        blocked_words: str = "",
        max_output_length: int = 0,
        block_pii: bool = False,
    ) -> str:
        result = text

        # Check blocked words
        if blocked_words:
            words = [w.strip().lower() for w in blocked_words.split(",") if w.strip()]
            text_lower = result.lower()
            for word in words:
                if word in text_lower:
                    return f"[BLOCKED] Content contains restricted word: '{word}'"

        # Redact PII patterns
        if block_pii:
            pii_patterns = [
                (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "[EMAIL REDACTED]"),
                (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', "[PHONE REDACTED]"),
                (r'\b\d{3}[-]?\d{2}[-]?\d{4}\b', "[SSN REDACTED]"),
            ]
            for pattern, replacement in pii_patterns:
                result = re.sub(pattern, replacement, result)

        # Enforce max length
        if max_output_length > 0 and len(result) > max_output_length:
            result = result[:max_output_length] + "... [truncated]"

        return result
