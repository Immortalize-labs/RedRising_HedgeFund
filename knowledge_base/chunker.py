"""Token-bounded recursive text splitter.

Splits text into chunks of ~350 tokens with 50-token overlap,
splitting on paragraphs first, then sentences, then words.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import tiktoken

_ENC = tiktoken.get_encoding("cl100k_base")

DEFAULT_CHUNK_SIZE = 350   # tokens
DEFAULT_OVERLAP = 50       # tokens


@dataclass
class Chunk:
    text: str
    index: int          # position within document
    token_count: int


def _tok_len(text: str) -> int:
    return len(_ENC.encode(text, disallowed_special=()))


def _split_paragraphs(text: str) -> list[str]:
    """Split on double-newline boundaries, keep non-empty."""
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def _split_sentences(text: str) -> list[str]:
    """Split on sentence-ending punctuation."""
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in parts if s.strip()]


def _merge_small(segments: list[str], max_tokens: int) -> list[str]:
    """Greedily merge consecutive segments that fit within max_tokens."""
    merged: list[str] = []
    buf = ""
    for seg in segments:
        candidate = f"{buf}\n\n{seg}".strip() if buf else seg
        if _tok_len(candidate) <= max_tokens:
            buf = candidate
        else:
            if buf:
                merged.append(buf)
            buf = seg
    if buf:
        merged.append(buf)
    return merged


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    """Split *text* into token-bounded chunks with overlap.

    Strategy:
      1. Split on paragraphs
      2. If a paragraph > chunk_size, split on sentences
      3. If a sentence > chunk_size, hard-split on words
      4. Merge small consecutive pieces back up to chunk_size
      5. Create overlap by prepending tail of previous chunk
    """
    # Step 1+2+3: break into pieces each <= chunk_size
    pieces: list[str] = []
    for para in _split_paragraphs(text):
        if _tok_len(para) <= chunk_size:
            pieces.append(para)
        else:
            for sent in _split_sentences(para):
                if _tok_len(sent) <= chunk_size:
                    pieces.append(sent)
                else:
                    # Hard split on words
                    words = sent.split()
                    buf: list[str] = []
                    for w in words:
                        candidate = " ".join(buf + [w])
                        if _tok_len(candidate) > chunk_size and buf:
                            pieces.append(" ".join(buf))
                            buf = [w]
                        else:
                            buf.append(w)
                    if buf:
                        pieces.append(" ".join(buf))

    # Step 4: merge small consecutive pieces
    merged = _merge_small(pieces, chunk_size)

    # Step 5: build final chunks with overlap
    chunks: list[Chunk] = []
    for i, text_block in enumerate(merged):
        if i > 0 and overlap > 0:
            prev_tokens = _ENC.encode(merged[i - 1], disallowed_special=())
            overlap_text = _ENC.decode(prev_tokens[-overlap:])
            text_block = overlap_text.strip() + "\n\n" + text_block
        chunks.append(Chunk(
            text=text_block,
            index=i,
            token_count=_tok_len(text_block),
        ))

    return chunks
