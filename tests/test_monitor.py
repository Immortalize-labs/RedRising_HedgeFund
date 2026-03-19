"""Tests for core/monitor/cycle.py — CycleMonitor and find_market."""
from __future__ import annotations

import pytest

from core.monitor.cycle import CycleMonitor


class TestCycleMonitorInit:
    """Verify CycleMonitor can be constructed with module dependencies."""

    def test_construction(self):
        """Smoke test: CycleMonitor accepts all required params."""
        # We use None/mock objects since we're only testing construction
        monitor = CycleMonitor(
            prediction=None,
            sizing=None,
            risk_gate=None,
            executor=None,
            slug_prefix="btc-updown-5m",
            window_seconds=300,
            min_remaining_s=90,
            asset="BTC",
            interval="5m",
            price_field="btc_price",
            min_confidence_prob=0.52,
        )
        assert monitor.running is True
        assert monitor.last_traded_epoch == 0
        assert monitor.state["total_trades"] == 0

    def test_state_persistence_path(self, tmp_path):
        monitor = CycleMonitor(
            prediction=None, sizing=None, risk_gate=None, executor=None,
            slug_prefix="test", window_seconds=300, min_remaining_s=90,
            asset="BTC", interval="5m", price_field="btc_price",
            min_confidence_prob=0.52,
            state_path=tmp_path / "state.json",
        )
        monitor.state["total_trades"] = 42
        monitor._save_state()
        assert (tmp_path / "state.json").exists()
