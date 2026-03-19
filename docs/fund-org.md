# Immortalize Labs HF — Fund Operating Structure

**Motto**: 用数字说话 — Let the numbers speak.

---

## Principles

1. Every decision backed by numbers — Sharpe, WR, drawdown, fill rate. No narratives.
2. Risk is independent from execution — can override any trader, any time.
3. CEO/CTO is managerial only — delegates, never executes IC work.
4. Directors own their departments — they create employees and tools.
5. Tools are entity-wide and standardized — shared across all departments.
6. If a department doesn't exist, create it. If an employee doesn't exist, the director creates one.
7. Every department has embedded devops access for self-serve wiring. Holiday owns platform standards and cross-cutting infrastructure.
7. Every handoff carries quantified acceptance criteria. No "looks good."

---

## Leadership

### J — Managing Partner (70%)

- Final authority on capital allocation and strategic direction
- Sets milestones and risk parameters
- Approves/rejects strategy promotions to live
- Approves rule changes (gate thresholds, risk policy)
- Approves new departments (structural changes)

### Darrow — CEO/CTO (30%)

- Oversees entire entity against milestones
- Decomposes strategic decisions into departmental tasks
- Defines acceptance criteria for every deliverable (quantified, time-bound)
- Routes work to the correct department
- Rejects incomplete work — sends it back with specific gaps
- Kills underperforming strategies within existing risk policy
- Reallocates headcount between departments
- Reports to J with numbers, not narratives
- **Does NOT**: code, analyze, run backtests, deploy, or execute any IC task

---

## Decision Authority Matrix

| Decision | Owner | Why |
|----------|-------|-----|
| Route task to department | Darrow | Operational |
| Define acceptance criteria | Darrow | Quality gate |
| Reject incomplete deliverable | Darrow | Gate enforcement |
| Kill underperforming strategy | Darrow | Within risk policy |
| Reallocate headcount | Darrow | Operational efficiency |
| Lower a gate threshold | **J** | Changing the rules |
| Enter new asset class | **J** | Capital + strategic direction |
| Change risk policy parameters | **J** | Changing the rules |
| Create new department | Darrow proposes, **J** approves | Structural change |
| Increase capital to a strategy | **J** | Capital decision |
| Strategic bets on unknowns | **J** | Risk appetite |

---

## Org Chart

```
J (Managing Partner, 70%)
  │
Darrow (CEO/CTO, 30%)
  │
  ├── Research ─── Director: Mustang
  │     Employees: Sevro, Tharax, Cassius, [Backtest Auditor]
  │
  ├── Risk ─── Director: Dancer
  │     Employees: Ares, [Exposure Monitor], [Risk Reporter]
  │
  ├── Execution ─── Director: Tactus
  │     Employees: 4 live traders, [Smart Order Router]
  │
  ├── Infrastructure ─── Director: Holiday
  │     Employees: Deploy Agent, Health Monitor, Test Runner, [CI Pipeline]
  │
  ├── QA ─── Director: [TBD]
  │     Employees: [Post-Deploy Validator], [Strategy Monitor]
  │
  ├── Operations ─── Director: Ragnar
  │     Employees: Settlement Checkers, Redeemer, Tick Collector, Strategy Control, Dashboard
  │
  └── Data ─── Director: Victra
        Employees: Accountant, [PnL Analyst], [Performance Analyst]
```

---

## Delegation Hierarchy

```
Darrow (CEO/CTO) — decides WHAT, WHO, and acceptance criteria
  │
  Director (department head) — decides HOW, creates employees + tools, manages logistics
  │
  Employee (agent) — executes specific tasks using tools, reports results with numbers
```

### Rules

1. **Darrow never does IC work.** Delegate or create the role.
2. **Directors own logistics.** They create employees, assign tasks, manage tools.
3. **Employees do the work.** Use existing tools, advance them, or build new ones.
4. **Tools are entity-wide.** Standardized, shared. File I/O, deploy, SSH, alerting — one way to do it.
5. **If a department doesn't exist, create it** — with a director, a mandate, and acceptance criteria.
6. **Escalate to J only when milestones are unclear** — everything else is Darrow's call.

