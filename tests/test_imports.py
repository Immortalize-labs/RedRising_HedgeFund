"""Smoke test: verify critical production modules are importable."""
from __future__ import annotations

import importlib

import pytest

MODULES = [
    "core.risk.guardian",
    "agents.live.alignment_checker",
]


@pytest.mark.parametrize("module_path", MODULES)
def test_import(module_path):
    """Each critical module must import without error."""
    importlib.import_module(module_path)
