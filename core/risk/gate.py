"""
Risk Gate
=========
Thin orchestration wrapper around RiskGuardian.
Adds kill-file support and Polymarket PM-veto logic.

Usage::

    from core.risk.gate import RiskGate, Verdict
    from core.risk.guardian import RiskGuardian

    gate = RiskGate(guardian=RiskGuardian())
    v = gate.check_trade(10.0, "UP")
    if not v.allowed:
        logger.warning("Trade blocked by %s: %s", v.gate, v.reason)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from core.risk.guardian import RiskGuardian

logger = logging.getLogger(__name__)

_DEFAULT_KILL_FILE = Path("data/RISK_KILL")


@dataclass
class Verdict:
    """Trade gate verdict."""
    allowed: bool
    reason: str
    gate: str       # which gate blocked: "kill_file" | "guardian" | "balance" | "pm_veto" | "none"


class RiskGate:
    """
    Orchestrates all pre-trade risk checks in priority order:
      1. Kill file (manual halt)
      2. Guardian hard limits (drawdown, exposure, adverse selection)
      3. Balance check (sufficient funds)
      4. PM veto (Polymarket market signal)
    """

    def __init__(
        self,
        guardian: RiskGuardian | None = None,
        kill_file_path: Path | None = None,
        pm_veto_mode: str = "off",          # "off" | "shadow" | "live"
        pm_disagree_thr: float = 0.02,      # min price gap to declare disagreement
    ):
        self.guardian = guardian
        self.kill_file_path = kill_file_path or _DEFAULT_KILL_FILE
        self.pm_veto_mode = pm_veto_mode
        self.pm_disagree_thr = pm_disagree_thr

    # ── Public API ─────────────────────────────────────────────────────────

    def check_trade(
        self,
        size_usd: float,
        direction: str,
        balance: float | None = None,
    ) -> Verdict:
        """
        Run all gates in priority order.

        Args:
            size_usd:  Notional trade size in USD.
            direction: "UP" or "DOWN".
            balance:   Available balance (optional balance check).

        Returns:
            Verdict with allowed/reason/gate.
        """
        # 1. Kill file
        kv = self.check_kill_file()
        if kv is not None:
            return kv

        # 2. Guardian
        if self.guardian is not None:
            ok, reason = self.guardian.check_trade(size_usd, direction)
            if not ok:
                return Verdict(allowed=False, reason=reason, gate="guardian")

        # 3. Balance
        if balance is not None and size_usd > balance:
            return Verdict(
                allowed=False,
                reason=f"Insufficient balance ${balance:.2f} for trade ${size_usd:.2f}",
                gate="balance",
            )

        return Verdict(allowed=True, reason="all_gates_passed", gate="none")

    def check_kill_file(self) -> Verdict | None:
        """
        Check for a manual kill file.

        Returns:
            Verdict if kill file is present, None otherwise.
        """
        if self.kill_file_path.exists():
            try:
                msg = self.kill_file_path.read_text().strip()
            except OSError:
                msg = "kill file present"
            return Verdict(
                allowed=False,
                reason=f"Kill file active: {msg}",
                gate="kill_file",
            )
        return None

    def check_pm_veto(self, direction: str, market_data: dict) -> Verdict:
        """
        Check whether Polymarket prices veto this direction.

        Args:
            direction:   "UP" or "DOWN".
            market_data: Dict with keys yes_price, no_price, remaining_sec.
                         If yes_price is None, veto is skipped.

        Returns:
            Verdict — allowed unless PM strongly disagrees.
        """
        if self.pm_veto_mode == "off":
            return Verdict(allowed=True, reason="pm_veto_off", gate="none")

        yes_price = market_data.get("yes_price")
        no_price = market_data.get("no_price")

        if yes_price is None or no_price is None:
            return Verdict(allowed=True, reason="pm_data_unavailable", gate="none")

        # Determine PM implied direction
        gap = abs(yes_price - no_price)
        if gap < self.pm_disagree_thr:
            return Verdict(allowed=True, reason="pm_neutral", gate="none")

        pm_direction = "UP" if yes_price > no_price else "DOWN"

        if pm_direction != direction:
            if self.pm_veto_mode == "live":
                return Verdict(
                    allowed=False,
                    reason=(
                        f"PM veto: AI={direction}, PM={pm_direction} "
                        f"(yes={yes_price:.3f}, no={no_price:.3f})"
                    ),
                    gate="pm_veto",
                )
            # shadow mode: log but allow
            logger.info(
                "[PM_VETO:shadow] AI=%s, PM=%s — would block in live mode",
                direction, pm_direction,
            )

        return Verdict(allowed=True, reason=f"pm_agrees:{pm_direction}", gate="none")

    def update_open_orders(self, delta: int) -> None:
        """Adjust the open orders counter on the guardian state."""
        if self.guardian is None:
            return
        self.guardian.state.open_orders = max(
            0, self.guardian.state.open_orders + delta
        )
