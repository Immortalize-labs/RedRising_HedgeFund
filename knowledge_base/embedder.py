"""Embedding wrapper — Ollama local (primary) with OpenAI fallback.

Primary: nomic-embed-text via Ollama (768-dim, free, local)
Fallback: text-embedding-3-small via OpenAI ($0.02/M tokens)
"""

from __future__ import annotations

import logging
import os

import requests

logger = logging.getLogger(__name__)

OLLAMA_MODEL = "nomic-embed-text"
OLLAMA_URL = "http://localhost:11434/api/embed"

OPENAI_MODEL = "text-embedding-3-small"
OPENAI_BATCH_SIZE = 512


def _ollama_embed(texts: list[str]) -> list[list[float]]:
    """Embed via local Ollama. Raises on failure."""
    embeddings = []
    for t in texts:
        r = requests.post(OLLAMA_URL, json={"model": OLLAMA_MODEL, "input": t}, timeout=30)
        r.raise_for_status()
        data = r.json()
        embeddings.append(data["embeddings"][0])
    return embeddings


def _openai_embed(texts: list[str]) -> list[list[float]]:
    """Embed via OpenAI API. Requires OPENAI_API_KEY."""
    from openai import OpenAI

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), OPENAI_BATCH_SIZE):
        batch = texts[i : i + OPENAI_BATCH_SIZE]
        resp = client.embeddings.create(model=OPENAI_MODEL, input=batch)
        sorted_data = sorted(resp.data, key=lambda d: d.index)
        all_embeddings.extend([d.embedding for d in sorted_data])
    return all_embeddings


def embed_texts(texts: list[str], client=None) -> list[list[float]]:
    """Embed texts. Tries Ollama first, falls back to OpenAI.

    Returns list of float vectors, one per input text.
    """
    try:
        return _ollama_embed(texts)
    except Exception as e:
        logger.debug("Ollama embedding failed (%s), trying OpenAI fallback", e)

    try:
        return _openai_embed(texts)
    except Exception as e:
        raise RuntimeError(
            f"Both Ollama and OpenAI embedding failed. "
            f"Ensure Ollama is running (ollama serve) or set OPENAI_API_KEY. "
            f"Last error: {e}"
        ) from e


def embed_query(query: str, client=None) -> list[float]:
    """Embed a single query string."""
    return embed_texts([query])[0]


def get_client():
    """Kept for backward compatibility. Returns None (Ollama needs no client)."""
    return None
