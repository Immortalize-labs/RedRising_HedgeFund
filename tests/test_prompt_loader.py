"""
Tests for core.prompts.loader — PromptLoader, PromptTemplate
=============================================================
Covers:
  - Template loading from YAML
  - Variable substitution
  - Few-shot example inclusion
  - System prompt and model config extraction
  - get_loader() singleton
  - trade_decision and risk_check templates specifically
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

# Project root on path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.prompts.loader import PromptLoader, PromptTemplate, get_loader


# ─── Fixtures ─────────────────────────────────────────────────────────────────

MINIMAL_TEMPLATE = {
    "name": "test_template",
    "version": "1.0",
    "model": "deepseek",
    "temperature": 0.0,
    "max_tokens": 256,
    "system": "You are a test assistant.",
    "prompt_template": "Symbol: {symbol}\nPrice: {price}\nDo something.",
    "output_schema": {
        "type": "object",
        "required": ["action"],
        "properties": {
            "action": {"type": "string"},
        },
    },
    "examples": [
        {
            "input": {"symbol": "BTC", "price": "84000"},
            "output": '{"action": "BUY"}',
        },
        {
            "input": {"symbol": "ETH", "price": "3200"},
            "output": '{"action": "SELL"}',
        },
    ],
}


@pytest.fixture
def tmp_templates_dir(tmp_path):
    """Create a temporary templates directory with a test template."""
    tmpl_dir = tmp_path / "templates"
    tmpl_dir.mkdir()
    # Write the minimal template
    (tmpl_dir / "test_template.yaml").write_text(yaml.dump(MINIMAL_TEMPLATE))
    return tmpl_dir


@pytest.fixture
def loader(tmp_templates_dir):
    """PromptLoader pointed at the temp directory."""
    return PromptLoader(templates_dir=tmp_templates_dir)


@pytest.fixture
def template(tmp_templates_dir):
    """Load the test PromptTemplate directly."""
    loader = PromptLoader(templates_dir=tmp_templates_dir)
    return loader.get("test_template")


# ─── PromptTemplate tests ─────────────────────────────────────────────────────

class TestPromptTemplate:
    """Test PromptTemplate render logic and metadata."""

    def test_template_loads_metadata(self, template):
        assert template.name == "test_template"
        assert template.version == "1.0"
        assert template.model == "deepseek"
        assert template.temperature == 0.0
        assert template.max_tokens == 256
        assert template.system == "You are a test assistant."

    def test_template_has_output_schema(self, template):
        assert template.output_schema["type"] == "object"
        assert "action" in template.output_schema["required"]

    def test_template_has_examples(self, template):
        assert len(template.examples) == 2
        assert template.examples[0]["input"]["symbol"] == "BTC"
        assert template.examples[1]["input"]["symbol"] == "ETH"

    def test_render_substitutes_variables(self, template):
        rendered = template.render({"symbol": "XRP", "price": "0.5812"})
        assert "XRP" in rendered
        assert "0.5812" in rendered
        assert "{symbol}" not in rendered
        assert "{price}" not in rendered

    def test_render_leaves_missing_vars_as_placeholders(self, template):
        """Variables not in the dict remain as {var} in the output."""
        rendered = template.render({"symbol": "SOL"})
        # {price} is not substituted
        assert "{price}" in rendered

    def test_render_converts_non_string_values(self, template):
        rendered = template.render({"symbol": "BTC", "price": 84250.0})
        assert "84250.0" in rendered

    def test_render_with_examples_includes_example_block(self, template):
        rendered = template.render_with_examples(
            {"symbol": "DOGE", "price": "0.12"}, n_examples=2
        )
        assert "## Examples" in rendered
        assert "Example 1" in rendered
        assert "Example 2" in rendered
        # BTC example input should appear
        assert "BTC" in rendered
        # The actual prompt should appear after the examples
        assert "DOGE" in rendered
        assert "Your Turn" in rendered

    def test_render_with_examples_respects_n_examples(self, template):
        rendered_1 = template.render_with_examples(
            {"symbol": "BTC", "price": "84000"}, n_examples=1
        )
        rendered_2 = template.render_with_examples(
            {"symbol": "BTC", "price": "84000"}, n_examples=2
        )
        # With n_examples=1 we get "Example 1" but not "Example 2"
        assert "Example 1" in rendered_1
        assert "Example 2" not in rendered_1
        assert "Example 2" in rendered_2

    def test_render_with_zero_examples_skips_individual_examples(self, template):
        """With n_examples=0, no individual example content is shown.
        The header/footer may still appear depending on implementation.
        The key assertion: no numbered Example N blocks and no example input."""
        rendered = template.render_with_examples(
            {"symbol": "BTC", "price": "84000"}, n_examples=0
        )
        # No individual example entries (no "Example 1", "Example 2" etc.)
        assert "### Example 1" not in rendered
        assert "### Example 2" not in rendered
        # The actual prompt variables ARE substituted
        assert "BTC" in rendered
        assert "84000" in rendered

    def test_render_output_is_string(self, template):
        result = template.render({"symbol": "BTC", "price": "84000"})
        assert isinstance(result, str)


# ─── PromptLoader tests ───────────────────────────────────────────────────────

class TestPromptLoader:
    """Test PromptLoader file loading, caching, and convenience API."""

    def test_get_returns_template(self, loader):
        t = loader.get("test_template")
        assert t is not None
        assert isinstance(t, PromptTemplate)

    def test_get_returns_none_for_missing(self, loader):
        t = loader.get("nonexistent_template")
        assert t is None

    def test_get_caches_on_second_call(self, loader):
        t1 = loader.get("test_template")
        t2 = loader.get("test_template")
        assert t1 is t2  # same object from cache

    def test_reload_clears_cache(self, loader):
        t1 = loader.get("test_template")
        loader.reload("test_template")
        t2 = loader.get("test_template")
        # After reload the cache is cleared; new object loaded from disk
        assert t1 is not t2

    def test_reload_all_clears_all_cache(self, loader):
        loader.get("test_template")
        assert "test_template" in loader._cache
        loader.reload()
        assert loader._cache == {}

    def test_render_convenience(self, loader):
        text = loader.render("test_template", {"symbol": "BTC", "price": "84000"})
        assert "BTC" in text
        assert isinstance(text, str)

    def test_render_with_examples_flag(self, loader):
        text = loader.render(
            "test_template",
            {"symbol": "BTC", "price": "84000"},
            with_examples=True,
        )
        assert "## Examples" in text

    def test_render_raises_on_missing_template(self, loader):
        with pytest.raises(ValueError, match="not found"):
            loader.render("nonexistent", {"symbol": "BTC"})

    def test_list_templates(self, loader):
        names = loader.list_templates()
        assert "test_template" in names

    def test_custom_templates_dir(self, tmp_path):
        """PromptLoader can be pointed at a custom directory."""
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()
        (custom_dir / "custom_tmpl.yaml").write_text(yaml.dump({
            "name": "custom_tmpl",
            "prompt_template": "Hello {name}!",
        }))
        custom_loader = PromptLoader(templates_dir=custom_dir)
        t = custom_loader.get("custom_tmpl")
        assert t is not None
        assert t.render({"name": "Tactus"}) == "Hello Tactus!"


# ─── Singleton tests ──────────────────────────────────────────────────────────

class TestGetLoader:
    """Test the module-level get_loader() singleton factory."""

    def test_get_loader_returns_prompt_loader(self):
        import core.prompts.loader as loader_module
        # Reset singleton to test fresh creation
        loader_module._loader = None
        l1 = get_loader()
        assert isinstance(l1, PromptLoader)

    def test_get_loader_returns_same_instance(self):
        import core.prompts.loader as loader_module
        loader_module._loader = None
        l1 = get_loader()
        l2 = get_loader()
        assert l1 is l2

    def test_get_loader_uses_default_templates_dir(self):
        import core.prompts.loader as loader_module
        loader_module._loader = None
        l = get_loader()
        expected = ROOT / "config" / "prompts" / "templates"
        assert l._dir == expected


# ─── Live template tests (trade_decision.yaml, risk_check.yaml) ───────────────

class TestLiveTemplates:
    """
    Validate the actual trade_decision and risk_check templates that live
    traders use. These tests load from the real config/prompts/templates/ dir.
    """

    @pytest.fixture
    def real_loader(self):
        return PromptLoader()  # uses default templates dir

    def test_trade_decision_template_loads(self, real_loader):
        t = real_loader.get("trade_decision")
        assert t is not None, "trade_decision.yaml not found in templates dir"

    def test_trade_decision_model_is_deepseek(self, real_loader):
        t = real_loader.get("trade_decision")
        assert t.model == "deepseek"

    def test_trade_decision_has_system_prompt(self, real_loader):
        t = real_loader.get("trade_decision")
        assert len(t.system) > 20
        assert "portfolio" in t.system.lower() or "trader" in t.system.lower()

    def test_trade_decision_has_output_schema(self, real_loader):
        t = real_loader.get("trade_decision")
        required = t.output_schema.get("required", [])
        for field in ["direction", "confidence", "size_usd", "reasoning"]:
            assert field in required, f"Missing required field: {field}"

    def test_trade_decision_has_three_examples(self, real_loader):
        t = real_loader.get("trade_decision")
        assert len(t.examples) >= 3, f"Expected >= 3 examples, got {len(t.examples)}"

    def test_trade_decision_renders_all_required_variables(self, real_loader):
        t = real_loader.get("trade_decision")
        variables = {
            "symbol": "BTC",
            "timeframe": "15m",
            "price": "84250",
            "timestamp": "2026-03-19 06:00 EST",
            "signals_block": "XGB prediction: LONG\nXGB probability: 0.6200\nConfidence: 0.1200",
            "current_exposure": "350.00",
            "open_positions": "ETH-15m LONG $200",
            "today_pnl": "+12.40",
            "last_5_outcomes": "W W L W W",
            "rolling_wr": "56.0",
        }
        rendered = t.render(variables)
        assert "BTC" in rendered
        assert "84250" in rendered
        assert "XGB prediction: LONG" in rendered
        # No unreplaced placeholders remain for the provided variables
        for key in variables:
            assert f"{{{key}}}" not in rendered, f"Variable {{{key}}} was not substituted"

    def test_trade_decision_render_with_examples(self, real_loader):
        t = real_loader.get("trade_decision")
        variables = {
            "symbol": "ETH",
            "timeframe": "15m",
            "price": "3180",
            "timestamp": "2026-03-19 06:00 EST",
            "signals_block": "XGB prediction: SHORT\nXGB probability: 0.7100\nConfidence: 0.2100",
            "current_exposure": "0.00",
            "open_positions": "none",
            "today_pnl": "+5.60",
            "last_5_outcomes": "W W W L W",
            "rolling_wr": "55.0",
        }
        rendered = t.render_with_examples(variables)
        assert "## Examples" in rendered
        assert "Your Turn" in rendered
        assert "ETH" in rendered

    def test_risk_check_template_loads(self, real_loader):
        t = real_loader.get("risk_check")
        assert t is not None, "risk_check.yaml not found in templates dir"

    def test_risk_check_model_is_configured(self, real_loader):
        t = real_loader.get("risk_check")
        # Model must be one we know about
        assert t.model in ("minimax", "deepseek", "deepseek-chat", "haiku", "gpt-mini")

    def test_risk_check_has_system_prompt(self, real_loader):
        t = real_loader.get("risk_check")
        assert len(t.system) > 20
        assert "risk" in t.system.lower() or "limit" in t.system.lower()

    def test_risk_check_output_schema_has_decision(self, real_loader):
        t = real_loader.get("risk_check")
        required = t.output_schema.get("required", [])
        for field in ["decision", "risk_score", "violations", "adjusted_size_usd"]:
            assert field in required, f"Missing required field: {field}"

    def test_risk_check_renders_all_required_variables(self, real_loader):
        t = real_loader.get("risk_check")
        variables = {
            "symbol": "BTC",
            "direction": "LONG",
            "proposed_size": "300",
            "confidence": "0.68",
            "total_exposure": "800.00",
            "open_positions": "ETH LONG $400, XRP SHORT $400",
            "today_pnl": "+8.50",
            "today_loss": "12.00",
            "drawdown_pct": "0.80",
            "last_10_outcomes": "W W L W W L W W L W",
            "wr_last_10": "70.0",
            "correlation": "0.75 with ETH position",
        }
        rendered = t.render(variables)
        assert "BTC" in rendered
        assert "LONG" in rendered
        for key in variables:
            assert f"{{{key}}}" not in rendered, f"Variable {{{key}}} was not substituted"

    def test_risk_check_examples_have_valid_json_output(self, real_loader):
        t = real_loader.get("risk_check")
        for i, ex in enumerate(t.examples):
            output_str = ex.get("output", "").strip()
            try:
                parsed = json.loads(output_str)
            except json.JSONDecodeError as e:
                pytest.fail(f"risk_check example {i} output is not valid JSON: {e}")
            assert "decision" in parsed, f"Example {i} missing 'decision'"
            assert parsed["decision"] in ("APPROVE", "REJECT", "REDUCE"), \
                f"Example {i}: invalid decision '{parsed['decision']}'"

    def test_trade_decision_examples_have_valid_json_output(self, real_loader):
        t = real_loader.get("trade_decision")
        for i, ex in enumerate(t.examples):
            output_str = ex.get("output", "").strip()
            try:
                parsed = json.loads(output_str)
            except json.JSONDecodeError as e:
                pytest.fail(f"trade_decision example {i} output is not valid JSON: {e}")
            assert "direction" in parsed, f"Example {i} missing 'direction'"
            assert parsed["direction"] in ("LONG", "SHORT", "FLAT"), \
                f"Example {i}: invalid direction '{parsed['direction']}'"
            assert 0.0 <= parsed["confidence"] <= 1.0, \
                f"Example {i}: confidence out of range"
            assert 0 <= parsed["size_usd"] <= 500, \
                f"Example {i}: size_usd out of range"


# ─── Variable substitution edge cases ────────────────────────────────────────

class TestVariableSubstitution:
    """Edge cases for the {variable} substitution logic."""

    def test_extra_variables_are_ignored(self, template):
        # Variables not in the template are just not used — no error
        rendered = template.render({"symbol": "BTC", "price": "84000", "extra_key": "ignored"})
        assert "ignored" not in rendered

    def test_integer_value_is_coerced_to_string(self, template):
        rendered = template.render({"symbol": "SOL", "price": 185})
        assert "185" in rendered

    def test_float_value_is_coerced_to_string(self, template):
        rendered = template.render({"symbol": "SOL", "price": 185.75})
        assert "185.75" in rendered

    def test_empty_string_value(self, template):
        rendered = template.render({"symbol": "", "price": "100"})
        assert "{symbol}" not in rendered

    def test_multiple_occurrences_of_same_variable(self, tmp_templates_dir, loader):
        """If a variable appears twice in the template, both are substituted."""
        (tmp_templates_dir / "multi.yaml").write_text(yaml.dump({
            "name": "multi",
            "prompt_template": "Symbol: {symbol}. Again: {symbol}.",
        }))
        loader.reload()
        t = loader.get("multi")
        rendered = t.render({"symbol": "XRP"})
        assert rendered == "Symbol: XRP. Again: XRP."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
