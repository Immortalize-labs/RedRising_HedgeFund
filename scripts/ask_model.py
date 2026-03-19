#!/usr/bin/env python3
"""
Multi-model caller for Claude Code agents.
6 providers, automatic fallback chain.

Usage:
    python scripts/ask_model.py -m opus -p "Deep strategy analysis"
    python scripts/ask_model.py -m sonnet -p "Code review"
    python scripts/ask_model.py -m deepseek -p "Analyze BTC momentum"
    python scripts/ask_model.py -m gpt -p "Risk assessment"
    python scripts/ask_model.py -m local -p "Quick sanity check"
    echo "long prompt" | python scripts/ask_model.py -m gpt --stdin
"""
import argparse
import os
import sys
from pathlib import Path

# Load .env from project root
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

MODEL_CONFIG = {
    # --- Anthropic (native — different API format) ---
    "opus": {
        "provider": "anthropic",
        "model": "claude-opus-4-6",
        "api_key_env": "ANTHROPIC_API_KEY",
        "fallback": "gpt-pro",
    },
    "sonnet": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-6",
        "api_key_env": "ANTHROPIC_API_KEY",
        "fallback": "gpt",
    },
    "haiku": {
        "provider": "anthropic",
        "model": "claude-haiku-4-5-20251001",
        "api_key_env": "ANTHROPIC_API_KEY",
        "fallback": "gpt-mini",
    },
    # --- DeepSeek (blocked at work → falls to GPT) ---
    "deepseek": {
        "provider": "openai",
        "base_url": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "model": "deepseek-reasoner",
        "fallback": "gpt",
    },
    "deepseek-chat": {
        "provider": "openai",
        "base_url": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "model": "deepseek-chat",
        "fallback": "gpt",
    },
    # --- GPT 5.4 ---
    "gpt": {
        "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "model": "gpt-5.4",
        "fallback": "local",
    },
    "gpt-pro": {
        "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "model": "gpt-5.4-pro",
        "fallback": "gpt",
    },
    "gpt-mini": {
        "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "model": "gpt-5.4",
        "fallback": "local",
    },
    # --- Local Ollama (air-gapped fallback) ---
    "local": {
        "provider": "openai",
        "base_url": "http://localhost:11434/v1",
        "api_key_env": "_OLLAMA_DUMMY",
        "model": "deepseek-r1:14b",
    },
}

os.environ.setdefault("_OLLAMA_DUMMY", "ollama")


def _ensure_httpx():
    try:
        import httpx
        return httpx
    except ImportError:
        os.system(f"{sys.executable} -m pip install httpx -q")
        import httpx
        return httpx


def _call_anthropic(cfg, messages, max_tokens):
    httpx = _ensure_httpx()
    api_key = os.environ.get(cfg["api_key_env"], "")

    # Convert from system/user format to Anthropic format
    system_text = ""
    user_messages = []
    for m in messages:
        if m["role"] == "system":
            system_text = m["content"]
        else:
            user_messages.append(m)

    payload = {
        "model": cfg["model"],
        "max_tokens": max_tokens,
        "messages": user_messages,
    }
    if system_text:
        payload["system"] = system_text

    resp = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json=payload,
        timeout=180,
    )
    resp.raise_for_status()
    data = resp.json()

    content = "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text")
    usage = data.get("usage", {})
    meta = f"\n---\nModel: {cfg['model']} | In: {usage.get('input_tokens', '?')} Out: {usage.get('output_tokens', '?')}"
    return f"{content}{meta}"


def _call_openai(cfg, messages, max_tokens):
    httpx = _ensure_httpx()
    api_key = os.environ.get(cfg["api_key_env"], "")

    tok_key = "max_completion_tokens" if "gpt-5" in cfg["model"] else "max_tokens"
    payload = {"model": cfg["model"], "messages": messages, tok_key: max_tokens}

    resp = httpx.post(
        f"{cfg['base_url']}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=180,
    )
    resp.raise_for_status()
    data = resp.json()

    content = data["choices"][0]["message"].get("content", "")
    reasoning = data["choices"][0]["message"].get("reasoning_content", "")
    usage = data.get("usage", {})
    meta = f"\n---\nModel: {cfg['model']} | In: {usage.get('prompt_tokens', '?')} Out: {usage.get('completion_tokens', '?')}"

    if reasoning:
        return f"<reasoning>\n{reasoning}\n</reasoning>\n\n{content}{meta}"
    return f"{content}{meta}"


def call_model(model_key: str, prompt: str, system: str = "", max_tokens: int = 4096) -> str:
    cfg = MODEL_CONFIG.get(model_key)
    if not cfg:
        return f"Error: Unknown model '{model_key}'. Available: {', '.join(MODEL_CONFIG)}"

    api_key = os.environ.get(cfg["api_key_env"], "")
    if not api_key:
        return f"Error: {cfg['api_key_env']} not set"

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        if cfg["provider"] == "anthropic":
            return _call_anthropic(cfg, messages, max_tokens)
        else:
            return _call_openai(cfg, messages, max_tokens)
    except Exception as e:
        fallback = cfg.get("fallback")
        if fallback:
            print(f"[warn] {cfg['model']} failed ({type(e).__name__}), → {fallback}", file=sys.stderr)
            return call_model(fallback, prompt, system, max_tokens)
        return f"Error: {model_key} failed, no fallback: {e}"


def main():
    parser = argparse.ArgumentParser(description="Call external LLM models")
    parser.add_argument("--model", "-m", required=True, choices=list(MODEL_CONFIG))
    parser.add_argument("--prompt", "-p", default="")
    parser.add_argument("--system", "-s", default="")
    parser.add_argument("--stdin", action="store_true")
    parser.add_argument("--max-tokens", type=int, default=4096)
    args = parser.parse_args()

    prompt = sys.stdin.read() if args.stdin else args.prompt
    if not prompt:
        print("Error: No prompt provided", file=sys.stderr)
        sys.exit(1)

    print(call_model(args.model, prompt, args.system, args.max_tokens))


if __name__ == "__main__":
    main()
