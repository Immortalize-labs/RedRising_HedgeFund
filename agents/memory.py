"""
Agent Memory System
===================
JSONL-based persistent memory per agent. Each agent gets:
  - Run history (what happened in each cycle)
  - Learnings (patterns discovered across runs)
  - Context retrieval (inject relevant memory into LLM prompts)

Storage: data/memory/<agent_id>/
  - runs.jsonl      — append-only run log
  - learnings.jsonl — extracted patterns and lessons
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent / "data" / "memory"


class AgentMemory:
    """Persistent JSONL memory for a single agent."""

    def __init__(self, agent_id: str, base_dir: Path | None = None):
        self.agent_id = agent_id
        self._dir = (base_dir or _ROOT) / agent_id
        self._dir.mkdir(parents=True, exist_ok=True)
        self._runs_path = self._dir / "runs.jsonl"
        self._learnings_path = self._dir / "learnings.jsonl"

    # ── Write ──────────────────────────────────────────────────────────

    def record_run(
        self,
        run_id: str,
        strategy_id: str = "",
        result: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Append a run record."""
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "strategy_id": strategy_id,
            "result": result or {},
            "metadata": metadata or {},
        }
        self._append(self._runs_path, entry)

    def add_learning(
        self, category: str, content: str, confidence: float = 0.5
    ) -> None:
        """Record a pattern or lesson learned."""
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "category": category,
            "content": content,
            "confidence": confidence,
        }
        self._append(self._learnings_path, entry)

    # ── Read ───────────────────────────────────────────────────────────

    def recent_runs(self, n: int = 10) -> list[dict]:
        """Return the N most recent runs."""
        return self._tail(self._runs_path, n)

    def learnings(self, category: str = "") -> list[dict]:
        """Return learnings, optionally filtered by category."""
        all_l = self._read_all(self._learnings_path)
        if category:
            return [l for l in all_l if l.get("category") == category]
        return all_l

    def get_context_for_llm(self, max_tokens_approx: int = 2000) -> str:
        """Build a context string for injection into LLM prompts.

        Returns a summary of recent runs + key learnings, capped at
        approximately max_tokens_approx characters.
        """
        parts: list[str] = []
        char_budget = max_tokens_approx * 4  # ~4 chars per token

        # Recent runs summary
        runs = self.recent_runs(5)
        if runs:
            parts.append("Recent runs:")
            for r in runs:
                line = f"  [{r.get('ts', '?')[:16]}] {r.get('strategy_id', '?')}: {json.dumps(r.get('result', {}), default=str)[:200]}"
                parts.append(line)

        # Key learnings (high confidence first)
        learnings = sorted(
            self.learnings(), key=lambda x: x.get("confidence", 0), reverse=True
        )[:10]
        if learnings:
            parts.append("\nKey learnings:")
            for l in learnings:
                line = f"  [{l.get('category', '?')}] {l.get('content', '')[:200]} (conf={l.get('confidence', 0):.1f})"
                parts.append(line)

        text = "\n".join(parts)
        if len(text) > char_budget:
            text = text[:char_budget] + "\n... (truncated)"

        return text if text.strip() else "No prior memory."

    # ── Helpers ────────────────────────────────────────────────────────

    def _append(self, path: Path, entry: dict) -> None:
        with open(path, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    def _read_all(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        results = []
        for line in path.read_text().strip().splitlines():
            if line:
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return results

    def _tail(self, path: Path, n: int) -> list[dict]:
        all_entries = self._read_all(path)
        return all_entries[-n:]

    @property
    def runs_path(self) -> Path:
        return self._runs_path

    @property
    def learnings_path(self) -> Path:
        return self._learnings_path


class AgentLogger:
    """Structured logging wrapper for agents. Writes to agent-specific log file."""

    def __init__(self, agent_id: str, base_dir: Path | None = None):
        self.agent_id = agent_id
        self._dir = (base_dir or _ROOT) / agent_id
        self._dir.mkdir(parents=True, exist_ok=True)
        self._log_path = self._dir / "agent.log.jsonl"

    def _write(self, level: str, msg: str, **kwargs: Any) -> None:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "agent": self.agent_id,
            "msg": msg,
            **kwargs,
        }
        with open(self._log_path, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    def info(self, msg: str, **kwargs: Any) -> None:
        self._write("INFO", msg, **kwargs)

    def warning(self, msg: str, **kwargs: Any) -> None:
        self._write("WARNING", msg, **kwargs)

    def error(self, msg: str, **kwargs: Any) -> None:
        self._write("ERROR", msg, **kwargs)

    def log_tool_call(
        self, tool_name: str, args: dict, result: Any
    ) -> None:
        self._write(
            "TOOL",
            f"Called {tool_name}",
            tool=tool_name,
            args=str(args)[:500],
            result=str(result)[:500],
        )

    def log_metrics(self, metrics: dict) -> None:
        self._write("METRICS", "Recorded metrics", metrics=metrics)


class RunArtifacts:
    """Container for artifacts produced during a single agent run."""

    def __init__(self) -> None:
        self.items: dict[str, Any] = {}

    def add(self, key: str, value: Any) -> None:
        self.items[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.items.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.items)
