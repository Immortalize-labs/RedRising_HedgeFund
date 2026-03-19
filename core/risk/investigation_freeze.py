"""
Investigation Freeze
====================
When a bug/misalignment is detected, auto-freeze that strategy from placing
new trades while investigating. Release after fix is verified.

Inspired by gstack's /investigate auto-freeze pattern.

Usage:
    from core.risk.investigation_freeze import freeze_manager

    # Freeze a strategy during investigation
    freeze_manager.freeze("btc-15m", reason="Alignment mismatch: AI says SHORT, position is LONG")

    # Check if frozen before placing trade
    if freeze_manager.is_frozen("btc-15m"):
        logger.warning("btc-15m is frozen — skipping trade")

    # Unfreeze after fix verified
    freeze_manager.unfreeze("btc-15m", resolution="Fixed signal cache staleness")
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

EST = timezone(timedelta(hours=-5))
_FREEZE_LOG = Path("data/freeze_log.jsonl")


@dataclass
class FreezeRecord:
    """Record of a strategy freeze event."""
    strategy: str
    frozen_at: str
    reason: str
    unfrozen_at: str = ""
    resolution: str = ""
    trades_blocked: int = 0
    duration_minutes: float = 0.0


class FreezeManager:
    """Manages strategy freeze/unfreeze lifecycle."""

    def __init__(self, log_path: Path | None = None):
        self._frozen: dict[str, FreezeRecord] = {}
        self._log_path = log_path or _FREEZE_LOG
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def freeze(self, strategy: str, reason: str) -> FreezeRecord:
        """Freeze a strategy. No new trades until unfrozen.

        Args:
            strategy: Strategy name (e.g., "btc-15m")
            reason: Why it's being frozen

        Returns:
            FreezeRecord for the freeze event.
        """
        now = datetime.now(EST).isoformat()
        record = FreezeRecord(strategy=strategy, frozen_at=now, reason=reason)
        self._frozen[strategy] = record

        logger.warning(f"[FREEZE] {strategy} frozen: {reason}")
        self._log_event("freeze", record)
        return record

    def unfreeze(self, strategy: str, resolution: str = "") -> FreezeRecord | None:
        """Unfreeze a strategy. Trades can resume.

        Args:
            strategy: Strategy name
            resolution: What was done to fix the issue

        Returns:
            Completed FreezeRecord, or None if wasn't frozen.
        """
        record = self._frozen.pop(strategy, None)
        if not record:
            logger.info(f"[FREEZE] {strategy} was not frozen")
            return None

        now = datetime.now(EST)
        record.unfrozen_at = now.isoformat()
        record.resolution = resolution

        # Calculate duration
        frozen_at = datetime.fromisoformat(record.frozen_at)
        record.duration_minutes = (now - frozen_at).total_seconds() / 60

        logger.info(f"[UNFREEZE] {strategy} unfrozen after {record.duration_minutes:.1f}m: {resolution}")
        self._log_event("unfreeze", record)
        return record

    def is_frozen(self, strategy: str) -> bool:
        """Check if a strategy is currently frozen."""
        return strategy in self._frozen

    def get_frozen(self) -> dict[str, FreezeRecord]:
        """Get all currently frozen strategies."""
        return dict(self._frozen)

    def block_trade(self, strategy: str) -> bool:
        """Record that a trade was blocked by freeze. Returns True if frozen.

        Call this before every trade attempt. If frozen, increments block counter.
        """
        if strategy in self._frozen:
            self._frozen[strategy].trades_blocked += 1
            logger.info(f"[FREEZE] Blocked trade #{self._frozen[strategy].trades_blocked} on {strategy}")
            return True
        return False

    def auto_freeze_on_misalignment(
        self,
        strategy: str,
        ai_direction: str,
        position_direction: str,
    ) -> FreezeRecord | None:
        """Auto-freeze if AI suggestion doesn't match open position.

        This is the alignment check mandated in CLAUDE.md:
        "Every cycle: check AI suggestion alignment with open positions. Auto-investigate misalignment."
        """
        if ai_direction == position_direction:
            return None  # aligned

        if self.is_frozen(strategy):
            return None  # already frozen

        reason = (
            f"Alignment mismatch: AI suggests {ai_direction}, "
            f"open position is {position_direction}. Auto-investigating."
        )
        return self.freeze(strategy, reason)

    def auto_freeze_on_error(self, strategy: str, error: str) -> FreezeRecord:
        """Auto-freeze on execution error (API failure, order rejection, etc.)."""
        reason = f"Execution error: {error}"
        return self.freeze(strategy, reason)

    def status(self) -> str:
        """Human-readable freeze status."""
        if not self._frozen:
            return "No strategies frozen."
        lines = ["Frozen strategies:"]
        for name, rec in self._frozen.items():
            lines.append(
                f"  {name}: {rec.reason} "
                f"(frozen at {rec.frozen_at}, {rec.trades_blocked} trades blocked)"
            )
        return "\n".join(lines)

    def _log_event(self, event_type: str, record: FreezeRecord) -> None:
        """Append freeze event to JSONL log."""
        entry = {"event": event_type, **asdict(record)}
        try:
            with open(self._log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError:
            logger.warning(f"Failed to write freeze log: {self._log_path}")


# Module-level singleton
freeze_manager = FreezeManager()
