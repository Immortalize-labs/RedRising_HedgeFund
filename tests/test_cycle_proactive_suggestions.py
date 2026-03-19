"""
Tests for proactive-suggestion wiring in CycleMonitor (core/monitor/cycle.py).

Acceptance criteria:
    AC1  state_checker.check_and_suggest is called at end of each completed cycle
    AC2  portfolio_state dict has correct shape (required keys present)
    AC3  CRITICAL suggestions → logger.error with [ALERT] prefix
    AC4  WARNING suggestions  → logger.warning with [ALERT] prefix
    AC5  INFO suggestions     → logger.info (no exception)
    AC6  Exception inside check_and_suggest is swallowed (never crashes trading loop)
    AC7  _build_portfolio_state reflects guardian equity drawdown correctly
    AC8  _build_portfolio_state is safe when guardian is None
"""
from __future__ import annotations

import logging
import types
from unittest.mock import MagicMock, patch

import core.monitor.cycle as cycle_module
from core.monitor.cycle import CycleMonitor

# ── Helpers ────────────────────────────────────────────────────────────────


def _make_monitor(**kwargs) -> CycleMonitor:
    """Return a minimal CycleMonitor with all external deps mocked out."""
    defaults = dict(
        prediction=None,
        sizing=None,
        risk_gate=MagicMock(),
        executor=MagicMock(),
        slug_prefix="btc-updown-15m",
        window_seconds=900,
        min_remaining_s=60,
        asset="BTC",
        interval="15m",
        price_field="btc_price",
        min_confidence_prob=0.52,
    )
    defaults.update(kwargs)
    monitor = CycleMonitor(**defaults)
    # Default cycle state
    monitor.state = {
        "total_trades": 10,
        "fills": 7,
        "cancels": 1,
        "pnl": 12.5,
        "last_trade_time": "2026-03-19T08:00:00-05:00",
    }
    return monitor


def _make_guardian_state(
    peak_equity: float = 100.0,
    current_equity: float = 98.0,
    daily_pnl: float = -5.0,
    recent_fills: list | None = None,
):
    state = types.SimpleNamespace(
        peak_equity=peak_equity,
        current_equity=current_equity,
        daily_pnl=daily_pnl,
        recent_fills=recent_fills if recent_fills is not None else [],
        open_positions=[],
        open_orders=0,
        killed=False,
        paused=False,
    )
    return state


def _attach_guardian(monitor: CycleMonitor, gstate=None) -> MagicMock:
    guardian = MagicMock()
    guardian.state = gstate or _make_guardian_state()
    monitor.risk_gate.guardian = guardian
    return guardian


# ── AC1: state_checker called once per completed cycle ─────────────────────


class TestStateCheckerCalledEachCycle:
    def test_check_and_suggest_called_after_successful_trade(self):
        monitor = _make_monitor()
        _attach_guardian(monitor)

        mock_suggestions = []
        with patch.object(cycle_module._state_checker, "check_and_suggest", return_value=mock_suggestions) as mock_check:
            monitor._run_proactive_checks()
        mock_check.assert_called_once()

    def test_check_and_suggest_called_with_dict_argument(self):
        monitor = _make_monitor()
        _attach_guardian(monitor)

        captured = {}

        def capture(state):
            captured["state"] = state
            return []

        with patch.object(cycle_module._state_checker, "check_and_suggest", side_effect=capture):
            monitor._run_proactive_checks()

        assert "state" in captured
        assert isinstance(captured["state"], dict)


# ── AC2: portfolio_state shape ─────────────────────────────────────────────