---

## Strategy Promotion Pipeline

Every strategy follows this pipeline from research to production.

```
Research ── backtest results ──► Darrow ── recommendation + numbers ──► J
                                                                        │
                                                                  approve/reject
                                                                        │
J ── approved ──► Darrow ── deploy task ──► Infrastructure
                                                  │
                                             deploy done
                                                  │
                    Darrow ◄─────────────── confirmed
                       │
                       ├── QA task ──► QA Team (monitor x cycles)
                       ├── Risk task ──► Risk (set limits, wire kill switch)
                       └── Ops task ──► Operations (settlement, registry, dashboard)
                                              │
                    Darrow ◄─────────────── all pass/fail + numbers
                       │
                       └── report to J
```

### Gate Criteria

#### Backtest Gate (Research → Darrow)

| Metric | Threshold | Period |
|--------|-----------|--------|
| OOS Sharpe | ≥ 0.5 | 30+ days OOS |
| Max Drawdown | ≤ 5% | full sample |
| Trade Count | ≥ 50 | OOS period |
| Decay Ratio (OOS/IS) | ≥ 0.3 | — |
| Calmar Ratio | ≥ 1.0 | OOS period |

If data insufficient: **rejected**. Research must wait for data or Data team must source it. Bar does not lower.

#### Deploy Gate (Darrow → Infrastructure)

| Metric | Threshold | Timing |
|--------|-----------|--------|
| Service Active | systemd running | immediate |
| Import Smoke | pass | immediate |
| Health Check | no alerts | 5 min post-deploy |
| Rollback Plan | documented | pre-deploy |

#### QA Gate (Darrow → QA)

| Metric | Threshold | Duration |
|--------|-----------|----------|
| Win Rate | within 5pp of backtest WR | 48 hours |
| Fill Rate | ≥ 80% | 48 hours |
| PnL | positive or within 1 SD of expected | 48 hours |
| Alignment | 0 misalignment incidents | 48 hours |
| Drawdown | < daily limit | 48 hours |

If QA fails any threshold — strategy is pulled. No exceptions.

---

## Data Ownership

| Data Type | Owner | Consumers |
|-----------|-------|-----------|
| Market data (ticks, candles, order book) | Data | Research, Execution |
| Feature engineering | Research | Research |
| Signal/trade logs | Operations | Data, QA, Risk |
| Settlement data | Operations | Data, Risk |
| Model weights + configs | Research | Execution, Infra |
| PnL ground truth (PM CSV) | Data | Darrow, Risk, J |

If Research is blocked on data: Darrow routes to Data director. Research moves to next priority.

---

## Departments

### Research — Director: Mustang

**Mandate**: Generate alpha. Maximize risk-adjusted returns. 用数字说话.

**Delivers to Darrow**: Backtest results with OOS Sharpe, WR, drawdown, trade count, decay ratio.

| Employee | Role | Tools | Status |
|----------|------|-------|--------|
| Sevro | Signal Miner (MFT, 5m–15m) | `experiment_*.py`, `build_*_features*.py`, backtest engine | **LIVE** |
| Tharax | Signal Miner (LFT, hourly/daily) | regime detection, macro overlay, backtest engine | Roadmap |
| Cassius | Model Trainer | `monthly_retrain.py`, model versioning, WFO pipeline | Partial |
| [Backtest Auditor] | Validate no lookahead, data integrity | lookahead detector, OOS validator | Roadmap |

### Risk — Director: Dancer

**Mandate**: Independent oversight. Can override any trader. Never lose more than planned.

**Authority**: Kill positions without Darrow's approval. Report after.

