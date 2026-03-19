"""
LLM Provider — DEPRECATED SHIM
================================
This module now delegates to core.llm.client (unified async client).
Kept for backward compatibility only. All new code should import from core.llm.client.

Old: subprocess.run() → ask_model.py (forks a new process per call, ~200-500ms overhead)
New: async httpx → direct API call (zero fork overhead, connection pooling)
"""
from __future__ import annotations

from core.llm.client import call, call_with_meta  # noqa: F401
