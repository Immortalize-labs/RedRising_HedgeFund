"""
Debate Engine
=============
4-round Bridgewater-inspired exploration protocol.

Round 1 — Independent: 3 researchers analyze in parallel (isolated)
Round 2 — Cross-pollination: each researcher reacts to others (parallel)
Round 3 — Synthesis: PM composes a single strategy (sequential)
Round 4 — Risk Review: Risk Manager approves/rejects (sequential)

No LangGraph. Uses engine.llm for model calls, concurrent.futures for parallelism.
"""
from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from agents.hf.characters import (
    PORTFOLIO_MANAGER,
    RISK_MANAGER,
    Round,
    get_researchers,
)
from core.llm.client import call as llm_call


@dataclass
class Proposal:
    role: str
    model: str
    content: str
    elapsed_sec: float = 0.0


@dataclass
class Reaction:
    role: str
    model: str
    content: str
    elapsed_sec: float = 0.0


@dataclass
class Synthesis:
    content: str
    model: str
    decision: str = ""          # PROCEED / NEEDS_MORE_WORK / REJECT
    elapsed_sec: float = 0.0


@dataclass
class RiskReview:
    content: str
    model: str
    decision: str = ""          # APPROVED / CONDITIONAL / NOT_YET
    veto_details: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    elapsed_sec: float = 0.0


@dataclass
class DebateResult:
    proposals: list[Proposal]
    reactions: list[Reaction]
    synthesis: Synthesis
    risk_review: RiskReview
    total_elapsed_sec: float = 0.0

    @property
    def approved(self) -> bool:
        return self.risk_review.decision == "APPROVED"

    @property
    def composite_strategy(self) -> str:
        return self.synthesis.content

    def summary(self) -> str:
        lines = [
            "=== Debate Result ===",
            f"Strategy: {self.synthesis.decision}",
            f"Risk: {self.risk_review.decision}",
            f"Time: {self.total_elapsed_sec:.1f}s",
            "Models used:",
        ]
        for p in self.proposals:
            lines.append(f"  R1 {p.role}: {p.model} ({p.elapsed_sec:.1f}s)")
        for r in self.reactions:
            lines.append(f"  R2 {r.role}: {r.model} ({r.elapsed_sec:.1f}s)")
        lines.append(f"  R3 PM: {self.synthesis.model} ({self.synthesis.elapsed_sec:.1f}s)")
        lines.append(f"  R4 Risk: {self.risk_review.model} ({self.risk_review.elapsed_sec:.1f}s)")
        return "\n".join(lines)


