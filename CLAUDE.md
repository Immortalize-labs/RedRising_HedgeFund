# RedRising HedgeFund

## Core Rules
- Timezone: GMT-5 (NY, USA). Never mess up time.
- Auto-fix bugs/issues immediately. No permission needed.
- Every cycle: check AI suggestion alignment with open positions. Auto-investigate misalignment.
- Portfolio sizing: configure in `config/risk_policy.yaml`.

## Key Paths
- Agent framework: `agents/base.py`
- Orchestrator / debate: `orchestrator/debate.py`
- Risk policy: `config/risk_policy.yaml`
- Inference config: `config/inference.yaml`
- Think tool: `scripts/think.py`

## Think Protocol (MANDATORY — EVERY MESSAGE)

Two think calls per user interaction. No exceptions.

### Think 1: ON RECEIVE (before any tool calls or investigation)
```bash
python scripts/think.py \
  --caller "agent-name" \
  --claim "What is the user asking/reporting?" \
  --priors "What do I already know that's relevant?" \
  --math "Any numbers to sanity-check?" \
  --hypotheses "What could be going on? Rank by likelihood." \
  --cheapest_check "What's the minimum I need to look at to answer correctly?" \
  --action "Investigation plan — what to read/check first"
```

### Think 2: BEFORE REPLY (after investigation, before responding)
```bash
python scripts/think.py \
  --caller "agent-name" \
  --claim "What am I about to tell the user?" \
  --priors "What did the data actually show?" \
  --math "Do my numbers add up?" \
  --hypotheses "Am I jumping to conclusions? What alternative explanations exist?" \
  --cheapest_check "Is there one more thing I should verify before responding?" \
  --action "Final response plan"
```

## Deploy Gate Criteria
- Pre-deploy: `pytest tests/ -x` must pass
- Backup current code before upload
- Import smoke test after upload
- Service restart + health check after 15s
- Auto-rollback if service is dead after deploy

## Report Schema (MANDATORY)
Every agent task must conclude with:
```json
{
  "agent": "agent-name",
  "department": "department-name",
  "task": "<task description>",
  "status": "pass|fail|blocked|escalate",
  "metrics": {},
  "detail": "<summary>",
  "blockers": [],
  "next_steps": []
}
```

## References
- @.claude/docs/trading-rules.md
- @.claude/docs/risk-policy.md
- @docs/fund-org.md
