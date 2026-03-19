# /deploy — Deploy to EC2

Deploy a specific component to EC2 with backup, rollback, and pre-deploy tests.

Usage: `/deploy <target>` — e.g., `/deploy eth`, `/deploy risk`, `/deploy all`

**Unified script**: `bash scripts/deploy.sh <target>`

Available targets based on `$ARGUMENTS`:

- `btc` — BTC 5-min trader
- `eth` — ETH 5-min trader
- `xrp` — XRP 5-min trader
- `btc-15m` — BTC 15-min trader
- `eth-15m` — ETH 15-min trader
- `xrp-15m` — XRP 15-min trader
- `risk` — Risk infra (drawdown-monitor, risk-reporter, restarts all traders)
- `health` — Health monitor
- `telegram` — Telegram reporter
- `redeemer` — Token redeemer
- `retrain` — Monthly retrain
- `collector` — Tick collector
- `core` — Shared code only (base_trader, client, guardian)
- `all-traders` — All 6 traders
- `all` — Everything

Special flags:
- `--rollback` — Restore from most recent backup: `bash scripts/deploy.sh eth --rollback`
- `--skip-tests` — Skip pre-deploy pytest gate
- `--status` — Show EC2 service status: `bash scripts/deploy.sh --status`

The deploy script automatically:
1. Runs `pytest tests/ -x` before deploying (pre-deploy gate)
2. Backs up current EC2 code to `.backups/<timestamp>/`
3. Uploads files via SCP
4. Runs import smoke test on EC2
5. Restarts affected services
6. Health checks after 15s — auto-rolls back if service is dead

If `$ARGUMENTS` is empty, run `bash scripts/deploy.sh --list` to show targets.

> **Managed workflow**: Use `/task deploy <target>` to route through Holiday (infra-director) with full gate checks and QA follow-up.
