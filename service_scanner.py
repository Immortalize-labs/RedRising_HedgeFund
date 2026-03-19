"""
Service Scanner
===============
Scans running systemd services and identifies unauthorized (rogue) services
against the authorized set derived from strategies.yaml.

Usage::

    authorized = build_authorized_set()
    rogues = scan(authorized=authorized)
    if rogues:
        report = format_report(rogues, authorized)
        print(report)
        auto_kill_rogues(rogues)
"""
from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ── Data Classes ───────────────────────────────────────────────────────────────


@dataclass
class ServiceInfo:
    """Parsed systemctl unit entry."""
    name: str
    full_name: str
    active_state: str
    sub_state: str
    load_state: str


@dataclass
class RogueService:
    """A service that is running but not authorized."""
    name: str
    full_name: str
    active_state: str
    sub_state: str
    reason: str
    recommendation: str   # "stop" | "investigate"


# ── Constants ──────────────────────────────────────────────────────────────────

# Services that are ALWAYS authorized regardless of strategy config
INFRA_SERVICES: frozenset[str] = frozenset([
    "polymarket-dashboard",
    "polymarket-redeemer",
    "polymarket-ledger-sync",
    "health-monitor",
    "strategy-monitor",
    "redeemer-watchdog",
    "telegram-watch",
    "sync-pnl",
    "drawdown-monitor",
])

# Regex patterns that identify trading-related services (eligible for scrutiny)
_DETECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"polymarket"),
    re.compile(r"\btrader\b"),
    re.compile(r"\btrading\b"),
    re.compile(r"\bstrategy\b"),
    re.compile(r"\blive\b"),
    re.compile(r"settlement"),
    re.compile(r"redeemer"),
    re.compile(r"dashboard"),
    re.compile(r"\bmomentum\b"),
    re.compile(r"\bxgb\b"),
    re.compile(r"\bkelly\b"),
    re.compile(r"\bqkelly\b"),
]


# ── Core Functions ─────────────────────────────────────────────────────────────


def list_active_units() -> list[ServiceInfo]:
    """
    Return all active systemd service units.
    Falls back to [] if systemctl is unavailable (macOS / CI).
    """
    try:
        result = subprocess.run(
            ["systemctl", "list-units", "--type=service", "--state=active", "--no-pager", "--no-legend"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return _parse_systemctl_output(result.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def _parse_systemctl_output(output: str) -> list[ServiceInfo]:
    """Parse `systemctl list-units` output into ServiceInfo objects."""
    services = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        full_name = parts[0]
        if not full_name.endswith(".service"):
            continue
        name = full_name[: -len(".service")]
        load_state = parts[1]
        active_state = parts[2]
        sub_state = parts[3]
        services.append(ServiceInfo(
            name=name,
            full_name=full_name,
            active_state=active_state,
            sub_state=sub_state,
            load_state=load_state,
        ))
    return services


def _matches_detection_pattern(name: str) -> bool:
    """Return True if the service name looks trading-related."""
    for pattern in _DETECTION_PATTERNS:
        if pattern.search(name):
            return True
    return False


def _load_authorized_from_yaml() -> frozenset[str]:
    """Load authorized service names from strategies.yaml."""
    try:
        from config.strategy_registry import StrategyRegistry
        reg = StrategyRegistry()
        authorized: set[str] = set()
        for s in reg.active():
            if s.systemd_trader:
                authorized.add(s.systemd_trader)
            if s.systemd_settlement:
                authorized.add(s.systemd_settlement)
        return frozenset(authorized)
    except Exception as e:
        logger.warning("Could not load strategies.yaml: %s", e)
        return frozenset()


def build_authorized_set() -> frozenset[str]:
    """Build the full authorized service set: infra + active strategy services."""
    return INFRA_SERVICES | _load_authorized_from_yaml()


def scan(authorized: frozenset[str] | None = None) -> list[RogueService]:
    """
    Scan running services and return those that are unauthorized.

    Args:
        authorized: Set of authorized service names. If None, builds from yaml.

    Returns:
        List of RogueService objects for each unauthorized service.
    """
    if authorized is None:
        authorized = build_authorized_set()

    units = list_active_units()
    rogues: list[RogueService] = []

    # Build a lookup of killed strategy services for better reason messages
    killed_services: dict[str, str] = {}
    try:
        from config.strategy_registry import StrategyRegistry
        reg = StrategyRegistry()
        for s in reg.killed():
            if s.systemd_trader:
                killed_services[s.systemd_trader] = s.display_name
            if s.systemd_settlement:
                killed_services[s.systemd_settlement] = s.display_name
    except Exception:
        pass

    for unit in units:
        # Skip non-trading services
        if not _matches_detection_pattern(unit.name):
            continue
        # Skip authorized services
        if unit.name in authorized:
            continue

        # Build reason
        if unit.name in killed_services:
            strat_name = killed_services[unit.name]
            reason = f"Killed strategy '{strat_name}' service still running"
        else:
            reason = "Unauthorized trading service — not in strategies.yaml"

        rogues.append(RogueService(
            name=unit.name,
            full_name=unit.full_name,
            active_state=unit.active_state,
            sub_state=unit.sub_state,
            reason=reason,
            recommendation="stop",
        ))

    return rogues


def stop_service(name: str) -> tuple[bool, str]:
    """
    Stop and disable a systemd service.

    Returns:
        (success, message)
    """
    try:
        stop_result = subprocess.run(
            ["systemctl", "stop", name],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if stop_result.returncode != 0:
            return False, f"stop failed rc={stop_result.returncode}: {stop_result.stderr}"

        subprocess.run(
            ["systemctl", "disable", name],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return True, f"stopped and disabled {name}"

    except subprocess.TimeoutExpired:
        return False, f"timeout stopping {name}"
    except Exception as e:
        return False, str(e)


def auto_kill_rogues(rogues: list[RogueService]) -> list[str]:
    """
    Stop all rogues with recommendation="stop".

    Returns:
        List of outcome strings ("OK: ..." or "FAIL: ...").
    """
    outcomes = []
    for rogue in rogues:
        if rogue.recommendation != "stop":
            continue
        ok, msg = stop_service(rogue.name)
        prefix = "OK" if ok else "FAIL"
        outcomes.append(f"{prefix}: {rogue.name} — {msg}")
    return outcomes


def format_report(rogues: list[RogueService], authorized: frozenset[str]) -> str:
    """Format a human-readable scan report."""
    lines = []
    if not rogues:
        lines.append("SCAN CLEAN — no unauthorized trading services running.")
        lines.append(f"Authorized services ({len(authorized)}): {', '.join(sorted(authorized))}")
    else:
        lines.append(f"{len(rogues)} UNAUTHORIZED TRADING SERVICES DETECTED")
        lines.append("")
        for r in rogues:
            lines.append(f"  [{r.recommendation.upper()}] {r.name}")
            lines.append(f"    Reason: {r.reason}")
            lines.append(f"    State: {r.active_state}/{r.sub_state}")
        lines.append("")
        lines.append(f"Authorized set: {', '.join(sorted(authorized))}")
    return "\n".join(lines)
