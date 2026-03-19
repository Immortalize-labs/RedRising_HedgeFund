"""Shared test fixtures for Claude HF test suite."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def project_root():
    return PROJECT_ROOT


@pytest.fixture
def sample_settlements():
    """Fake settlement data for drawdown/risk tests."""
    return {
        "m1": {
            "won": True, "pnl": 0.40, "cost": 5.0,
            "timestamp": "2026-03-12T10:00:00Z",
        },
        "m2": {
            "won": False, "pnl": -4.90, "cost": 5.0,
            "timestamp": "2026-03-12T11:00:00Z",
        },
        "m3": {
            "won": True, "pnl": 0.40, "cost": 5.0,
            "timestamp": "2026-03-12T12:00:00Z",
        },
    }


@pytest.fixture
def sample_settlements_old():
    """Settlements before BASELINE_DATE — should be filtered out."""
    return {
        "old1": {
            "won": True, "pnl": 10.0, "cost": 5.0,
            "timestamp": "2026-03-01T10:00:00Z",
        },
    }
