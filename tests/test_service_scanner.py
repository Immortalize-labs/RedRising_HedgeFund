"""
Tests for scripts/service_scanner.py
=====================================
All systemctl calls are mocked — tests run on any OS (macOS, CI, EC2).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import service_scanner as ss
from service_scanner import (
    INFRA_SERVICES,
    RogueService,
    ServiceInfo,
    _matches_detection_pattern,
    _parse_systemctl_output,
    auto_kill_rogues,
    build_authorized_set,
    format_report,
    scan,
    stop_service,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_SYSTEMCTL_OUTPUT = """\
polymarket-btc-15m-trader.service    loaded active running Polymarket BTC 15m Trader
polymarket-eth-15m-trader.service    loaded active running Polymarket ETH 15m Trader
polymarket-xrp-15m-trader.service    loaded active running Polymarket XRP 15m Trader
polymarket-eth-trader.service        loaded active running Polymarket ETH Trader
btc-15m-settlement.service           loaded active running BTC 15m Settlement
eth-15m-settlement.service           loaded active running ETH 15m Settlement
xrp-15m-settlement.service          loaded active running XRP 15m Settlement
polymarket-dashboard.service         loaded active running Dashboard
polymarket-redeemer.service          loaded active running Redeemer
health-monitor.service               loaded active running Health Monitor
drawdown-monitor.service             loaded active running Drawdown Monitor
ssh.service                          loaded active running OpenSSH
cron.service                         loaded active running Cron Daemon
systemd-resolved.service             loaded active running Network Name Resolution
"""

ROGUE_OUTPUT = """\
momentum-live.service                loaded active running Momentum Live Trader
polymarket-btc-15m-trader.service    loaded active running Polymarket BTC 15m Trader
polymarket-dashboard.service         loaded active running Dashboard
eth-xgb-settlement.service           loaded active running ETH Settlement
weird-strategy-v3.service            loaded active running Weird Strategy
ssh.service                          loaded active running OpenSSH
"""

AUTHORIZED_SAMPLE: frozenset[str] = frozenset([
    # Active strategy services
    "polymarket-btc-15m-trader",
    "polymarket-eth-15m-trader",
    "polymarket-xrp-15m-trader",
    "polymarket-eth-trader",
    "btc-15m-settlement",
    "eth-15m-settlement",
    "xrp-15m-settlement",
    # Infra
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


# ── Parsing Tests ─────────────────────────────────────────────────────────────

class TestParseSystemctlOutput:
    def test_parses_correct_number_of_services(self):
        services = _parse_systemctl_output(SAMPLE_SYSTEMCTL_OUTPUT)
        # 14 lines, all end with .service
        assert len(services) == 14

    def test_strips_service_suffix_from_name(self):
        services = _parse_systemctl_output(SAMPLE_SYSTEMCTL_OUTPUT)
        names = {s.name for s in services}
        assert "polymarket-btc-15m-trader" in names
        assert "polymarket-btc-15m-trader.service" not in names

    def test_preserves_full_name(self):
        services = _parse_systemctl_output(SAMPLE_SYSTEMCTL_OUTPUT)
        full_names = {s.full_name for s in services}
        assert "polymarket-btc-15m-trader.service" in full_names

    def test_active_state_parsed(self):
        services = _parse_systemctl_output(SAMPLE_SYSTEMCTL_OUTPUT)
        svc = next(s for s in services if s.name == "polymarket-btc-15m-trader")
        assert svc.active_state == "active"
        assert svc.sub_state == "running"
        assert svc.load_state == "loaded"

    def test_ignores_non_service_lines(self):
        output = "some.socket  loaded active running Socket\n"
        services = _parse_systemctl_output(output)
        assert len(services) == 0

    def test_handles_empty_output(self):
        assert _parse_systemctl_output("") == []

    def test_handles_whitespace_only(self):
        assert _parse_systemctl_output("   \n  \n") == []

    def test_skips_short_lines(self):
        output = "bad.service loaded\n"
        services = _parse_systemctl_output(output)
        assert len(services) == 0


# ── Detection Pattern Tests ───────────────────────────────────────────────────

class TestDetectionPatterns:
    @pytest.mark.parametrize("name", [
        "polymarket-eth-trader",
        "polymarket-btc-15m-trader",
        "polymarket-momentum-trader",
        "eth-xgb-settlement",
        "btc-15m-settlement",
        "xrp-xgb-settlement",
        "mom-settlement",
        "momentum-live",
        "eth-strategy-v2",
        "btc-trading-engine",
        "strategy-monitor",
        "live-trader-eth",
        "polymarket-redeemer",
        "polymarket-dashboard",
        "xgb-settlement",
        "qkelly-settlement",
    ])
    def test_matches_trading_related(self, name):
        assert _matches_detection_pattern(name) is True, \
            f"'{name}' should match detection patterns"

    @pytest.mark.parametrize("name", [
        "ssh",
        "cron",
        "systemd-resolved",
        "nginx",
        "ufw",
        "ntp",
        "fail2ban",
        "docker",
        "rsyslog",
        "snapd",
        "accounts-daemon",
    ])
    def test_no_match_for_unrelated(self, name):
        assert _matches_detection_pattern(name) is False, \
            f"'{name}' should not match detection patterns"


# ── Authorized Set Tests ──────────────────────────────────────────────────────

class TestBuildAuthorizedSet:
    def test_includes_infra_services(self):
        authorized = build_authorized_set()
        for svc in INFRA_SERVICES:
            assert svc in authorized, f"infra service '{svc}' should always be authorized"

    def test_includes_active_strategy_services(self):
        """Active strategies from strategies.yaml should be authorized."""
        authorized = build_authorized_set()
        # btc-15m, eth-15m, xrp-15m are active in strategies.yaml
        assert "polymarket-btc-15m-trader" in authorized
        assert "polymarket-eth-15m-trader" in authorized
        assert "polymarket-xrp-15m-trader" in authorized

    def test_does_not_include_killed_strategy_services(self):
        """Killed strategies must NOT appear in the authorized set."""
        authorized = build_authorized_set()
        # momentum, btc-5m, eth-5m-w2, xrp-5m, qkelly are all killed
        assert "polymarket-momentum-trader" not in authorized
        assert "polymarket-trader" not in authorized       # btc-5m
        assert "polymarket-eth-v1-trader" not in authorized
        assert "polymarket-xrp-trader" not in authorized

    def test_killed_settlement_services_not_authorized(self):
        authorized = build_authorized_set()
        assert "eth-xgb-settlement" not in authorized     # eth-5m (killed)
        assert "xrp-xgb-settlement" not in authorized     # xrp-5m (killed)
        assert "xgb-settlement" not in authorized          # btc-5m (killed)
        assert "mom-settlement" not in authorized          # momentum (killed)
        assert "qkelly-settlement" not in authorized       # qkelly (killed)


# ── Scan Logic Tests ──────────────────────────────────────────────────────────

class TestScan:
    def _make_units(self, names: list[str]) -> list[ServiceInfo]:
        return [
            ServiceInfo(
                name=n,
                full_name=f"{n}.service",
                active_state="active",
                sub_state="running",
                load_state="loaded",
            )
            for n in names
        ]

    def test_clean_scan_returns_empty(self):
        authorized = frozenset(["polymarket-btc-15m-trader", "polymarket-dashboard"])
        units = self._make_units(["polymarket-btc-15m-trader", "polymarket-dashboard", "ssh"])
        with patch.object(ss, "list_active_units", return_value=units):
            rogues = scan(authorized=authorized)
        assert rogues == []

    def test_rogue_detected_single(self):
        authorized = frozenset(["polymarket-btc-15m-trader"])
        units = self._make_units([
            "polymarket-btc-15m-trader",
            "momentum-live",           # not authorized
        ])
        with patch.object(ss, "list_active_units", return_value=units):
            rogues = scan(authorized=authorized)
        assert len(rogues) == 1
        assert rogues[0].name == "momentum-live"

    def test_rogue_detected_multiple(self):
        authorized = frozenset(["polymarket-btc-15m-trader", "polymarket-dashboard"])
        units = self._make_units([
            "polymarket-btc-15m-trader",
            "polymarket-dashboard",
            "momentum-live",           # rogue
            "eth-xgb-settlement",      # rogue
            "ssh",                     # fine, no pattern match
        ])
        with patch.object(ss, "list_active_units", return_value=units):
            rogues = scan(authorized=authorized)
        rogue_names = {r.name for r in rogues}
        assert "momentum-live" in rogue_names
        assert "eth-xgb-settlement" in rogue_names
        assert len(rogues) == 2

    def test_infra_services_never_flagged(self):
        authorized = AUTHORIZED_SAMPLE
        units = self._make_units(list(INFRA_SERVICES) + ["polymarket-btc-15m-trader"])
        with patch.object(ss, "list_active_units", return_value=units):
            rogues = scan(authorized=authorized)
        assert rogues == []

    def test_non_trading_services_ignored(self):
        authorized = frozenset()  # nothing authorized
        units = self._make_units(["ssh", "cron", "nginx", "docker"])
        with patch.object(ss, "list_active_units", return_value=units):
            rogues = scan(authorized=authorized)
        assert rogues == [], "Non-trading services should not be flagged even if unauthorized"

    def test_rogue_recommendation_is_stop_for_active(self):
        authorized = frozenset()
        units = [
            ServiceInfo(
                name="momentum-live",
                full_name="momentum-live.service",
                active_state="active",
                sub_state="running",
                load_state="loaded",
            )
        ]
        with patch.object(ss, "list_active_units", return_value=units):
            rogues = scan(authorized=authorized)
        assert rogues[0].recommendation == "stop"

    def test_empty_unit_list_returns_no_rogues(self):
        with patch.object(ss, "list_active_units", return_value=[]):
            rogues = scan(authorized=frozenset())
        assert rogues == []

    def test_rogue_reason_mentions_killed_strategy(self):
        """For a known killed strategy service, reason should name the strategy."""
        # momentum-live is NOT in strategies.yaml under any strategy, but
        # polymarket-momentum-trader IS the momentum killed strategy's trader.
        authorized = frozenset(["polymarket-btc-15m-trader"])
        units = [
            ServiceInfo(
                name="polymarket-momentum-trader",
                full_name="polymarket-momentum-trader.service",
                active_state="active",
                sub_state="running",
                load_state="loaded",
            )
        ]
        with patch.object(ss, "list_active_units", return_value=units):
            rogues = scan(authorized=authorized)
        assert len(rogues) == 1
        assert "momentum" in rogues[0].reason.lower()


# ── strategies.yaml Parsing via Registry ─────────────────────────────────────

class TestStrategiesYamlParsing:
    """Verify that the scanner correctly reads active/killed state from strategies.yaml."""

    def test_active_strategies_have_authorized_services(self):
        """Services derived from active strategies are in the authorized set."""
        from config.strategy_registry import StrategyRegistry
        reg = StrategyRegistry()

        from service_scanner import _load_authorized_from_yaml
        yaml_authorized = _load_authorized_from_yaml()

        for s in reg.active():
            if s.systemd_trader:
                assert s.systemd_trader in yaml_authorized, \
                    f"Active strategy {s.display_name} trader '{s.systemd_trader}' should be authorized"
            if s.systemd_settlement:
                assert s.systemd_settlement in yaml_authorized, \
                    f"Active strategy {s.display_name} settlement '{s.systemd_settlement}' should be authorized"

    def test_killed_strategies_not_in_authorized_set(self):
        """No service from a killed strategy should be authorized."""
        from config.strategy_registry import StrategyRegistry
        reg = StrategyRegistry()

        from service_scanner import _load_authorized_from_yaml
        yaml_authorized = _load_authorized_from_yaml()

        for s in reg.killed():
            if s.systemd_trader:
                assert s.systemd_trader not in yaml_authorized, \
                    f"Killed strategy {s.display_name} trader '{s.systemd_trader}' must NOT be authorized"
            if s.systemd_settlement:
                assert s.systemd_settlement not in yaml_authorized, \
                    f"Killed strategy {s.display_name} settlement '{s.systemd_settlement}' must NOT be authorized"

    def test_specific_known_killed_services_unauthorized(self):
        """Regression test for the exact services from the incident report."""
        from service_scanner import _load_authorized_from_yaml
        yaml_authorized = _load_authorized_from_yaml()

        # These were the incident services
        assert "polymarket-momentum-trader" not in yaml_authorized
        assert "eth-xgb-settlement" not in yaml_authorized


# ── Auto-Kill Tests ───────────────────────────────────────────────────────────

class TestAutoKill:
    def _rogue(self, name: str, recommendation: str = "stop") -> RogueService:
        return RogueService(
            name=name,
            full_name=f"{name}.service",
            active_state="active",
            sub_state="running",
            reason="test rogue",
            recommendation=recommendation,
        )

    def test_stop_service_calls_systemctl(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            ok, msg = stop_service("momentum-live")

        assert ok is True
        assert "momentum-live" in msg
        # Should call stop AND disable
        assert mock_run.call_count == 2
        stop_call_args = mock_run.call_args_list[0][0][0]
        assert "stop" in stop_call_args
        assert "momentum-live" in stop_call_args

    def test_stop_service_returns_false_on_nonzero_exit(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Unit not found"

        with patch("subprocess.run", return_value=mock_result):
            ok, msg = stop_service("nonexistent-service")

        assert ok is False
        assert "failed" in msg.lower() or "rc=" in msg

    def test_stop_service_handles_timeout(self):
        import subprocess
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="systemctl", timeout=15)):
            ok, msg = stop_service("some-service")
        assert ok is False
        assert "timeout" in msg.lower()

    def test_auto_kill_rogues_stops_each_rogue(self):
        rogues = [self._rogue("momentum-live"), self._rogue("eth-xgb-settlement")]
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            outcomes = auto_kill_rogues(rogues)

        assert len(outcomes) == 2
        # 2 rogues x 2 calls each (stop + disable) = 4
        assert mock_run.call_count == 4

    def test_auto_kill_skips_investigate_recommendation(self):
        rogues = [self._rogue("weird-strategy", recommendation="investigate")]
        with patch("subprocess.run") as mock_run:
            outcomes = auto_kill_rogues(rogues)
        mock_run.assert_not_called()
        assert outcomes == []

    def test_auto_kill_returns_ok_messages(self):
        rogue = self._rogue("momentum-live")
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            outcomes = auto_kill_rogues([rogue])

        assert len(outcomes) == 1
        assert outcomes[0].startswith("OK:")

    def test_auto_kill_returns_fail_messages_on_error(self):
        rogue = self._rogue("momentum-live")
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "unit not found"

        with patch("subprocess.run", return_value=mock_result):
            outcomes = auto_kill_rogues([rogue])

        assert len(outcomes) == 1
        assert outcomes[0].startswith("FAIL:")


# ── Reporting Tests ───────────────────────────────────────────────────────────

class TestFormatReport:
    def test_clean_report_says_clean(self):
        report = format_report([], AUTHORIZED_SAMPLE)
        assert "CLEAN" in report
        assert "no unauthorized" in report.lower()

    def test_rogue_report_lists_service_name(self):
        rogue = RogueService(
            name="momentum-live",
            full_name="momentum-live.service",
            active_state="active",
            sub_state="running",
            reason="killed strategy still running",
            recommendation="stop",
        )
        report = format_report([rogue], AUTHORIZED_SAMPLE)
        assert "momentum-live" in report
        assert "STOP" in report
        assert "killed strategy" in report.lower()

    def test_rogue_report_shows_count(self):
        rogues = [
            RogueService("a", "a.service", "active", "running", "r", "stop"),
            RogueService("b", "b.service", "active", "running", "r", "stop"),
        ]
        report = format_report(rogues, AUTHORIZED_SAMPLE)
        assert "2 UNAUTHORIZED" in report

    def test_report_includes_authorized_list(self):
        report = format_report([], frozenset(["polymarket-dashboard"]))
        assert "polymarket-dashboard" in report


# ── Integration: list_active_units with mocked subprocess ────────────────────

class TestListActiveUnits:
    def test_calls_systemctl_with_correct_args(self):
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            from service_scanner import list_active_units
            list_active_units()

        call_args = mock_run.call_args[0][0]
        assert "systemctl" in call_args
        assert "list-units" in call_args
        assert "--type=service" in call_args
        assert "--state=active" in call_args

    def test_returns_empty_on_filenotfound(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            from service_scanner import list_active_units
            result = list_active_units()
        assert result == []

    def test_returns_empty_on_timeout(self):
        import subprocess
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="systemctl", timeout=15)):
            from service_scanner import list_active_units
            result = list_active_units()
        assert result == []

    def test_parses_real_style_output(self):
        mock_result = MagicMock()
        mock_result.stdout = SAMPLE_SYSTEMCTL_OUTPUT
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            from service_scanner import list_active_units
            services = list_active_units()

        names = {s.name for s in services}
        assert "polymarket-btc-15m-trader" in names
        assert "polymarket-dashboard" in names
        assert "ssh" in names  # present but will be filtered out by pattern matching

    def test_rogue_output_detected_in_full_scan(self):
        """End-to-end: parse rogue output, cross-check against authorized set."""
        mock_result = MagicMock()
        mock_result.stdout = ROGUE_OUTPUT
        mock_result.returncode = 0

        authorized = frozenset([
            "polymarket-btc-15m-trader",
            "polymarket-dashboard",
        ])

        with patch("subprocess.run", return_value=mock_result):
            rogues = scan(authorized=authorized)

        rogue_names = {r.name for r in rogues}
        # momentum-live, eth-xgb-settlement, weird-strategy-v3 are rogue
        assert "momentum-live" in rogue_names
        assert "eth-xgb-settlement" in rogue_names
        # weird-strategy-v3 matches "strategy" pattern
        assert "weird-strategy-v3" in rogue_names
        # Authorized services must NOT appear
        assert "polymarket-btc-15m-trader" not in rogue_names
        assert "polymarket-dashboard" not in rogue_names
        # ssh doesn't match — must not appear
        assert "ssh" not in rogue_names
