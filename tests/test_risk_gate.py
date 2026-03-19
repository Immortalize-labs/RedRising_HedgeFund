"""Tests for core/risk/gate.py — RiskGate wrapping RiskGuardian."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from core.risk.gate import RiskGate, Verdict
from core.risk.guardian import RiskGuardian


class TestVerdict:
    def test_allowed(self):
        v = Verdict(allowed=True, reason="passed", gate="none")
        assert v.allowed is True

    def test_blocked(self):
        v = Verdict(allowed=False, reason="daily_loss", gate="guardian")
        assert v.allowed is False


class TestRiskGateKillFile:
    def test_no_kill_file(self, tmp_path):
        gate = RiskGate(kill_file_path=tmp_path / "RISK_KILL")
        assert gate.check_kill_file() is None

    def test_kill_file_present(self, tmp_path):
        kf = tmp_path / "RISK_KILL"
        kf.write_text("manual halt")
        gate = RiskGate(kill_file_path=kf)
        v = gate.check_kill_file()
        assert v is not None
        assert v.allowed is False
        assert "manual halt" in v.reason
        assert v.gate == "kill_file"


class TestRiskGateCheckTrade:
    def test_passed_no_guardian(self):
        gate = RiskGate(guardian=None)
        v = gate.check_trade(10.0, "UP")
        assert v.allowed is True

    def test_passed_with_guardian(self):
        g = RiskGuardian()
        g.state.current_equity = 100.0
        g.state.peak_equity = 100.0
        gate = RiskGate(guardian=g)
        v = gate.check_trade(10.0, "UP")
        assert v.allowed is True

    def test_blocked_by_guardian_killed(self):
        g = RiskGuardian()
        g.state.killed = True
        gate = RiskGate(guardian=g)
        v = gate.check_trade(10.0, "UP")
        assert v.allowed is False
        assert v.gate == "guardian"

    def test_blocked_by_balance(self):
        gate = RiskGate(guardian=None)
        v = gate.check_trade(10.0, "UP", balance=5.0)
        assert v.allowed is False
        assert v.gate == "balance"

    def test_kill_file_blocks_before_guardian(self, tmp_path):
        kf = tmp_path / "RISK_KILL"
        kf.write_text("halt")
        g = RiskGuardian()
        gate = RiskGate(guardian=g, kill_file_path=kf)
        v = gate.check_trade(10.0, "UP")
        assert v.gate == "kill_file"


class TestRiskGatePMVeto:
    def test_pm_unavailable(self):
        gate = RiskGate(pm_veto_mode="live")
        v = gate.check_pm_veto("UP", {"yes_price": None})
        assert v.allowed is True

    def test_pm_agrees(self):
        gate = RiskGate(pm_veto_mode="live", pm_disagree_thr=0.02)
        v = gate.check_pm_veto("UP", {"yes_price": 0.55, "no_price": 0.45, "remaining_sec": 200})
        assert v.allowed is True
        assert "pm_agrees" in v.reason

    def test_pm_disagrees(self):
        gate = RiskGate(pm_veto_mode="live", pm_disagree_thr=0.02)
        v = gate.check_pm_veto("DOWN", {"yes_price": 0.55, "no_price": 0.45, "remaining_sec": 200})
        assert v.allowed is False
        assert v.gate == "pm_veto"

    def test_pm_neutral(self):
        gate = RiskGate(pm_veto_mode="live", pm_disagree_thr=0.02)
        v = gate.check_pm_veto("UP", {"yes_price": 0.50, "no_price": 0.50, "remaining_sec": 200})
        assert v.allowed is True
        assert "pm_neutral" in v.reason


class TestRiskGateOpenOrders:
    def test_update_open_orders(self):
        g = RiskGuardian()
        gate = RiskGate(guardian=g)
        gate.update_open_orders(+1)
        assert g.state.open_orders == 1
        gate.update_open_orders(-1)
        assert g.state.open_orders == 0
        gate.update_open_orders(-1)
        assert g.state.open_orders == 0  # clamp to 0
