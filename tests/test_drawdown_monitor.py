"""Unit tests for scripts.drawdown_monitor metrics and limits."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.drawdown_monitor import (
    BASELINE_DATE,
    compute_strategy_metrics,
    check_limits,
)


# ── compute_strategy_metrics ───────────────────────────────────────────────


def test_metrics_basic(sample_settlements):
    m = compute_strategy_metrics(sample_settlements, "2026-03-12")
    assert m["wins"] == 2
    assert m["losses"] == 1
    assert m["daily_pnl"] == pytest.approx(-4.10, abs=0.01)  # 0.40 - 4.90 + 0.40
    assert m["total_pnl"] == pytest.approx(-4.10, abs=0.01)


def test_metrics_empty():
    m = compute_strategy_metrics({}, "2026-03-12")
    assert m["daily_pnl"] == 0.0
    assert m["wins"] == 0


def test_metrics_filters_before_baseline(sample_settlements_old):
    m = compute_strategy_metrics(sample_settlements_old, "2026-03-12")
    # old settlement (Mar 1) is before BASELINE_DATE (Mar 12)
    assert m["wins"] == 0
    assert m["total_pnl"] == 0.0


def test_metrics_daily_vs_total():
    """Only today's settlements count toward daily_pnl."""
    settlements = {
        "yesterday": {
            "won": True, "pnl": 5.0, "cost": 5.0,
            "timestamp": "2026-03-13T10:00:00Z",
        },
        "today": {
            "won": False, "pnl": -3.0, "cost": 5.0,
            "timestamp": "2026-03-14T10:00:00Z",
        },
    }
    m = compute_strategy_metrics(settlements, "2026-03-14")
    assert m["total_pnl"] == pytest.approx(2.0, abs=0.01)
    assert m["daily_pnl"] == pytest.approx(-3.0, abs=0.01)


def test_metrics_drawdown():
    """Drawdown = peak - current."""
    settlements = {
        "w1": {"won": True, "pnl": 10.0, "cost": 5.0, "timestamp": "2026-03-12T10:00:00Z"},
        "l1": {"won": False, "pnl": -15.0, "cost": 5.0, "timestamp": "2026-03-12T11:00:00Z"},
    }
    m = compute_strategy_metrics(settlements, "2026-03-12")
    assert m["peak_pnl"] == pytest.approx(10.0)
    assert m["total_pnl"] == pytest.approx(-5.0)
    assert m["drawdown"] == pytest.approx(15.0)  # 10 - (-5)


# ── check_limits ───────────────────────────────────────────────────────────


def test_within_limits():
    metrics = {
        "eth-5m": {"daily_pnl": -10.0, "total_pnl": 20.0, "total_cost": 100.0, "peak_pnl": 25.0},
    }
    assert check_limits(metrics, "2026-03-12") is None


def test_portfolio_daily_loss_triggers():
    metrics = {
        "eth-5m": {"daily_pnl": -30.0, "total_pnl": 0.0, "total_cost": 50.0, "peak_pnl": 0.0},
        "xrp-5m": {"daily_pnl": -25.0, "total_pnl": 0.0, "total_cost": 50.0, "peak_pnl": 0.0},
    }
    reason = check_limits(metrics, "2026-03-12")
    assert reason is not None
    assert "PORTFOLIO DAILY LOSS" in reason
