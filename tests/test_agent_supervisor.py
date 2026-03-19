"""Tests for the Agent Supervisor framework."""

from unittest.mock import MagicMock, patch

import pytest
import yaml

from agents.incident_log import IncidentLog

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_dir(tmp_path):
    return tmp_path


@pytest.fixture
def incident_log(tmp_dir):
    return IncidentLog("test-agent", base_dir=tmp_dir)


@pytest.fixture
def minimal_manifest(tmp_dir):
    """Create a minimal manifest with mock check/action modules."""
    manifest = {
        "agent": {
            "id": "test-agent",
            "codename": "TestBot",
            "checks": [
                {
                    "name": "always_pass",
                    "module": "tests.test_agent_supervisor",
                    "function": "mock_check_pass",
                    "interval_s": 60,
                    "scope": "per_strategy",
                },
                {
                    "name": "always_fail",
                    "module": "tests.test_agent_supervisor",
                    "function": "mock_check_fail",
                    "interval_s": 60,
                    "scope": "per_strategy",
                },
            ],
            "actions": [
                {
                    "name": "test_escalate",
                    "module": "tests.test_agent_supervisor",
                    "function": "mock_action",
                    "authority": "escalate",
                    "trigger": {"check": "always_fail", "consecutive_failures": 1},
                    "cooldown_s": 0,
                },
                {
                    "name": "test_auto",
                    "module": "tests.test_agent_supervisor",
                    "function": "mock_action",
                    "authority": "auto",
                    "trigger": {"check": "always_fail", "consecutive_failures": 2},
                    "cooldown_s": 60,
                    "max_per_day": 3,
                    "dry_run_delay_s": 0,
                },
            ],
            "thresholds_file": None,
        }
    }
    path = tmp_dir / "test_manifest.yaml"
    with open(path, "w") as f:
        yaml.dump(manifest, f)
    return path


# ── Mock check/action functions (importable by manifest) ─────────────────────


def mock_check_pass(strategy, qa=None):
    return True, "all good"


def mock_check_fail(strategy, qa=None):
    return False, "something broke"


_action_calls = []


def mock_action(**kwargs):
    _action_calls.append(kwargs)
    return {"success": True, "detail": "mocked"}


# ── Mock strategy ─────────────────────────────────────────────────────────────


class MockStrategy:
    def __init__(self, name="test-strat"):
        self.display_name = name
        self.systemd_trader = f"polymarket-{name}"
        self.id = name


# ── IncidentLog Tests ─────────────────────────────────────────────────────────


class TestIncidentLog:
    def test_record_and_read(self, incident_log):
        incident_log.record({"check": "foo", "strategy": "bar", "detail": "baz"})
        entries = incident_log.all()
        assert len(entries) == 1
        assert entries[0]["check"] == "foo"
        assert "ts" in entries[0]

    def test_recent_filter(self, incident_log):
        incident_log.record({"check": "a", "strategy": "s1"})
        incident_log.record({"check": "b", "strategy": "s2"})
        recent = incident_log.recent(hours=1)
        assert len(recent) == 2

    def test_similar_count(self, incident_log):
        incident_log.record({"check": "freshness", "strategy": "eth-5m"})
        incident_log.record({"check": "freshness", "strategy": "eth-5m"})
        incident_log.record({"check": "freshness", "strategy": "btc-15m"})
        assert incident_log.similar_count("freshness", "eth-5m") == 2
        assert incident_log.similar_count("freshness", "btc-15m") == 1
        assert incident_log.similar_count("sizing", "eth-5m") == 0

    def test_empty_log(self, incident_log):
        assert incident_log.all() == []
        assert incident_log.recent() == []
        assert incident_log.similar_count("x", "y") == 0

    def test_path(self, incident_log):
        assert incident_log.path.name == "incidents.jsonl"
        assert "test-agent" in str(incident_log.path)


# ── AgentSupervisor Tests ────────────────────────────────────────────────────


