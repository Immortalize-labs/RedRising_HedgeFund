#!/usr/bin/env python3
"""CLI: Query the Knowledge Base.

Usage:
    python scripts/kb_query.py "kelly criterion position sizing"
    python scripts/kb_query.py "polymarket fill rate" --top-k 3 --type note

Prints formatted context to stdout — designed for piping into agent prompts.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from knowledge_base import get_kb


def main():
    parser = argparse.ArgumentParser(description="Query the Knowledge Base")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results")
    parser.add_argument("--type", choices=["book", "paper", "note", "web"], default=None)
    parser.add_argument("--raw", action="store_true", help="Print raw chunks without formatting")
    args = parser.parse_args()

    kb = get_kb()
    results = kb.query(args.query, top_k=args.top_k, doc_type=args.type)

    if not results:
        print("No results found.", file=sys.stderr)
        sys.exit(1)

    if args.raw:
        for r in results:
            print(f"[{r.source} | {r.doc_type} | dist={r.distance:.4f}]")
            print(r.text)
            print()
    else:
        print(kb.format_for_prompt(results))


if __name__ == "__main__":
    main()