class TestPortfolioStateShape:
    def test_required_top_level_keys_present(self):
        monitor = _make_monitor()
        _attach_guardian(monitor)
        state = monitor._build_portfolio_state()
        assert "drawdown_pct" in state
        assert "strategies" in state

    def test_strategies_keyed_by_strategy_name(self):
        monitor = _make_monitor()
        monitor.executor.strategy_name = "btc-15m"
        _attach_guardian(monitor)
        state = monitor._build_portfolio_state()
        assert "btc-15m" in state["strategies"]

    def test_strategy_info_has_fill_rate(self):
        monitor = _make_monitor()
        _attach_guardian(monitor)
        state = monitor._build_portfolio_state()
        strat = next(iter(state["strategies"].values()))
        assert "fill_rate" in strat

    def test_fill_rate_computed_correctly(self):
        monitor = _make_monitor()
        monitor.state["total_trades"] = 20
        monitor.state["fills"] = 16
        _attach_guardian(monitor)
        state = monitor._build_portfolio_state()
        strat = next(iter(state["strategies"].values()))
        assert abs(strat["fill_rate"] - 0.8) < 1e-9

    def test_last_trade_ts_parsed_from_iso_string(self):
        monitor = _make_monitor()
        monitor.state["last_trade_time"] = "2026-03-19T08:00:00-05:00"
        _attach_guardian(monitor)
        state = monitor._build_portfolio_state()
        assert state["last_trade_ts"] is not None
        assert isinstance(state["last_trade_ts"], float)
        assert state["last_trade_ts"] > 0

    def test_direction_from_last_signal(self):
        monitor = _make_monitor()
        sig = MagicMock()
        sig.prediction = "UP"
        monitor._last_signal = sig
        _attach_guardian(monitor)
        state = monitor._build_portfolio_state()
        strat = next(iter(state["strategies"].values()))
        assert strat["direction"] == "UP"

    def test_recent_trades_from_guardian(self):
        monitor = _make_monitor()
        fills = [{"won": True}, {"won": False}, {"won": True}]
        _attach_guardian(monitor, _make_guardian_state(recent_fills=fills))
        state = monitor._build_portfolio_state()
        strat = next(iter(state["strategies"].values()))
        assert strat["recent_trades"] == fills

    def test_daily_pnl_from_guardian(self):
        monitor = _make_monitor()
        _attach_guardian(monitor, _make_guardian_state(daily_pnl=-18.0))
        state = monitor._build_portfolio_state()
        strat = next(iter(state["strategies"].values()))
        assert strat["daily_pnl"] == -18.0

    def test_backtest_win_rate_not_present(self):
        """backtest_win_rate is not available in cycle state — must be omitted."""
        monitor = _make_monitor()
        _attach_guardian(monitor)
        state = monitor._build_portfolio_state()
        strat = next(iter(state["strategies"].values()))
        assert "backtest_win_rate" not in strat


# ── AC7: drawdown computed from guardian equity ────────────────────────────


class TestDrawdownComputation:
    def test_drawdown_pct_correct(self):
        monitor = _make_monitor()
        # peak=100, current=98 → 2% drawdown
        _attach_guardian(monitor, _make_guardian_state(peak_equity=100.0, current_equity=98.0))
        state = monitor._build_portfolio_state()
        assert abs(state["drawdown_pct"] - 2.0) < 0.01

    def test_drawdown_zero_when_at_peak(self):
        monitor = _make_monitor()
        _attach_guardian(monitor, _make_guardian_state(peak_equity=100.0, current_equity=100.0))
        state = monitor._build_portfolio_state()
        assert state["drawdown_pct"] == 0.0

    def test_drawdown_zero_when_peak_is_zero(self):
        """No peak recorded yet — drawdown should default to 0."""
        monitor = _make_monitor()
        _attach_guardian(monitor, _make_guardian_state(peak_equity=0.0, current_equity=0.0))
        state = monitor._build_portfolio_state()
        assert state["drawdown_pct"] == 0.0


# ── AC8: guardian is None ──────────────────────────────────────────────────


class TestGuardianNone:
    def test_build_state_safe_when_guardian_is_none(self):
        monitor = _make_monitor()
        monitor.risk_gate.guardian = None
        state = monitor._build_portfolio_state()
        assert "drawdown_pct" in state
        assert state["drawdown_pct"] == 0.0

    def test_strategy_info_omits_win_rate_when_guardian_none(self):
        monitor = _make_monitor()
        monitor.risk_gate.guardian = None
        state = monitor._build_portfolio_state()
        strat = next(iter(state["strategies"].values()))
        # win_rate only set when guardian provides recent_fills
        assert strat.get("win_rate") is None or "win_rate" not in strat


# ── AC3: CRITICAL → logger.error with [ALERT] prefix ──────────────────────