class DebateEngine:
    """Orchestrates the 4-round debate protocol."""

    def __init__(self, max_tokens: int = 4096, timeout: int = 300):
        self.max_tokens = max_tokens
        self.timeout = timeout

    def run(self, research_brief: str, existing_assets: str = "", skip_risk: bool = False) -> DebateResult:
        """Execute full debate. Set skip_risk=True for research-only (no Round 4)."""
        t0 = time.time()

        context = ""
        if existing_assets:
            context = f"\n\nExisting live strategies (avoid correlation):\n{existing_assets}"

        # Round 1 — Independent
        proposals = self._round_1(research_brief, context)

        # Round 2 — Cross-pollination
        reactions = self._round_2(research_brief, proposals, context)

        # Round 3 — PM Synthesis
        synthesis = self._round_3(research_brief, proposals, reactions, context)

        # Round 4 — Risk Review (optional)
        if skip_risk:
            risk_review = RiskReview(content="Skipped", model="none", decision="SKIPPED")
        else:
            risk_review = self._round_4(synthesis, proposals, context)

        return DebateResult(
            proposals=proposals,
            reactions=reactions,
            synthesis=synthesis,
            risk_review=risk_review,
            total_elapsed_sec=time.time() - t0,
        )

    def _round_1(self, brief: str, context: str) -> list[Proposal]:
        """3 researchers, parallel, isolated. KB context injected."""
        # Enrich with Knowledge Base context if available
        kb_context = ""
        try:
            from knowledge_base import get_kb
            kb = get_kb()
            results = kb.query(brief, top_k=5)
            if results:
                kb_context = kb.format_for_prompt(results)
        except Exception:
            pass  # KB not configured or empty — proceed without

        researchers = get_researchers()
        proposals = []

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {}
            for r in researchers:
                system = r.system_prompt(Round.INDEPENDENT, context)
                prompt_parts = [f"Research Brief:\n{brief}"]
                if kb_context:
                    prompt_parts.append(f"\n{kb_context}")
                prompt = "\n".join(prompt_parts)
                f = pool.submit(self._call, r.model_key, prompt, system)
                futures[f] = r

            for f in as_completed(futures):
                r = futures[f]
                content, elapsed = f.result()
                proposals.append(Proposal(
                    role=r.role.value,
                    model=r.model_key,
                    content=content,
                    elapsed_sec=elapsed,
                ))

        return proposals

    def _round_2(self, brief: str, proposals: list[Proposal], context: str) -> list[Reaction]:
        """3 researchers react to each other, parallel."""
        researchers = get_researchers()
        reactions = []

        # Format proposals for cross-reading
        proposals_text = "\n\n".join(
            f"--- {p.role} ({p.model}) ---\n{p.content}" for p in proposals
        )

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {}
            for r in researchers:
                system = r.system_prompt(Round.CROSS_POLLINATION, context)
                prompt = (
                    f"Research Brief:\n{brief}\n\n"
                    f"=== All Round 1 Proposals ===\n{proposals_text}\n\n"
                    f"Your original proposal is labeled '{r.role.value}'. "
                    f"Now react to the others."
                )
                f = pool.submit(self._call, r.model_key, prompt, system)
                futures[f] = r

            for f in as_completed(futures):
                r = futures[f]
                content, elapsed = f.result()
                reactions.append(Reaction(
                    role=r.role.value,
                    model=r.model_key,
                    content=content,
                    elapsed_sec=elapsed,
                ))

        return reactions

    def _round_3(
        self, brief: str, proposals: list[Proposal],
        reactions: list[Reaction], context: str,
    ) -> Synthesis:
        """PM synthesizes everything into one strategy."""
        pm = PORTFOLIO_MANAGER
        system = pm.system_prompt(Round.SYNTHESIS, context)

        proposals_text = "\n\n".join(
            f"--- {p.role} ({p.model}) ---\n{p.content}" for p in proposals
        )
        reactions_text = "\n\n".join(
            f"--- {r.role} ({r.model}) ---\n{r.content}" for r in reactions
        )

        prompt = (
            f"Research Brief:\n{brief}\n\n"
            f"=== Round 1: Independent Proposals ===\n{proposals_text}\n\n"
            f"=== Round 2: Cross-Pollination ===\n{reactions_text}\n\n"
            f"Now synthesize into ONE composite strategy."
        )

        content, elapsed = self._call(pm.model_key, prompt, system)
        decision = _extract_decision(content, ["PROCEED", "NEEDS_MORE_WORK", "REJECT"])

        return Synthesis(content=content, model=pm.model_key, decision=decision, elapsed_sec=elapsed)

    def _round_4(self, synthesis: Synthesis, proposals: list[Proposal], context: str) -> RiskReview:
        """Risk Manager reviews the composite strategy."""
        rm = RISK_MANAGER
        system = rm.system_prompt(Round.RISK_REVIEW, context)

        proposals_summary = "\n".join(
            f"- {p.role}: {p.content[:200]}..." for p in proposals
        )

        prompt = (
            f"=== PM Composite Strategy ===\n{synthesis.content}\n\n"
            f"=== Research Summaries ===\n{proposals_summary}\n\n"
            f"Evaluate. Find reasons to reject."
        )

        content, elapsed = self._call(rm.model_key, prompt, system, max_tokens=4096)
        decision = _extract_decision(content, ["APPROVED", "CONDITIONAL", "NOT_YET"])

        veto_details = _extract_list(content, "VETO DETAILS")
        conditions = _extract_list(content, "CONDITIONS")

        return RiskReview(
            content=content,
            model=rm.model_key,
            decision=decision,
            veto_details=veto_details,
            conditions=conditions,
            elapsed_sec=elapsed,
        )

    def _call(self, model_key: str, prompt: str, system: str, max_tokens: int | None = None) -> tuple[str, float]:
        """Call model via unified async client, return (content, elapsed_seconds)."""
        t0 = time.time()
        content = llm_call(
            model_key=model_key,
            prompt=prompt,
            system=system,
            max_tokens=max_tokens or self.max_tokens,
        )
        return content, time.time() - t0


def _extract_decision(text: str, options: list[str]) -> str:
    """Extract a decision keyword from text."""
    upper = text.upper()
    for opt in options:
        if opt in upper:
            return opt
    return options[-1]  # default to last (most conservative)


def _extract_list(text: str, header: str) -> list[str]:
    """Extract a bulleted list following a header."""
    pattern = rf"{header}[:\s]*\n((?:\s*[-•*]\s*.+\n?)+)"
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return []
    items = re.findall(r"[-•*]\s*(.+)", match.group(1))
    return [i.strip() for i in items if i.strip()]


def run_debate(research_brief: str, existing_assets: str = "", **kwargs) -> DebateResult:
    """Convenience function."""
    engine = DebateEngine(**kwargs)
    return engine.run(research_brief, existing_assets)
