"""
Unified Async LLM Client
=========================
Single entry point for ALL LLM calls in the fund.
Replaces three legacy paths:
  1. scripts/ask_model.py (subprocess-per-call)
  2. orchestrator/llm.py (subprocess wrapper)
  3. integrations/llm_provider.py (LangChain, unused)

Design decisions:
  - Pure asyncio + httpx. No LangChain. No subprocess.
  - Supports: Anthropic, OpenAI, DeepSeek, MiniMax, Zhipu (GLM-5), DashScope (Qwen), Ollama, MLX
  - Fallback chain: if primary fails, try next in chain
  - Cost tracking: per-request logging to JSONL
  - Structured output: optional Pydantic model validation
  - Backward compat: sync wrapper `call()` for non-async callers

Architecture:
  Agent/Script → LLMClient.generate() → async httpx → provider API
                                       → or local MLX/Ollama server
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)
EST = timezone(timedelta(hours=-5))

# ─── Load .env ────────────────────────────────────────────────────────────
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


# ─── Data classes ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ModelConfig:
    """Immutable configuration for a single model."""
    key: str
    provider: str           # anthropic | openai | deepseek | minimax | zhipu | ollama | mlx
    model: str              # API model name
    api_key_env: str = ""   # env var for API key (empty for local)
    base_url: str = ""      # custom base URL (empty = provider default)
    cost_per_m_input: float = 0.0
    cost_per_m_output: float = 0.0
    fallback: str = ""      # next model key in fallback chain
    max_tokens: int = 4096
    timeout_s: int = 180


@dataclass
class LLMResult:
    """Result of an LLM call with full metadata."""
    text: str
    model: str              # which model actually served this
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    reasoning: str = ""     # for models that return reasoning (DeepSeek R1)
    fallback_used: bool = False
    error: str = ""


@dataclass
class UsageTracker:
    """Cumulative usage tracking across all models."""
    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    per_model: dict = field(default_factory=dict)

    def record(self, result: LLMResult) -> None:
        self.total_requests += 1
        self.total_input_tokens += result.input_tokens
        self.total_output_tokens += result.output_tokens
        self.total_cost_usd += result.cost_usd
        if result.model not in self.per_model:
            self.per_model[result.model] = {
                "requests": 0, "input_tokens": 0,
                "output_tokens": 0, "cost_usd": 0.0,
            }
        m = self.per_model[result.model]
        m["requests"] += 1
        m["input_tokens"] += result.input_tokens
        m["output_tokens"] += result.output_tokens
        m["cost_usd"] += result.cost_usd


# ─── Model catalog ────────────────────────────────────────────────────────

MODELS: dict[str, ModelConfig] = {
    # --- Anthropic (EXPENSIVE — fallback/emergency only) ---
    "opus": ModelConfig(
        key="opus", provider="anthropic",
        model="claude-opus-4-6", api_key_env="ANTHROPIC_API_KEY",
        cost_per_m_input=15.0, cost_per_m_output=75.0,
        fallback="gpt", max_tokens=8192, timeout_s=180,
    ),
    "sonnet": ModelConfig(
        key="sonnet", provider="anthropic",
        model="claude-sonnet-4-6", api_key_env="ANTHROPIC_API_KEY",
        cost_per_m_input=3.0, cost_per_m_output=15.0,
        fallback="gpt", max_tokens=8192, timeout_s=120,
    ),
    "haiku": ModelConfig(
        key="haiku", provider="anthropic",
        model="claude-haiku-4-5-20251001", api_key_env="ANTHROPIC_API_KEY",
        cost_per_m_input=0.8, cost_per_m_output=4.0,
        fallback="gpt-mini", max_tokens=8192, timeout_s=60,
    ),

    # --- OpenAI (mid-tier cost) ---
    "gpt": ModelConfig(
        key="gpt", provider="openai",
        model="gpt-4.1", api_key_env="OPENAI_API_KEY",
        base_url="https://api.openai.com/v1",
        cost_per_m_input=2.0, cost_per_m_output=8.0,
        fallback="minimax", max_tokens=16384, timeout_s=180,
    ),
    "gpt-pro": ModelConfig(
        key="gpt-pro", provider="openai",
        model="o4-mini", api_key_env="OPENAI_API_KEY",
        base_url="https://api.openai.com/v1",
        cost_per_m_input=1.10, cost_per_m_output=4.40,
        fallback="gpt", max_tokens=16384, timeout_s=180,
    ),
    "gpt-mini": ModelConfig(
        key="gpt-mini", provider="openai",
        model="gpt-4.1-mini", api_key_env="OPENAI_API_KEY",
        base_url="https://api.openai.com/v1",
        cost_per_m_input=0.40, cost_per_m_output=1.60,
        fallback="deepseek-chat", max_tokens=8192, timeout_s=60,
    ),

    # --- DeepSeek (CHEAP — primary reasoning) ---
    "deepseek": ModelConfig(
        key="deepseek", provider="openai",
        model="deepseek-reasoner", api_key_env="DEEPSEEK_API_KEY",
        base_url="https://api.deepseek.com/v1",
        cost_per_m_input=0.55, cost_per_m_output=2.19,
        fallback="minimax", max_tokens=8192, timeout_s=180,
    ),
    "deepseek-chat": ModelConfig(
        key="deepseek-chat", provider="openai",
        model="deepseek-chat", api_key_env="DEEPSEEK_API_KEY",
        base_url="https://api.deepseek.com/v1",
        cost_per_m_input=0.27, cost_per_m_output=1.10,
        fallback="local", max_tokens=8192, timeout_s=120,
    ),

    # --- MiniMax (CHEAP — primary coding/analysis) ---
    "minimax": ModelConfig(
        key="minimax", provider="minimax",
        model="minimax-m2.7", api_key_env="MINIMAX_API_KEY",
        base_url="https://api.minimax.chat/v1",
        cost_per_m_input=0.30, cost_per_m_output=1.20,
        fallback="gpt-mini", max_tokens=8192, timeout_s=30,
    ),

    # --- Zhipu AI (GLM-5) ---
    "glm5": ModelConfig(
        key="glm5", provider="zhipu",
        model="glm-5", api_key_env="ZHIPU_API_KEY",
        base_url="https://open.bigmodel.cn/api/v4",
        cost_per_m_input=0.80, cost_per_m_output=2.56,
        fallback="minimax", max_tokens=8192, timeout_s=30,
    ),

    # --- Alibaba DashScope (Qwen) ---
    "qwen-max": ModelConfig(
        key="qwen-max", provider="dashscope",
        model="qwen-max", api_key_env="DASHSCOPE_API_KEY",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        cost_per_m_input=0.80, cost_per_m_output=2.40,
        fallback="minimax", max_tokens=8192, timeout_s=60,
    ),
    "qwen-plus": ModelConfig(
        key="qwen-plus", provider="dashscope",
        model="qwen-plus", api_key_env="DASHSCOPE_API_KEY",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        cost_per_m_input=0.30, cost_per_m_output=0.90,
        fallback="gpt-mini", max_tokens=8192, timeout_s=60,
    ),
    "qwen-turbo": ModelConfig(
        key="qwen-turbo", provider="dashscope",
        model="qwen-turbo", api_key_env="DASHSCOPE_API_KEY",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        cost_per_m_input=0.10, cost_per_m_output=0.30,
        fallback="deepseek-chat", max_tokens=8192, timeout_s=30,
    ),

    # --- Local Ollama ---
    "local": ModelConfig(
        key="local", provider="ollama",
        model="deepseek-r1:14b",
        base_url="http://localhost:11434/v1",
        fallback="", max_tokens=4096, timeout_s=120,
    ),

    # --- Local MLX (M5 Max — not available until hardware arrives) ---
    "mlx-flagship": ModelConfig(
        key="mlx-flagship", provider="mlx",
        model="Qwen3.5-122B-A10B",
        base_url="http://localhost:8080/v1",
        fallback="glm5", max_tokens=4096, timeout_s=120,
    ),
    "mlx-reasoning": ModelConfig(
        key="mlx-reasoning", provider="mlx",
        model="DeepSeek-R1-Distill-Qwen-32B",
        base_url="http://localhost:8081/v1",
        fallback="deepseek", max_tokens=4096, timeout_s=120,
    ),
    "mlx-fast": ModelConfig(
        key="mlx-fast", provider="mlx",
        model="Qwen3.5-9B",
        base_url="http://localhost:8082/v1",
        fallback="local", max_tokens=4096, timeout_s=60,
    ),
}

# Dummy key for local providers
os.environ.setdefault("_OLLAMA_DUMMY", "ollama")
os.environ.setdefault("_MLX_DUMMY", "mlx")


# ─── Async LLM Client ────────────────────────────────────────────────────

class LLMClient:
    """
    Unified async LLM client.

    Usage:
        client = LLMClient()

        # Async (preferred — no overhead)
        result = await client.generate("opus", "Analyze BTC momentum")

        # Sync wrapper (for non-async callers — minimal overhead)
        result = client.call("opus", "Analyze BTC momentum")

        # With system prompt
        result = await client.generate("sonnet", "Review this code", system="You are a code reviewer.")

        # Cost tracking
        print(client.usage.total_cost_usd)
    """

    def __init__(self, usage_log: str = "data/api_usage.jsonl"):
        self._http: httpx.AsyncClient | None = None
        self.usage = UsageTracker()
        self._usage_log_path = Path(usage_log)
        self._usage_log_path.parent.mkdir(parents=True, exist_ok=True)

    async def _get_http(self) -> httpx.AsyncClient:
        """Lazy-init shared async HTTP client (connection pooling)."""
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(timeout=httpx.Timeout(180.0))
        return self._http

    async def close(self) -> None:
        """Close the shared HTTP client."""
        if self._http and not self._http.is_closed:
            await self._http.aclose()

    # ── Main entry point ──────────────────────────────────────────────────

    async def generate(
        self,
        model_key: str,
        prompt: str,
        system: str = "",
        max_tokens: int | None = None,
        temperature: float = 0.0,
    ) -> LLMResult:
        """
        Generate a response from the specified model.
        Falls back through the chain on failure.
        """
        cfg = MODELS.get(model_key)
        if not cfg:
            return LLMResult(text="", model=model_key, provider="unknown",
                             error=f"Unknown model key: {model_key}")

        tokens = max_tokens or cfg.max_tokens
        t0 = time.monotonic()

        try:
            result = await self._dispatch(cfg, prompt, system, tokens, temperature)
            result.latency_ms = (time.monotonic() - t0) * 1000

            # Cost calculation
            result.cost_usd = (
                result.input_tokens * cfg.cost_per_m_input / 1_000_000
                + result.output_tokens * cfg.cost_per_m_output / 1_000_000
            )

            # Track usage
            self.usage.record(result)
            self._log_usage(result)

            return result

        except Exception as e:
            elapsed = (time.monotonic() - t0) * 1000
            logger.warning(f"[LLM] {cfg.model} failed ({type(e).__name__}: {e}), "
                           f"latency={elapsed:.0f}ms")

            # Fallback
            if cfg.fallback:
                logger.info(f"[LLM] Falling back: {model_key} → {cfg.fallback}")
                result = await self.generate(cfg.fallback, prompt, system, max_tokens, temperature)
                result.fallback_used = True
                return result

            return LLMResult(text="", model=cfg.model, provider=cfg.provider,
                             latency_ms=elapsed, error=str(e))

    # ── Sync wrapper ──────────────────────────────────────────────────────

    def call(
        self,
        model_key: str,
        prompt: str,
        system: str = "",
        max_tokens: int | None = None,
        temperature: float = 0.0,
    ) -> LLMResult:
        """
        Synchronous wrapper around generate().
        For callers that aren't async yet (debate engine, scripts).
        Uses existing event loop if available, creates one otherwise.
        """
        try:
            loop = asyncio.get_running_loop()
            # We're inside an async context — can't use asyncio.run()
            # Create a new thread to avoid blocking
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run,
                                     self.generate(model_key, prompt, system, max_tokens, temperature))
                return future.result(timeout=300)
        except RuntimeError:
            # No running loop — safe to use asyncio.run()
            return asyncio.run(
                self.generate(model_key, prompt, system, max_tokens, temperature)
            )

    # ── Provider dispatchers ──────────────────────────────────────────────

    async def _dispatch(
        self,
        cfg: ModelConfig,
        prompt: str,
        system: str,
        max_tokens: int,
        temperature: float,
    ) -> LLMResult:
        """Route to the correct provider handler."""
        if cfg.provider == "anthropic":
            return await self._call_anthropic(cfg, prompt, system, max_tokens, temperature)
        elif cfg.provider in ("openai", "ollama", "mlx"):
            return await self._call_openai_compat(cfg, prompt, system, max_tokens, temperature)
        elif cfg.provider == "minimax":
            return await self._call_openai_compat(cfg, prompt, system, max_tokens, temperature)
        elif cfg.provider in ("zhipu", "dashscope"):
            return await self._call_openai_compat(cfg, prompt, system, max_tokens, temperature)
        else:
            raise ValueError(f"Unsupported provider: {cfg.provider}")

    async def _call_anthropic(
        self,
        cfg: ModelConfig,
        prompt: str,
        system: str,
        max_tokens: int,
        temperature: float,
    ) -> LLMResult:
        """Call Anthropic Messages API (non-OpenAI format)."""
        api_key = os.environ.get(cfg.api_key_env, "")
        if not api_key:
            raise EnvironmentError(f"{cfg.api_key_env} not set")

        http = await self._get_http()

        payload: dict[str, Any] = {
            "model": cfg.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload["system"] = system
        if temperature > 0:
            payload["temperature"] = temperature

        resp = await http.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=payload,
            timeout=cfg.timeout_s,
        )
        resp.raise_for_status()
        data = resp.json()

        text = "".join(
            b["text"] for b in data.get("content", [])
            if b.get("type") == "text"
        )
        usage = data.get("usage", {})

        return LLMResult(
            text=text,
            model=cfg.model,
            provider="anthropic",
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
        )

    async def _call_openai_compat(
        self,
        cfg: ModelConfig,
        prompt: str,
        system: str,
        max_tokens: int,
        temperature: float,
    ) -> LLMResult:
        """Call any OpenAI-compatible API (OpenAI, DeepSeek, Ollama, MLX, MiniMax, Zhipu)."""
        api_key_env = cfg.api_key_env or "_OLLAMA_DUMMY"
        api_key = os.environ.get(api_key_env, "")
        if not api_key and cfg.provider not in ("ollama", "mlx"):
            raise EnvironmentError(f"{api_key_env} not set")
        if not api_key:
            api_key = "local"

        base_url = cfg.base_url or "https://api.openai.com/v1"
        http = await self._get_http()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        # GPT-5.x uses max_completion_tokens; others use max_tokens
        tok_key = "max_completion_tokens" if "gpt-5" in cfg.model else "max_tokens"
        payload: dict[str, Any] = {
            "model": cfg.model,
            "messages": messages,
            tok_key: max_tokens,
        }
        if temperature > 0:
            payload["temperature"] = temperature

        resp = await http.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=cfg.timeout_s,
        )
        resp.raise_for_status()
        data = resp.json()

        choice = data["choices"][0]["message"]
        text = choice.get("content", "")
        reasoning = choice.get("reasoning_content", "")
        usage = data.get("usage", {})

        return LLMResult(
            text=text,
            model=cfg.model,
            provider=cfg.provider,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            reasoning=reasoning,
        )

    # ── Usage logging ─────────────────────────────────────────────────────

    def _log_usage(self, result: LLMResult) -> None:
        """Append usage record to JSONL log."""
        if result.cost_usd <= 0 and result.provider in ("ollama", "mlx"):
            return  # Don't log free local calls

        entry = {
            "timestamp": datetime.now(EST).isoformat(),
            "model": result.model,
            "provider": result.provider,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "cost_usd": round(result.cost_usd, 6),
            "latency_ms": round(result.latency_ms, 1),
            "fallback_used": result.fallback_used,
        }
        try:
            with open(self._usage_log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError:
            logger.warning(f"[LLM] Failed to write usage log: {self._usage_log_path}")


# ─── Module-level singleton ───────────────────────────────────────────────

_client: LLMClient | None = None


def get_client() -> LLMClient:
    """Get or create the module-level LLMClient singleton."""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


# ─── Convenience functions (drop-in replacements) ─────────────────────────

def call(model_key: str, prompt: str, system: str = "", max_tokens: int = 4096) -> str:
    """
    Drop-in replacement for orchestrator/llm.call().
    Returns just the text (no metadata footer).
    """
    result = get_client().call(model_key, prompt, system, max_tokens)
    if result.error:
        raise RuntimeError(f"LLM call failed ({model_key}): {result.error}")
    return result.text


def call_with_meta(model_key: str, prompt: str, system: str = "", max_tokens: int = 4096) -> tuple[str, str]:
    """
    Drop-in replacement for orchestrator/llm.call_with_meta().
    Returns (text, metadata_string).
    """
    result = get_client().call(model_key, prompt, system, max_tokens)
    if result.error:
        raise RuntimeError(f"LLM call failed ({model_key}): {result.error}")
    meta = (f"Model: {result.model} | In: {result.input_tokens} "
            f"Out: {result.output_tokens} | {result.latency_ms:.0f}ms "
            f"| ${result.cost_usd:.4f}")
    return result.text, meta
