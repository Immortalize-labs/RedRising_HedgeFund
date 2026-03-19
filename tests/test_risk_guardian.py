"""Unit tests for core.risk.guardian.RiskGuardian."""
from __future__ import annotations

from core.risk.guardian import RiskGuardian, RiskLimits

# ── Basic check_trade gates ────────────────────────────────────────────────


def test_trade_allowed_under_limits():
    g = RiskGuardian()
    ok, reason = g.check_trade(100.0, "BUY")
    assert ok is True
    assert reason == "OK"


def test_position_limit_blocks():
    g = RiskGuardian(RiskLimits(max_position_usd=50.0))
    ok, reason = g.check_trade(100.0, "BUY")
    assert ok is False
    assert "Position" in reason


def test_exposure_limit_blocks():
    g = RiskGuardian(RiskLimits(max_exposure_usd=100.0))
    g.state.open_positions = [{"notional": 80.0}]
    ok, reason = g.check_trade(30.0, "BUY")
    assert ok is False
    assert "Exposure" in reason


def test_open_orders_limit_blocks():
    g = RiskGuardian(RiskLimits(max_open_orders=2))
    g.state.open_orders = 2
    ok, reason = g.check_trade(10.0, "BUY")
    assert ok is False
    assert "Open orders" in reason


def test_daily_loss_blocks():
    g = RiskGuardian(RiskLimits(max_daily_loss_usd=50.0))
    g.state.daily_pnl = -60.0
    ok, reason = g.check_trade(10.0, "BUY")
    assert ok is False
    assert "Daily loss" in reason


# ── Kill switch & adverse selection ────────────────────────────────────────


def test_killed_state_blocks_all():
    g = RiskGuardian()
    g.state.killed = True
    ok, reason = g.check_trade(1.0, "BUY")
    assert ok is False
    assert "KILLED" in reason


def test_paused_state_blocks():
    g = RiskGuardian()
    g.state.paused = True
    ok, reason = g.check_trade(1.0, "BUY")
    assert ok is False
    assert "PAUSED" in reason


def test_drawdown_triggers_kill():
    g = RiskGuardian(RiskLimits(max_drawdown_pct=2.0))
    g.state.peak_equity = 1000.0
    g.state.current_equity = 970.0  # 3% drawdown
    ok, reason = g.check_trade(10.0, "BUY")
    assert ok is False
    assert "KILL SWITCH" in reason
    assert g.state.killed is True


def test_adverse_selection_pauses():
    g = RiskGuardian(RiskLimits(adverse_window=5, adverse_min_wr=0.20))
    # 5 consecutive losses = 0% WR
    g.state.recent_fills = [{"won": False}] * 5
    ok, reason = g.check_trade(10.0, "BUY")
    assert ok is False
    assert "ADVERSE" in reason
    assert g.state.paused is True


def test_adverse_selection_not_triggered_with_enough_wins():
    g = RiskGuardian(RiskLimits(adverse_window=5, adverse_min_wr=0.20))
    g.state.recent_fills = [{"won": True}] * 3 + [{"won": False}] * 2
    ok, _ = g.check_trade(10.0, "BUY")
    assert ok is True


# ── Regime scaling ─────────────────────────────────────────────────────────


def test_regime_low_vol():
    g = RiskGuardian()
    assert g.regime_size_multiplier(20.0) == 1.0


def test_regime_high_vol():
    g = RiskGuardian()
    assert g.regime_size_multiplier(100.0) == 0.25


def test_regime_mid_vol():
    g = RiskGuardian()
    mult = g.regime_size_multiplier(65.0)  # midpoint
    assert 0.25 < mult < 1.0


# ── update_fill & reset ───────────────────────────────────────────────────


def test_update_fill_tracks_pnl():
    g = RiskGuardian()
    g.update_fill({"pnl": 10.0, "won": True})
    assert g.state.daily_pnl == 10.0
    assert g.state.current_equity == 10.0
    assert g.state.peak_equity == 10.0


def test_update_fill_caps_recent_fills():
    g = RiskGuardian()
    for i in range(60):
        g.update_fill({"pnl": 0.1, "won": True})
    assert len(g.state.recent_fills) == 50


def test_reset_daily():
    g = RiskGuardian()
    g.state.daily_pnl = -30.0
    g.state.paused = True
    g.reset_daily()
    assert g.state.daily_pnl == 0.0
    assert g.state.paused is False


# ── save_state / load_state round-trip ─────────────────────────────────────


def test_save_load_roundtrip(tmp_path):
    g = RiskGuardian()
    g.state.daily_pnl = -15.5
    g.state.peak_equity = 200.0
    g.state.current_equity = 185.0
    g.state.killed = False
    g.state.recent_fills = [{"pnl": 1.0, "won": True}] * 3

    path = tmp_path / "risk_state.json"
    g.save_state(path)
    assert path.exists()

    g2 = RiskGuardian()
    g2.load_state(path)
    assert g2.state.daily_pnl == -15.5
    assert g2.state.peak_equity == 200.0
    assert g2.state.current_equity == 185.0
    assert len(g2.state.recent_fills) == 3


def test_load_state_missing_file(tmp_path):
    g = RiskGuardian()
    g.load_state(tmp_path / "nonexistent.json")
    assert g.state.daily_pnl == 0.0  # stays at defaults


def test_save_state_atomic(tmp_path):
    """Verify no .tmp file left behind after save."""
    g = RiskGuardian()
    path = tmp_path / "risk_state.json"
    g.save_state(path)
    assert path.exists()
    assert not path.with_suffix(".tmp").exists()
