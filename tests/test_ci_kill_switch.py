"""
Tests for CI-based kill switch in strategy_perf_monitor.
========================================================
Validates:
1. Wilson CI calculation matches known values
2. ETH-15m scenario (22/50) would NOT be killed
3. Clearly bad strategy (20/100) WOULD be killed
4. No kill fires when sample < 30 trades
5. Gate file reading for baseline WR
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from scripts.strategy_perf_monitor import (
    DEFAULT_BASELINE_WR,
    KILL_MARGIN_PP,
    MIN_TRADES_FOR_KILL,
    load_baseline_wr,
    wilson_ci,
)

# ---------------------------------------------------------------------------
# Wilson CI calculation tests
# ---------------------------------------------------------------------------

class TestWilsonCI:
    """Validate Wilson score interval against known values."""

    def test_wilson_ci_22_of_50(self):
        """ETH-15m scenario: 22 wins out of 50 trades.

        Expected approximately (0.310, 0.578).
        With this CI, upper bound 0.578 is NOT below any reasonable
        kill line, so ETH-15m should NOT be killed.
        """
        lower, upper = wilson_ci(22, 50)
        assert abs(lower - 0.310) < 0.01, f"Lower bound {lower:.4f} should be ~0.310"
        assert abs(upper - 0.578) < 0.01, f"Upper bound {upper:.4f} should be ~0.578"

    def test_wilson_ci_20_of_100(self):
        """Clearly bad strategy: 20 wins out of 100 trades.

        Expected approximately (0.133, 0.285).
        Upper bound 0.285 is far below any reasonable baseline (55%)
        minus 5pp = 50%, so this WOULD trigger kill.
        """
        lower, upper = wilson_ci(20, 100)
        assert abs(lower - 0.133) < 0.01, f"Lower bound {lower:.4f} should be ~0.133"
        assert abs(upper - 0.285) < 0.01, f"Upper bound {upper:.4f} should be ~0.285"

    def test_wilson_ci_zero_trades(self):
        """Edge case: no trades at all."""
        lower, upper = wilson_ci(0, 0)
        assert lower == 0.0
        assert upper == 1.0

    def test_wilson_ci_all_wins(self):
        """All trades are wins."""
        lower, upper = wilson_ci(50, 50)
        assert lower > 0.9, f"Lower bound {lower:.4f} should be > 0.9 for 50/50"
        assert upper == 1.0

    def test_wilson_ci_no_wins(self):
        """All trades are losses."""
        lower, upper = wilson_ci(0, 50)
        assert lower == 0.0
        assert upper < 0.1, f"Upper bound {upper:.4f} should be < 0.1 for 0/50"

    def test_wilson_ci_50_percent(self):
        """Exactly 50% WR with 100 trades. CI should be roughly symmetric around 0.50."""
        lower, upper = wilson_ci(50, 100)
        center = (lower + upper) / 2
        assert abs(center - 0.50) < 0.01
        # Width should be about 0.10 each side
        assert abs(upper - lower - 0.196) < 0.02

    def test_wilson_ci_small_sample(self):
        """Small sample: 3 wins out of 5. Wide interval expected."""
        lower, upper = wilson_ci(3, 5)
        assert lower < 0.25
        assert upper > 0.85
        assert upper - lower > 0.5  # very wide


# ---------------------------------------------------------------------------
# Kill decision logic tests
# ---------------------------------------------------------------------------

class TestKillDecisionLogic:
    """Test the kill decision criteria without needing live services."""

    def _should_kill(self, wins: int, n: int, baseline_wr: float) -> bool:
        """Replicate the kill decision logic from run_check()."""
        if n < MIN_TRADES_FOR_KILL:
            return False
        _, ci_upper = wilson_ci(wins, n)
        kill_line = baseline_wr - KILL_MARGIN_PP / 100.0
        return ci_upper < kill_line

    def test_eth_15m_not_killed(self):
        """ETH-15m: 22/50 at 44% WR should NOT be killed.

        Baseline from gate file is 60.7% -> kill line = 55.7%.
        CI upper = ~57.8% which is ABOVE 55.7%.
        This is the exact scenario that motivated this change.
        """
        # With baseline 0.607 (from ETHXGB15M01_fix.json backtest_after.wr)
        assert not self._should_kill(22, 50, baseline_wr=0.607)

    def test_clearly_bad_strategy_killed(self):
        """20/100 at 20% WR should be killed against any reasonable baseline."""
        # CI upper ~0.285, kill line for 55% baseline = 0.50
        assert self._should_kill(20, 100, baseline_wr=0.55)

    def test_marginal_strategy_not_killed(self):
        """45/100 at 45% WR with 55% baseline. Kill line = 50%.

        CI upper for 45/100 is ~0.549, which is above 0.50.
        Should NOT kill -- still within statistical noise.
        """
        assert not self._should_kill(45, 100, baseline_wr=0.55)

    def test_no_kill_below_min_trades(self):
        """Even terrible WR should not trigger kill with < 30 trades."""
        # 2 wins out of 20 = 10% WR, but only 20 trades
        assert not self._should_kill(2, 20, baseline_wr=0.55)
        # 0 wins out of 29 = 0% WR, but only 29 trades
        assert not self._should_kill(0, 29, baseline_wr=0.55)

    def test_kill_at_exactly_min_trades(self):
        """At exactly 30 trades, terrible WR should trigger kill."""
        # 3 wins out of 30 = 10% WR
        assert self._should_kill(3, 30, baseline_wr=0.55)

    def test_no_kill_when_performing_well(self):
        """Strategy at 60% WR with 55% baseline should never be killed."""
        assert not self._should_kill(60, 100, baseline_wr=0.55)
        assert not self._should_kill(30, 50, baseline_wr=0.55)

    def test_high_baseline_harder_to_survive(self):
        """Higher baseline = higher kill line = easier to get killed."""
        # 35/100 = 35% WR, CI upper ~0.45
        # Baseline 55%: kill line 50%, CI upper 0.45 < 0.50 -> KILL
        assert self._should_kill(35, 100, baseline_wr=0.55)
        # Baseline 40%: kill line 35%, CI upper 0.45 > 0.35 -> NO KILL
        assert not self._should_kill(35, 100, baseline_wr=0.40)


# ---------------------------------------------------------------------------
# Gate file / baseline WR loading tests
# ---------------------------------------------------------------------------

class TestLoadBaselineWR:
    """Test gate file reading for baseline WR extraction."""

    def test_load_from_fix_gate(self, tmp_path):
        """Read backtest_after.wr from a _fix.json gate file."""
        gates_dir = tmp_path / "data" / "gates"
        gates_dir.mkdir(parents=True)
        gate = {
            "type": "fix",
            "strategy_id": "TESTSTRAT01",
            "backtest_after": {"wr": 60.7, "pnl": 39.63, "n": 28},
            "approved_at": "2026-03-16T18:50:00Z",
        }
        (gates_dir / "TESTSTRAT01_fix.json").write_text(json.dumps(gate))

        with patch("scripts.strategy_perf_monitor.PROJECT_ROOT", tmp_path):
            result = load_baseline_wr("TESTSTRAT01")
        assert abs(result - 0.607) < 0.001

    def test_load_from_launch_gate(self, tmp_path):
        """Read backtest.oos_wr from a _launch.json gate file."""
        gates_dir = tmp_path / "data" / "gates"
        gates_dir.mkdir(parents=True)
        gate = {
            "type": "launch",
            "strategy_id": "TESTSTRAT01",
            "backtest": {"oos_wr": 58.0, "oos_sharpe": 1.2},
        }
        (gates_dir / "TESTSTRAT01_launch.json").write_text(json.dumps(gate))

        with patch("scripts.strategy_perf_monitor.PROJECT_ROOT", tmp_path):
            result = load_baseline_wr("TESTSTRAT01")
        assert abs(result - 0.58) < 0.001

    def test_fix_gate_takes_priority_over_launch(self, tmp_path):
        """_fix.json should be checked before _launch.json."""
        gates_dir = tmp_path / "data" / "gates"
        gates_dir.mkdir(parents=True)
        fix_gate = {
            "backtest_after": {"wr": 65.0},
        }
        launch_gate = {
            "backtest": {"oos_wr": 55.0},
        }
        (gates_dir / "TESTSTRAT01_fix.json").write_text(json.dumps(fix_gate))
        (gates_dir / "TESTSTRAT01_launch.json").write_text(json.dumps(launch_gate))

        with patch("scripts.strategy_perf_monitor.PROJECT_ROOT", tmp_path):
            result = load_baseline_wr("TESTSTRAT01")
        # Should use fix gate's 65%, not launch gate's 55%
        assert abs(result - 0.65) < 0.001

    def test_default_when_no_gate_file(self, tmp_path):
        """Falls back to DEFAULT_BASELINE_WR when no gate file exists."""
        gates_dir = tmp_path / "data" / "gates"
        gates_dir.mkdir(parents=True)

        with patch("scripts.strategy_perf_monitor.PROJECT_ROOT", tmp_path):
            result = load_baseline_wr("NONEXISTENT01")
        assert result == DEFAULT_BASELINE_WR

    def test_handles_fractional_wr_in_gate(self, tmp_path):
        """Gate file with WR already as fraction (<=1.0) should be returned as-is."""
        gates_dir = tmp_path / "data" / "gates"
        gates_dir.mkdir(parents=True)
        gate = {
            "backtest_after": {"wr": 0.607},
        }
        (gates_dir / "TESTSTRAT01_fix.json").write_text(json.dumps(gate))

        with patch("scripts.strategy_perf_monitor.PROJECT_ROOT", tmp_path):
            result = load_baseline_wr("TESTSTRAT01")
        assert abs(result - 0.607) < 0.001

    def test_real_gate_files(self):
        """Verify we can read the actual gate files in the repo."""
        # ETHXGB15M01: backtest_after.wr = 60.7
        eth_baseline = load_baseline_wr("ETHXGB15M01")
        assert abs(eth_baseline - 0.607) < 0.001, f"ETH baseline {eth_baseline} should be ~0.607"

        # BTCXGB15M01: backtest_after.wr = 58.1
        btc_baseline = load_baseline_wr("BTCXGB15M01")
        assert abs(btc_baseline - 0.581) < 0.001, f"BTC baseline {btc_baseline} should be ~0.581"

        # XRPXGB15M01: backtest_after.wr = 69.2
        xrp_baseline = load_baseline_wr("XRPXGB15M01")
        assert abs(xrp_baseline - 0.692) < 0.001, f"XRP baseline {xrp_baseline} should be ~0.692"


# ---------------------------------------------------------------------------
# Integration: ETH-15m would-have-survived scenario
# ---------------------------------------------------------------------------

class TestETH15mSurvival:
    """Confirm the exact scenario that caused the false kill is now safe."""

    def test_eth_15m_44pct_wr_50_trades(self):
        """ETH-15m had ~44% WR over 50 trades and was killed.

        With Wilson CI: 22/50 -> CI=[31.0%, 57.8%]
        Baseline from gate: 60.7% -> kill line = 55.7%
        CI upper 57.8% > 55.7% -> NO KILL (correct!)
        """
        lower, upper = wilson_ci(22, 50)
        baseline = 0.607  # from ETHXGB15M01_fix.json
        kill_line = baseline - 0.05

        assert upper > kill_line, (
            f"ETH-15m should survive: CI upper {upper:.3f} should be > "
            f"kill line {kill_line:.3f} (baseline {baseline:.3f} - 5pp)"
        )
