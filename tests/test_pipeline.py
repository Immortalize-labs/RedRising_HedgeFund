"""
Tests for orchestrator/pipeline.py
===================================
Tests the promotion pipeline: RESEARCH → BACKTEST → PAPER → LIVE
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from orchestrator.pipeline import PromotionPipeline
from orchestrator.state import new_state


class TestPipelineGates:

    def test_research_gate_fails_with_no_signals(self):
        pipeline = PromotionPipeline()
        state = new_state("test-strategy")
        state["validated_signals"] = []

        result = pipeline.evaluate(state)
        assert not result.passed
        assert result.gate == "RESEARCH"

    def test_research_gate_passes_with_good_signals(self):
        pipeline = PromotionPipeline()
        state = new_state("test-strategy")
        state["validated_signals"] = [
            {"verdict": "REAL", "ic": 0.05},
            {"verdict": "REAL", "ic": 0.03},
            {"verdict": "REAL", "ic": 0.02},
        ]

        result = pipeline.evaluate(state)
        assert result.passed

    def test_backtest_gate_fails_low_sharpe(self):
        pipeline = PromotionPipeline()
        state = new_state("test-strategy")
        state["decision"] = "BACKTEST"
        state["walkforward_metrics"] = {
            "oos_sharpe": 0.2, "oos_days": 60, "decay_ratio": 0.5,
        }
        state["backtest_metrics"] = {
            "max_drawdown_pct": 3.0, "n_trades": 100, "calmar": 2.0,
        }

        result = pipeline.evaluate(state)
        assert not result.passed
        assert result.metrics["oos_sharpe"] is False  # failed this check

    def test_backtest_gate_passes(self):
        pipeline = PromotionPipeline()
        state = new_state("test-strategy")
        state["decision"] = "BACKTEST"
        state["walkforward_metrics"] = {
            "oos_sharpe": 1.2, "oos_days": 60, "decay_ratio": 0.5,
        }
        state["backtest_metrics"] = {
            "max_drawdown_pct": 3.0, "n_trades": 100, "calmar": 2.0,
        }

        result = pipeline.evaluate(state)
        assert result.passed


class TestPipelineAdvance:

    def test_advance_from_research(self):
        pipeline = PromotionPipeline()
        state = new_state("test-strategy")
        state["validated_signals"] = [
            {"verdict": "REAL", "ic": 0.05},
            {"verdict": "REAL", "ic": 0.03},
            {"verdict": "REAL", "ic": 0.02},
        ]

        result = pipeline.advance(state)
        assert result.advanced
        assert result.final_stage == "BACKTEST"
        assert state["decision"] == "BACKTEST"

    def test_advance_blocked_at_research(self):
        pipeline = PromotionPipeline()
        state = new_state("test-strategy")
        state["validated_signals"] = []

        result = pipeline.advance(state)
        assert not result.advanced
        assert result.halted
        assert state["decision"] == "RESEARCH"  # unchanged

    def test_advance_already_live(self):
        pipeline = PromotionPipeline()
        state = new_state("test-strategy")
        state["decision"] = "LIVE"

        result = pipeline.advance(state)
        assert result.halted
        assert "Already at LIVE" in result.halt_reason


class TestPipelineRunFull:

    def test_run_full_all_gates_pass(self):
        """Strategy goes from RESEARCH → LIVE in one run."""
        pipeline = PromotionPipeline()
        state = new_state("full-run")

        # Seed all required data
        state["validated_signals"] = [
            {"verdict": "REAL", "ic": 0.05},
            {"verdict": "REAL", "ic": 0.03},
            {"verdict": "REAL", "ic": 0.02},
        ]
        state["walkforward_metrics"] = {
            "oos_sharpe": 1.2, "oos_days": 60, "decay_ratio": 0.5,
        }
        state["backtest_metrics"] = {
            "max_drawdown_pct": 3.0, "n_trades": 100, "calmar": 2.0,
        }
        state["paper_metrics"] = {
            "slippage_delta_bps": 1.0, "fill_rate": 0.90,
            "risk_incidents": 0, "paper_days": 14,
        }

        result = pipeline.run_full(state)
        assert result.final_stage == "LIVE"
        assert not result.halted
        assert len(result.gates_evaluated) == 3
        assert state["decision"] == "LIVE"

    def test_run_full_blocked_at_backtest(self):
        pipeline = PromotionPipeline()
        state = new_state("blocked-run")

        state["validated_signals"] = [
            {"verdict": "REAL", "ic": 0.05},
            {"verdict": "REAL", "ic": 0.03},
            {"verdict": "REAL", "ic": 0.02},
        ]
        # Bad backtest — low sharpe
        state["walkforward_metrics"] = {"oos_sharpe": 0.1, "oos_days": 10, "decay_ratio": 0.1}
        state["backtest_metrics"] = {"max_drawdown_pct": 8.0, "n_trades": 20, "calmar": 0.3}

        result = pipeline.run_full(state)
        assert result.halted
        assert result.final_stage == "BACKTEST"
        assert len(result.gates_evaluated) == 2  # research passed, backtest failed


class TestPipelineHooks:

    def test_hooks_fire_on_advance(self):
        events = []

        def on_advance(state, gate):
            events.append(("advance", state["decision"]))

        def on_gate_pass(state, gate):
            events.append(("pass", gate.gate))

        pipeline = PromotionPipeline(hooks={
            "on_advance": on_advance,
            "on_gate_pass": on_gate_pass,
        })
        state = new_state("hook-test")
        state["validated_signals"] = [
            {"verdict": "REAL", "ic": 0.05},
            {"verdict": "REAL", "ic": 0.03},
            {"verdict": "REAL", "ic": 0.02},
        ]

        pipeline.advance(state)
        assert ("advance", "BACKTEST") in events
        assert ("pass", "RESEARCH") in events

    def test_hooks_fire_on_fail(self):
        events = []

        def on_fail(state, gate):
            events.append(("fail", gate.gate))

        pipeline = PromotionPipeline(hooks={"on_gate_fail": on_fail})
        state = new_state("fail-hook-test")
        state["validated_signals"] = []

        pipeline.advance(state)
        assert ("fail", "RESEARCH") in events


class TestHealthCheck:

    def test_healthy_strategy(self):
        pipeline = PromotionPipeline()
        state = new_state("health-test")
        state["live_metrics"] = {"drawdown_pct": 0.5, "daily_pnl": 10.0}

        result = pipeline.health_check(state)
        assert result.passed
        assert result.metrics == {}

    def test_unhealthy_drawdown(self):
        pipeline = PromotionPipeline()
        state = new_state("dd-test")
        state["live_metrics"] = {"drawdown_pct": 3.0, "daily_pnl": -60.0}

        result = pipeline.health_check(state)
        assert not result.passed
        assert "drawdown" in result.metrics
        assert "daily_loss" in result.metrics


class TestPipelineSummary:

    def test_summary_format(self):
        pipeline = PromotionPipeline()
        state = new_state("summary-test")
        state["validated_signals"] = [
            {"verdict": "REAL", "ic": 0.05},
            {"verdict": "REAL", "ic": 0.03},
            {"verdict": "REAL", "ic": 0.02},
        ]

        result = pipeline.advance(state)
        s = result.summary()
        assert "RESEARCH" in s
        assert "BACKTEST" in s
        assert "PASS" in s


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