| Employee | Role | Tools | Status |
|----------|------|-------|--------|
| Ares | Drawdown Monitor | `drawdown_monitor.py`, circuit breaker, kill switch | **LIVE** |
| [Exposure Monitor] | Portfolio-level risk | portfolio aggregator, correlation matrix, VaR | Roadmap |
| [Risk Reporter] | Daily metrics | `risk_reporter.py`, Sharpe/Calmar/WR per strategy | Roadmap |

### Execution — Director: Tactus

**Mandate**: Execute trades. Maximize fill quality. Minimize slippage.

| Employee | Role | Tools | Status |
|----------|------|-------|--------|
| ETH-5m Trader | 5m ETH directional | `live_trader_eth.py`, W1 | **LIVE** |
| BTC-15m Trader | 15m BTC directional | `live_trader_btc_15m.py`, W1 | **LIVE** |
| ETH-15m Trader | 15m ETH directional | `live_trader_eth_15m.py`, W1 | **LIVE** |
| XRP-15m Trader | 15m XRP directional | `live_trader_xrp_15m.py`, W1 | **LIVE** |
| [Smart Order Router] | Fill optimization | book depth, timing, slippage analysis | Roadmap |

### Infrastructure — Director: Holiday

**Mandate**: Deploy with confidence. Detect failures before they cost money. Own platform standards and cross-cutting infrastructure — EC2, deploy pipelines, CI/CD, health monitoring.

**Embedded DevOps Model**: Every department director has access to `devops-engineer` for self-serve departmental wiring (cron jobs, config integration, service setup, pipeline scheduling). Holiday sets platform standards; departments handle their own plumbing.

**Receives from Darrow**: Deploy tasks with target, config, rollback plan.

**Returns to Darrow**: Deploy confirmation — service status, smoke test, health check.

| Employee | Role | Tools | Status |
|----------|------|-------|--------|
| Deploy Agent | Upload, restart, verify, rollback | `deploy.sh`, backup, pre-deploy tests | **LIVE** |
| Health Monitor | 60s cycle, alerting | `health_monitor.py`, Telegram/Discord | **LIVE** |
| Test Runner | Pre-deploy gate | `pytest` (160 tests), blocks deploy on failure | **LIVE** |
| [CI Pipeline] | Automated test/deploy | GitHub Actions, lint, auto-promote | Roadmap |

### QA — Director: [TBD]

**Mandate**: Validate that what shipped works as expected. Independent from the team that built it.

**Receives from Darrow**: Validation task — strategy name, expected metrics, monitoring duration.

**Returns to Darrow**: Pass/fail + actual numbers vs expected.

| Employee | Role | Tools | Status |
|----------|------|-------|--------|
| [Post-Deploy Validator] | Verify deploy health | `post_deploy_verify.py`, service checks | Partial |
| [Strategy Monitor] | Track live strategy vs backtest expectations | WR/PnL/fill tracker, anomaly detection | Roadmap |

### Operations — Director: Ragnar

**Mandate**: Keep the machine running. Settlements, data pipelines, strategy control.

| Employee | Role | Tools | Status |
|----------|------|-------|--------|
| Settlement Checkers (4) | Per-strategy settlement + redemption | `*_settlement_checker.py` | **LIVE** |
| Redeemer | Batch gasless redemption | `redeem_gasless.py` | **LIVE** |
| Tick Collector | Binance + PM data pipeline | `live_tick_collector.py` | **LIVE** |
| Strategy Control | Kill/start/stop, ops log | `strategy_ctl.py`, `ops_verify.py` | **LIVE** |
| Dashboard | Unified view | `unified_dashboard.py` | **LIVE** |

### Data — Director: Victra

**Mandate**: Ground truth. PnL reconciliation. Data sourcing. 用数字说话 starts here.

**Delivers to Darrow**: Verified PnL numbers, data quality reports, cross-verified reconciliation.

