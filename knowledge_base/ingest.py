"""File parsing and ChromaDB ingestion.

Supports: PDF (.pdf), Markdown (.md), HTML (.html/.htm), plain text (.txt),
          EPUB (.epub).

PDF parsing uses Marker (marker-pdf) for high-fidelity extraction:
  - LaTeX math formulas preserved as $...$ and $$...$$
  - Images/figures extracted and saved to data/kb_images/
  - Tables preserved in Markdown format
  - Falls back to pypdf (_read_pdf_legacy) if Marker fails on a specific file
"""

from __future__ import annotations

import re
import warnings
from pathlib import Path
from typing import Optional

from .chunker import Chunk, chunk_text
from .kb import KnowledgeBase

# ---------------------------------------------------------------------------
# Image output directory
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
KB_IMAGES_DIR = _PROJECT_ROOT / "data" / "kb_images"


# ---------------------------------------------------------------------------
# PDF parsing — Marker (primary) + pypdf (fallback)
# ---------------------------------------------------------------------------

# Module-level model cache so we load once per process, not once per file.
_MARKER_MODELS: Optional[dict] = None


def _get_marker_models() -> dict:
    """Load and cache Marker's surya/detection models (CPU, float32 for MPS compat)."""
    global _MARKER_MODELS
    if _MARKER_MODELS is not None:
        return _MARKER_MODELS

    import torch
    from marker.models import create_model_dict

    # MPS has an index-out-of-bounds bug with large PDFs on Apple Silicon.
    # Force CPU + float32 to avoid the crash. Slower but reliable.
    device = "cpu"
    dtype = torch.float32

    print("  [Marker] Loading models (first call, ~20s)...", flush=True)
    _MARKER_MODELS = create_model_dict(device=device, dtype=dtype)
    print("  [Marker] Models ready.", flush=True)
    return _MARKER_MODELS


def _save_images(images: dict, book_stem: str) -> list[str]:
    """Save PIL images from Marker output; return list of description strings."""
    if not images:
        return []

    KB_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    descriptions: list[str] = []

    for img_name, pil_img in images.items():
        # Normalise filename: strip any path components marker might add
        safe_name = re.sub(r"[^\w.\-]", "_", Path(img_name).name)
        out_path = KB_IMAGES_DIR / f"{book_stem}__{safe_name}"
        try:
            if pil_img.mode not in ("RGB", "L"):
                pil_img = pil_img.convert("RGB")
            pil_img.save(str(out_path), "JPEG", quality=85)
            descriptions.append(
                f"[Figure from '{book_stem}': extracted chart/image saved to {out_path.name}]"
            )
        except Exception as exc:
            descriptions.append(
                f"[Figure from '{book_stem}': image extraction failed — {exc}]"
            )

    return descriptions


def _read_pdf(path: Path) -> str:
    """Parse PDF with Marker: preserves LaTeX math, tables, extracts images.

    Returns Markdown text with:
      - Block math as $$...$$
      - Inline math as $...$
      - Tables as Markdown tables
      - Image placeholders for figures
    Falls back to _read_pdf_legacy on any Marker failure.
    """
    try:
        from marker.converters.pdf import PdfConverter

        models = _get_marker_models()
        converter = PdfConverter(artifact_dict=models)

        print(f"  [Marker] Converting {path.name}...", flush=True)
        result = converter(str(path))

        # result.markdown  — full Markdown string
        # result.images    — dict[str, PIL.Image]
        # result.metadata  — dict with page count etc.

        markdown_text = result.markdown or ""
        page_count = result.metadata.get("page_count", "?")
        print(
            f"  [Marker] OK — {len(markdown_text):,} chars, "
            f"{page_count} pages, {len(result.images)} images",
            flush=True,
        )

        # Save extracted images and inject placeholder text
        image_descriptions = _save_images(result.images, path.stem)
        if image_descriptions:
            # Append figure descriptions as a separate section at the end
            figure_section = "\n\n## Extracted Figures\n\n" + "\n\n".join(
                image_descriptions
            )
            markdown_text = markdown_text + figure_section

        return markdown_text

    except Exception as exc:
        warnings.warn(
            f"Marker failed on {path.name} ({exc}). Falling back to pypdf.",
            stacklevel=2,
        )
        return _read_pdf_legacy(path)


def _read_pdf_legacy(path: Path) -> str:
    """Fallback PDF parser using pypdf (plain text only, no math/images)."""
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n\n".join(pages)


# ---------------------------------------------------------------------------
# EPUB parsing
# ---------------------------------------------------------------------------

def _read_epub(path: Path) -> str:
    """Extract plain text from an EPUB file via ebooklib + BeautifulSoup."""
    import ebooklib
    from bs4 import BeautifulSoup
    from ebooklib import epub

    book = epub.read_epub(str(path), options={"ignore_ncx": True})
    parts: list[str] = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        raw_html = item.get_content().decode("utf-8", errors="replace")
        soup = BeautifulSoup(raw_html, "html.parser")
        # Remove script/style noise
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        # Collapse excessive whitespace while preserving paragraph breaks
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Other format parsers
# ---------------------------------------------------------------------------

def _read_markdown(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_html(path: Path) -> str:
    """Strip HTML tags, return plain text."""
    raw = path.read_text(encoding="utf-8")
    text = re.sub(r"<script[^>]*>.*?</script>", "", raw, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


PARSERS = {
    ".pdf": _read_pdf,
    ".epub": _read_epub,
    ".md": _read_markdown,
    ".html": _read_html,
    ".htm": _read_html,
    ".txt": _read_text,
}


# ---------------------------------------------------------------------------
# Doc type detection
# ---------------------------------------------------------------------------

def _detect_doc_type(path: Path) -> str:
    """Guess doc_type from parent directory name."""
    parent = path.parent.name.lower()
    if parent in ("books", "book"):
        return "book"
    if parent in ("papers", "paper"):
        return "paper"
    if parent in ("notes", "note", "docs"):
        return "note"
    if parent in ("web", "articles"):
        return "web"
    return "note"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ingest_file(
    kb: KnowledgeBase,
    file_path: str | Path,
    doc_type: str | None = None,
    chunk_size: int = 350,
    overlap: int = 50,
) -> int:
    """Parse a file, chunk it, embed and upsert into KB.

    Returns number of chunks ingested.
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = path.suffix.lower()
    parser = PARSERS.get(suffix)
    if parser is None:
        raise ValueError(
            f"Unsupported file type: {suffix}. "
            f"Supported: {', '.join(PARSERS.keys())}"
        )

    text = parser(path)
    if not text.strip():
        return 0

    chunks: list[Chunk] = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    source = path.name
    doc_type = doc_type or _detect_doc_type(path)

    return kb.ingest_chunks(chunks, source=source, doc_type=doc_type)


def ingest_directory(
    kb: KnowledgeBase,
    dir_path: str | Path,
    doc_type: str | None = None,
    recursive: bool = True,
) -> dict[str, int]:
    """Ingest all supported files in a directory.

    Returns dict of {filename: chunk_count}.
    """
    dir_path = Path(dir_path).resolve()
    if not dir_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {dir_path}")

    results: dict[str, int] = {}
    pattern = "**/*" if recursive else "*"

    for path in sorted(dir_path.glob(pattern)):
        if path.is_file() and path.suffix.lower() in PARSERS:
            count = ingest_file(kb, path, doc_type=doc_type)
            results[path.name] = count

    return results
