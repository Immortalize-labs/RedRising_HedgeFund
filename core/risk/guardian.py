"""
Risk Guardian
=============
Hard risk limits enforced before every trade.
Wraps RiskLimits (config) and RiskState (runtime) to produce allow/deny verdicts.

Usage::

    from core.risk.guardian import RiskGuardian, RiskLimits

    g = RiskGuardian()
    ok, reason = g.check_trade(10.0, "BUY")
    if not ok:
        logger.warning("Trade blocked: %s", reason)
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RiskLimits:
    """Configurable hard limits. Defaults match risk_policy.yaml."""
    max_position_usd: float = 500.0
    max_exposure_usd: float = 2000.0
    max_daily_loss_usd: float = 50.0
    max_drawdown_pct: float = 2.0
    max_open_orders: int = 8
    # Kill switch
    adverse_window: int = 10
    adverse_min_wr: float = 0.20


@dataclass
class RiskState:
    """Runtime state tracked across trades."""
    daily_pnl: float = 0.0
    current_equity: float = 0.0
    peak_equity: float = 0.0
    open_orders: int = 0
    open_positions: list = field(default_factory=list)
    recent_fills: list = field(default_factory=list)
    killed: bool = False
    paused: bool = False


class RiskGuardian:
    """Enforces hard risk limits before every trade."""

    def __init__(self, limits: RiskLimits | None = None):
        self.limits = limits or RiskLimits()
        self.state = RiskState()

    # ── Primary gate ───────────────────────────────────────────────────────

    def check_trade(self, size_usd: float, direction: str) -> tuple[bool, str]:
        """
        Gate a proposed trade through all hard limits.

        Returns:
            (allowed, reason) — reason is "OK" if allowed.
        """
        # 1. Kill / pause state
        if self.state.killed:
            return False, "KILLED — no trades allowed until manual reset"
        if self.state.paused:
            return False, "PAUSED — adverse selection detected, awaiting review"

        # 2. Drawdown kill switch
        if self.state.peak_equity > 0:
            dd_pct = (self.state.peak_equity - self.state.current_equity) / self.state.peak_equity * 100
            if dd_pct > self.limits.max_drawdown_pct:
                self.state.killed = True
                return False, (
                    f"KILL SWITCH triggered — drawdown {dd_pct:.2f}% exceeds "
                    f"{self.limits.max_drawdown_pct:.1f}% limit"
                )

        # 3. Position limit
        if size_usd > self.limits.max_position_usd:
            return False, (
                f"Position ${size_usd:.2f} exceeds max_position_usd "
                f"${self.limits.max_position_usd:.2f}"
            )

        # 4. Exposure limit
        current_exposure = sum(p.get("notional", 0.0) for p in self.state.open_positions)
        if current_exposure + size_usd > self.limits.max_exposure_usd:
            return False, (
                f"Exposure ${current_exposure + size_usd:.2f} would exceed "
                f"max_exposure_usd ${self.limits.max_exposure_usd:.2f}"
            )

        # 5. Open orders limit
        if self.state.open_orders >= self.limits.max_open_orders:
            return False, (
                f"Open orders {self.state.open_orders} at max_open_orders "
                f"{self.limits.max_open_orders}"
            )

        # 6. Daily loss limit
        if self.state.daily_pnl <= -self.limits.max_daily_loss_usd:
            return False, (
                f"Daily loss ${self.state.daily_pnl:.2f} exceeds "
                f"max_daily_loss_usd ${self.limits.max_daily_loss_usd:.2f}"
            )

        # 7. Adverse selection check
        settled = [f for f in self.state.recent_fills if f.get("won") is not None]
        if len(settled) >= self.limits.adverse_window:
            last_n = settled[-self.limits.adverse_window:]
            wr = sum(1 for f in last_n if f.get("won")) / self.limits.adverse_window
            if wr < self.limits.adverse_min_wr:
                self.state.paused = True
                return False, (
                    f"ADVERSE SELECTION — WR {wr*100:.1f}% over last "
                    f"{self.limits.adverse_window} trades below "
                    f"{self.limits.adverse_min_wr*100:.0f}% threshold"
                )

        return True, "OK"

    # ── Regime scaling ─────────────────────────────────────────────────────

    def regime_size_multiplier(self, vol: float) -> float:
        """
        Scale trade size by volatility regime.

        vol < 30  → 1.0 (full size)
        vol > 80  → 0.25 (quarter size)
        Between   → linear interpolation
        """
        LOW_VOL = 30.0
        HIGH_VOL = 80.0
        if vol <= LOW_VOL:
            return 1.0
        if vol >= HIGH_VOL:
            return 0.25
        frac = (vol - LOW_VOL) / (HIGH_VOL - LOW_VOL)
        return 1.0 - frac * 0.75

    # ── State management ───────────────────────────────────────────────────

    def update_fill(self, fill: dict[str, Any]) -> None:
        """Update runtime state after a trade fill."""
        pnl = fill.get("pnl", 0.0)
        self.state.daily_pnl += pnl
        self.state.current_equity += pnl
        if self.state.current_equity > self.state.peak_equity:
            self.state.peak_equity = self.state.current_equity
        self.state.recent_fills.append(fill)
        # Cap recent fills at 50
        if len(self.state.recent_fills) > 50:
            self.state.recent_fills = self.state.recent_fills[-50:]

    def reset_daily(self) -> None:
        """Reset daily counters. Call at start of each trading day."""
        self.state.daily_pnl = 0.0
        self.state.paused = False

    # ── Persistence ────────────────────────────────────────────────────────

    def save_state(self, path: Path) -> None:
        """Atomically save state to JSON."""
        data = asdict(self.state)
        tmp = path.with_suffix(".tmp")
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            tmp.write_text(json.dumps(data, indent=2))
            tmp.rename(path)
        except OSError as e:
            logger.error("Failed to save risk state: %s", e)
            if tmp.exists():
                tmp.unlink(missing_ok=True)

    def load_state(self, path: Path) -> None:
        """Load state from JSON. Silent no-op if file missing."""
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            for k, v in data.items():
                if hasattr(self.state, k):
                    setattr(self.state, k, v)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load risk state from %s: %s", path, e)
