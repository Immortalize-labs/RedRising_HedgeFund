"""
Tests for Investigation Freeze module.
=======================================
Tests the FreezeManager (and module-level freeze_manager singleton) lifecycle:
  - freeze() / unfreeze() lifecycle
  - block_trade() counter increment
  - is_frozen() state transitions
  - auto_freeze_on_misalignment() trigger conditions
  - auto_freeze_on_error() trigger
  - Already-frozen guard (no double-freeze)
  - Unfreeze returns None when not frozen
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from core.risk.investigation_freeze import FreezeManager, FreezeRecord


# ─── Helpers ─────────────────────────────────────────────────────────────────

def make_manager(tmp_path: Path) -> FreezeManager:
    """Fresh FreezeManager with tmp log path for each test."""
    return FreezeManager(log_path=tmp_path / "freeze_log.jsonl")


# ─── Freeze / Unfreeze Lifecycle ─────────────────────────────────────────────

class TestFreezeUnfreezeCycle:
    def test_freeze_creates_record(self, tmp_path):
        mgr = make_manager(tmp_path)
        rec = mgr.freeze("btc-15m", reason="test reason")
        assert isinstance(rec, FreezeRecord)
        assert rec.strategy == "btc-15m"
        assert rec.reason == "test reason"
        assert rec.frozen_at != ""
        assert rec.unfrozen_at == ""
        assert rec.trades_blocked == 0

    def test_is_frozen_true_after_freeze(self, tmp_path):
        mgr = make_manager(tmp_path)
        assert not mgr.is_frozen("btc-15m")
        mgr.freeze("btc-15m", reason="x")
        assert mgr.is_frozen("btc-15m")

    def test_is_frozen_false_after_unfreeze(self, tmp_path):
        mgr = make_manager(tmp_path)
        mgr.freeze("btc-15m", reason="x")
        mgr.unfreeze("btc-15m", resolution="fixed")
        assert not mgr.is_frozen("btc-15m")

    def test_unfreeze_completes_record(self, tmp_path):
        mgr = make_manager(tmp_path)
        mgr.freeze("eth-15m", reason="misalignment")
        time.sleep(0.05)  # ensure nonzero duration
        rec = mgr.unfreeze("eth-15m", resolution="cache cleared")
        assert rec is not None
        assert rec.unfrozen_at != ""
        assert rec.resolution == "cache cleared"
        assert rec.duration_minutes >= 0.0

    def test_unfreeze_nonexistent_returns_none(self, tmp_path):
        mgr = make_manager(tmp_path)
        result = mgr.unfreeze("nonexistent")
        assert result is None

    def test_multiple_strategies_independent(self, tmp_path):
        mgr = make_manager(tmp_path)
        mgr.freeze("btc-15m", reason="a")
        mgr.freeze("eth-15m", reason="b")
        assert mgr.is_frozen("btc-15m")
        assert mgr.is_frozen("eth-15m")
        mgr.unfreeze("btc-15m")
        assert not mgr.is_frozen("btc-15m")
        assert mgr.is_frozen("eth-15m")  # unaffected

    def test_get_frozen_returns_current_frozen(self, tmp_path):
        mgr = make_manager(tmp_path)
        mgr.freeze("xrp-15m", reason="x")
        mgr.freeze("sol-15m", reason="y")
        frozen = mgr.get_frozen()
        assert "xrp-15m" in frozen
        assert "sol-15m" in frozen
        assert len(frozen) == 2


# ─── block_trade() Counter ────────────────────────────────────────────────────

class TestBlockTrade:
    def test_block_trade_returns_false_when_not_frozen(self, tmp_path):
        mgr = make_manager(tmp_path)
        result = mgr.block_trade("btc-15m")
        assert result is False

    def test_block_trade_returns_true_when_frozen(self, tmp_path):
        mgr = make_manager(tmp_path)
        mgr.freeze("btc-15m", reason="test")
        result = mgr.block_trade("btc-15m")
        assert result is True

    def test_block_trade_increments_counter(self, tmp_path):
        mgr = make_manager(tmp_path)
        mgr.freeze("btc-15m", reason="test")
        mgr.block_trade("btc-15m")
        mgr.block_trade("btc-15m")
        mgr.block_trade("btc-15m")
        assert mgr._frozen["btc-15m"].trades_blocked == 3

    def test_block_trade_counter_zero_before_any_block(self, tmp_path):
        mgr = make_manager(tmp_path)
        mgr.freeze("eth-15m", reason="x")
        assert mgr._frozen["eth-15m"].trades_blocked == 0

    def test_block_trade_no_increment_when_not_frozen(self, tmp_path):
        mgr = make_manager(tmp_path)
        # 5 calls on unfrozen strategy — no error, no side effects
        for _ in range(5):
            assert mgr.block_trade("sol-15m") is False


# ─── auto_freeze_on_misalignment() ───────────────────────────────────────────

class TestAutoFreezeOnMisalignment:
    def test_aligned_returns_none(self, tmp_path):
        mgr = make_manager(tmp_path)
        result = mgr.auto_freeze_on_misalignment("btc-15m", "UP", "UP")
        assert result is None
        assert not mgr.is_frozen("btc-15m")

    def test_misalignment_freezes(self, tmp_path):
        mgr = make_manager(tmp_path)
        result = mgr.auto_freeze_on_misalignment("btc-15m", "UP", "DOWN")
        assert result is not None
        assert isinstance(result, FreezeRecord)
        assert mgr.is_frozen("btc-15m")

    def test_misalignment_reason_contains_directions(self, tmp_path):
        mgr = make_manager(tmp_path)
        rec = mgr.auto_freeze_on_misalignment("eth-15m", "DOWN", "UP")
        assert "DOWN" in rec.reason
        assert "UP" in rec.reason

    def test_already_frozen_skips_double_freeze(self, tmp_path):
        mgr = make_manager(tmp_path)
        mgr.freeze("btc-15m", reason="manual freeze")
        result = mgr.auto_freeze_on_misalignment("btc-15m", "UP", "DOWN")
        # Already frozen — should return None (no second freeze record)
        assert result is None
        # Still frozen, original reason intact
        assert mgr.is_frozen("btc-15m")
        assert "manual freeze" in mgr._frozen["btc-15m"].reason

    def test_down_up_mismatch_triggers(self, tmp_path):
        mgr = make_manager(tmp_path)
        result = mgr.auto_freeze_on_misalignment("xrp-15m", "DOWN", "UP")
        assert result is not None
        assert mgr.is_frozen("xrp-15m")

    def test_unfreeze_after_misalignment_freeze(self, tmp_path):
        mgr = make_manager(tmp_path)
        mgr.auto_freeze_on_misalignment("sol-15m", "UP", "DOWN")
        assert mgr.is_frozen("sol-15m")
        mgr.unfreeze("sol-15m", resolution="alignment fixed")
        assert not mgr.is_frozen("sol-15m")


# ─── auto_freeze_on_error() ──────────────────────────────────────────────────

class TestAutoFreezeOnError:
    def test_error_freezes_strategy(self, tmp_path):
        mgr = make_manager(tmp_path)
        rec = mgr.auto_freeze_on_error("bnb-15m", "API timeout after 10s")
        assert isinstance(rec, FreezeRecord)
        assert mgr.is_frozen("bnb-15m")

    def test_error_reason_contains_message(self, tmp_path):
        mgr = make_manager(tmp_path)
        error_msg = "Connection refused: clob.polymarket.com:443"
        rec = mgr.auto_freeze_on_error("doge-15m", error_msg)
        assert error_msg in rec.reason

    def test_error_freeze_blockable(self, tmp_path):
        mgr = make_manager(tmp_path)
        mgr.auto_freeze_on_error("hype-15m", "order rejected")
        assert mgr.block_trade("hype-15m") is True

    def test_error_freeze_then_unfreeze(self, tmp_path):
        mgr = make_manager(tmp_path)
        mgr.auto_freeze_on_error("btc-15m", "500 Internal Server Error")
        assert mgr.is_frozen("btc-15m")
        mgr.unfreeze("btc-15m", resolution="API recovered")
        assert not mgr.is_frozen("btc-15m")


# ─── Log File ────────────────────────────────────────────────────────────────

class TestLogFile:
    def test_freeze_writes_to_log(self, tmp_path):
        log_path = tmp_path / "freeze_log.jsonl"
        mgr = FreezeManager(log_path=log_path)
        mgr.freeze("btc-15m", reason="log test")
        assert log_path.exists()
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["event"] == "freeze"
        assert entry["strategy"] == "btc-15m"

    def test_unfreeze_appends_to_log(self, tmp_path):
        log_path = tmp_path / "freeze_log.jsonl"
        mgr = FreezeManager(log_path=log_path)
        mgr.freeze("eth-15m", reason="x")
        mgr.unfreeze("eth-15m", resolution="y")
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 2
        events = [json.loads(l)["event"] for l in lines]
        assert events == ["freeze", "unfreeze"]

    def test_log_directory_created(self, tmp_path):
        nested = tmp_path / "deep" / "path" / "freeze_log.jsonl"
        mgr = FreezeManager(log_path=nested)
        mgr.freeze("xrp-15m", reason="test dir creation")
        assert nested.exists()


# ─── Status Output ───────────────────────────────────────────────────────────

class TestStatus:
    def test_status_no_frozen(self, tmp_path):
        mgr = make_manager(tmp_path)
        status = mgr.status()
        assert "No strategies frozen" in status

    def test_status_shows_frozen_strategy(self, tmp_path):
        mgr = make_manager(tmp_path)
        mgr.freeze("btc-15m", reason="alignment mismatch")
        status = mgr.status()
        assert "btc-15m" in status
        assert "alignment mismatch" in status
