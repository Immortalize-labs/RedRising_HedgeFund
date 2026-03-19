"""
Agent Supervisor
================
Runs configured checks against active strategies and fires actions when
failure thresholds are reached.

Each supervisor is defined by a YAML manifest file:

    agent:
      id: "ares"
      codename: "Ares"
      checks:
        - name: freshness
          module: agents.checks.freshness
          function: check_trade_freshness
          interval_s: 60
          scope: per_strategy
      actions:
        - name: escalate_freshness
          module: agents.actions.notify
          function: send_escalation
          authority: escalate
          trigger:
            check: freshness
            consecutive_failures: 2
          cooldown_s: 300
          max_per_day: 10

Usage::

    sup = AgentSupervisor(Path("agents/manifests/ares.yaml"))
    incidents = sup.run_cycle()
"""
from __future__ import annotations

import importlib
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from agents.incident_log import IncidentLog

logger = logging.getLogger(__name__)
EST = timezone(timedelta(hours=-5))


class AgentSupervisor:
    """Runs check/action cycles driven by a YAML manifest."""

    def __init__(self, manifest_path: Path):
        self._manifest_path = Path(manifest_path)
        spec = self._load_manifest()

        agent_spec = spec["agent"]
        self.agent_id: str = agent_spec["id"]
        self.codename: str = agent_spec.get("codename", self.agent_id)

        self.checks: list[dict] = self._bind_functions(agent_spec.get("checks", []), "check")
        self.actions: list[dict] = self._bind_functions(agent_spec.get("actions", []), "action")

        self.incident_log = IncidentLog(self.agent_id)
        self._failure_counts: dict[str, int] = {}   # key: "check_name:strategy_name"
        self._last_action_time: dict[str, float] = {}
        self._daily_action_counts: dict[str, int] = {}
        self._daily_reset_date: str = date.today().isoformat()

        # Strategy registry — can be replaced in tests
        self._registry: Any = None

    # ── Public API ─────────────────────────────────────────────────────────

    def run_cycle(self) -> list[dict]:
        """
        Run one check cycle across all active strategies.

        Returns list of incident dicts generated this cycle.
        """
        self._reset_daily_if_needed()
        incidents: list[dict] = []

        strategies = self._get_active_strategies()

        for strategy in strategies:
            for check in self.checks:
                key = f"{check['name']}:{strategy.id}"
                ok, detail = self._run_check(check, strategy)

                if ok:
                    # Recovery
                    if key in self._failure_counts and self._failure_counts[key] > 0:
                        incident = {
                            "check": check["name"],
                            "strategy": strategy.id,
                            "result": "recovered",
                            "detail": detail,
                        }
                        incidents.append(incident)
                        self.incident_log.record(incident)
                    self._failure_counts[key] = 0
                else:
                    # Failure
                    self._failure_counts[key] = self._failure_counts.get(key, 0) + 1
                    consecutive = self._failure_counts[key]
                    incident = {
                        "check": check["name"],
                        "strategy": strategy.id,
                        "result": "fail",
                        "detail": detail,
                        "consecutive": consecutive,
                    }
                    incidents.append(incident)
                    self.incident_log.record(incident)

                    # Fire matching actions
                    for action in self._matching_actions(check["name"], consecutive):
                        self._fire_action(action, strategy, check, detail)

        return incidents

    # ── Internal ───────────────────────────────────────────────────────────

    def _run_check(self, check: dict, strategy) -> tuple[bool, str]:
        """Execute a check function against a strategy."""
        try:
            fn = check["_fn"]
            result = fn(strategy)
            if isinstance(result, tuple):
                return result
            return bool(result), ""
        except Exception as e:
            logger.warning("[%s] check %s raised: %s", self.agent_id, check["name"], e)
            return False, str(e)

    def _matching_actions(self, check_name: str, consecutive: int) -> list[dict]:
        """Return actions whose trigger matches the check + consecutive count."""
        matches = []
        for action in self.actions:
            trigger = action.get("trigger", {})
            trigger_check = trigger.get("check", "")
            threshold = trigger.get("consecutive_failures", 1)
            # Wildcard "*" matches any check
            if trigger_check not in (check_name, "*"):
                continue
            if consecutive >= threshold:
                matches.append(action)
        return matches

    def _fire_action(self, action: dict, strategy, check: dict, detail: str) -> None:
        """Fire an action if cooldown and daily limit allow."""
        name = action["name"]
        now = datetime.now(EST).timestamp()

        # Cooldown check
        cooldown_s = action.get("cooldown_s", 0)
        last = self._last_action_time.get(name, 0)
        if cooldown_s > 0 and (now - last) < cooldown_s:
            return

        # Daily limit check
        max_per_day = action.get("max_per_day", 9999)
        if self._check_daily_limit(name, max_per_day):
            logger.info("[%s] action %s at daily limit", self.agent_id, name)
            return

        # Execute
        try:
            fn = action["_fn"]
            result = fn(
                agent_id=self.agent_id,
                action_name=name,
                check=check["name"],
                strategy=strategy.id,
                detail=detail,
            )
            self._last_action_time[name] = now
            self._daily_action_counts[name] = self._daily_action_counts.get(name, 0) + 1
            logger.info("[%s] action %s fired: %s", self.agent_id, name, result)
        except Exception as e:
            logger.warning("[%s] action %s failed: %s", self.agent_id, name, e)

    def _check_daily_limit(self, action_name: str, max_per_day: int) -> bool:
        """Return True if daily limit reached."""
        return self._daily_action_counts.get(action_name, 0) >= max_per_day

    def _reset_daily_if_needed(self) -> None:
        today = date.today().isoformat()
        if today != self._daily_reset_date:
            self._daily_action_counts.clear()
            self._daily_reset_date = today

    def _get_active_strategies(self) -> list:
        """Get active strategies from registry (or empty list)."""
        if self._registry is not None:
            return self._registry.active()
        try:
            from config.strategy_registry import StrategyRegistry
            return StrategyRegistry().active()
        except Exception:
            return []

    def _load_manifest(self) -> dict:
        with open(self._manifest_path) as f:
            return yaml.safe_load(f)

    def _bind_functions(self, specs: list[dict], kind: str) -> list[dict]:
        """Import and bind _fn for each spec dict."""
        bound = []
        for spec in specs:
            entry = dict(spec)
            module_name = spec.get("module", "")
            fn_name = spec.get("function", "")
            try:
                mod = importlib.import_module(module_name)
                entry["_fn"] = getattr(mod, fn_name)
            except (ImportError, AttributeError) as e:
                logger.warning("Cannot bind %s.%s: %s", module_name, fn_name, e)
                err_msg = f"unbound: {e}"
                entry["_fn"] = lambda *a, _msg=err_msg, **kw: (False, _msg)
            bound.append(entry)
        return bound
