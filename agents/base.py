"""
Agent Base
==========
Factory for creating standardized async agent nodes.
Pure asyncio — no LangGraph, no LangChain.

Every agent follows the same pattern:
  1. Receives a shared state dict
  2. Has a system prompt defining its role
  3. Has access to registered tool functions
  4. Has persistent memory (JSONL-backed)
  5. Returns updated state

Two node types:
  - LLM node: calls an LLM model, optionally uses tools
  - Tool node: deterministic computation, no LLM
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Sequence

from agents.memory import AgentLogger, AgentMemory
from core.llm.client import call as llm_call

logger = logging.getLogger(__name__)


# ─── Tool Protocol ────────────────────────────────────────────────────────

class Tool:
    """Simple tool wrapper. No LangChain dependency."""

    def __init__(
        self,
        name: str,
        description: str,
        fn: Callable,
        async_fn: Callable | None = None,
    ):
        self.name = name
        self.description = description
        self._fn = fn
        self._async_fn = async_fn

    def invoke(self, args: dict) -> Any:
        return self._fn(**args)

    async def ainvoke(self, args: dict) -> Any:
        if self._async_fn:
            return await self._async_fn(**args)
        return self._fn(**args)

    def schema(self) -> dict:
        """Return a JSON-schema-like description for LLM tool-use prompts."""
        return {"name": self.name, "description": self.description}


# ─── LLM Agent Node Factory ──────────────────────────────────────────────

def create_agent_node(
    name: str,
    system_prompt: str,
    tools: Sequence[Tool] | None = None,
    model_key: str = "minimax",
    temperature: float = 0.0,
    state_updater: Callable | None = None,
) -> Callable:
    """
    Factory for async agent nodes.

    Each node:
      1. Reads the shared state
      2. Injects memory context into prompt
      3. Calls the LLM via core.llm.client
      4. Executes tool calls if LLM requests them
      5. Applies optional state_updater
      6. Records run in persistent memory
      7. Returns state updates

    Parameters
    ----------
    name : str
        Agent name for logging and memory.
    system_prompt : str
        System prompt defining the agent's role.
    tools : Sequence[Tool], optional
        Tools available to the agent.
    model_key : str
        Model key from core.llm.client catalog (default: minimax).
    temperature : float
        LLM temperature (default 0 for deterministic).
    state_updater : callable, optional
        Function(state, tool_results) -> dict of state updates.

    Returns
    -------
    Callable
        An async function that takes state dict and returns state updates.
    """
    tools = tools or []
    agent_logger = AgentLogger(name)
    agent_memory = AgentMemory(name)

    async def node(state: dict) -> dict:
        logger.info(f"[{name}] starting...")
        agent_logger.info("Agent invoked", run_id=state.get("run_id", "?"))

        # Build prompt with memory context
        memory_context = agent_memory.get_context_for_llm()
        full_system = system_prompt
        if memory_context != "No prior memory.":
            full_system += f"\n\n--- AGENT MEMORY ---\n{memory_context}\n--- END MEMORY ---"

        # Add tool descriptions to system prompt if tools available
        if tools:
            tool_desc = "\n".join(
                f"  - {t.name}: {t.description}" for t in tools
            )
            full_system += (
                f"\n\nAvailable tools:\n{tool_desc}\n\n"
                "To call a tool, respond with JSON: "
                '{\"tool\": \"<name>\", \"args\": {<args>}}'
            )

        # Build user message from state
        user_msg = _build_state_context(state, name)

        # Call LLM
        try:
            response = llm_call(
                model_key=model_key,
                prompt=user_msg,
                system=full_system,
                max_tokens=4096,
            )
        except Exception as e:
            logger.error(f"[{name}] LLM error: {e}", exc_info=True)
            agent_logger.error(f"LLM error: {e}")
            agent_memory.add_learning("error", f"LLM call failed: {e}")
            return {
                "errors": state.get("errors", []) + [f"{name}: LLM error: {e}"],
            }

        # Parse tool calls from response
        tool_results = []
        if tools:
            tool_results = _extract_and_run_tools(response, tools, name, agent_logger)

        # Build state updates
        updates: dict[str, Any] = {
            "messages": state.get("messages", []) + [
                {"role": "assistant", "agent": name, "content": response}
            ],
        }

        if tool_results:
            updates["tool_results"] = state.get("tool_results", []) + tool_results

        if state_updater and tool_results:
            custom = state_updater(state, tool_results)
            if custom:
                updates.update(custom)

        # Record in persistent memory
        agent_memory.record_run(
            run_id=state.get("run_id", "unknown"),
            strategy_id=state.get("strategy_id", "unknown"),
            result={
                "tools_called": len(tool_results),
                "response_len": len(response),
                "updates": list(updates.keys()),
            },
        )

        logger.info(f"[{name}] complete. Tools: {len(tool_results)}, Response: {len(response)} chars")
        agent_logger.info(f"Completed. Tools: {len(tool_results)}")
        return updates

    node.__name__ = f"{name}_node"
    node.agent_logger = agent_logger
    node.agent_memory = agent_memory
    return node


# ─── Deterministic Tool Node Factory ─────────────────────────────────────

def create_tool_node(
    name: str,
    tool_fn: Callable,
    state_updater: Callable,
) -> Callable:
    """
    Create a deterministic tool-only node (no LLM).

    For agents that don't need reasoning — just computation.
    Examples: BacktestAgent, RiskAuditAgent, DataPipelineAgent.
    """
    agent_logger = AgentLogger(name)
    agent_memory = AgentMemory(name)

    async def node(state: dict) -> dict:
        logger.info(f"[{name}] starting (deterministic)...")
        agent_logger.info("Invoked (deterministic)", run_id=state.get("run_id", "?"))

        try:
            results = tool_fn(state)

            # Log metrics
            if isinstance(results, dict):
                loggable = {
                    k: v for k, v in results.items()
                    if not isinstance(v, (list, dict)) or len(str(v)) < 200
                }
                agent_logger.log_metrics(loggable)

            updates = state_updater(state, results)

            agent_memory.record_run(
                run_id=state.get("run_id", "unknown"),
                strategy_id=state.get("strategy_id", "unknown"),
                result={"updates": list(updates.keys()) if isinstance(updates, dict) else []},
            )

            logger.info(f"[{name}] complete.")
            return updates

        except Exception as e:
            logger.error(f"[{name}] error: {e}", exc_info=True)
            agent_logger.error(f"Error: {e}")
            agent_memory.add_learning("error", f"Failed: {e}")
            return {
                "errors": state.get("errors", []) + [f"{name}: {e}"],
            }

    node.__name__ = f"{name}_node"
    node.agent_logger = agent_logger
    node.agent_memory = agent_memory
    return node


# ─── Helpers ──────────────────────────────────────────────────────────────

def _build_state_context(state: dict, agent_name: str) -> str:
    """Build a context message from current state for the agent."""
    parts = [f"Current state for agent '{agent_name}':"]

    parts.append(f"  Run ID: {state.get('run_id', 'N/A')}")
    parts.append(f"  Strategy: {state.get('strategy_id', 'N/A')}")
    parts.append(f"  Decision: {state.get('decision', 'N/A')}")

    if state.get("universe"):
        parts.append(f"  Universe: {json.dumps(state['universe'], default=str)}")

    if state.get("validated_signals"):
        n = len(state["validated_signals"])
        passing = sum(1 for s in state["validated_signals"] if s.get("verdict") == "REAL")
        parts.append(f"  Signals: {passing}/{n} passed validation")

    if state.get("alpha_spec"):
        parts.append(f"  Alpha spec: {json.dumps(state['alpha_spec'], default=str)}")

    if state.get("backtest_metrics"):
        m = state["backtest_metrics"]
        parts.append(f"  Backtest: Sharpe={m.get('sharpe', 'N/A')}, MaxDD={m.get('max_dd_pct', 'N/A')}%")

    if state.get("walkforward_metrics"):
        m = state["walkforward_metrics"]
        parts.append(f"  Walk-forward: OOS Sharpe={m.get('oos_sharpe', 'N/A')}, Days={m.get('oos_days', 'N/A')}")

    if state.get("errors"):
        parts.append(f"  Errors: {state['errors'][-3:]}")

    return "\n".join(parts)


def _extract_and_run_tools(
    response: str, tools: Sequence[Tool], agent_name: str, agent_logger: AgentLogger,
) -> list[dict]:
    """Parse tool calls from LLM response and execute them."""
    results = []
    tool_map = {t.name: t for t in tools}

    # Look for JSON tool calls in response
    import re
    pattern = r'\{"tool"\s*:\s*"([^"]+)"\s*,\s*"args"\s*:\s*(\{[^}]*\})\}'
    matches = re.findall(pattern, response)

    for tool_name, args_str in matches:
        if tool_name not in tool_map:
            logger.warning(f"[{agent_name}] unknown tool: {tool_name}")
            agent_logger.warning(f"Unknown tool: {tool_name}")
            continue

        try:
            args = json.loads(args_str)
            tool = tool_map[tool_name]
            result = tool.invoke(args)
            results.append({
                "tool": tool_name,
                "args": args,
                "result": result,
            })
            agent_logger.log_tool_call(tool_name, args, result)
            logger.info(f"[{agent_name}] tool {tool_name} -> {str(result)[:100]}")
        except Exception as e:
            logger.error(f"[{agent_name}] tool {tool_name} failed: {e}")
            agent_logger.error(f"Tool {tool_name} failed: {e}")
            results.append({
                "tool": tool_name,
                "args": args_str,
                "error": str(e),
            })

    return results