| Employee | Role | Tools | Status |
|----------|------|-------|--------|
| Accountant | Ground truth PnL, cross-verify signals | `accounting_reconciler.py`, PM CSV | **LIVE** |
| [PnL Analyst] | Product x date breakdown, WR analysis, cash flow | analysis tools, reporting | Needs creation |
| [Performance Analyst] | Strategy attribution, regime PnL, decay tracking | backtest comparison tools | Roadmap |

---

## Shared Tools (Entity-Wide)

| Tool | What | Location |
|------|------|----------|
| `deploy.sh` | Upload, restart, verify, rollback | `scripts/deploy.sh` |
| `strategy_ctl.py` | Kill/start/stop/status/sizing | `scripts/strategy_ctl.py` |
| `ops_verify.py` | Yaml ↔ systemd state check | `scripts/ops_verify.py` |
| `strategies.yaml` | Single source of truth — strategy state | `config/strategies.yaml` |
| `strategy_registry.py` | Programmatic access to configs | `config/strategy_registry.py` |
| SSH/SCP | EC2 access via `${EC2_KEY_PATH}` | — |
| Telegram/Discord notify | Alerting | `scripts/discord_notify.py`, health_monitor |
| `pytest` gate | 160 tests, blocks deploy | `tests/` |
| `ops_log.jsonl` | Append-only decision log | `data/ops_log.jsonl` |

---

## Scorecard

| Department | Director | Live | Partial | Roadmap | Total |
|------------|----------|------|---------|---------|-------|
| Research | Mustang | 1 | 1 | 2 | 4 |
| Risk | Dancer | 1 | 0 | 2 | 3 |
| Execution | Tactus | 4 | 0 | 1 | 5 |
| Infrastructure | Holiday | 3 | 0 | 1 | 4 |
| QA | [TBD] | 0 | 1 | 1 | 2 |
| Operations | Ragnar | 5 | 0 | 0 | 5 |
| Data | Victra | 1 | 0 | 2 | 3 |
| **Total** | **7 depts** | **15** | **2** | **9** | **26** |

---

## Milestones

### Milestone 1: Risk Foundation ✓ DEPLOYED

### Milestone 2: Infrastructure Foundation ✓ BUILT

### Milestone 2.5: Discord Integration ✓ WIRED

### Milestone 3: Research Expansion
- Statistical Signal Researcher, LFT overlay, Backtest Auditor

### Milestone 4: Scale
- SOL trader, Smart Order Router, CI Pipeline

### Milestone 5: Data Foundation (NEW)
- Victra stands up Data department
- Fix accounting reconciliation (loss undercounting — currently ~50% match, target ≥ 95%)
- PnL Analyst agent — product x date x WR automated reporting
- Performance attribution — which strategies earn, which bleed

---

## Codebase Map

```
Claude_HF/
├── agents/              # Agent definitions
│   ├── hf/              # Characters, monitor sentinel, risk guardian
│   └── live/            # BasePMTrader base class
├── config/              # Risk policies, strategy configs
│   ├── risk_policy.yaml
│   ├── strategies.yaml
│   └── strategy_registry.py
├── core/                # Domain logic
│   ├── risk/            # RiskGuardian
│   ├── signals/         # Signal generation
│   ├── backtest/        # Backtesting framework
│   └── portfolio/       # Portfolio optimization
├── data/models/         # XGBoost weights + feature lists
├── docs/                # This file, trading rules, research briefs
├── integrations/        # Polymarket client, LLM provider
├── memory/              # Persistent agent memory
├── orchestrator/        # Debate protocol, promotion gates, LLM, state
├── research/            # Model research sandbox
├── scripts/             # Everything executable
│   ├── live_trader_*    # Trader scripts (BasePMTrader subclasses)
│   ├── *_settlement_*   # Settlement checkers
│   ├── deploy.sh        # Unified deploy
│   ├── experiment_*     # Research experiments
│   └── accounting_reconciler.py
├── strategies/          # Strategy modules
└── tests/               # 160 tests, pre-deploy gate
```
