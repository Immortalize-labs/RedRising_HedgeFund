# RedRising HedgeFund

[![CI](https://github.com/Immortalize-labs/RedRising_HedgeFund/actions/workflows/ci.yml/badge.svg)](https://github.com/Immortalize-labs/RedRising_HedgeFund/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**An AI-native hedge fund framework where autonomous agents research, trade, and manage risk — organized as a Red Rising-inspired hierarchy.**


> 用数字说话 — Let the numbers speak.

---

## The Vision

What if you could run a hedge fund where every department — research, risk, execution, operations, infrastructure, QA, and data — is managed by AI agents with distinct personalities, domain expertise, and accountability? Where no code ships without an independent test. Where no strategy goes live without surviving a four-round adversarial debate. Where a misalignment between AI suggestion and open position triggers an automatic investigation before the next trade fires.

RedRising HedgeFund is that framework. Inspired by Pierce Brown's Red Rising series, each department is led by a named director with a specific mandate, voice, and team of specialist agents beneath them. Darrow commands the operation. Mustang leads research. Dancer holds independent risk authority. Holiday keeps the machines running.

This is NOT a backtesting library. It is a complete organizational operating system for an AI-managed quantitative fund. Every decision is logged, every delegation carries quantified acceptance criteria, and every handoff is gated by numbers — not vibes.

---

## Architecture

```
                          J (Managing Partner)
                                  |
                           Darrow (CEO/CTO)
                                  |
        +---------+---------+---------+---------+---------+---------+
        |         |         |         |         |         |         |
     Mustang   Dancer    Tactus    Holiday    Ragnar     Pax     Victra
    Research    Risk    Execution   Infra      Ops       QA       Data
        |
   +---------+---------+
   |         |         |
 Sevro    Cassius   Tharax
Signals   Models   Regime
```

### Research Desk (The Howlers)

```
Mustang (Research Director)
   |
   +-- Sevro (Signals)       The Mathematician — Renaissance DNA, permutation tests, IC
   +-- Cassius (Models)      The Builder — Jane Street engineering, production-first
   +-- Tharax (Regime)       The Regime Thinker — D.E. Shaw + Bridgewater, macro overlay
   +-- [Backtest Auditor]    Lookahead detection, OOS validation (roadmap)
```

---

## Key Features

**Hierarchical Agent Organization**
Seven departments. Twenty-six roles across live, partial, and roadmap states. Every agent has a mandate, a model assignment, and a scope boundary it cannot cross.

**Think Protocol**
Mandatory structured reasoning before every decision. Two think calls per agent message: one on receive to parse the task, one before reply to sanity-check conclusions. All reasoning logged to `data/think_log.jsonl` for full audit trail.

**Four-Round Debate System**
Research goes through a Bridgewater-inspired adversarial review before any strategy reaches Darrow. Round 1: three researchers analyze independently. Round 2: cross-pollination, each reads the others. Round 3: PM synthesizes one composite strategy. Round 4: Risk Manager finds reasons to reject.

**Investigation Freeze**
When alignment mismatch is detected — AI suggests SHORT, open position is LONG — the strategy is automatically frozen. No new trades until root cause is found and fix is verified. Freeze duration, trades blocked, and resolution are all logged.

**Proactive Risk Suggestions**
Rule-based engine inspects portfolio state every cycle. Surfaces actionable warnings before conditions escalate into hard risk blocks. No LLM calls — deterministic, sub-millisecond.

**Knowledge Base**
ChromaDB-powered research library. Ingest papers, books, and strategy notes. Researchers query it automatically during Round 1 debates. Hybrid semantic + keyword search.

**Multi-Model Inference (M5 Max Optimized)**
Three-tier local model stack mapped to agent roles by complexity. Flagship for research and risk. Reasoning-optimized for execution math. Fast for operational tasks. API fallback when local is overloaded. One config file drives all routing.

**Promotion Pipeline with Hard Gates**
A strategy moves from research to production only if it clears every gate: OOS Sharpe >= 0.5, max drawdown <= 5%, minimum 50 OOS trades, decay ratio >= 0.3. No subjective overrides. Bar does not lower.

**160-Test Pre-Deploy Gate**
`pytest tests/` must pass before any deploy. Service must be active, smoke test must pass, health check at 5 minutes. Auto-rollback if service is dead after deploy.

---

## Departments

| Department | Director | Mandate | Voice |
|------------|----------|---------|-------|
| Research | Mustang | Generate alpha. Maximize risk-adjusted returns. | Precise, data-driven, numbers-first |
| Risk | Dancer | Independent oversight. Can override any trader, any time. | Adversarial, evidence-based, uncompromising |
| Execution | Tactus | Execute trades. Maximize fill quality. Minimize slippage. | Direct, latency-aware, fill-obsessed |
| Infrastructure | Holiday | Deploy with confidence. Detect failures before they cost money. | Methodical, reliability-first, unbreakable |
| QA | Pax | Validate that what shipped works as expected. Independent. | Skeptical, thorough, evidence-driven |
| Operations | Ragnar | Keep the machine running. Settlements, pipelines, strategy control. | Pragmatic, operational, always-on |
| Data | Victra | Ground truth. PnL reconciliation. Data sourcing. | Precise, reconciliation-focused, no narratives |

---

## The Research Team (The Howlers)

Mustang's research department runs three active desks, each with a distinct analytical lens. When a research brief arrives, all three work independently before seeing each other's output.

**Sevro — The Mathematician**
Inspired by Renaissance Technologies. Information theory, stochastic calculus, statistical mechanics. Does not trust patterns until they survive permutation tests, walk-forward validation, and OOS decay analysis. Speaks in IC ranges and formal hypotheses.

**Cassius — The Builder**
Inspired by Jane Street engineering culture. Theory is worthless without implementation. Thinks in latency, fill rates, data pipelines, and execution costs. Stress-tests every idea against production reality. If it cannot be built robustly, it does not ship.

**Tharax — The Regime Thinker**
Inspired by D.E. Shaw and Bridgewater. Every signal's edge is conditional on which regime is active. Always asks: in which regime does this work, and what triggers the regime change? Manages tail risk under regime misclassification.

**Portfolio Manager — The Synthesizer**
Inspired by Ray Dalio. Synthesizes three independent perspectives into one actionable composite strategy with explicit signal weights, sizing rules, and entry/exit criteria. Not a consensus builder — makes decisions.

**Risk Manager — The Guardian**
Inspired by Jane Street and AQR. Last line of defense. Every strategy is guilty until proven innocent. Eight hard veto triggers. Has veto power. Reports after — not before.

---

## Think Protocol

Every agent calls `think.py` twice per task: once on receive, once before reply.

```bash
python scripts/think.py \
  --caller "holiday" \
  --claim "What is the infra issue?" \
  --priors "What is the current service state?" \
  --math "Is the service actually down or is it a monitoring artifact?" \
  --hypotheses "Deploy failure vs config vs upstream — ranked by likelihood" \
  --cheapest_check "systemctl status before assuming the worst" \
  --action "What to do next"
```

Output:
```
============================================================
THINK  [2026-03-19T15:07:46-05:00]  caller=holiday
============================================================
  CLAIM:          What is the infra issue?
  PRIORS:         Service was last deployed 2h ago, health check passed
  MATH:           Is the service actually down or is it a monitoring artifact?
  HYPOTHESES:     Deploy failure vs config vs upstream — ranked by likelihood
  CHEAPEST CHECK: systemctl status before assuming the worst
  ACTION:         What to do next
============================================================
```

All reasoning is appended to `data/think_log.jsonl`. Full audit trail.

---

## Promotion Pipeline

A strategy earns production access by clearing every gate in sequence. No shortcuts.

```
Research Complete
      |
      v
Backtest Gate (Research -> Darrow)
  OOS Sharpe >= 0.5
  Max Drawdown <= 5%
  Trades >= 50 (OOS)
  Decay Ratio >= 0.3
  Calmar >= 1.0
      |
      v
Darrow Review -> J Approval
      |
      v
Deploy Gate (Darrow -> Holiday)
  pytest must pass (160 tests)
  Backup current EC2 code
  Import smoke test on EC2
  Service restart + health check at 15s
  Auto-rollback if service dead
      |
      v
QA Gate (48-hour window)
  Win rate within 5pp of backtest
  Fill rate >= 80%
  PnL positive or within 1 SD of expected
  Zero alignment incidents
  Drawdown < daily limit
      |
      v
Risk Limits + Kill Switch Wired (Dancer)
      |
      v
Operations Live (Ragnar)
  Settlement checkers deployed
  Dashboard wired
  Ops log entry created
```

---

## Quick Start

```bash
git clone https://github.com/yourusername/RedRising_HedgeFund.git
cd RedRising_HedgeFund

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys and model endpoints

# Run a research debate
python scripts/run_debate.py --brief "Analyze 15-minute BTC momentum signals"

# Query the knowledge base
python scripts/kb_query.py --query "momentum factor decay in crypto"

# Ingest a paper
python scripts/kb_ingest.py --path docs/your_paper.pdf

# Run the test suite
pytest tests/ -v
```

---

## Configuration

### `config/risk_policy.yaml`
Single source of truth for all risk parameters. Gate criteria, live limits, kill switch thresholds. Consumed by RiskGuardian, drawdown monitor, and risk reporter.

### `config/inference.yaml`
Three-tier model stack configuration. Maps agent roles to model tiers (flagship/reasoning/fast). VRAM budgets, fallback chains, escalation tags. Hot-reloadable at runtime.

### `config/api_providers.yaml`
API provider routing. Fallback chain when local models are unavailable. Scrubbed for open source — add your own keys.

### `.claude/agents/`
Director and desk lead configurations. Each file defines an agent's mandate, scope boundaries, available employees, and report schema.

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| ML / Modeling | XGBoost, scikit-learn, pandas, numpy |
| Knowledge Base | ChromaDB, nomic-embed-text |
| Local Inference | MLX (Apple Silicon), Ollama fallback |
| Frontier Models | DeepSeek R1, Qwen3.5, GPT-4o (configurable) |
| Agent Framework | Pure asyncio — no LangGraph, no LangChain |
| Testing | pytest (160 tests pre-deploy gate) |
| Deployment | systemd services, SSH, bash deploy scripts |
| Alerting | Telegram / Discord webhook |

---

## Model Stack (M5 Max Configuration)

The default inference configuration is optimized for Apple M5 Max (128 GB unified memory):

| Tier | Model | VRAM | Agents |
|------|-------|------|--------|
| Flagship | Qwen3.5-122B-A10B (Q4) | 70 GB | Research, Risk, QA |
| Reasoning | DeepSeek-R1-Distill-Qwen-32B (Q4) | 20 GB | Execution |
| Fast | Qwen3.5-9B (Q4) | 7 GB | Ops, Infra, Data |
| Embedding | nomic-embed-text | 0.3 GB | RAG pipeline |
| **Total** | | **97.3 GB / 118 GB** | |

For API-only setups, configure `config/api_providers.yaml` with your preferred providers. The inference router automatically falls back to API when local models are unavailable.

---

## Codebase Map

```
RedRising_HedgeFund/
├── .claude/
│   ├── agents/              # Director + desk lead configs (Claude Code sub-agents)
│   ├── commands/            # Slash commands: /task, /ops, /deploy, /health, /review
│   └── docs/                # Trading rules, risk policy reference
├── agents/
│   ├── base.py              # Agent node factory (LLM + tool nodes)
│   ├── memory.py            # Persistent JSONL-backed agent memory
│   ├── manifest.py          # Agent registry
│   └── hf/
│       └── characters.py    # Research team personas (Sevro, Cassius, Tharax, PM, Risk)
├── orchestrator/
│   ├── debate.py            # 4-round Bridgewater debate engine
│   ├── gates.py             # Promotion gate validators
│   ├── pipeline.py          # Research -> live pipeline
│   └── state.py             # Shared pipeline state schema
├── core/
│   ├── llm/
│   │   └── client.py        # Unified multi-provider LLM client
│   ├── prompts/
│   │   └── loader.py        # Prompt template loader
│   └── risk/
│       ├── investigation_freeze.py   # Auto-freeze on misalignment
│       └── proactive_suggestions.py  # Deterministic portfolio state checker
├── knowledge_base/
│   ├── kb.py                # ChromaDB wrapper
│   ├── chunker.py           # Text chunking strategies
│   ├── embedder.py          # nomic-embed-text interface
│   └── ingest.py            # Document ingestion pipeline
├── config/
│   ├── risk_policy.yaml     # Gate criteria + live limits
│   └── inference.yaml       # Three-tier model stack config
├── scripts/
│   ├── think.py             # Structured reasoning tool (mandatory per agent)
│   ├── run_debate.py        # Launch a research debate
│   ├── kb_query.py          # Knowledge base query interface
│   └── kb_ingest.py         # Knowledge base ingestion
├── docs/
│   └── fund-org.md          # Full org chart and decision authority matrix
└── tests/                   # 160 tests, pre-deploy gate
```

---

## Decision Authority

| Decision | Owner | Rule |
|----------|-------|------|
| Route task to department | Darrow | Operational |
| Kill underperforming strategy | Darrow | Within risk policy |
| Lower a gate threshold | J only | Changing the rules |
| Override risk veto | Nobody | Bar does not lower |
| Kill positions without approval | Dancer | Risk authority |
| Capital allocation | J only | Capital decision |

---

## Inspired By

Named for the characters of Pierce Brown's **Red Rising** series — a story about intelligence, hierarchy, loyalty, and what happens when the right person is put in the right role. The naming is not cosmetic: each character was chosen for psychological fit with their department's mandate.

Dancer holds risk because she is never wrong about people. Holiday holds infrastructure because she keeps the machines running no matter what. Mustang leads research because she sees angles others miss. The names are load-bearing.

---

## Contributing

Pull requests welcome. Open an issue first for major changes.

If you extend the framework:
- Every new agent needs a Think Protocol implementation
- Every new gate needs a quantified threshold (no subjective criteria)
- Every new department needs a director, a mandate, and acceptance criteria
- Darrow is managerial only — never does IC work

---

## License

MIT License. See `LICENSE` for details.

---

*RedRising HedgeFund is an open-source framework for research and education. It is not financial advice. Past performance of any backtested strategy is not indicative of future results.*
