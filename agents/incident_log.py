"""
Incident Log
============
JSONL-backed log of agent check failures.

Usage::

    log = IncidentLog("ares")
    log.record({"check": "freshness", "strategy": "eth-5m", "detail": "..."})
    recent = log.recent(hours=24)
    count = log.similar_count("freshness", "eth-5m")
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

EST = timezone(timedelta(hours=-5))
_BASE = Path("data/incidents")


class IncidentLog:
    """Persistent JSONL-backed incident log for a named agent."""

    def __init__(self, agent_id: str, base_dir: Path | None = None):
        self._agent_id = agent_id
        base = base_dir or _BASE
        self.path: Path = base / agent_id / "incidents.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # ── Write ──────────────────────────────────────────────────────────────

    def record(self, entry: dict) -> None:
        """Append an incident entry. Adds timestamp automatically."""
        stamped = dict(entry)
        if "ts" not in stamped:
            stamped["ts"] = datetime.now(EST).isoformat()
        with open(self.path, "a") as f:
            f.write(json.dumps(stamped) + "\n")

    # ── Read ───────────────────────────────────────────────────────────────

    def all(self) -> list[dict]:
        """Return all recorded incidents."""
        if not self.path.exists():
            return []
        lines = self.path.read_text().strip().splitlines()
        out = []
        for line in lines:
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return out

    def recent(self, hours: float = 24.0) -> list[dict]:
        """Return incidents from the last N hours."""
        cutoff = datetime.now(EST) - timedelta(hours=hours)
        result = []
        for entry in self.all():
            ts_str = entry.get("ts", "")
            try:
                ts = datetime.fromisoformat(ts_str)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=EST)
                if ts >= cutoff:
                    result.append(entry)
            except (ValueError, TypeError):
                result.append(entry)  # keep if unparseable
        return result

    def similar_count(self, check: str, strategy: str) -> int:
        """Count incidents with matching check and strategy."""
        return sum(
            1 for e in self.all()
            if e.get("check") == check and e.get("strategy") == strategy
        )
