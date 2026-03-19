"""
Drawdown Monitor
================
Computes per-strategy PnL metrics and checks portfolio-level loss limits.

Usage::

    metrics = compute_strategy_metrics(settlements, today_date_str)
    reason = check_limits(metrics, today_date_str)
    if reason:
        logger.error("LIMIT BREACH: %s", reason)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Baseline date — settlements before this date are excluded from metrics
BASELINE_DATE = "2026-03-12"

# Portfolio-level daily loss limit (USD)
PORTFOLIO_DAILY_LOSS_LIMIT = -50.0


def compute_strategy_metrics(settlements: dict, today: str) -> dict:
    """
    Compute PnL metrics from a settlements dict.

    Args:
        settlements: dict of market_id -> {won, pnl, cost, timestamp}
        today:       Date string "YYYY-MM-DD" for daily PnL filtering

    Returns:
        dict with keys: wins, losses, daily_pnl, total_pnl, total_cost,
                        peak_pnl, drawdown
    """
    wins = 0
    losses = 0
    daily_pnl = 0.0
    total_pnl = 0.0
    total_cost = 0.0
    running_pnl = 0.0
    peak_pnl = 0.0

    baseline_dt = datetime.strptime(BASELINE_DATE, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    today_str = today[:10]  # YYYY-MM-DD

    for market_id, s in settlements.items():
        ts_str = s.get("timestamp", "")
        pnl = s.get("pnl", 0.0)
        cost = s.get("cost", 0.0)
        won = s.get("won", False)

        # Parse timestamp
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue

        # Filter before baseline
        if ts < baseline_dt:
            continue

        # Accumulate totals
        total_pnl += pnl
        total_cost += cost
        running_pnl += pnl
        if running_pnl > peak_pnl:
            peak_pnl = running_pnl

        if won:
            wins += 1
        else:
            losses += 1

        # Daily PnL — only today's settlements
        trade_date = ts.strftime("%Y-%m-%d")
        if trade_date == today_str:
            daily_pnl += pnl

    drawdown = peak_pnl - total_pnl

    return {
        "wins": wins,
        "losses": losses,
        "daily_pnl": daily_pnl,
        "total_pnl": total_pnl,
        "total_cost": total_cost,
        "peak_pnl": peak_pnl,
        "drawdown": drawdown,
    }


def check_limits(metrics: dict[str, dict], today: str) -> str | None:
    """
    Check portfolio-level daily loss limits.

    Args:
        metrics: dict of strategy_id -> metrics dict (from compute_strategy_metrics)
        today:   Date string for context

    Returns:
        Reason string if a limit is breached, None if all clear.
    """
    portfolio_daily_pnl = sum(m.get("daily_pnl", 0.0) for m in metrics.values())
    if portfolio_daily_pnl <= PORTFOLIO_DAILY_LOSS_LIMIT:
        return (
            f"PORTFOLIO DAILY LOSS ${portfolio_daily_pnl:.2f} exceeded limit "
            f"${PORTFOLIO_DAILY_LOSS_LIMIT:.2f} on {today}"
        )
    return None
