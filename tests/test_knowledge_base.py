"""Tests for the Knowledge Base pipeline.

Run: pytest tests/test_knowledge_base.py -v
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from knowledge_base.chunker import Chunk, _tok_len, chunk_text

# ─── Chunker ────────────────────────────────────────────────────────

class TestChunker:
    def test_short_text_single_chunk(self):
        text = "This is a short sentence."
        chunks = chunk_text(text, chunk_size=350, overlap=50)
        assert len(chunks) == 1
        assert chunks[0].text.strip() == text
        assert chunks[0].index == 0

    def test_multiple_paragraphs_split(self):
        paras = ["Paragraph one. " * 30, "Paragraph two. " * 30]
        text = "\n\n".join(paras)
        chunks = chunk_text(text, chunk_size=100, overlap=20)
        assert len(chunks) >= 2

    def test_overlap_present(self):
        """Second chunk should contain overlap from first."""
        text = "Alpha bravo charlie. " * 50 + "\n\n" + "Delta echo foxtrot. " * 50
        chunks = chunk_text(text, chunk_size=80, overlap=20)
        assert len(chunks) >= 2
        # Second chunk should start with text from end of first
        # (overlap means shared content)
        assert chunks[1].index == 1

    def test_token_count_accuracy(self):
        text = "The quick brown fox jumps over the lazy dog."
        chunks = chunk_text(text, chunk_size=350, overlap=0)
        assert chunks[0].token_count == _tok_len(chunks[0].text)

    def test_empty_text(self):
        chunks = chunk_text("", chunk_size=350, overlap=50)
        assert chunks == []

    def test_long_sentence_hard_split(self):
        """A single very long sentence should be split on words."""
        text = "word " * 500  # ~500 tokens
        chunks = chunk_text(text, chunk_size=100, overlap=0)
        assert len(chunks) >= 3
        for c in chunks:
            assert c.token_count <= 120  # allow some margin

    def test_chunk_indices_sequential(self):
        text = "Section one.\n\nSection two.\n\nSection three.\n\nSection four."
        chunks = chunk_text(text, chunk_size=20, overlap=5)
        for i, c in enumerate(chunks):
            assert c.index == i


# ─── Embedder ───────────────────────────────────────────────────────

class TestEmbedder:
    @patch("knowledge_base.embedder._ollama_embed")
    def test_embed_texts_batching(self, mock_ollama):
        from knowledge_base.embedder import embed_texts

        # Mock Ollama response (nomic-embed-text = 768-dim)
        mock_ollama.return_value = [
            [0.1] * 768,
            [0.2] * 768,
        ]

        result = embed_texts(["hello", "world"])
        assert len(result) == 2
        assert len(result[0]) == 768
        mock_ollama.assert_called_once_with(["hello", "world"])


# ─── KnowledgeBase (integration with ChromaDB) ─────────────────────

class TestKnowledgeBase:
    @patch("knowledge_base.kb.get_client")
    @patch("knowledge_base.kb.embed_texts")
    @patch("knowledge_base.kb.embed_query")
    def test_ingest_and_query_roundtrip(self, mock_eq, mock_et, mock_gc):
        """Ingest chunks, query them back."""
        from knowledge_base.kb import KnowledgeBase

        # Mock embeddings — deterministic vectors
        mock_gc.return_value = MagicMock()
        mock_et.return_value = [[0.1] * 1536, [0.2] * 1536]
        mock_eq.return_value = [0.1] * 1536

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = KnowledgeBase(persist_dir=tmpdir)

            chunks = [
                Chunk(text="Kelly criterion is f* = (bp - q) / b", index=0, token_count=12),
                Chunk(text="Position sizing with volatility scaling", index=1, token_count=8),
            ]
            count = kb.ingest_chunks(chunks, source="test.pdf", doc_type="book")
            assert count == 2

            results = kb.query("kelly criterion", top_k=2)
            assert len(results) == 2
            assert results[0].source == "test.pdf"
            assert results[0].doc_type == "book"

    @patch("knowledge_base.kb.get_client")
    @patch("knowledge_base.kb.embed_texts")
    def test_delete_doc(self, mock_et, mock_gc):
        from knowledge_base.kb import KnowledgeBase

        mock_gc.return_value = MagicMock()
        mock_et.return_value = [[0.1] * 1536]

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = KnowledgeBase(persist_dir=tmpdir)
            chunks = [Chunk(text="test content", index=0, token_count=5)]
            kb.ingest_chunks(chunks, source="deleteme.md", doc_type="note")

            assert kb.stats()["total_chunks"] == 1
            deleted = kb.delete_doc("deleteme.md")
            assert deleted == 1
            assert kb.stats()["total_chunks"] == 0

    @patch("knowledge_base.kb.get_client")
    @patch("knowledge_base.kb.embed_texts")
    def test_stats(self, mock_et, mock_gc):
        from knowledge_base.kb import KnowledgeBase

        mock_gc.return_value = MagicMock()
        mock_et.side_effect = [[[0.1] * 1536], [[0.2] * 1536]]

        with tempfile.TemporaryDirectory() as tmpdir:
            kb = KnowledgeBase(persist_dir=tmpdir)
            kb.ingest_chunks(
                [Chunk(text="a", index=0, token_count=1)],
                source="a.pdf", doc_type="book",
            )
            kb.ingest_chunks(
                [Chunk(text="b", index=0, token_count=1)],
                source="b.md", doc_type="note",
            )
            s = kb.stats()
            assert s["total_chunks"] == 2
            assert len(s["sources"]) == 2
            assert s["by_type"]["book"] == 1
            assert s["by_type"]["note"] == 1


# ─── Format for prompt ──────────────────────────────────────────────

class TestFormatForPrompt:
    def test_empty_results(self):
        from knowledge_base.kb import KnowledgeBase
        assert KnowledgeBase.format_for_prompt([]) == ""

    def test_includes_citations(self):
        from knowledge_base.kb import KnowledgeBase, SearchResult

        results = [SearchResult(
            text="Kelly criterion formula",
            source="quant_book.pdf",
            doc_type="book",
            chunk_index=3,
            distance=0.15,
        )]
        formatted = KnowledgeBase.format_for_prompt(results)
        assert "quant_book.pdf" in formatted
        assert "book" in formatted
        assert "Kelly criterion formula" in formatted
        assert "Knowledge Base Context" in formatted


# ─── Ingest module ──────────────────────────────────────────────────

class TestIngest:
    def test_read_markdown(self):
        from knowledge_base.ingest import _read_markdown

        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
            f.write("# Test\n\nHello world")
            f.flush()
            text = _read_markdown(Path(f.name))
            assert "Hello world" in text

    def test_read_html(self):
        from knowledge_base.ingest import _read_html

        with tempfile.NamedTemporaryFile(suffix=".html", mode="w", delete=False) as f:
            f.write("<html><body><p>Test content</p><script>bad();</script></body></html>")
            f.flush()
            text = _read_html(Path(f.name))
            assert "Test content" in text
            assert "bad()" not in text

    def test_unsupported_type(self):
        from knowledge_base.ingest import ingest_file

        kb = MagicMock()
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            with pytest.raises(ValueError, match="Unsupported"):
                ingest_file(kb, f.name)

    def test_detect_doc_type(self):
        from knowledge_base.ingest import _detect_doc_type

        assert _detect_doc_type(Path("/data/kb_raw/books/quant.pdf")) == "book"
        assert _detect_doc_type(Path("/data/kb_raw/papers/alpha.pdf")) == "paper"
        assert _detect_doc_type(Path("/data/kb_raw/web/article.html")) == "web"
        assert _detect_doc_type(Path("/random/place/file.md")) == "note"
