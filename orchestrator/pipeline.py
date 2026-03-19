"""
Promotion Pipeline
==================
Wires state.py + gates.py into an executable promotion pipeline.

Strategy lifecycle:
  RESEARCH → [research_gate] → BACKTEST → [backtest_gate] → PAPER → [deployment_gate] → LIVE

Each transition:
  1. Runs the gate function against current state
  2. Records gate result (pass/fail + metrics)
  3. Advances state or halts with reason

No LangGraph. Pure function composition with state dict.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from orchestrator.state import StrategyState, new_state
from orchestrator.gates import (
    research_gate,
    backtest_gate,
    deployment_gate,
    monitor_check,
)

logger = logging.getLogger(__name__)


# ─── Stage definitions ────────────────────────────────────────────────────

STAGES = ["RESEARCH", "BACKTEST", "PAPER", "LIVE", "HALT"]

GATE_MAP: dict[str, Callable] = {
    "RESEARCH": research_gate,      # RESEARCH → BACKTEST
    "BACKTEST": backtest_gate,      # BACKTEST → PAPER
    "PAPER": deployment_gate,       # PAPER → LIVE
}

NEXT_STAGE: dict[str, str] = {
    "RESEARCH": "BACKTEST",
    "BACKTEST": "PAPER",
    "PAPER": "LIVE",
}


@dataclass
class GateResult:
    """Result of a single gate evaluation."""
    gate: str
    passed: bool
    metrics: dict[str, Any]
    timestamp: str = ""
    elapsed_ms: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class PipelineResult:
    """Result of running the pipeline on a strategy."""
    strategy_id: str
    initial_stage: str
    final_stage: str
    gates_evaluated: list[GateResult] = field(default_factory=list)
    halted: bool = False
    halt_reason: str = ""
    elapsed_ms: float = 0.0

    @property
    def advanced(self) -> bool:
        return self.final_stage != self.initial_stage and not self.halted

    def summary(self) -> str:
        lines = [
            f"Pipeline: {self.strategy_id}",
            f"  {self.initial_stage} → {self.final_stage}",
            f"  Advanced: {self.advanced}",
        ]
        for g in self.gates_evaluated:
            status = "PASS" if g.passed else "FAIL"
            lines.append(f"  Gate [{g.gate}]: {status} — {g.metrics}")
        if self.halted:
            lines.append(f"  HALTED: {self.halt_reason}")
        lines.append(f"  Time: {self.elapsed_ms:.0f}ms")
        return "\n".join(lines)


class PromotionPipeline:
    """Executes the strategy promotion pipeline.

    Usage:
        pipeline = PromotionPipeline()
        result = pipeline.evaluate(state)   # Check one gate
        result = pipeline.advance(state)    # Try to advance to next stage
        result = pipeline.run_full(state)   # Run all gates until blocked
    """

    def __init__(
        self,
        gate_overrides: dict[str, Callable] | None = None,
        hooks: dict[str, Callable] | None = None,
    ):
        """
        Args:
            gate_overrides: Override default gate functions
            hooks: Callbacks for events: on_advance, on_halt, on_gate_pass, on_gate_fail
        """
        self.gates = {**GATE_MAP, **(gate_overrides or {})}
        self.hooks = hooks or {}

    def evaluate(self, state: StrategyState) -> GateResult:
        """Evaluate the gate for the current stage. Does NOT modify state."""
        stage = state.get("decision", "RESEARCH")
        gate_fn = self.gates.get(stage)

        if gate_fn is None:
            return GateResult(
                gate=stage, passed=False,
                metrics={"error": f"No gate defined for stage '{stage}'"},
            )

        t0 = time.time()
        verdict, metrics = gate_fn(state)
        elapsed = (time.time() - t0) * 1000

        passed = verdict in ("pass", "go_live")
        return GateResult(
            gate=stage, passed=passed, metrics=metrics, elapsed_ms=elapsed,
        )

    def advance(self, state: StrategyState) -> PipelineResult:
        """Try to advance the strategy one stage. Returns result + updated state."""
        t0 = time.time()
        stage = state.get("decision", "RESEARCH")
        result = PipelineResult(
            strategy_id=state.get("strategy_id", "unknown"),
            initial_stage=stage,
            final_stage=stage,
        )

        if stage == "LIVE":
            result.halted = True
            result.halt_reason = "Already at LIVE stage"
            result.elapsed_ms = (time.time() - t0) * 1000
            return result

        if stage == "HALT":
            result.halted = True
            result.halt_reason = "Strategy is halted"
            result.elapsed_ms = (time.time() - t0) * 1000
            return result

        # Evaluate gate
        gate_result = self.evaluate(state)
        result.gates_evaluated.append(gate_result)

        if gate_result.passed:
            next_stage = NEXT_STAGE.get(stage, "HALT")
            state["decision"] = next_stage
            state.setdefault("gate_results", {})[stage] = {
                "verdict": "pass",
                "metrics": gate_result.metrics,
                "ts": gate_result.timestamp,
            }
            result.final_stage = next_stage
            logger.info(f"[{result.strategy_id}] {stage} → {next_stage}")
            self._fire_hook("on_advance", state, gate_result)
            self._fire_hook("on_gate_pass", state, gate_result)
        else:
            state.setdefault("gate_results", {})[stage] = {
                "verdict": "fail",
                "metrics": gate_result.metrics,
                "ts": gate_result.timestamp,
            }
            result.halted = True
            result.halt_reason = f"Gate {stage} failed: {gate_result.metrics}"
            logger.info(f"[{result.strategy_id}] blocked at {stage}: {gate_result.metrics}")
            self._fire_hook("on_gate_fail", state, gate_result)

        result.elapsed_ms = (time.time() - t0) * 1000
        return result

    def run_full(self, state: StrategyState) -> PipelineResult:
        """Run the pipeline from current stage until blocked or LIVE."""
        t0 = time.time()
        initial_stage = state.get("decision", "RESEARCH")
        all_gates: list[GateResult] = []

        while True:
            stage = state.get("decision", "RESEARCH")
            if stage in ("LIVE", "HALT"):
                break
            if stage not in self.gates:
                break

            result = self.advance(state)
            all_gates.extend(result.gates_evaluated)

            if result.halted:
                return PipelineResult(
                    strategy_id=state.get("strategy_id", "unknown"),
                    initial_stage=initial_stage,
                    final_stage=state.get("decision", stage),
                    gates_evaluated=all_gates,
                    halted=True,
                    halt_reason=result.halt_reason,
                    elapsed_ms=(time.time() - t0) * 1000,
                )

        return PipelineResult(
            strategy_id=state.get("strategy_id", "unknown"),
            initial_stage=initial_stage,
            final_stage=state.get("decision", "RESEARCH"),
            gates_evaluated=all_gates,
            elapsed_ms=(time.time() - t0) * 1000,
        )

    def health_check(self, state: StrategyState) -> GateResult:
        """Run the live monitoring check (doesn't advance stages)."""
        t0 = time.time()
        verdict, metrics = monitor_check(state)
        return GateResult(
            gate="MONITOR",
            passed=(verdict == "healthy"),
            metrics=metrics,
            elapsed_ms=(time.time() - t0) * 1000,
        )

    def _fire_hook(self, hook_name: str, state: StrategyState, gate_result: GateResult) -> None:
        hook = self.hooks.get(hook_name)
        if hook:
            try:
                hook(state, gate_result)
            except Exception as e:
                logger.error(f"Hook {hook_name} failed: {e}")
