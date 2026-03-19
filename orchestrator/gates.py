"""
Promotion Gates
===============
Threshold checks that determine whether a strategy advances.
Returns (pass/fail, reason_dict).
"""
from __future__ import annotations

from typing import Any

# Thresholds from config/risk_policy.yaml (Immortalize Labs, proven)
RESEARCH_THRESHOLDS = {
    "min_passing_signals": 3,
    "min_abs_ic": 0.01,
    "max_perm_pvalue": 0.05,
    "max_stability_delta": 0.02,
}

BACKTEST_THRESHOLDS = {
    "min_oos_sharpe": 0.5,
    "min_oos_days": 30,
    "min_decay_ratio": 0.3,
    "max_drawdown_pct": 5.0,
    "min_trades": 50,
    "min_calmar": 1.0,
    "max_turnover_daily": 10.0,
}

DEPLOYMENT_THRESHOLDS = {
    "max_slippage_delta_bps": 2.0,
    "min_fill_rate": 0.80,
    "max_risk_incidents": 0,
    "min_paper_days": 7,
}

MONITOR_THRESHOLDS = {
    "max_drawdown_live_pct": 2.0,
    "max_daily_loss_usd": 50.0,
    "adverse_selection_window": 10,
    "adverse_selection_min_win_rate": 0.20,
}


def research_gate(state: dict[str, Any]) -> tuple[str, dict]:
    """Check if validated signals are sufficient to proceed to backtest."""
    signals = state.get("validated_signals", [])
    real = [s for s in signals if s.get("verdict") == "REAL"]
    strong = [s for s in real if abs(s.get("ic", 0)) > RESEARCH_THRESHOLDS["min_abs_ic"]]

    passed = len(real) >= RESEARCH_THRESHOLDS["min_passing_signals"] and len(strong) >= 1
    return ("pass" if passed else "fail", {
        "real_signals": len(real),
        "strong_signals": len(strong),
        "required": RESEARCH_THRESHOLDS["min_passing_signals"],
    })


def backtest_gate(state: dict[str, Any]) -> tuple[str, dict]:
    """Check if backtest metrics meet promotion thresholds."""
    wf = state.get("walkforward_metrics", {})
    bt = state.get("backtest_metrics", {})
    t = BACKTEST_THRESHOLDS

    checks = {
        "oos_sharpe": wf.get("oos_sharpe", 0) >= t["min_oos_sharpe"],
        "oos_days": wf.get("oos_days", 0) >= t["min_oos_days"],
        "decay_ratio": wf.get("decay_ratio", 0) >= t["min_decay_ratio"],
        "max_drawdown": bt.get("max_drawdown_pct", 100) <= t["max_drawdown_pct"],
        "trade_count": bt.get("n_trades", 0) >= t["min_trades"],
        "calmar": bt.get("calmar", 0) >= t["min_calmar"],
    }
    passed = all(checks.values())
    return ("pass" if passed else "fail", checks)


def deployment_gate(state: dict[str, Any]) -> tuple[str, dict]:
    """Check if paper trading results warrant live deployment."""
    pm = state.get("paper_metrics", {})
    t = DEPLOYMENT_THRESHOLDS

    checks = {
        "slippage_ok": pm.get("slippage_delta_bps", 999) <= t["max_slippage_delta_bps"],
        "fill_rate_ok": pm.get("fill_rate", 0) >= t["min_fill_rate"],
        "risk_incidents": pm.get("risk_incidents", 999) <= t["max_risk_incidents"],
        "paper_days": pm.get("paper_days", 0) >= t["min_paper_days"],
    }
    passed = all(checks.values())
    return ("go_live" if passed else "reject", checks)


def monitor_check(state: dict[str, Any]) -> tuple[str, dict]:
    """Runtime health check for live strategies."""
    lm = state.get("live_metrics", {})
    t = MONITOR_THRESHOLDS

    alerts = {}
    if lm.get("drawdown_pct", 0) > t["max_drawdown_live_pct"]:
        alerts["drawdown"] = lm["drawdown_pct"]
    if lm.get("daily_pnl", 0) < -t["max_daily_loss_usd"]:
        alerts["daily_loss"] = lm["daily_pnl"]

    recent = lm.get("recent_fills", [])
    if len(recent) >= t["adverse_selection_window"]:
        wins = sum(1 for f in recent[-t["adverse_selection_window"]:] if f.get("won"))
        wr = wins / t["adverse_selection_window"]
        if wr < t["adverse_selection_min_win_rate"]:
            alerts["adverse_selection"] = wr

    status = "alert" if alerts else "healthy"
    return (status, alerts)
