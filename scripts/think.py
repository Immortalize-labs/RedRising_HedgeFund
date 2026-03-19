#!/usr/bin/env python3
"""Think Tool — Structured reasoning before action.

Forces agents to reason through claims before delegating or acting.
Logs all reasoning to data/think_log.jsonl for audit trail.

Usage:
    python scripts/think.py \
        --claim "What is being reported" \
        --priors "What I already know" \
        --math "Basic arithmetic check" \
        --hypotheses "Ranked causes" \
        --cheapest_check "Simplest verification" \
        --action "What to do next"
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta

EST = timezone(timedelta(hours=-5))
LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "think_log.jsonl")


def think(args: argparse.Namespace) -> dict:
    entry = {
        "timestamp": datetime.now(EST).isoformat(),
        "caller": args.caller or "unknown",
        "claim": args.claim,
        "priors": args.priors,
        "math": args.math,
        "hypotheses": args.hypotheses,
        "cheapest_check": args.cheapest_check,
        "action": args.action,
    }

    # Log to JSONL
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return entry


def format_output(entry: dict) -> str:
    lines = [
        "=" * 60,
        f"THINK  [{entry['timestamp']}]  caller={entry['caller']}",
        "=" * 60,
        f"  CLAIM:          {entry['claim']}",
        f"  PRIORS:         {entry['priors']}",
        f"  MATH:           {entry['math']}",
        f"  HYPOTHESES:     {entry['hypotheses']}",
        f"  CHEAPEST CHECK: {entry['cheapest_check']}",
        f"  ACTION:         {entry['action']}",
        "=" * 60,
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Think Tool — structured reasoning before action")
    parser.add_argument("--claim", required=True, help="What is being reported/asked?")
    parser.add_argument("--priors", required=True, help="What do I already know?")
    parser.add_argument("--math", required=True, help="Basic arithmetic sanity check")
    parser.add_argument("--hypotheses", required=True, help="Ranked causes by likelihood")
    parser.add_argument("--cheapest_check", required=True, help="Simplest verification before big action")
    parser.add_argument("--action", required=True, help="What to do based on reasoning")
    parser.add_argument("--caller", default=None, help="Who is calling (agent name)")

    args = parser.parse_args()
    entry = think(args)
    print(format_output(entry))


if __name__ == "__main__":
    main()
