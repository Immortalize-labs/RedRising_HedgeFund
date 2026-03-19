#!/usr/bin/env python3
"""
Run a strategy research debate.

Usage:
    python scripts/run_debate.py --brief "Explore intra-window mean reversion on Polymarket 5-min BTC"
    python scripts/run_debate.py --brief-file research_briefs/brief_001.md
    python scripts/run_debate.py --brief "..." --output data/debates/debate_001.json
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.hf.characters import team_summary
from orchestrator.debate import DebateEngine, DebateResult
from memory.store import GlobalMemory


def save_result(result: DebateResult, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_elapsed_sec": result.total_elapsed_sec,
        "synthesis_decision": result.synthesis.decision,
        "risk_decision": result.risk_review.decision,
        "proposals": [
            {"role": p.role, "model": p.model, "elapsed": p.elapsed_sec, "content": p.content}
            for p in result.proposals
        ],
        "reactions": [
            {"role": r.role, "model": r.model, "elapsed": r.elapsed_sec, "content": r.content}
            for r in result.reactions
        ],
        "synthesis": {
            "model": result.synthesis.model,
            "decision": result.synthesis.decision,
            "elapsed": result.synthesis.elapsed_sec,
            "content": result.synthesis.content,
        },
        "risk_review": {
            "model": result.risk_review.model,
            "decision": result.risk_review.decision,
            "elapsed": result.risk_review.elapsed_sec,
            "veto_details": result.risk_review.veto_details,
            "conditions": result.risk_review.conditions,
            "content": result.risk_review.content,
        },
    }
    output_path.write_text(json.dumps(data, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Run strategy research debate")
    parser.add_argument("--brief", "-b", default="", help="Research brief text")
    parser.add_argument("--brief-file", "-f", default="", help="Path to research brief file")
    parser.add_argument("--output", "-o", default="", help="Output JSON path")
    parser.add_argument("--existing", "-e", default="", help="Existing strategies context")
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--skip-risk", action="store_true", help="Research only, no risk review")
    parser.add_argument("--dry-run", action="store_true", help="Print team and exit")
    args = parser.parse_args()

    if args.dry_run:
        print(team_summary())
        return

    brief = args.brief
    if args.brief_file:
        brief = Path(args.brief_file).read_text().strip()
    if not brief:
        print("Error: provide --brief or --brief-file", file=sys.stderr)
        sys.exit(1)

    # Existing strategies context
    existing = args.existing
    if not existing:
        gm = GlobalMemory()
        existing = gm.orchestrator_context()

    print(f"{'='*60}")
    print(team_summary())
    print(f"{'='*60}")
    print(f"Brief: {brief[:200]}...")
    print(f"{'='*60}\n")

    engine = DebateEngine(max_tokens=args.max_tokens, timeout=args.timeout)
    result = engine.run(brief, existing, skip_risk=args.skip_risk)

    # Print summary
    print(f"\n{'='*60}")
    print(result.summary())
    print(f"{'='*60}\n")

    # Print key outputs
    print("=== PM SYNTHESIS ===")
    print(result.synthesis.content[:2000])
    print(f"\n=== RISK REVIEW ({result.risk_review.decision}) ===")
    print(result.risk_review.content[:2000])

    # Save
    if args.output:
        out = Path(args.output)
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = ROOT / "data" / "debates" / f"debate_{ts}.json"

    save_result(result, out)
    print(f"\nSaved to: {out}")

    # Log to global memory
    gm = GlobalMemory()
    gm.journal("debate_completed", {
        "brief": brief[:200],
        "synthesis_decision": result.synthesis.decision,
        "risk_decision": result.risk_review.decision,
        "elapsed": result.total_elapsed_sec,
        "output": str(out),
    })


if __name__ == "__main__":
    main()
