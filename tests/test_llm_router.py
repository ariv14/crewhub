"""Tests for multi-provider LLM Router (Phase 0B)."""

import os
from unittest.mock import AsyncMock, patch, MagicMock

import pytest


class TestBuildRouter:
    """Test Router construction from available env vars."""

    def test_no_keys_returns_none(self):
        """Router returns None when no API keys are set."""
        with patch.dict(os.environ, {}, clear=True):
            from demo_agents.base import _build_router
            router = _build_router()
            assert router is None

    def test_single_key_builds_router(self):
        """Router builds with a single provider key."""
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}, clear=True):
            from demo_agents.base import _build_router
            router = _build_router()
            assert router is not None

    def test_multiple_keys_builds_router(self):
        """Router includes all providers with keys."""
        env = {
            "GROQ_API_KEY": "groq-key",
            "GEMINI_API_KEY": "gemini-key",
            "CEREBRAS_API_KEY": "cerebras-key",
        }
        with patch.dict(os.environ, env, clear=True):
            from demo_agents.base import _build_router
            router = _build_router()
            assert router is not None
            # Should have 3 model deployments
            assert len(router.model_list) == 3


class TestLlmCall:
    """Test llm_call function with Router integration."""

    @pytest.mark.asyncio
    async def test_ollama_bypasses_router(self):
        """Ollama models should bypass the Router entirely."""
        from demo_agents.base import llm_call

        with patch("demo_agents.base._ollama_call", new_callable=AsyncMock) as mock:
            mock.return_value = "ollama response"
            result = await llm_call("system", "hello", model="ollama/llama3.2")
            assert result == "ollama response"
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_router_used_when_available(self):
        """When Router is initialized, it should be used for non-Ollama calls."""
        import demo_agents.base as base_mod

        mock_router = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="router response"))]
        mock_router.acompletion = AsyncMock(return_value=mock_response)

        old_router = base_mod._router
        base_mod._router = mock_router
        try:
            result = await base_mod.llm_call("system", "hello")
            assert result == "router response"
            mock_router.acompletion.assert_called_once()
        finally:
            base_mod._router = old_router

    @pytest.mark.asyncio
    async def test_fallback_to_direct_call(self):
        """When Router fails, falls back to direct litellm call."""
        import demo_agents.base as base_mod

        mock_router = MagicMock()
        mock_router.acompletion = AsyncMock(side_effect=Exception("Router failed"))

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="direct response"))]

        old_router = base_mod._router
        base_mod._router = mock_router
        try:
            with patch.dict(os.environ, {"MODEL": "groq/llama-3.3-70b-versatile"}):
                with patch("litellm.acompletion", new_callable=AsyncMock, return_value=mock_response):
                    result = await base_mod.llm_call("system", "hello")
                    assert result == "direct response"
        finally:
            base_mod._router = old_router

    @pytest.mark.asyncio
    async def test_echo_fallback_when_all_fail(self):
        """When everything fails, returns echo string."""
        import demo_agents.base as base_mod

        mock_router = MagicMock()
        mock_router.acompletion = AsyncMock(side_effect=Exception("Router failed"))

        old_router = base_mod._router
        base_mod._router = mock_router
        try:
            with patch.dict(os.environ, {"MODEL": "groq/llama-3.3-70b-versatile"}):
                with patch("litellm.acompletion", new_callable=AsyncMock, side_effect=Exception("Direct failed")):
                    result = await base_mod.llm_call("system", "hello world")
                    assert "[LLM unavailable" in result
                    assert "hello world" in result
        finally:
            base_mod._router = old_router


class TestBackendRouter:
    """Test the backend LLM router module."""

    def test_no_keys_returns_none(self):
        """Backend router returns None with no keys."""
        with patch.dict(os.environ, {}, clear=True):
            import src.core.llm_router as mod
            mod._initialized = False
            mod._router = None
            router = mod.get_router()
            assert router is None

    def test_builds_with_keys(self):
        """Backend router builds when keys available."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test"}, clear=True):
            import src.core.llm_router as mod
            mod._initialized = False
            mod._router = None
            router = mod.get_router()
            assert router is not None

    @pytest.mark.asyncio
    async def test_completion_uses_router(self):
        """completion() function routes through the Router."""
        import src.core.llm_router as mod

        mock_router = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="backend response"))]
        mock_router.acompletion = AsyncMock(return_value=mock_response)

        mod._initialized = True
        old_router = mod._router
        mod._router = mock_router
        try:
            result = await mod.completion(messages=[{"role": "user", "content": "hi"}])
            assert result == "backend response"
        finally:
            mod._router = old_router
            mod._initialized = False
