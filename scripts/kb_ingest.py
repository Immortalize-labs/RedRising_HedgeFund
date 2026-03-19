#!/usr/bin/env python3
"""CLI: Ingest documents into the Knowledge Base.

Usage:
    python scripts/kb_ingest.py add <file>          [--type book|paper|note|web]
    python scripts/kb_ingest.py add-dir <directory>  [--type book|paper|note|web]
    python scripts/kb_ingest.py list
    python scripts/kb_ingest.py delete <source_name>
    python scripts/kb_ingest.py reindex <directory>  [--type book|paper|note|web]
"""

import argparse
import sys
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from knowledge_base import get_kb
from knowledge_base.ingest import ingest_directory, ingest_file


def cmd_add(args):
    kb = get_kb()
    count = ingest_file(kb, args.file, doc_type=args.type)
    print(f"Ingested {Path(args.file).name}: {count} chunks")


def cmd_add_dir(args):
    kb = get_kb()
    results = ingest_directory(kb, args.directory, doc_type=args.type)
    total = sum(results.values())
    for name, count in results.items():
        print(f"  {name}: {count} chunks")
    print(f"Total: {total} chunks from {len(results)} files")


def cmd_list(args):
    kb = get_kb()
    s = kb.stats()
    if s["total_chunks"] == 0:
        print("Knowledge base is empty.")
        return
    print(f"Total chunks: {s['total_chunks']}")
    print("\nBy type:")
    for t, count in sorted(s["by_type"].items()):
        print(f"  {t}: {count}")
    print(f"\nSources ({len(s['sources'])}):")
    for src in s["sources"]:
        print(f"  - {src}")


def cmd_delete(args):
    kb = get_kb()
    count = kb.delete_doc(args.source)
    if count:
        print(f"Deleted {count} chunks for '{args.source}'")
    else:
        print(f"No chunks found for '{args.source}'")


def cmd_reindex(args):
    kb = get_kb()
    # Delete existing, then re-ingest
    old_stats = kb.stats()
    for src in old_stats["sources"]:
        kb.delete_doc(src)
    results = ingest_directory(kb, args.directory, doc_type=args.type)
    total = sum(results.values())
    print(f"Reindexed: {total} chunks from {len(results)} files")


def main():
    parser = argparse.ArgumentParser(description="Knowledge Base ingestion CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Ingest a single file")
    p_add.add_argument("file", help="Path to file")
    p_add.add_argument("--type", choices=["book", "paper", "note", "web"], default=None)

    p_dir = sub.add_parser("add-dir", help="Ingest all files in a directory")
    p_dir.add_argument("directory", help="Path to directory")
    p_dir.add_argument("--type", choices=["book", "paper", "note", "web"], default=None)

    sub.add_parser("list", help="List ingested documents")

    p_del = sub.add_parser("delete", help="Delete a source's chunks")
    p_del.add_argument("source", help="Source name (filename)")

    p_re = sub.add_parser("reindex", help="Delete all and re-ingest from directory")
    p_re.add_argument("directory", help="Path to directory")
    p_re.add_argument("--type", choices=["book", "paper", "note", "web"], default=None)

    args = parser.parse_args()
    {
        "add": cmd_add,
        "add-dir": cmd_add_dir,
        "list": cmd_list,
        "delete": cmd_delete,
        "reindex": cmd_reindex,
    }[args.command](args)


if __name__ == "__main__":
    main()
