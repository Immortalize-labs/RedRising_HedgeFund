"""Unit tests for agents.live.alignment_checker.AlignmentChecker."""
from __future__ import annotations

import time

from agents.live.alignment_checker import AlignmentChecker


def _order(side: str = "UP", age_s: float = 10.0) -> dict:
    return {"side": side, "placed_at": time.time() - age_s}


def test_no_pending_order():
    ac = AlignmentChecker()
    result = ac.check({}, {"prediction": "UP"}, None)
    assert result["aligned"] is True
    assert result["reason"] == "no_pending_order"


def test_no_signal():
    ac = AlignmentChecker()
    result = ac.check({}, None, _order("UP"))
    assert result["aligned"] is True
    assert result["reason"] == "no_signal"


def test_signal_matches_order():
    ac = AlignmentChecker()
    result = ac.check({}, {"prediction": "UP"}, _order("UP"))
    assert result["aligned"] is True
    assert result["reason"] == "signal_matches_order"


def test_signal_misaligned():
    ac = AlignmentChecker()
    result = ac.check({}, {"prediction": "DOWN"}, _order("UP"))
    assert result["aligned"] is False
    assert "signal=DOWN" in result["reason"]
    assert "order=UP" in result["reason"]


def test_stale_order_returns_aligned():
    ac = AlignmentChecker(max_age_s=60.0)
    old_order = {"side": "UP", "placed_at": time.time() - 120.0}
    result = ac.check({}, {"prediction": "DOWN"}, old_order)
    assert result["aligned"] is True
    assert "stale_order" in result["reason"]


def test_cycle_skip():
    ac = AlignmentChecker(check_every_n_cycles=3)
    # Cycles 1, 2 should skip; cycle 3 should check
    r1 = ac.check({}, {"prediction": "DOWN"}, _order("UP"))
    assert r1["aligned"] is True  # cycle 1: skip
    r2 = ac.check({}, {"prediction": "DOWN"}, _order("UP"))
    assert r2["aligned"] is True  # cycle 2: skip
    r3 = ac.check({}, {"prediction": "DOWN"}, _order("UP"))
    assert r3["aligned"] is False  # cycle 3: actual check


def test_missing_direction_data():
    ac = AlignmentChecker()
    result = ac.check({}, {"prediction": ""}, _order("UP"))
    assert result["aligned"] is True
    assert result["reason"] == "missing_direction_data"


def test_case_insensitive():
    ac = AlignmentChecker()
    result = ac.check({}, {"prediction": "up"}, _order("UP"))
    assert result["aligned"] is True
