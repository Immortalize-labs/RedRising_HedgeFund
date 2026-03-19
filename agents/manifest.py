"""
Agent Manifest System
=====================
Load, validate, and query YAML agent manifests.
Every agent in the system has a manifest describing:
  - Identity (id, codename, display name)
  - Type (supervisor, trader, researcher, deterministic)
  - Model (which LLM model key it uses)
  - Tools (which tool categories it has access to)
  - Checks/actions (for supervisor-type agents)
  - Schedule (how often it runs)
  - Dependencies (other agents it requires)

Manifests live in: config/agents/<agent_id>.yaml
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_MANIFEST_DIR = Path(__file__).resolve().parent.parent / "config" / "agents"

# Required fields for all agent types
_REQUIRED_FIELDS = {"id", "type", "display_name"}

# Valid agent types
_VALID_TYPES = {"supervisor", "trader", "researcher", "analyst", "deterministic", "monitor"}


@dataclass
class AgentManifest:
    """Parsed and validated agent manifest."""
    id: str
    type: str
    display_name: str
    codename: str = ""
    description: str = ""
    model_key: str = "minimax"
    tool_categories: list[str] = field(default_factory=list)
    schedule_s: int = 0          # 0 = event-driven, >0 = periodic
    dependencies: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)  # type-specific config

    # Supervisor-specific
    checks: list[dict] = field(default_factory=list)
    actions: list[dict] = field(default_factory=list)
    escalation: dict[str, Any] = field(default_factory=dict)
    thresholds_file: str = ""

    @property
    def is_periodic(self) -> bool:
        return self.schedule_s > 0

    def summary(self) -> str:
        tools = ", ".join(self.tool_categories) if self.tool_categories else "none"
        deps = ", ".join(self.dependencies) if self.dependencies else "none"
        return (
            f"{self.display_name} ({self.id})\n"
            f"  Type: {self.type} | Model: {self.model_key}\n"
            f"  Tools: {tools}\n"
            f"  Schedule: {'every ' + str(self.schedule_s) + 's' if self.is_periodic else 'event-driven'}\n"
            f"  Dependencies: {deps}"
        )


def load_manifest(path: Path) -> AgentManifest:
    """Load and validate a single manifest from YAML."""
    with open(path) as f:
        raw = yaml.safe_load(f)

    # Support both flat and nested formats
    data = raw.get("agent", raw)

    # Validate required fields
    missing = _REQUIRED_FIELDS - set(data.keys())
    if missing:
        raise ValueError(f"Manifest {path.name}: missing required fields: {missing}")

    agent_type = data.get("type", "")
    if agent_type not in _VALID_TYPES:
        raise ValueError(
            f"Manifest {path.name}: invalid type '{agent_type}'. "
            f"Valid: {_VALID_TYPES}"
        )

    return AgentManifest(
        id=data["id"],
        type=data["type"],
        display_name=data["display_name"],
        codename=data.get("codename", data["id"]),
        description=data.get("description", ""),
        model_key=data.get("model_key", "minimax"),
        tool_categories=data.get("tool_categories", []),
        schedule_s=data.get("schedule_s", 0),
        dependencies=data.get("dependencies", []),
        config=data.get("config", {}),
        checks=data.get("checks", []),
        actions=data.get("actions", []),
        escalation=data.get("escalation", {}),
        thresholds_file=data.get("thresholds_file", ""),
    )


class ManifestRegistry:
    """Registry of all agent manifests. Loads from config/agents/."""

    def __init__(self, manifest_dir: Path | None = None):
        self._dir = manifest_dir or _MANIFEST_DIR
        self._manifests: dict[str, AgentManifest] = {}
        self._load_all()

    def _load_all(self) -> None:
        """Load all YAML manifests from the directory."""
        if not self._dir.exists():
            logger.warning(f"Manifest directory not found: {self._dir}")
            return

        for path in sorted(self._dir.glob("*.yaml")):
            try:
                manifest = load_manifest(path)
                self._manifests[manifest.id] = manifest
                logger.debug(f"Loaded manifest: {manifest.id}")
            except Exception as e:
                logger.error(f"Failed to load {path.name}: {e}")

    def get(self, agent_id: str) -> AgentManifest | None:
        return self._manifests.get(agent_id)

    def all(self) -> list[AgentManifest]:
        return list(self._manifests.values())

    def by_type(self, agent_type: str) -> list[AgentManifest]:
        return [m for m in self._manifests.values() if m.type == agent_type]

    def ids(self) -> list[str]:
        return list(self._manifests.keys())

    def summary(self) -> str:
        lines = [f"Agent Registry ({len(self._manifests)} agents):"]
        for m in self._manifests.values():
            lines.append(f"  {m.id:20s} | {m.type:12s} | {m.model_key:10s} | {m.display_name}")
        return "\n".join(lines)

    def validate_dependencies(self) -> list[str]:
        """Check that all declared dependencies exist. Returns list of errors."""
        errors = []
        known_ids = set(self._manifests.keys())
        for m in self._manifests.values():
            for dep in m.dependencies:
                if dep not in known_ids:
                    errors.append(f"{m.id}: dependency '{dep}' not found in registry")
        return errors

    def __len__(self) -> int:
        return len(self._manifests)

    def __contains__(self, agent_id: str) -> bool:
        return agent_id in self._manifests
