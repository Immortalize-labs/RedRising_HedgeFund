"""
Tests for agents/base.py + agents/memory.py
============================================
Validates the pure-async agent node system (no LangGraph).
"""
import asyncio
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.memory import AgentMemory, AgentLogger, RunArtifacts
from agents.base import Tool, create_agent_node, create_tool_node


class TestAgentMemory:
    """Test persistent JSONL memory."""

    def test_record_and_retrieve_run(self, tmp_path):
        mem = AgentMemory("test-agent", base_dir=tmp_path)
        mem.record_run("run-001", "btc-15m", result={"sharpe": 1.2})
        mem.record_run("run-002", "eth-15m", result={"sharpe": 0.8})

        runs = mem.recent_runs(10)
        assert len(runs) == 2
        assert runs[0]["run_id"] == "run-001"
        assert runs[1]["result"]["sharpe"] == 0.8

    def test_add_and_query_learnings(self, tmp_path):
        mem = AgentMemory("test-agent", base_dir=tmp_path)
        mem.add_learning("pattern", "BTC mean-reverts in Asian session", confidence=0.8)
        mem.add_learning("error", "API timeout at 3am EST", confidence=0.6)
        mem.add_learning("pattern", "Volume spikes predict reversals", confidence=0.9)

        patterns = mem.learnings("pattern")
        assert len(patterns) == 2

        all_l = mem.learnings()
        assert len(all_l) == 3

    def test_context_for_llm(self, tmp_path):
        mem = AgentMemory("test-agent", base_dir=tmp_path)
        mem.record_run("r1", "btc", result={"pnl": 5.0})
        mem.add_learning("pattern", "Strong momentum signal", confidence=0.9)

        ctx = mem.get_context_for_llm()
        assert "Recent runs:" in ctx
        assert "Key learnings:" in ctx
        assert "Strong momentum signal" in ctx

    def test_empty_memory_returns_no_prior(self, tmp_path):
        mem = AgentMemory("fresh-agent", base_dir=tmp_path)
        assert mem.get_context_for_llm() == "No prior memory."

    def test_memory_persistence(self, tmp_path):
        # Write with one instance
        mem1 = AgentMemory("persist-test", base_dir=tmp_path)
        mem1.record_run("r1", "test", result={"x": 1})
        mem1.add_learning("test", "persisted learning", confidence=1.0)

        # Read with a new instance
        mem2 = AgentMemory("persist-test", base_dir=tmp_path)
        assert len(mem2.recent_runs()) == 1
        assert len(mem2.learnings()) == 1


class TestAgentLogger:
    """Test structured agent logging."""

    def test_logging_creates_file(self, tmp_path):
        al = AgentLogger("log-test", base_dir=tmp_path)
        al.info("Test message", extra_field="test")
        al.warning("Warning message")
        al.error("Error message")
        al.log_tool_call("my_tool", {"arg": "val"}, "result")
        al.log_metrics({"sharpe": 1.5, "trades": 100})

        log_path = tmp_path / "log-test" / "agent.log.jsonl"
        assert log_path.exists()
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 5

        first = json.loads(lines[0])
        assert first["level"] == "INFO"
        assert first["agent"] == "log-test"


class TestRunArtifacts:
    def test_add_get(self):
        art = RunArtifacts()
        art.add("model", "xgboost")
        art.add("features", ["rsi", "macd"])
        assert art.get("model") == "xgboost"
        assert art.get("missing", "default") == "default"
        assert "model" in art.to_dict()


class TestTool:
    def test_tool_invoke(self):
        def add(a: int, b: int) -> int:
            return a + b

        t = Tool("add", "Add two numbers", add)
        assert t.invoke({"a": 1, "b": 2}) == 3
        assert t.schema()["name"] == "add"

    @pytest.mark.asyncio
    async def test_tool_async_invoke(self):
        async def async_add(a: int, b: int) -> int:
            return a + b

        t = Tool("add", "Add two numbers", lambda **kw: sum(kw.values()), async_fn=async_add)
        result = await t.ainvoke({"a": 3, "b": 4})
        assert result == 7


class TestCreateAgentNode:
    """Test LLM agent node factory."""

    @pytest.mark.asyncio
    async def test_basic_agent_node(self, tmp_path):
        """Agent node calls LLM and returns state updates."""
        with patch("agents.base.llm_call", return_value="Analysis complete. Sharpe looks good."):
            node = create_agent_node(
                name="test-analyst",
                system_prompt="You are a quantitative analyst.",
                model_key="minimax",
            )
            # Override memory dir to tmp
            node.agent_memory._dir = tmp_path / "test-analyst"
            node.agent_memory._dir.mkdir(parents=True, exist_ok=True)
            node.agent_memory._runs_path = node.agent_memory._dir / "runs.jsonl"
            node.agent_memory._learnings_path = node.agent_memory._dir / "learnings.jsonl"
            node.agent_logger._dir = tmp_path / "test-analyst"
            node.agent_logger._log_path = node.agent_logger._dir / "agent.log.jsonl"

            state = {"run_id": "test-001", "strategy_id": "btc-15m", "decision": "RESEARCH"}
            result = await node(state)

            assert "messages" in result
            assert result["messages"][-1]["content"] == "Analysis complete. Sharpe looks good."
            assert result["messages"][-1]["agent"] == "test-analyst"

    @pytest.mark.asyncio
    async def test_agent_handles_llm_error(self, tmp_path):
        """Agent gracefully handles LLM failures."""
        with patch("agents.base.llm_call", side_effect=ConnectionError("API down")):
            node = create_agent_node(
                name="error-agent",
                system_prompt="You are a test agent.",
            )
            node.agent_memory._dir = tmp_path / "error-agent"
            node.agent_memory._dir.mkdir(parents=True, exist_ok=True)
            node.agent_memory._runs_path = node.agent_memory._dir / "runs.jsonl"
            node.agent_memory._learnings_path = node.agent_memory._dir / "learnings.jsonl"

            state = {"run_id": "test-err", "errors": []}
            result = await node(state)

            assert "errors" in result
            assert any("LLM error" in e for e in result["errors"])


class TestCreateToolNode:
    """Test deterministic tool node factory."""

    @pytest.mark.asyncio
    async def test_tool_node(self, tmp_path):
        def compute_sharpe(state):
            returns = state.get("returns", [1, 2, 3])
            avg = sum(returns) / len(returns)
            return {"sharpe": avg / 0.5}

        def update_state(state, results):
            return {"backtest_metrics": results}

        node = create_tool_node("sharpe-calc", compute_sharpe, update_state)
        node.agent_memory._dir = tmp_path / "sharpe-calc"
        node.agent_memory._dir.mkdir(parents=True, exist_ok=True)
        node.agent_memory._runs_path = node.agent_memory._dir / "runs.jsonl"
        node.agent_memory._learnings_path = node.agent_memory._dir / "learnings.jsonl"

        state = {"run_id": "test", "returns": [0.01, 0.02, 0.03]}
        result = await node(state)

        assert "backtest_metrics" in result
        assert result["backtest_metrics"]["sharpe"] == 0.04


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
