# Copyright (c) 2026 CrewHub. All rights reserved.
# Proprietary and confidential. See LICENSE for details.
"""Multi-provider LLM router for backend services.

Builds a LiteLLM Router from available API keys with automatic failover.
Used by eval_service, content_filter, and any future backend LLM calls.

Provider priority (all free tier):
  1. Groq — fastest inference, 30 RPM
  2. Cerebras — fast, Llama 70B
  3. SambaNova — Llama 70B/405B
  4. Gemini Flash — highest quota (1M tokens/day)
"""

import logging
import os

logger = logging.getLogger(__name__)

_router = None
_initialized = False

# (env_var, model_string, rpm_limit)
_PROVIDERS = [
    ("GROQ_API_KEY", "groq/llama-3.3-70b-versatile", 30),
    ("CEREBRAS_API_KEY", "cerebras/llama-3.3-70b", 30),
    ("SAMBANOVA_API_KEY", "sambanova/Meta-Llama-3.3-70B-Instruct", 20),
    ("GEMINI_API_KEY", "gemini/gemini-2.0-flash", 15),
]


def get_router():
    """Get or build the shared LLM Router. Returns None if no keys available."""
    global _router, _initialized
    if _initialized:
        return _router

    _initialized = True
    try:
        from litellm import Router
    except ImportError:
        logger.warning("litellm not installed, LLM router unavailable")
        return None

    model_list = []
    for env_var, model_str, rpm in _PROVIDERS:
        key = os.environ.get(env_var)
        if key:
            model_list.append({
                "model_name": "backend-llm",
                "litellm_params": {
                    "model": model_str,
                    "api_key": key,
                    "rpm": rpm,
                },
            })

    if not model_list:
        logger.info("No LLM API keys found, router disabled")
        return None

    providers = [m["litellm_params"]["model"] for m in model_list]
    logger.info("Backend LLM Router: %d providers — %s", len(model_list), providers)

    _router = Router(
        model_list=model_list,
        num_retries=2,
        timeout=30,
        allowed_fails=3,
        cooldown_time=60,
        retry_after=1,
    )
    return _router


async def completion(messages: list[dict], **kwargs) -> str:
    """Call the LLM router and return the text response.

    Falls back to direct litellm.acompletion if router unavailable.
    Raises on failure (caller handles errors).
    """
    router = get_router()
    if router:
        response = await router.acompletion(model="backend-llm", messages=messages, **kwargs)
        return response.choices[0].message.content

    # Fallback: try direct call with first available key
    from litellm import acompletion
    for env_var, model_str, _ in _PROVIDERS:
        if os.environ.get(env_var):
            response = await acompletion(model=model_str, messages=messages, **kwargs)
            return response.choices[0].message.content

    raise RuntimeError("No LLM providers configured")
