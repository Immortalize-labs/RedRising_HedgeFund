"""Knowledge Base — RAG pipeline for all agents.

Usage:
    from knowledge_base import get_kb

    kb = get_kb()
    chunks = kb.query("kelly criterion position sizing", top_k=5)
    context = kb.format_for_prompt(chunks)
"""

from __future__ import annotations

from .kb import KnowledgeBase

_instance: KnowledgeBase | None = None


def get_kb(persist_dir: str | None = None) -> KnowledgeBase:
    """Return singleton KnowledgeBase instance."""
    global _instance
    if _instance is None:
        _instance = KnowledgeBase(persist_dir=persist_dir)
    return _instance


__all__ = ["get_kb", "KnowledgeBase"]
