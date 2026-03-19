"""KnowledgeBase — ChromaDB-backed vector store for quant knowledge.

Core operations: query, format_for_prompt, ingest_chunks, stats, delete_doc.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import chromadb

from .chunker import Chunk
from .embedder import embed_query, embed_texts, get_client

# Default persistent storage location
DEFAULT_STORE = Path(__file__).resolve().parent.parent / "data" / "kb_store"
COLLECTION_NAME = "knowledge_base"


@dataclass
class SearchResult:
    text: str
    source: str       # filename or URL
    doc_type: str     # book, paper, note, web
    chunk_index: int
    distance: float   # lower = more similar


class KnowledgeBase:
    """Queryable vector store backed by ChromaDB."""

    def __init__(self, persist_dir: str | Path | None = None):
        persist_dir = Path(persist_dir or DEFAULT_STORE)
        persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        self._oai = get_client()

    # ------------------------------------------------------------------
    # Ingest
    # ------------------------------------------------------------------

    def ingest_chunks(
        self,
        chunks: list[Chunk],
        source: str,
        doc_type: str = "note",
    ) -> int:
        """Embed and upsert chunks into ChromaDB. Returns chunk count."""
        if not chunks:
            return 0

        texts = [c.text for c in chunks]
        embeddings = embed_texts(texts, client=self._oai)

        ids = [f"{source}::chunk_{c.index}" for c in chunks]
        metadatas = [
            {"source": source, "doc_type": doc_type, "chunk_index": c.index}
            for c in chunks
        ]

        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        return len(chunks)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def query(
        self,
        question: str,
        top_k: int = 5,
        doc_type: str | None = None,
    ) -> list[SearchResult]:
        """Semantic search. Optional filter by doc_type."""
        q_emb = embed_query(question, client=self._oai)

        where = {"doc_type": doc_type} if doc_type else None
        results = self._collection.query(
            query_embeddings=[q_emb],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        hits: list[SearchResult] = []
        if not results["documents"] or not results["documents"][0]:
            return hits

        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            hits.append(SearchResult(
                text=doc,
                source=meta["source"],
                doc_type=meta["doc_type"],
                chunk_index=meta["chunk_index"],
                distance=dist,
            ))
        return hits

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    @staticmethod
    def format_for_prompt(
        results: list[SearchResult],
        max_tokens: int = 2000,
    ) -> str:
        """Format search results as a text block for LLM prompt injection."""
        if not results:
            return ""

        lines = ["--- Knowledge Base Context ---"]
        approx_tokens = 10  # header overhead
        for r in results:
            citation = f"[{r.source} | {r.doc_type} | chunk {r.chunk_index}]"
            block = f"\n{citation}\n{r.text}\n"
            # Rough token estimate: 1 token ≈ 4 chars
            block_tokens = len(block) // 4
            if approx_tokens + block_tokens > max_tokens:
                break
            lines.append(block)
            approx_tokens += block_tokens

        lines.append("--- End Knowledge Base Context ---")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Admin
    # ------------------------------------------------------------------

    def delete_doc(self, source: str) -> int:
        """Delete all chunks for a given source. Returns deleted count."""
        existing = self._collection.get(
            where={"source": source},
            include=[],
        )
        if not existing["ids"]:
            return 0
        self._collection.delete(ids=existing["ids"])
        return len(existing["ids"])

    def stats(self) -> dict:
        """Return collection stats: total chunks, unique sources, by type."""
        total = self._collection.count()
        if total == 0:
            return {"total_chunks": 0, "sources": [], "by_type": {}}

        all_meta = self._collection.get(include=["metadatas"])
        sources = set()
        by_type: dict[str, int] = {}
        for m in all_meta["metadatas"]:
            sources.add(m["source"])
            t = m["doc_type"]
            by_type[t] = by_type.get(t, 0) + 1

        return {
            "total_chunks": total,
            "sources": sorted(sources),
            "by_type": by_type,
        }
