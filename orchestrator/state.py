"""
Strategy State Schema
=====================
Single source of truth for a strategy flowing through the pipeline.
No LangGraph dependency — plain typed dict.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, TypedDict


class StrategyState(TypedDict, total=False):
    # Identity
    run_id: str
    strategy_id: str
    created_at: str

    # Research outputs
    universe: list[str]
    features: list[dict[str, Any]]
    validated_signals: list[dict[str, Any]]
    alpha_spec: dict[str, Any]

    # Debate outputs
    proposals: list[dict[str, Any]]       # Round 1
    reactions: list[dict[str, Any]]       # Round 2
    synthesis: dict[str, Any]             # Round 3
    risk_review: dict[str, Any]           # Round 4

    # Backtest outputs
    backtest_params: dict[str, Any]
    backtest_metrics: dict[str, Any]
    walkforward_metrics: dict[str, Any]
    robustness_metrics: dict[str, Any]
    risk_report: dict[str, Any]

    # Deployment outputs
    paper_metrics: dict[str, Any]
    live_metrics: dict[str, Any]
    deployment_manifest: dict[str, Any]

    # Control flow
    decision: str   # RESEARCH | BACKTEST | PAPER | LIVE | HALT
    gate_results: dict[str, str]
    errors: list[str]
    artifacts: dict[str, Any]


def new_state(strategy_id: str = "unnamed") -> StrategyState:
    return StrategyState(
        run_id=str(uuid.uuid4())[:8],
        strategy_id=strategy_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        decision="RESEARCH",
        gate_results={},
        errors=[],
        artifacts={},
    )
