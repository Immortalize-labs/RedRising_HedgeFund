"""
Prompt Template Loader
======================
Loads YAML prompt templates, renders with variables, provides few-shot examples.

Usage:
    from core.prompts.loader import PromptLoader

    loader = PromptLoader()
    prompt = loader.render("trade_decision", {
        "symbol": "BTC",
        "timeframe": "15m",
        "price": "84250",
        "signals_block": "RSI: 72.3\\nOFI: +0.45",
        ...
    })
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "config" / "prompts" / "templates"


class PromptTemplate:
    """A loaded prompt template with metadata."""

    def __init__(self, data: dict[str, Any], path: Path):
        self.name: str = data.get("name", path.stem)
        self.version: str = data.get("version", "0.1")
        self.model: str = data.get("model", "deepseek")
        self.temperature: float = data.get("temperature", 0.0)
        self.max_tokens: int = data.get("max_tokens", 512)
        self.system: str = data.get("system", "")
        self.prompt_template: str = data.get("prompt_template", "")
        self.output_schema: dict = data.get("output_schema", {})
        self.examples: list[dict] = data.get("examples", [])
        self.roles: dict = data.get("roles", {})
        self._raw = data
        self._path = path

    def render(self, variables: dict[str, str]) -> str:
        """Render the prompt template with variables.

        Args:
            variables: Dict mapping template variable names to values.

        Returns:
            Rendered prompt string.
        """
        prompt = self.prompt_template
        for key, value in variables.items():
            prompt = prompt.replace(f"{{{key}}}", str(value))
        return prompt

    def render_with_examples(self, variables: dict[str, str], n_examples: int = 3) -> str:
        """Render prompt with few-shot examples prepended.

        Args:
            variables: Template variables.
            n_examples: Number of examples to include (default 3).

        Returns:
            Rendered prompt with examples.
        """
        parts = []

        # Add few-shot examples
        if self.examples:
            parts.append("## Examples\n")
            for i, ex in enumerate(self.examples[:n_examples]):
                parts.append(f"### Example {i + 1}")
                if "input" in ex:
                    # Build example input from the template
                    ex_prompt = self.prompt_template
                    for key, value in ex["input"].items():
                        ex_prompt = ex_prompt.replace(f"{{{key}}}", str(value))
                    parts.append(ex_prompt.strip())
                if "output" in ex:
                    parts.append(f"**Output:**\n{ex['output'].strip()}")
                parts.append("")

            parts.append("---\n## Your Turn\n")

        # Add actual prompt
        parts.append(self.render(variables))

        return "\n".join(parts)

    def get_system_for_role(self, role: str) -> str:
        """Get system prompt for a specific role (debate templates)."""
        if role in self.roles:
            return self.roles[role].get("system", self.system)
        return self.system

    def get_model_for_role(self, role: str) -> str:
        """Get model for a specific role."""
        if role in self.roles:
            return self.roles[role].get("model", self.model)
        return self.model


class PromptLoader:
    """Loads and caches prompt templates from YAML files."""

    def __init__(self, templates_dir: Path | str | None = None):
        self._dir = Path(templates_dir) if templates_dir else _TEMPLATES_DIR
        self._cache: dict[str, PromptTemplate] = {}

    def get(self, name: str) -> PromptTemplate | None:
        """Load a template by name. Caches on first load."""
        if name in self._cache:
            return self._cache[name]

        path = self._dir / f"{name}.yaml"
        if not path.exists():
            logger.warning(f"Prompt template not found: {path}")
            return None

        try:
            data = yaml.safe_load(path.read_text())
            template = PromptTemplate(data, path)
            self._cache[name] = template
            return template
        except Exception as e:
            logger.error(f"Failed to load prompt template {name}: {e}")
            return None

    def render(self, name: str, variables: dict[str, str], with_examples: bool = False) -> str:
        """Convenience: load + render in one call."""
        template = self.get(name)
        if not template:
            raise ValueError(f"Template '{name}' not found in {self._dir}")
        if with_examples:
            return template.render_with_examples(variables)
        return template.render(variables)

    def list_templates(self) -> list[str]:
        """List all available template names."""
        return [p.stem for p in self._dir.glob("*.yaml")]

    def reload(self, name: str | None = None) -> None:
        """Clear cache, forcing reload on next access."""
        if name:
            self._cache.pop(name, None)
        else:
            self._cache.clear()


# Module-level singleton
_loader: PromptLoader | None = None


def get_loader() -> PromptLoader:
    """Get or create the module-level PromptLoader singleton."""
    global _loader
    if _loader is None:
        _loader = PromptLoader()
    return _loader
