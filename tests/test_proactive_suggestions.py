"""
Tests for core/risk/proactive_suggestions.py

Each of the 8 triggers is covered by:
  - A test that fires the trigger (state at the threshold)
  - A test that stays below the threshold (no false positive)

Additional tests cover:
  - Severity ordering (critical before warning before info)
  - JSONL logging (written to tmp_path)
  - Module-level singleton exists
  - Edge cases (missing keys, insufficient data)
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from core.risk.proactive_suggestions import (
    CRITICAL,
    INFO,
    WARNING,
    PortfolioStateChecker,
    Suggestion,
    state_checker,
)

# ── Helpers ────────────────────────────────────────────────────────────────

def _checker(tmp_path: Path) -> PortfolioStateChecker:
    """Return a checker that logs to a temp file."""
    return PortfolioStateChecker(log_path=tmp_path / "suggestions.jsonl")


def _base_state(**overrides) -> dict:
    """Minimal healthy portfolio state — all triggers silent."""
    state = {
        "drawdown_pct": 0.0,
        "last_trade_ts": time.time() - 60,  # 1 minute ago
        "strategies": {
            "btc-15m": {
                "fill_rate": 0.85,
                "win_rate": 0.55,
                "backtest_win_rate": 0.55,
                "recent_trades": [{"won": True}] * 10,
                "daily_pnl": 5.0,
                "direction": "UP",
            },
            "eth-15m": {
                "fill_rate": 0.90,
                "win_rate": 0.58,
                "backtest_win_rate": 0.58,
                "recent_trades": [{"won": True}] * 10,
                "daily_pnl": 8.0,
                "direction": "DOWN",
            },
        },
    }
    state.update(overrides)
    return state


# ── Trigger 1: Drawdown warning ────────────────────────────────────────────


class TestDrawdownWarning:
    def test_fires_at_1_6_pct(self, tmp_path):
        checker = _checker(tmp_path)
        state = _base_state(drawdown_pct=1.6)
        suggestions = checker.check_and_suggest(state)
        triggers = [s.trigger for s in suggestions]
        assert "drawdown_warning" in triggers

    def test_severity_is_warning(self, tmp_path):
        checker = _checker(tmp_path)
        state = _base_state(drawdown_pct=1.6)
        suggestions = checker.check_and_suggest(state)
        dd = next(s for s in suggestions if s.trigger == "drawdown_warning")
        assert dd.severity == WARNING

    def test_does_not_fire_below_threshold(self, tmp_path):
        checker = _checker(tmp_path)
        state = _base_state(drawdown_pct=1.4)
        suggestions = checker.check_and_suggest(state)
        assert not any(s.trigger == "drawdown_warning" for s in suggestions)

    def test_does_not_fire_at_zero(self, tmp_path):
        checker = _checker(tmp_path)
        suggestions = checker.check_and_suggest(_base_state(drawdown_pct=0.0))
        assert not any("drawdown" in s.trigger for s in suggestions)


# ── Trigger 2: Drawdown critical ───────────────────────────────────────────


class TestDrawdownCritical:
    def test_fires_at_2_1_pct(self, tmp_path):
        checker = _checker(tmp_path)
        state = _base_state(drawdown_pct=2.1)
        suggestions = checker.check_and_suggest(state)
        triggers = [s.trigger for s in suggestions]
        assert "drawdown_critical" in triggers

    def test_severity_is_critical(self, tmp_path):
        checker = _checker(tmp_path)
        state = _base_state(drawdown_pct=2.1)
        suggestions = checker.check_and_suggest(state)
        dd = next(s for s in suggestions if s.trigger == "drawdown_critical")
        assert dd.severity == CRITICAL

    def test_critical_not_warning_when_above_2pct(self, tmp_path):
        """Critical threshold should shadow the warning — only critical fires."""
        checker = _checker(tmp_path)
        state = _base_state(drawdown_pct=2.5)
        suggestions = checker.check_and_suggest(state)
        # Critical fires, warning does NOT (critical threshold is higher)
        assert any(s.trigger == "drawdown_critical" for s in suggestions)
        assert not any(s.trigger == "drawdown_warning" for s in suggestions)

    def test_does_not_fire_at_1_9_pct(self, tmp_path):
        checker = _checker(tmp_path)
        state = _base_state(drawdown_pct=1.9)
        suggestions = checker.check_and_suggest(state)
        assert not any(s.trigger == "drawdown_critical" for s in suggestions)


# ── Trigger 3: Fill rate low ───────────────────────────────────────────────


class TestFillRateLow:
    def _state_with_fill(self, fill_rate: float) -> dict:
        s = _base_state()
        s["strategies"]["btc-15m"]["fill_rate"] = fill_rate
        return s

    def test_fires_at_65_pct(self, tmp_path):
        checker = _checker(tmp_path)
        suggestions = checker.check_and_suggest(self._state_with_fill(0.65))
        assert any(s.trigger == "fill_rate_low" and s.strategy == "btc-15m" for s in suggestions)

    def test_severity_is_warning(self, tmp_path):
        checker = _checker(tmp_path)
        suggestions = checker.check_and_suggest(self._state_with_fill(0.65))
        s = next(s for s in suggestions if s.trigger == "fill_rate_low")
        assert s.severity == WARNING

    def test_does_not_fire_at_70_pct(self, tmp_path):
        checker = _checker(tmp_path)
        # Exactly 70% — should NOT fire (threshold is strictly <)
        suggestions = checker.check_and_suggest(self._state_with_fill(0.70))
        assert not any(s.trigger == "fill_rate_low" for s in suggestions)

    def test_does_not_fire_at_85_pct(self, tmp_path):
        checker = _checker(tmp_path)
        suggestions = checker.check_and_suggest(self._state_with_fill(0.85))
        assert not any(s.trigger == "fill_rate_low" for s in suggestions)

    def test_no_fill_rate_key_is_silent(self, tmp_path):
        checker = _checker(tmp_path)
        state = _base_state()
        del state["strategies"]["btc-15m"]["fill_rate"]
        suggestions = checker.check_and_suggest(state)
        assert not any(s.trigger == "fill_rate_low" and s.strategy == "btc-15m" for s in suggestions)


# ── Trigger 4: WR drop below backtest ─────────────────────────────────────


class TestWRBelowBacktest:
    def _state_with_wr(self, live_wr: float, bt_wr: float) -> dict:
        s = _base_state()
        s["strategies"]["btc-15m"]["win_rate"] = live_wr
        s["strategies"]["btc-15m"]["backtest_win_rate"] = bt_wr
        return s

    def test_fires_when_5pp_drop(self, tmp_path):
        checker = _checker(tmp_path)
        suggestions = checker.check_and_suggest(self._state_with_wr(0.48, 0.55))
        # drop = 7pp → above 5pp threshold
        assert any(s.trigger == "wr_below_backtest" and s.strategy == "btc-15m" for s in suggestions)

    def test_severity_is_warning(self, tmp_path):
        checker = _checker(tmp_path)
        suggestions = checker.check_and_suggest(self._state_with_wr(0.48, 0.55))
        s = next(s for s in suggestions if s.trigger == "wr_below_backtest")
        assert s.severity == WARNING

    def test_does_not_fire_at_4pp_drop(self, tmp_path):
        checker = _checker(tmp_path)
        # 4pp drop — below the 5pp threshold
        suggestions = checker.check_and_suggest(self._state_with_wr(0.51, 0.55))
        assert not any(s.trigger == "wr_below_backtest" for s in suggestions)

    def test_does_not_fire_when_wr_above_backtest(self, tmp_path):
        checker = _checker(tmp_path)
        suggestions = checker.check_and_suggest(self._state_with_wr(0.60, 0.55))
        assert not any(s.trigger == "wr_below_backtest" for s in suggestions)

    def test_missing_backtest_wr_is_silent(self, tmp_path):
        checker = _checker(tmp_path)
        state = _base_state()
        del state["strategies"]["btc-15m"]["backtest_win_rate"]
        suggestions = checker.check_and_suggest(state)
        assert not any(s.trigger == "wr_below_backtest" for s in suggestions)


# ── Trigger 5: Adverse selection / kill switch ─────────────────────────────


class TestAdverseSelection:
    def _state_with_trades(self, trades: list[dict], strategy: str = "btc-15m") -> dict:
        s = _base_state()
        s["strategies"][strategy]["recent_trades"] = trades
        return s

    def test_fires_at_10_pct_wr(self, tmp_path):
        checker = _checker(tmp_path)
        trades = [{"won": False}] * 10
        suggestions = checker.check_and_suggest(self._state_with_trades(trades))
        assert any(s.trigger == "adverse_selection" and s.strategy == "btc-15m" for s in suggestions)

    def test_severity_is_critical(self, tmp_path):
        checker = _checker(tmp_path)
        trades = [{"won": False}] * 10
        suggestions = checker.check_and_suggest(self._state_with_trades(trades))
        s = next(s for s in suggestions if s.trigger == "adverse_selection")
        assert s.severity == CRITICAL

    def test_fires_at_exactly_1_win_in_10(self, tmp_path):
        checker = _checker(tmp_path)
        # 1/10 = 10% WR < 20% threshold
        trades = [{"won": True}] + [{"won": False}] * 9
        suggestions = checker.check_and_suggest(self._state_with_trades(trades))
        assert any(s.trigger == "adverse_selection" for s in suggestions)

    def test_does_not_fire_at_20_pct_wr(self, tmp_path):
        checker = _checker(tmp_path)
        # Exactly 20% WR — should NOT fire (threshold is strictly <)
        trades = [{"won": True}] * 2 + [{"won": False}] * 8
        suggestions = checker.check_and_suggest(self._state_with_trades(trades))
        assert not any(s.trigger == "adverse_selection" for s in suggestions)

    def test_does_not_fire_with_fewer_than_10_settled(self, tmp_path):
        checker = _checker(tmp_path)
        # Only 5 settled trades — insufficient for adverse selection check
        trades = [{"won": False}] * 5
        suggestions = checker.check_and_suggest(self._state_with_trades(trades))
        assert not any(s.trigger == "adverse_selection" for s in suggestions)

    def test_unsettled_trades_excluded(self, tmp_path):
        """Trades with won=None must not count toward the adverse window."""
        checker = _checker(tmp_path)
        # 5 unsettled + 5 losses = only 5 settled → no trigger
        trades = [{"won": None}] * 5 + [{"won": False}] * 5
        suggestions = checker.check_and_suggest(self._state_with_trades(trades))
        assert not any(s.trigger == "adverse_selection" for s in suggestions)


# ── Trigger 6: Daily PnL below -$25 ───────────────────────────────────────


class TestDailyPnLLow:
    def _state_with_pnl(self, pnl: float) -> dict:
        s = _base_state()
        s["strategies"]["btc-15m"]["daily_pnl"] = pnl
        return s

    def test_fires_at_minus_30(self, tmp_path):
        checker = _checker(tmp_path)
        suggestions = checker.check_and_suggest(self._state_with_pnl(-30.0))
        assert any(s.trigger == "daily_pnl_low" and s.strategy == "btc-15m" for s in suggestions)

    def test_severity_is_warning(self, tmp_path):
        checker = _checker(tmp_path)
        suggestions = checker.check_and_suggest(self._state_with_pnl(-30.0))
        s = next(s for s in suggestions if s.trigger == "daily_pnl_low")
        assert s.severity == WARNING

    def test_does_not_fire_at_minus_25(self, tmp_path):
        checker = _checker(tmp_path)
        # Exactly -$25 — NOT below threshold
        suggestions = checker.check_and_suggest(self._state_with_pnl(-25.0))
        assert not any(s.trigger == "daily_pnl_low" for s in suggestions)

    def test_does_not_fire_for_positive_pnl(self, tmp_path):
        checker = _checker(tmp_path)
        suggestions = checker.check_and_suggest(self._state_with_pnl(10.0))
        assert not any(s.trigger == "daily_pnl_low" for s in suggestions)

    def test_missing_daily_pnl_is_silent(self, tmp_path):
        checker = _checker(tmp_path)
        state = _base_state()
        del state["strategies"]["btc-15m"]["daily_pnl"]
        suggestions = checker.check_and_suggest(state)
        assert not any(s.trigger == "daily_pnl_low" and s.strategy == "btc-15m" for s in suggestions)


# ── Trigger 7: All positions same direction ─────────────────────────────────


class TestCorrelatedPositions:
    def test_fires_when_all_up(self, tmp_path):
        checker = _checker(tmp_path)
        state = _base_state()
        state["strategies"]["btc-15m"]["direction"] = "UP"
        state["strategies"]["eth-15m"]["direction"] = "UP"
        suggestions = checker.check_and_suggest(state)
        assert any(s.trigger == "all_positions_correlated" for s in suggestions)

    def test_fires_when_all_down(self, tmp_path):
        checker = _checker(tmp_path)
        state = _base_state()
        state["strategies"]["btc-15m"]["direction"] = "DOWN"
        state["strategies"]["eth-15m"]["direction"] = "DOWN"
        suggestions = checker.check_and_suggest(state)
        assert any(s.trigger == "all_positions_correlated" for s in suggestions)

    def test_severity_is_info(self, tmp_path):
        checker = _checker(tmp_path)
        state = _base_state()
        state["strategies"]["btc-15m"]["direction"] = "UP"
        state["strategies"]["eth-15m"]["direction"] = "UP"
        suggestions = checker.check_and_suggest(state)
        s = next(s for s in suggestions if s.trigger == "all_positions_correlated")
        assert s.severity == INFO

    def test_does_not_fire_with_mixed_directions(self, tmp_path):
        checker = _checker(tmp_path)
        # Base state already has UP and DOWN
        suggestions = checker.check_and_suggest(_base_state())
        assert not any(s.trigger == "all_positions_correlated" for s in suggestions)

    def test_does_not_fire_with_single_active_strategy(self, tmp_path):
        checker = _checker(tmp_path)
        state = _base_state()
        state["strategies"]["eth-15m"]["direction"] = ""  # no position
        suggestions = checker.check_and_suggest(state)
        assert not any(s.trigger == "all_positions_correlated" for s in suggestions)

    def test_does_not_fire_with_no_strategies(self, tmp_path):
        checker = _checker(tmp_path)
        state = _base_state()
        state["strategies"] = {}
        suggestions = checker.check_and_suggest(state)
        assert not any(s.trigger == "all_positions_correlated" for s in suggestions)


# ── Trigger 8: No trades in 2+ hours ───────────────────────────────────────


class TestNoRecentTrades:
    def test_fires_after_2h(self, tmp_path):
        checker = _checker(tmp_path)
        state = _base_state(last_trade_ts=time.time() - 7201)  # 2h 1s ago
        suggestions = checker.check_and_suggest(state)
        assert any(s.trigger == "no_recent_trades" for s in suggestions)

    def test_severity_is_info(self, tmp_path):
        checker = _checker(tmp_path)
        state = _base_state(last_trade_ts=time.time() - 7201)
        suggestions = checker.check_and_suggest(state)
        s = next(s for s in suggestions if s.trigger == "no_recent_trades")
        assert s.severity == INFO

    def test_does_not_fire_within_2h(self, tmp_path):
        checker = _checker(tmp_path)
        state = _base_state(last_trade_ts=time.time() - 3600)  # 1h ago
        suggestions = checker.check_and_suggest(state)
        assert not any(s.trigger == "no_recent_trades" for s in suggestions)

    def test_does_not_fire_when_no_timestamp(self, tmp_path):
        checker = _checker(tmp_path)
        state = _base_state()
        del state["last_trade_ts"]
        suggestions = checker.check_and_suggest(state)
        assert not any(s.trigger == "no_recent_trades" for s in suggestions)


# ── Severity ordering ───────────────────────────────────────────────────────


class TestSeverityOrdering:
    def test_critical_before_warning_before_info(self, tmp_path):
        checker = _checker(tmp_path)
        # Arrange state that fires all three severity levels
        state = {
            "drawdown_pct": 2.5,           # critical
            "last_trade_ts": time.time() - 7300,  # info
            "strategies": {
                "btc-15m": {
                    "fill_rate": 0.60,     # warning
                    "win_rate": 0.55,
                    "backtest_win_rate": 0.55,
                    "recent_trades": [{"won": True}] * 10,
                    "daily_pnl": 5.0,
                    "direction": "UP",
                },
            },
        }
        suggestions = checker.check_and_suggest(state)
        severities = [s.severity for s in suggestions]
        _order = {CRITICAL: 0, WARNING: 1, INFO: 2}
        ordered = sorted(severities, key=lambda x: _order[x])
        assert severities == ordered, f"Expected ordered severities, got: {severities}"


# ── JSONL logging ────────────────────────────────────────────────────────────


class TestJSONLLogging:
    def test_logged_to_file(self, tmp_path):
        checker = _checker(tmp_path)
        state = _base_state(drawdown_pct=1.6)
        suggestions = checker.check_and_suggest(state)
        log_file = tmp_path / "suggestions.jsonl"
        assert log_file.exists()
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == len(suggestions)

    def test_log_entries_are_valid_json(self, tmp_path):
        checker = _checker(tmp_path)
        state = _base_state(drawdown_pct=1.6)
        checker.check_and_suggest(state)
        log_file = tmp_path / "suggestions.jsonl"
        for line in log_file.read_text().strip().split("\n"):
            obj = json.loads(line)
            assert "trigger" in obj
            assert "severity" in obj
            assert "ts" in obj

    def test_no_log_when_no_suggestions(self, tmp_path):
        checker = _checker(tmp_path)
        checker.check_and_suggest(_base_state())
        log_file = tmp_path / "suggestions.jsonl"
        # No suggestions → no file written (or empty)
        if log_file.exists():
            assert log_file.read_text().strip() == ""

    def test_log_appends_across_calls(self, tmp_path):
        checker = _checker(tmp_path)
        state = _base_state(drawdown_pct=1.6)
        checker.check_and_suggest(state)
        checker.check_and_suggest(state)
        log_file = tmp_path / "suggestions.jsonl"
        lines = [l for l in log_file.read_text().strip().split("\n") if l]
        # Two calls → twice the entries
        assert len(lines) >= 2

    def test_timestamp_is_populated(self, tmp_path):
        checker = _checker(tmp_path)
        state = _base_state(drawdown_pct=1.6)
        suggestions = checker.check_and_suggest(state)
        for s in suggestions:
            assert s.ts != ""


# ── Singleton ────────────────────────────────────────────────────────────────


def test_module_singleton_exists():
    """Module-level state_checker singleton must be importable."""
    assert state_checker is not None
    assert isinstance(state_checker, PortfolioStateChecker)


# ── Suggestion dataclass ─────────────────────────────────────────────────────


def test_suggestion_dataclass_fields():
    s = Suggestion(
        trigger="test_trigger",
        severity=WARNING,
        suggested_action="Do something",
        reasoning="Because of X",
        strategy="btc-15m",
    )
    assert s.trigger == "test_trigger"
    assert s.severity == WARNING
    assert s.strategy == "btc-15m"
    assert s.ts == ""  # default empty, populated by checker


# ── Clean state: no false positives ─────────────────────────────────────────


def test_healthy_state_produces_no_suggestions(tmp_path):
    """A well-behaved portfolio should produce zero suggestions."""
    checker = _checker(tmp_path)
    suggestions = checker.check_and_suggest(_base_state())
    assert suggestions == [], f"Expected no suggestions, got: {[s.trigger for s in suggestions]}"
