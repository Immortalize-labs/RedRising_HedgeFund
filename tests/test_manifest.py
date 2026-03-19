"""
Tests for agents/manifest.py
"""
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.manifest import load_manifest, ManifestRegistry, AgentManifest


MANIFEST_DIR = ROOT / "config" / "agents"


class TestLoadManifest:

    def test_load_ares(self):
        m = load_manifest(MANIFEST_DIR / "ares.yaml")
        assert m.id == "ares"
        assert m.type == "supervisor"
        assert m.display_name == "QA Monitor"
        assert len(m.checks) == 6
        assert len(m.actions) == 3

    def test_load_debate_team(self):
        m = load_manifest(MANIFEST_DIR / "debate_team.yaml")
        assert m.id == "debate_team"
        assert m.type == "researcher"
        assert not m.is_periodic

    def test_load_live_trader(self):
        m = load_manifest(MANIFEST_DIR / "live_trader.yaml")
        assert m.id == "live_trader"
        assert m.type == "trader"
        assert m.is_periodic
        assert m.schedule_s == 300
        assert len(m.config["active_instances"]) == 7

    def test_load_redeemer(self):
        m = load_manifest(MANIFEST_DIR / "redeemer.yaml")
        assert m.id == "redeemer"
        assert m.type == "deterministic"

    def test_load_drawdown_monitor(self):
        m = load_manifest(MANIFEST_DIR / "drawdown_monitor.yaml")
        assert m.id == "drawdown_monitor"
        assert m.type == "monitor"

    def test_invalid_type_raises(self, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text("agent:\n  id: x\n  type: invalid\n  display_name: X\n")
        with pytest.raises(ValueError, match="invalid type"):
            load_manifest(bad)

    def test_missing_required_raises(self, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text("agent:\n  id: x\n")
        with pytest.raises(ValueError, match="missing required"):
            load_manifest(bad)


class TestManifestRegistry:

    def test_load_all(self):
        reg = ManifestRegistry(MANIFEST_DIR)
        assert len(reg) >= 5  # ares, debate_team, live_trader, redeemer, drawdown_monitor
        assert "ares" in reg
        assert "live_trader" in reg

    def test_get_by_type(self):
        reg = ManifestRegistry(MANIFEST_DIR)
        supervisors = reg.by_type("supervisor")
        assert any(m.id == "ares" for m in supervisors)

    def test_summary(self):
        reg = ManifestRegistry(MANIFEST_DIR)
        s = reg.summary()
        assert "Agent Registry" in s
        assert "ares" in s

    def test_validate_dependencies(self):
        reg = ManifestRegistry(MANIFEST_DIR)
        errors = reg.validate_dependencies()
        # live_trader depends on ares which exists
        assert not errors, f"Dependency errors: {errors}"

    def test_manifest_summary(self):
        reg = ManifestRegistry(MANIFEST_DIR)
        m = reg.get("ares")
        s = m.summary()
        assert "QA Monitor" in s
        assert "supervisor" in s


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
