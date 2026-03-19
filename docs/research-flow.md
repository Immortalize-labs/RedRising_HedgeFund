# Research Flow — Daily Intelligence Pipeline

## Overview

The research department operates a continuous intelligence pipeline that discovers, filters, ingests, and debates new knowledge daily. This ensures every research decision is grounded in the latest academic and practitioner literature — not gut feeling.

```
SEARCH → FILTER → INGEST → PRESENT → DEBATE → ACTION
```

## Daily Schedule

| Time | Stage | What Happens |
|------|-------|-------------|
| 6:00 AM | **Scan** | Automated fetch from ArXiv, GitHub, SSRN, crypto research |
| 6:05 AM | **Filter** | AI quality gate (relevance + rigor + implementability >= 10/15) |
| 6:10 AM | **Ingest** | Passing sources auto-ingested into desk-specific KB namespace |
| 6:15 AM | **Brief** | Daily brief generated per research desk |
| 6:30 AM | **Present** | Each desk lead picks 1 paper, writes structured presentation |
| 7:00 AM | **Debate** | Cross-desk feedback round (every reviewer comments on all 4) |
| 7:30 AM | **Synthesize** | Research Director compiles actionable ideas, archives the rest |

## Scan Sources

| Source | Type | Frequency | Filter |
|--------|------|-----------|--------|
| ArXiv quant-fin | Papers | Daily (~5-10/day) | Relevance to crypto, short-horizon |
| ArXiv stat-ML | Papers | Daily | Trading-applicable methods |
| GitHub trending | Repos | Daily | Quant, crypto, ML tags |
| SSRN finance | Working papers | Daily | New working papers |
| Crypto research | Reports | Daily | Messari, Delphi, selected blogs |

## Quality Gate (10/15 minimum)

Every source is scored on three axes (1-5 each):

| Criterion | Score 1 | Score 5 |
|-----------|---------|---------|
| **Relevance** | Tangentially related | Directly applicable to our 15-min crypto prediction |
| **Rigor** | Blog post, no methodology | Peer-reviewed, robust statistical testing |
| **Implementability** | Theoretical only | Clear formulas, reproducible, ready to code |

Sources scoring below 10/15 are logged but not ingested.

## Knowledge Base Namespaces

Each research desk maintains its own curated knowledge section:

```
knowledge_base/sources/
├── signals/       ← Clown's desk (time-series, spectral, regime)
├── models/        ← Pebble's desk (ML/DL, ensembles, training)
├── structure/     ← Screwface's desk (microstructure, orderbook)
├── strategy/      ← Thistle's desk (portfolio, Kelly, allocation)
├── general/       ← Shared across all desks
├── research/      ← Curated paper summaries (all desks)
└── web/           ← Web-sourced documentation
```

## Presentation Format

Each desk lead presents one paper daily using this structure:

```markdown
# Daily Paper — [Desk Name]
**Presenter**: [Name] ([Desk])
**Date**: YYYY-MM-DD

## Paper
**Title**: [Full title]
**Authors**: [Authors] ([Year])
**Source**: [Journal/Venue]

## Why I Picked This
[2-3 sentences — what caught their eye, why it matters NOW]

## Key Findings
[3-5 bullet points — the actual results]

## Applicability to Us
[Specific: which strategy, which feature, what IC improvement expected]

## Limitations / Red Flags
[Honest critique — sample size, overfitting risk, domain-specific caveats]

## Proposed Action
[Concrete: "Add X to feature pipeline" or "No action — interesting but not tradeable"]
```

## Feedback Format

Each reviewer comments from their domain's perspective:

```markdown
**Reviewer**: [Name] ([Desk])
**On**: [Presenter]'s paper ([Title])

- **Agree / Challenge / Extend**: [one of three]
- **Comment**: [2-3 sentences from their domain lens]
- **Cross-domain connection**: [optional — how this connects to their work]
```

## Seminar Output

All artifacts are stored chronologically:

```
research/seminars/
├── 2026-03-20/
│   ├── signals_clown.md          ← Clown's paper pick
│   ├── models_pebble.md          ← Pebble's paper pick
│   ├── structure_screwface.md    ← Screwface's paper pick
│   ├── strategy_thistle.md       ← Thistle's paper pick
│   ├── feedback.md               ← All cross-desk feedback
│   └── synthesis.md              ← Director's summary + action items
```

## The Flywheel

```
Better KB → Better paper picks → Better debates → Better hypotheses → Better experiments → Better KB
```

Over time, each desk's knowledge base becomes the deepest curated collection in its domain. The cross-desk feedback ensures no one operates in a bubble. The daily cadence creates institutional memory that compounds.

## Research Tracker

All active, completed, and backlogged research is tracked in a central document with:

- **Status**: Planned / Active / PASS / FAIL
- **Owner**: Which desk lead owns it
- **Result**: Quantified outcome (IC scores, gate pass/fail)
- **Follow-up**: What happens next
- **Scripts**: Where the code lives
- **Findings**: Where the write-up lives

This ensures no research thread is forgotten and every experiment is traceable.
