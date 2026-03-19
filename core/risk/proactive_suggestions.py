"""
Proactive State Suggestions
============================
Rule-based engine that inspects portfolio state every cycle and surfaces
actionable suggestions BEFORE conditions escalate into hard risk blocks.

Inspired by gstack's proactive skill suggestion pattern.
No LLM calls — pure deterministic rules.

Usage::

    from core.risk.proactive_suggestions import state_checker

    suggestions = state_checker.check_and_suggest(portfolio_state)
    for s in suggestions:
        logger.warning("[%s] %s — %s", s.severity.upper(), s.trigger, s.suggested_action)

Portfolio State Dict Schema
---------------------------
The ``portfolio_state`` dict accepted by ``check_and_suggest`` must contain:

Required keys:
    drawdown_pct        float   Current drawdown from peak (0–100 scale, e.g. 1.5 = 1.5%)
    strategies          dict    Map of strategy_name -> strategy_info dict (see below)

Optional keys:
    last_trade_ts       float   Unix timestamp of the most recent trade (any strategy)

Strategy info dict (per strategy inside ``strategies``):
    fill_rate           float   Fill rate 0–1 (e.g. 0.85 = 85%)
    win_rate            float   Observed WR over last N trades, 0–1
    backtest_win_rate   float   Expected WR from backtest, 0–1
    recent_trades       list    Last trades — each entry must have key "won" (bool | None)
    daily_pnl           float   Today's realized PnL in USD
    direction           str     Current open position direction: "UP", "DOWN", or "" / None

Example::

    state = {
        "drawdown_pct": 1.8,
        "last_trade_ts": 1742345678.0,
        "strategies": {
            "btc-15m": {
                "fill_rate": 0.65,
                "win_rate": 0.48,
                "backtest_win_rate": 0.55,
                "recent_trades": [{"won": False}] * 10,
                "daily_pnl": -18.0,
                "direction": "UP",
            },
        },
    }
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

EST = timezone(timedelta(hours=-5))
_SUGGESTIONS_LOG = Path("data/suggestions.jsonl")

# Severity constants — kept as plain strings to stay JSON-serialisable
INFO = "info"
WARNING = "warning"
CRITICAL = "critical"

# Trigger thresholds — match risk_policy.yaml
_DD_WARN_PCT = 1.5         # drawdown % that raises a warning
_DD_CRIT_PCT = 2.0         # drawdown % that raises critical halt suggestion
_FILL_WARN = 0.70          # fill rate below this triggers escalation suggestion
_WR_DROP_PP = 0.05         # 5 percentage-point drop below backtest WR
_ADVERSE_WR = 0.20         # WR below this over the adverse window triggers kill suggestion
_ADVERSE_WINDOW = 10       # number of recent settled trades to evaluate
_DAILY_PNL_WARN = -25.0    # daily PnL below this triggers size-reduction suggestion
_NO_TRADE_SECS = 7_200     # 2 hours without a trade → connectivity check


@dataclass
class Suggestion:
    """A single proactive suggestion surfaced by the state checker."""

    trigger: str            # machine-readable trigger name
    severity: str           # "info" | "warning" | "critical"
    suggested_action: str   # one-line action the supervisor should take
    reasoning: str          # why this suggestion was raised (numbers included)
    strategy: str = ""      # which strategy triggered it ("" = portfolio-level)
    ts: str = ""            # ISO timestamp (populated automatically by checker)


class PortfolioStateChecker:
    """
    Inspects a portfolio state snapshot and returns zero or more
    ``Suggestion`` objects ranked by severity.

    All checks are stateless per call — the caller passes the full snapshot.
    Logging to ``data/suggestions.jsonl`` is append-only and fault-tolerant.
    """

    def __init__(self, log_path: Path | None = None):
        self._log_path = log_path or _SUGGESTIONS_LOG
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Public API ─────────────────────────────────────────────────────────

    def check_and_suggest(self, portfolio_state: dict[str, Any]) -> list[Suggestion]:
        """
        Evaluate all triggers against the current portfolio state.

        Args:
            portfolio_state: See module docstring for expected schema.

        Returns:
            List of Suggestion objects, ordered: critical first, then warning, then info.
        """
        suggestions: list[Suggestion] = []

        drawdown_pct: float = portfolio_state.get("drawdown_pct", 0.0)
        strategies: dict[str, dict] = portfolio_state.get("strategies", {})
        last_trade_ts: float | None = portfolio_state.get("last_trade_ts")

        # ── Portfolio-level triggers ───────────────────────────────────────
        suggestions.extend(self._check_drawdown(drawdown_pct))
        suggestions.extend(self._check_correlation(strategies))
        suggestions.extend(self._check_no_trades(last_trade_ts))

        # ── Per-strategy triggers ──────────────────────────────────────────
        for name, info in strategies.items():
            suggestions.extend(self._check_fill_rate(name, info))
            suggestions.extend(self._check_wr_drop(name, info))
            suggestions.extend(self._check_adverse_wr(name, info))
            suggestions.extend(self._check_daily_pnl(name, info))

        # Sort: critical → warning → info
        _order = {CRITICAL: 0, WARNING: 1, INFO: 2}
        suggestions.sort(key=lambda s: _order.get(s.severity, 99))

        # Stamp timestamps and log
        now_str = datetime.now(EST).isoformat()
        for s in suggestions:
            s.ts = now_str
            self._log(s)

        return suggestions

    # ── Individual trigger methods ─────────────────────────────────────────

    def _check_drawdown(self, drawdown_pct: float) -> list[Suggestion]:
        """Drawdown > 1.5% → warning; > 2.0% → critical."""
        if drawdown_pct > _DD_CRIT_PCT:
            return [Suggestion(
                trigger="drawdown_critical",
                severity=CRITICAL,
                suggested_action="Halt all trading immediately. Await manual review.",
                reasoning=(
                    f"Portfolio drawdown is {drawdown_pct:.2f}% — exceeds critical "
                    f"threshold of {_DD_CRIT_PCT:.1f}%. Risk policy mandates halt."
                ),
            )]
        if drawdown_pct > _DD_WARN_PCT:
            return [Suggestion(
                trigger="drawdown_warning",
                severity=WARNING,
                suggested_action="Initiate kill review. Consider reducing all position sizes.",
                reasoning=(
                    f"Portfolio drawdown is {drawdown_pct:.2f}% — above warning "
                    f"threshold of {_DD_WARN_PCT:.1f}%. Monitor closely."
                ),
            )]
        return []

    def _check_fill_rate(self, name: str, info: dict) -> list[Suggestion]:
        """Fill rate < 70% for any strategy → escalation adjustment suggestion."""
        fill_rate: float | None = info.get("fill_rate")
        if fill_rate is None:
            return []
        if fill_rate < _FILL_WARN:
            pct = fill_rate * 100
            return [Suggestion(
                trigger="fill_rate_low",
                severity=WARNING,
                suggested_action=(
                    "Adjust order escalation timing or entry price for this strategy. "
                    "Consider switching from maker to taker for critical fills."
                ),
                reasoning=(
                    f"{name} fill rate is {pct:.1f}% — below the {_FILL_WARN*100:.0f}% "
                    f"minimum gate. Execution quality degraded."
                ),
                strategy=name,
            )]
        return []

    def _check_wr_drop(self, name: str, info: dict) -> list[Suggestion]:
        """WR drops 5pp+ below backtest WR → investigation suggestion."""
        live_wr: float | None = info.get("win_rate")
        bt_wr: float | None = info.get("backtest_win_rate")
        if live_wr is None or bt_wr is None:
            return []
        drop = bt_wr - live_wr
        if drop >= _WR_DROP_PP:
            return [Suggestion(
                trigger="wr_below_backtest",
                severity=WARNING,
                suggested_action=(
                    "Investigate signal quality, feature drift, or regime change. "
                    "Review recent fills for adverse selection."
                ),
                reasoning=(
                    f"{name} live WR is {live_wr*100:.1f}% vs backtest {bt_wr*100:.1f}% "
                    f"— drop of {drop*100:.1f}pp exceeds {_WR_DROP_PP*100:.0f}pp threshold."
                ),
                strategy=name,
            )]
        return []

    def _check_adverse_wr(self, name: str, info: dict) -> list[Suggestion]:
        """WR < 20% over last 10 settled trades → kill switch suggestion."""
        recent_trades: list[dict] = info.get("recent_trades", [])
        settled = [t for t in recent_trades if t.get("won") is not None]
        if len(settled) < _ADVERSE_WINDOW:
            return []
        last_n = settled[-_ADVERSE_WINDOW:]
        wins = sum(1 for t in last_n if t.get("won"))
        wr = wins / _ADVERSE_WINDOW
        if wr < _ADVERSE_WR:
            return [Suggestion(
                trigger="adverse_selection",
                severity=CRITICAL,
                suggested_action=(
                    "Activate kill switch for this strategy. "
                    "Halt trading and investigate adverse selection or broken signal."
                ),
                reasoning=(
                    f"{name} win rate is {wr*100:.1f}% over last {_ADVERSE_WINDOW} settled "
                    f"trades ({wins}/{_ADVERSE_WINDOW} wins) — below {_ADVERSE_WR*100:.0f}% kill threshold."
                ),
                strategy=name,
            )]
        return []

    def _check_daily_pnl(self, name: str, info: dict) -> list[Suggestion]:
        """Single strategy daily PnL < -$25 → size reduction suggestion."""
        daily_pnl: float | None = info.get("daily_pnl")
        if daily_pnl is None:
            return []
        if daily_pnl < _DAILY_PNL_WARN:
            return [Suggestion(
                trigger="daily_pnl_low",
                severity=WARNING,
                suggested_action=(
                    "Reduce position size for this strategy by 50%. "
                    "Do not increase size until daily PnL recovers above -$10."
                ),
                reasoning=(
                    f"{name} daily PnL is ${daily_pnl:.2f} — below the "
                    f"${_DAILY_PNL_WARN:.0f} warning threshold."
                ),
                strategy=name,
            )]
        return []

    def _check_correlation(self, strategies: dict[str, dict]) -> list[Suggestion]:
        """All open positions in same direction → correlation review suggestion."""
        directions = [
            info.get("direction", "")
            for info in strategies.values()
            if info.get("direction")  # exclude empty / None
        ]
        if len(directions) < 2:
            return []  # need at least 2 active positions to measure correlation
        unique = set(directions)
        if len(unique) == 1:
            common_dir = next(iter(unique))
            return [Suggestion(
                trigger="all_positions_correlated",
                severity=INFO,
                suggested_action=(
                    "Review portfolio correlation. Consider hedging or pausing new "
                    "entries until directional concentration normalizes."
                ),
                reasoning=(
                    f"All {len(directions)} active positions are {common_dir}. "
                    f"Concentrated directional exposure increases tail risk."
                ),
            )]
        return []

    def _check_no_trades(self, last_trade_ts: float | None) -> list[Suggestion]:
        """No trades in 2+ hours → connectivity check suggestion."""
        if last_trade_ts is None:
            return []
        elapsed = time.time() - last_trade_ts
        if elapsed >= _NO_TRADE_SECS:
            hours = elapsed / 3600
            return [Suggestion(
                trigger="no_recent_trades",
                severity=INFO,
                suggested_action=(
                    "Check exchange connectivity, API key validity, and live trader process health. "
                    "Verify kill file is not active."
                ),
                reasoning=(
                    f"No trades recorded for {hours:.1f}h "
                    f"(threshold: {_NO_TRADE_SECS/3600:.0f}h). "
                    f"Possible connectivity or process failure."
                ),
            )]
        return []

    # ── Logging ────────────────────────────────────────────────────────────

    def _log(self, suggestion: Suggestion) -> None:
        """Append suggestion to JSONL log. Fault-tolerant."""
        try:
            with open(self._log_path, "a") as fh:
                fh.write(json.dumps(asdict(suggestion)) + "\n")
        except OSError as exc:
            logger.warning("Failed to write suggestion log %s: %s", self._log_path, exc)


# Module-level singleton — import and call directly in supervisor
state_checker = PortfolioStateChecker()