class TestAgentSupervisor:
    def test_manifest_loading(self, minimal_manifest):
        from agents.supervisor import AgentSupervisor

        sup = AgentSupervisor(minimal_manifest)
        assert sup.agent_id == "test-agent"
        assert sup.codename == "TestBot"
        assert len(sup.checks) == 2
        assert len(sup.actions) == 2

    def test_check_functions_imported(self, minimal_manifest):
        from agents.supervisor import AgentSupervisor

        sup = AgentSupervisor(minimal_manifest)
        for check in sup.checks:
            assert callable(check["_fn"])

    def test_action_functions_imported(self, minimal_manifest):
        from agents.supervisor import AgentSupervisor

        sup = AgentSupervisor(minimal_manifest)
        for action in sup.actions:
            assert callable(action["_fn"])

    def test_run_cycle_detects_failures(self, minimal_manifest):
        from agents.supervisor import AgentSupervisor

        sup = AgentSupervisor(minimal_manifest)
        mock_reg = MagicMock()
        mock_reg.active.return_value = [MockStrategy("eth-5m")]
        sup._registry = mock_reg
        _action_calls.clear()
        incidents = sup.run_cycle()

        # always_fail triggers test_escalate (consecutive_failures=1)
        assert len(incidents) > 0
        fail_incidents = [i for i in incidents if i["check"] == "always_fail"]
        assert len(fail_incidents) >= 1

    def test_consecutive_failure_tracking(self, minimal_manifest):
        from agents.supervisor import AgentSupervisor

        sup = AgentSupervisor(minimal_manifest)
        mock_reg = MagicMock()
        mock_reg.active.return_value = [MockStrategy("eth-5m")]
        sup._registry = mock_reg

        # Cycle 1: always_fail hits 1 consecutive -> triggers test_escalate only
        _action_calls.clear()
        sup.run_cycle()
        cycle1_calls = len(_action_calls)

        # Cycle 2: always_fail hits 2 consecutive -> triggers test_escalate + test_auto
        sup.run_cycle()
        cycle2_calls = len(_action_calls) - cycle1_calls
        assert cycle2_calls > cycle1_calls  # more actions triggered

    def test_cooldown_respected(self, minimal_manifest):
        from agents.supervisor import AgentSupervisor

        sup = AgentSupervisor(minimal_manifest)
        mock_reg = MagicMock()
        mock_reg.active.return_value = [MockStrategy("eth-5m")]
        sup._registry = mock_reg
        _action_calls.clear()

        # Run 3 cycles — test_auto has cooldown_s=60
        sup.run_cycle()
        sup.run_cycle()
        sup.run_cycle()

        # test_auto should only fire once (cooldown blocks repeats)
        auto_calls = [
            c for c in _action_calls if c.get("action_name") == "test_auto"
        ]
        assert len(auto_calls) <= 1

    def test_daily_limit(self, minimal_manifest):
        from agents.supervisor import AgentSupervisor

        sup = AgentSupervisor(minimal_manifest)
        # Manually set daily count near limit
        sup._daily_action_counts["test_auto"] = 3
        from datetime import date
        sup._daily_reset_date = date.today().isoformat()
        assert sup._check_daily_limit("test_auto", 3) is True

    def test_incident_log_written(self, minimal_manifest):
        from agents.supervisor import AgentSupervisor

        sup = AgentSupervisor(minimal_manifest)
        mock_reg = MagicMock()
        mock_reg.active.return_value = [MockStrategy("eth-5m")]
        sup._registry = mock_reg
        sup.run_cycle()

        entries = sup.incident_log.all()
        assert len(entries) > 0

    def test_recovery_logged(self, minimal_manifest):
        from agents.supervisor import AgentSupervisor

        sup = AgentSupervisor(minimal_manifest)
        mock_reg = MagicMock()
        mock_reg.active.return_value = [MockStrategy("eth-5m")]
        sup._registry = mock_reg

        # Seed a failure state so recovery can trigger
        sup._failure_counts["always_pass:eth-5m"] = 2

        incidents = sup.run_cycle()

        recovered = [i for i in incidents if i["result"] == "recovered"]
        assert len(recovered) >= 1

    def test_wildcard_trigger(self, minimal_manifest):
        """Wildcard '*' trigger should match any check."""
        from agents.supervisor import AgentSupervisor

        sup = AgentSupervisor(minimal_manifest)
        # Add a wildcard action
        sup.actions.append({
            "name": "wildcard_alert",
            "_fn": mock_action,
            "authority": "auto",
            "trigger": {"check": "*", "consecutive_failures": 1},
            "cooldown_s": 0,
        })

        matched = sup._matching_actions("trade_freshness", 1)
        wildcard_matched = [a for a in matched if a["name"] == "wildcard_alert"]
        assert len(wildcard_matched) == 1


# ── Action Handler Tests ─────────────────────────────────────────────────────


class TestActionHandlers:
    def test_send_escalation_no_channels(self):
        """send_escalation works even if Discord/Telegram unavailable."""
        from agents.actions.notify import send_escalation

        with patch("agents.actions.notify._get_discord_sender", return_value=None), \
             patch("agents.actions.notify._get_telegram_sender", return_value=None):
            result = send_escalation(
                agent_id="ares",
                check="test",
                strategy="eth-5m",
                detail="test detail",
            )
        assert result["success"] is False
        assert result["sent_to"] == []

    def test_send_escalation_with_mock_discord(self):
        from agents.actions.notify import send_escalation

        mock_send = MagicMock(return_value=True)
        with patch("agents.actions.notify._get_discord_sender", return_value=mock_send), \
             patch("agents.actions.notify._get_telegram_sender", return_value=None):
            result = send_escalation(
                agent_id="ares",
                check="test",
                strategy="eth-5m",
                detail="test detail",
            )
        assert result["success"] is True
        assert "discord" in result["sent_to"]
        mock_send.assert_called_once()

    def test_restart_service_no_service_name(self):
        from agents.actions.infra import restart_service

        result = restart_service(
            agent_id="ares",
            check="test",
            strategy="eth-5m",
            detail="stale",
        )
        assert result["success"] is False
        assert "no service_name" in result["detail"]

    def test_trigger_rollback_escalates(self):
        from agents.actions.deploy import trigger_rollback

        with patch("agents.actions.notify._get_discord_sender", return_value=None), \
             patch("agents.actions.notify._get_telegram_sender", return_value=None):
            result = trigger_rollback(
                agent_id="ares",
                check="test",
                strategy="eth-5m",
                detail="post-deploy failure",
            )
        assert result["action"] == "escalated_rollback"
