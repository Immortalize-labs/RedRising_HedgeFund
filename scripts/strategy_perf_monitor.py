"""
Strategy Performance Monitor
============================
CI-based kill switch using Wilson score intervals.

Uses Wilson confidence intervals — not naive WR — to avoid false kills
in small sample sizes (e.g., ETH-15m at 44% over 50 trades was NOT broken).

Usage::

    wilson_ci(22, 50)  -> (0.310, 0.578)
    load_baseline_wr("ETHXGB15M01")  -> 0.607

    lower, upper = wilson_ci(wins, total)
    kill_line = baseline_wr - KILL_MARGIN_PP / 100
    if n >= MIN_TRADES_FOR_KILL and upper < kill_line:
        kill_strategy(...)
"""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path

logger = logging.getLogger(__name__)

# Kill decision parameters
MIN_TRADES_FOR_KILL = 30       # do not kill on fewer than this many trades
DEFAULT_BASELINE_WR = 0.55    # fallback if no gate file exists
KILL_MARGIN_PP = 5.0          # pp margin below baseline WR before killing (5pp = 0.05)

# Wilson CI confidence level
_Z = 1.96   # 95% confidence

# Project root (patchable in tests)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def wilson_ci(wins: int, n: int, z: float = _Z) -> tuple[float, float]:
    """
    Wilson score confidence interval for a binomial proportion.

    Args:
        wins: Number of successes.
        n:    Total trials.
        z:    Z-score for desired confidence level (default 1.96 = 95%).

    Returns:
        (lower, upper) confidence interval bounds in [0, 1].
    """
    if n == 0:
        return 0.0, 1.0

    p = wins / n
    z2 = z * z
    denom = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    margin = (z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))) / denom
    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)
    return lower, upper


def load_baseline_wr(strategy_id: str) -> float:
    """
    Load baseline win rate from gate files.

    Checks in order:
      1. data/gates/<strategy_id>_fix.json  -> backtest_after.wr
      2. data/gates/<strategy_id>_launch.json -> backtest.oos_wr
      3. Falls back to DEFAULT_BASELINE_WR

    WR stored as percentage (e.g., 60.7) is converted to fraction (0.607).
    WR already as fraction (<= 1.0) is returned as-is.

    Args:
        strategy_id: Strategy identifier, e.g. "ETHXGB15M01"

    Returns:
        Baseline WR as fraction [0, 1].
    """
    gates_dir = PROJECT_ROOT / "data" / "gates"

    # 1. Fix gate
    fix_path = gates_dir / f"{strategy_id}_fix.json"
    if fix_path.exists():
        try:
            data = json.loads(fix_path.read_text())
            wr_raw = data.get("backtest_after", {}).get("wr")
            if wr_raw is not None:
                return _normalise_wr(float(wr_raw))
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Could not read fix gate %s: %s", fix_path, e)

    # 2. Launch gate
    launch_path = gates_dir / f"{strategy_id}_launch.json"
    if launch_path.exists():
        try:
            data = json.loads(launch_path.read_text())
            wr_raw = data.get("backtest", {}).get("oos_wr")
            if wr_raw is not None:
                return _normalise_wr(float(wr_raw))
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Could not read launch gate %s: %s", launch_path, e)

    return DEFAULT_BASELINE_WR


def _normalise_wr(wr: float) -> float:
    """Convert WR to fraction. Values > 1 are treated as percentages."""
    if wr > 1.0:
        return wr / 100.0
    return wr
