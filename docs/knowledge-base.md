# Knowledge Base Architecture

## Overview

The Knowledge Base (KB) is the institutional memory of the fund. Every research paper, practitioner article, and technical reference is chunked, embedded, and searchable — so no researcher starts from zero.

```
Source Document → Chunker → Embedder → ChromaDB → Query Interface
```

## Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Vector Store | ChromaDB | Persistent vector storage, metadata filtering |
| Embedder | nomic-embed-text (768-dim) | Document embedding, semantic search |
| Chunker | Custom (350-token children, 1400-token parents) | Parent-child chunking for context preservation |
| Search | Hybrid (0.7 vector + 0.3 keyword) | RRF fusion for best-of-both retrieval |
| Reranker | BAAI/bge-reranker-v2-m3 | Cross-encoder reranking for precision |

## Document Types

| Type | Source | Example |
|------|--------|---------|
| `paper` | Academic papers, ArXiv | Barndorff-Nielsen & Shephard (2010) on realized semivariance |
| `book` | Textbook chapters | Gençay et al. (2002) wavelet methods in finance |
| `web` | Documentation, blogs | Anthropic prompt engineering guides |
| `note` | Internal research notes | Experiment findings, literature reviews |

## Ingestion Pipeline

### CLI Interface

```bash
# Ingest a single file
python scripts/kb_ingest.py add paper.pdf --type paper

# Ingest a directory
python scripts/kb_ingest.py add-dir knowledge_base/sources/research/ --type paper

# List all ingested documents
python scripts/kb_ingest.py list

# Delete a source
python scripts/kb_ingest.py delete "paper_name"

# Reindex everything
python scripts/kb_ingest.py reindex knowledge_base/sources/ --type paper
```

### Supported Formats

- **PDF** — Academic papers, books (auto-extracted text)
- **Markdown** — Research notes, web scrapes, summaries
- **Text** — Plain text documents

## Query Interface

```bash
# Search the knowledge base
python scripts/kb_query.py "realized semivariance for crypto prediction"

# Search with type filter
python scripts/kb_query.py "wavelet decomposition" --type paper

# Search with top-k
python scripts/kb_query.py "Kelly criterion position sizing" --top-k 5
```

## Chunking Strategy

We use **parent-child chunking** for optimal retrieval:

```
Parent Chunk (1400 tokens)
├── Child Chunk 1 (350 tokens)  ← matched by vector search
├── Child Chunk 2 (350 tokens)  ← matched by vector search
├── Child Chunk 3 (350 tokens)
└── Child Chunk 4 (350 tokens)

When a child matches → return the parent for full context
```

This solves the classic chunking dilemma:
- Small chunks = better vector match precision
- Large chunks = better context for the LLM
- Parent-child = both

## Search Configuration

From `config/rag.yaml`:

```yaml
search:
  hybrid_alpha: 0.7        # 70% vector, 30% keyword
  fusion_method: rrf        # Reciprocal Rank Fusion
  rrf_k: 60                # RRF constant
  top_k: 10                # Results to return

reranker:
  model: BAAI/bge-reranker-v2-m3
  top_n: 5                 # Reranked results
  timeout_ms: 500          # Max reranker latency
```

## Namespace Organization

```
knowledge_base/
├── sources/
│   ├── signals/        ← Time-series, spectral methods, regime detection
│   ├── models/         ← ML/DL, training, feature selection
│   ├── structure/      ← Market microstructure, orderbook dynamics
│   ├── strategy/       ← Portfolio theory, risk management
│   ├── research/       ← Curated academic paper summaries
│   ├── web/            ← Web-sourced documentation
│   └── general/        ← Cross-domain references
├── chroma/             ← ChromaDB persistent storage (gitignored)
├── __init__.py
├── kb.py               ← Core KB class
├── chunker.py          ← Chunking logic
├── embedder.py         ← Embedding interface
└── ingest.py           ← Ingestion pipeline
```

## Current Stats

| Metric | Value |
|--------|-------|
| Total chunks | 2,005 |
| Total sources | 30 |
| Paper summaries | 19 |
| Web documents | 8 |
| Embedding model | nomic-embed-text (768-dim) |
| Vector store | ChromaDB (SQLite backend) |

## Auto-Ingestion (Daily Scan)

The daily research scan (see `docs/research-flow.md`) automatically ingests new sources:

1. Scanner finds new papers/repos matching desk domains
2. Quality filter scores relevance/rigor/implementability (gate: 10/15)
3. Passing sources are auto-downloaded and ingested
4. Each source is tagged with desk namespace metadata
5. Desk leads are notified of new additions to their domain

This ensures the KB grows daily with curated, high-quality content.