class TestCriticalAlert:
    def test_critical_suggestion_logs_at_error_level(self, caplog):
        from core.risk.proactive_suggestions import CRITICAL, Suggestion

        monitor = _make_monitor()
        _attach_guardian(monitor)

        critical_suggestion = Suggestion(
            trigger="drawdown_critical",
            severity=CRITICAL,
            suggested_action="Halt all trading.",
            reasoning="Drawdown 2.5%",
            strategy="btc-15m",
            ts="2026-03-19T08:00:00-05:00",
        )

        with patch.object(cycle_module._state_checker, "check_and_suggest", return_value=[critical_suggestion]):
            with caplog.at_level(logging.ERROR, logger="core.monitor.cycle"):
                monitor._run_proactive_checks()

        error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert error_records, "Expected at least one ERROR log for CRITICAL suggestion"
        assert any("[ALERT]" in r.message for r in error_records)

    def test_critical_message_contains_trigger(self, caplog):
        from core.risk.proactive_suggestions import CRITICAL, Suggestion

        monitor = _make_monitor()
        _attach_guardian(monitor)

        s = Suggestion(
            trigger="adverse_selection",
            severity=CRITICAL,
            suggested_action="Activate kill switch.",
            reasoning="WR 10%",
            strategy="btc-15m",
            ts="2026-03-19T08:00:00-05:00",
        )

        with patch.object(cycle_module._state_checker, "check_and_suggest", return_value=[s]):
            with caplog.at_level(logging.ERROR, logger="core.monitor.cycle"):
                monitor._run_proactive_checks()

        error_msgs = [r.message for r in caplog.records if r.levelno == logging.ERROR]
        assert any("adverse_selection" in m for m in error_msgs)


# ── AC4: WARNING → logger.warning with [ALERT] prefix ─────────────────────


class TestWarningAlert:
    def test_warning_suggestion_logs_at_warning_level(self, caplog):
        from core.risk.proactive_suggestions import WARNING, Suggestion

        monitor = _make_monitor()
        _attach_guardian(monitor)

        w = Suggestion(
            trigger="fill_rate_low",
            severity=WARNING,
            suggested_action="Adjust escalation timing.",
            reasoning="Fill rate 65%",
            strategy="btc-15m",
            ts="2026-03-19T08:00:00-05:00",
        )

        with patch.object(cycle_module._state_checker, "check_and_suggest", return_value=[w]):
            with caplog.at_level(logging.WARNING, logger="core.monitor.cycle"):
                monitor._run_proactive_checks()

        warn_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert warn_records, "Expected at least one WARNING log"
        assert any("[ALERT]" in r.message for r in warn_records)


# ── AC5: INFO suggestion → logger.info ─────────────────────────────────────


class TestInfoAlert:
    def test_info_suggestion_logs_at_info_level(self, caplog):
        from core.risk.proactive_suggestions import INFO, Suggestion

        monitor = _make_monitor()
        _attach_guardian(monitor)

        info_s = Suggestion(
            trigger="all_positions_correlated",
            severity=INFO,
            suggested_action="Review portfolio correlation.",
            reasoning="All positions UP.",
            strategy="",
            ts="2026-03-19T08:00:00-05:00",
        )

        with patch.object(cycle_module._state_checker, "check_and_suggest", return_value=[info_s]):
            with caplog.at_level(logging.INFO, logger="core.monitor.cycle"):
                monitor._run_proactive_checks()

        info_records = [r for r in caplog.records if r.levelno == logging.INFO]
        assert info_records, "Expected at least one INFO log"


# ── AC6: Exception in check_and_suggest is swallowed ──────────────────────


class TestExceptionSafety:
    def test_exception_does_not_propagate(self):
        monitor = _make_monitor()
        _attach_guardian(monitor)

        with patch.object(
            cycle_module._state_checker,
            "check_and_suggest",
            side_effect=RuntimeError("simulated check failure"),
        ):
            # Must not raise
            monitor._run_proactive_checks()

    def test_exception_logs_warning_not_error(self, caplog):
        monitor = _make_monitor()
        _attach_guardian(monitor)

        with patch.object(
            cycle_module._state_checker,
            "check_and_suggest",
            side_effect=RuntimeError("boom"),
        ):
            with caplog.at_level(logging.WARNING, logger="core.monitor.cycle"):
                monitor._run_proactive_checks()

        warn_msgs = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert any("non-fatal" in m or "proactive_check" in m for m in warn_msgs)


# ── No suggestions → no error logs ─────────────────────────────────────────


class TestNoFalseAlerts:
    def test_no_logs_when_no_suggestions(self, caplog):
        monitor = _make_monitor()
        _attach_guardian(monitor)

        with patch.object(cycle_module._state_checker, "check_and_suggest", return_value=[]):
            with caplog.at_level(logging.WARNING, logger="core.monitor.cycle"):
                monitor._run_proactive_checks()

        warn_or_error = [
            r for r in caplog.records
            if r.levelno >= logging.WARNING and "ALERT" in r.message
        ]
        assert warn_or_error == [], f"Expected no alerts, got: {[r.message for r in warn_or_error]}"
