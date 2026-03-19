"""
Tests for core.llm.client — Unified Async LLM Client
=====================================================
Tests the new async client that replaces subprocess-based ask_model.py.
"""
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.llm.client import (
    MODELS,
    LLMClient,
    LLMResult,
    call,
    call_with_meta,
)


class TestModelCatalog:
    """Test the model catalog is correctly configured."""

    def test_all_models_have_required_fields(self):
        for key, cfg in MODELS.items():
            assert cfg.key == key, f"{key}: key mismatch"
            assert cfg.provider in ("anthropic", "openai", "deepseek", "minimax",
                                     "zhipu", "dashscope", "ollama", "mlx"), f"{key}: invalid provider"
            assert cfg.model, f"{key}: missing model name"
            assert cfg.max_tokens > 0, f"{key}: invalid max_tokens"
            assert cfg.timeout_s > 0, f"{key}: invalid timeout"

    def test_fallback_chains_are_valid(self):
        for key, cfg in MODELS.items():
            if cfg.fallback:
                assert cfg.fallback in MODELS, \
                    f"{key}: fallback '{cfg.fallback}' not in catalog"

    def test_minimax_exists(self):
        assert "minimax" in MODELS
        assert MODELS["minimax"].model == "minimax-m2.7"
        assert MODELS["minimax"].cost_per_m_output == 1.20

    def test_glm5_exists(self):
        assert "glm5" in MODELS
        assert MODELS["glm5"].provider == "zhipu"

    def test_mlx_models_exist(self):
        assert "mlx-flagship" in MODELS
        assert "mlx-reasoning" in MODELS
        assert "mlx-fast" in MODELS

    def test_no_circular_fallbacks(self):
        """Ensure no infinite fallback loops."""
        for key, cfg in MODELS.items():
            visited = {key}
            current = cfg.fallback
            depth = 0
            while current and depth < 20:
                assert current not in visited, \
                    f"Circular fallback chain detected: {key} → ... → {current}"
                visited.add(current)
                current = MODELS[current].fallback if current in MODELS else ""
                depth += 1


class TestLLMClient:
    """Test the async LLM client."""

    @pytest.fixture
    def client(self):
        return LLMClient(usage_log="/tmp/test_llm_usage.jsonl")

    def test_unknown_model_returns_error(self):
        client = LLMClient(usage_log="/tmp/test_llm_usage.jsonl")
        result = client.call("nonexistent_model", "test")
        assert result.error
        assert "Unknown model key" in result.error

    @pytest.mark.asyncio
    async def test_anthropic_dispatch(self, client):
        """Test Anthropic API call format."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Hello from Claude"}],
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, '_get_http') as mock_http:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_http.return_value = mock_client

            os.environ["ANTHROPIC_API_KEY"] = "test-key"
            result = await client.generate("opus", "Hello")

            assert result.text == "Hello from Claude"
            assert result.provider == "anthropic"
            assert result.input_tokens == 10
            assert result.output_tokens == 5
            assert result.cost_usd > 0

    @pytest.mark.asyncio
    async def test_openai_compat_dispatch(self, client):
        """Test OpenAI-compatible API call format."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello from GPT"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, '_get_http') as mock_http:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_http.return_value = mock_client

            os.environ["OPENAI_API_KEY"] = "test-key"
            result = await client.generate("gpt", "Hello")

            assert result.text == "Hello from GPT"
            assert result.input_tokens == 10

    @pytest.mark.asyncio
    async def test_fallback_on_error(self, client):
        """Test fallback chain when primary fails."""
        call_count = 0

        async def mock_dispatch(cfg, prompt, system, max_tokens, temperature):
            nonlocal call_count
            call_count += 1
            if cfg.key == "opus":
                raise ConnectionError("API down")
            return LLMResult(
                text="Fallback response",
                model=cfg.model,
                provider=cfg.provider,
                input_tokens=5,
                output_tokens=3,
            )

        with patch.object(client, '_dispatch', side_effect=mock_dispatch):
            result = await client.generate("opus", "test")
            assert result.text == "Fallback response"
            assert result.fallback_used

    def test_usage_tracking(self, client):
        result = LLMResult(
            text="test", model="gpt-4.1", provider="openai",
            input_tokens=100, output_tokens=50, cost_usd=0.005,
        )
        client.usage.record(result)
        assert client.usage.total_requests == 1
        assert client.usage.total_cost_usd == 0.005
        assert "gpt-4.1" in client.usage.per_model


class TestBackwardCompat:
    """Test backward-compatible convenience functions."""

    def test_call_returns_string(self):
        """call() should return a plain string like old orchestrator/llm.call()."""
        with patch('core.llm.client.get_client') as mock:
            mock_client = MagicMock()
            mock_client.call.return_value = LLMResult(
                text="response text", model="test", provider="test"
            )
            mock.return_value = mock_client

            result = call("opus", "test prompt")
            assert isinstance(result, str)
            assert result == "response text"

    def test_call_with_meta_returns_tuple(self):
        """call_with_meta() should return (text, meta) like old orchestrator/llm.call_with_meta()."""
        with patch('core.llm.client.get_client') as mock:
            mock_client = MagicMock()
            mock_client.call.return_value = LLMResult(
                text="response text", model="gpt-4.1", provider="openai",
                input_tokens=100, output_tokens=50, latency_ms=1234.5, cost_usd=0.005,
            )
            mock.return_value = mock_client

            text, meta = call_with_meta("gpt", "test prompt")
            assert text == "response text"
            assert "gpt-4.1" in meta
            assert "100" in meta  # input tokens


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
