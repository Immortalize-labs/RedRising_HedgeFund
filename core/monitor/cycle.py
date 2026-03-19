"""
Cycle Monitor
=============
One trading cycle: find market → get signal → size → gate → execute.
Runs every window_seconds and reports proactive portfolio suggestions.

Usage::

    monitor = CycleMonitor(
        prediction=predictor,
        sizing=sizer,
        risk_gate=gate,
        executor=executor,
        slug_prefix="btc-updown-15m",
        window_seconds=900,
        min_remaining_s=60,
        asset="BTC",
        interval="15m",
        price_field="btc_price",
        min_confidence_prob=0.52,
    )
    monitor.run_cycle()
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core.risk.proactive_suggestions import CRITICAL, WARNING, PortfolioStateChecker

logger = logging.getLogger(__name__)
EST = timezone(timedelta(hours=-5))

# Module-level singleton for proactive suggestions (patchable in tests)
_state_checker = PortfolioStateChecker()


def find_market(slug_prefix: str, min_remaining_s: int = 60) -> dict | None:
    """
    Find the next open market matching the slug prefix.

    In production this queries the Gamma API.  In tests it is patched.

    Returns:
        dict with keys: remaining_sec, yes_price, no_price, slug
        or None if no eligible market found.
    """
    # Stub — replaced by real implementation in live traders
    return None


class CycleMonitor:
    """
    Runs one complete trading cycle per call to run_cycle().

    Parameters mirror the live trader constructors for compatibility.
    """

    def __init__(
        self,
        prediction,
        sizing,
        risk_gate,
        executor,
        slug_prefix: str,
        window_seconds: int,
        min_remaining_s: int,
        asset: str,
        interval: str,
        price_field: str,
        min_confidence_prob: float,
        state_path: Path | None = None,
    ):
        self.prediction = prediction
        self.sizing = sizing
        self.risk_gate = risk_gate
        self.executor = executor
        self.slug_prefix = slug_prefix
        self.window_seconds = window_seconds
        self.min_remaining_s = min_remaining_s
        self.asset = asset
        self.interval = interval
        self.price_field = price_field
        self.min_confidence_prob = min_confidence_prob
        self._state_path = state_path

        self.running: bool = True
        self.last_traded_epoch: int = 0
        self._last_signal: Any = None

        self.state: dict = {
            "total_trades": 0,
            "fills": 0,
            "cancels": 0,
            "pnl": 0.0,
            "last_trade_time": "",
        }

        if state_path and state_path.exists():
            self._load_state()

    # ── Public API ─────────────────────────────────────────────────────────

    def run_cycle(self) -> None:
        """Execute one trading cycle."""
        current_epoch = int(time.time() // self.window_seconds)

        if current_epoch <= self.last_traded_epoch:
            return  # already traded this epoch

        # Kill file check
        if self.risk_gate is not None:
            kv = self.risk_gate.check_kill_file()
            if kv is not None:
                logger.warning("[CycleMonitor] Kill file active: %s", kv.reason)
                return

        # Find market
        market = find_market(self.slug_prefix, self.min_remaining_s)
        if market is None:
            return

        remaining = market.get("remaining_sec", 0)
        if remaining < self.min_remaining_s:
            return

        # Get signal
        if self.prediction is None:
            self.executor.log_skip(reason="no_predictor", market=market)
            return

        signal = self.prediction.predict(market)
        self._last_signal = signal

        # Check confidence
        min_prob = getattr(self.sizing, "min_prob", self.min_confidence_prob)
        if signal.probability < min_prob:
            self.executor.log_skip(reason="low_confidence", market=market, signal=signal)
            return

        # PM veto check
        if self.risk_gate is not None:
            pm_mode = getattr(self.risk_gate, "pm_veto_mode", "off")
            if pm_mode != "off":
                pv = self.risk_gate.check_pm_veto(signal.prediction, market)
                if not pv.allowed:
                    self.executor.log_skip(reason="pm_veto", market=market, signal=signal)
                    return

        # Size
        if self.sizing is None:
            self.executor.log_skip(reason="no_sizer", market=market)
            return

        size = self.sizing.compute(signal, market)

        # Execute
        result = self.executor.execute(signal=signal, size=size, market=market)
        if result is None:
            self.executor.log_skip(reason="execute_returned_none", market=market)
            return

        # Update state
        self.last_traded_epoch = current_epoch
        self.state["total_trades"] += 1
        now = datetime.now(EST).isoformat()
        self.state["last_trade_time"] = now
        self._save_state()

        # Proactive checks at end of cycle
        self._run_proactive_checks()

    def _run_proactive_checks(self) -> None:
        """Run proactive portfolio state checks. Exceptions are swallowed."""
        try:
            portfolio_state = self._build_portfolio_state()
            suggestions = _state_checker.check_and_suggest(portfolio_state)
            for s in suggestions:
                msg = f"[ALERT] {s.trigger}: {s.suggested_action} — {s.reasoning}"
                if s.severity == CRITICAL:
                    logger.error(msg)
                elif s.severity == WARNING:
                    logger.warning(msg)
                else:
                    logger.info(msg)
        except Exception as exc:
            logger.warning("[proactive_check] non-fatal error: %s", exc)

    def _build_portfolio_state(self) -> dict:
        """Build portfolio state dict for the proactive suggestions checker."""
        # Drawdown from guardian
        drawdown_pct = 0.0
        guardian = None
        if self.risk_gate is not None:
            guardian = getattr(self.risk_gate, "guardian", None)
        if guardian is not None:
            gs = guardian.state
            if gs.peak_equity > 0:
                drawdown_pct = (gs.peak_equity - gs.current_equity) / gs.peak_equity * 100

        # Fill rate
        total = self.state.get("total_trades", 0)
        fills = self.state.get("fills", 0)
        fill_rate = fills / total if total > 0 else 1.0

        # Strategy name
        strat_name = getattr(self.executor, "strategy_name", self.slug_prefix) if self.executor else self.slug_prefix

        # Direction from last signal
        direction = ""
        if self._last_signal is not None:
            direction = getattr(self._last_signal, "prediction", "")

        # Recent fills and daily PnL from guardian
        recent_trades: list = []
        daily_pnl: float = 0.0
        win_rate: float | None = None
        if guardian is not None:
            gs = guardian.state
            recent_trades = list(gs.recent_fills)
            daily_pnl = gs.daily_pnl
            settled = [f for f in recent_trades if f.get("won") is not None]
            if settled:
                win_rate = sum(1 for f in settled if f.get("won")) / len(settled)

        strategy_info: dict = {
            "fill_rate": fill_rate,
            "recent_trades": recent_trades,
            "daily_pnl": daily_pnl,
            "direction": direction,
        }
        if win_rate is not None:
            strategy_info["win_rate"] = win_rate

        # Parse last_trade_ts
        last_trade_ts: float | None = None
        ltt = self.state.get("last_trade_time", "")
        if ltt:
            try:
                dt = datetime.fromisoformat(ltt)
                last_trade_ts = dt.timestamp()
            except (ValueError, TypeError):
                pass

        state: dict = {
            "drawdown_pct": drawdown_pct,
            "strategies": {strat_name: strategy_info},
        }
        if last_trade_ts is not None:
            state["last_trade_ts"] = last_trade_ts

        return state

    # ── State persistence ──────────────────────────────────────────────────

    def _save_state(self) -> None:
        if self._state_path is None:
            return
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._state_path.write_text(json.dumps(self.state, indent=2))
        except OSError as e:
            logger.warning("Failed to save cycle state: %s", e)

    def _load_state(self) -> None:
        try:
            data = json.loads(self._state_path.read_text())
            self.state.update(data)
        except (json.JSONDecodeError, OSError):
            pass
