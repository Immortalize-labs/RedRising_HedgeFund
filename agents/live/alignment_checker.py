"""
Alignment Checker
=================
Every cycle: verify that the AI signal matches the open order direction.
Misalignment triggers an investigation freeze.

Usage::

    checker = AlignmentChecker()
    result = checker.check(state, signal, pending_order)
    if not result["aligned"]:
        logger.warning("MISALIGNMENT: %s", result["reason"])
"""
from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)


class AlignmentChecker:
    """
    Checks alignment between AI signal direction and the pending order direction.

    Parameters
    ----------
    max_age_s : float
        Orders older than this are considered stale and exempt from alignment checks.
    check_every_n_cycles : int
        Only run the full check every N cycles (reduces noise on noisy signals).
    """

    def __init__(
        self,
        max_age_s: float = 300.0,
        check_every_n_cycles: int = 1,
    ):
        self.max_age_s = max_age_s
        self.check_every_n_cycles = check_every_n_cycles
        self._cycle_count: int = 0

    def check(
        self,
        state: dict,
        signal: dict | None,
        pending_order: dict | None,
    ) -> dict:
        """
        Check alignment.

        Args:
            state:         Current trading state dict (unused currently, for extensibility).
            signal:        Dict with key "prediction" (str: "UP"/"DOWN"). Can be None.
            pending_order: Dict with key "side" (str: "UP"/"DOWN") and "placed_at" (float).
                           Can be None.

        Returns:
            Dict with keys:
                aligned (bool): True if no misalignment detected.
                reason  (str):  Human-readable explanation.
        """
        # Cycle skip logic
        if self.check_every_n_cycles > 1:
            self._cycle_count += 1
            if self._cycle_count < self.check_every_n_cycles:
                return {"aligned": True, "reason": "cycle_skip"}
            else:
                self._cycle_count = 0

        # No pending order → nothing to misalign against
        if pending_order is None:
            return {"aligned": True, "reason": "no_pending_order"}

        # No signal → cannot determine misalignment
        if signal is None:
            return {"aligned": True, "reason": "no_signal"}

        # Stale order check
        placed_at = pending_order.get("placed_at", 0.0)
        if placed_at and (time.time() - placed_at) > self.max_age_s:
            return {"aligned": True, "reason": "stale_order"}

        # Missing direction data
        prediction = str(signal.get("prediction", "")).upper()
        order_side = str(pending_order.get("side", "")).upper()
        if not prediction or not order_side:
            return {"aligned": True, "reason": "missing_direction_data"}

        # Alignment check
        if prediction == order_side:
            return {"aligned": True, "reason": "signal_matches_order"}

        return {
            "aligned": False,
            "reason": f"MISALIGNMENT: signal={prediction}, order={order_side}",
        }
