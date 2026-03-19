# /status — Live Trading Status

Show EC2 process health and recent P&L snapshot.

```bash
cd /path/to/your/project

echo "=== EC2 Process Status ==="
# Check live trader processes (adjust host/key as needed)
EC2_HOST="${EC2_HOST:-}"
if [ -n "$EC2_HOST" ]; then
  ssh -i "${EC2_KEY_PATH:-data/your-ec2-key.pem}" "ubuntu@$EC2_HOST" \
    "ps aux | grep -E 'live_trader|tick_collector' | grep -v grep"
else
  echo "(EC2_HOST not set — showing local processes)"
  ps aux | grep -E 'live_trader|tick_collector' | grep -v grep
fi

echo ""
echo "=== Recent Trades (last 10) ==="
python - <<'EOF'
import json, pathlib, sys
from datetime import datetime

for path in [
    "data/paper_trading/trades.jsonl",
    "data/live_trading_v2/trades.jsonl",
    "data/momentum_live/trades.jsonl",
]:
    p = pathlib.Path(path)
    if not p.exists():
        continue
    lines = p.read_text().strip().splitlines()
    trades = [json.loads(l) for l in lines if l.strip()]
    recent = trades[-10:]
    print(f"\n-- {path} ({len(trades)} total) --")
    for t in recent:
        ts = t.get("timestamp", t.get("ts", "?"))
        side = t.get("side", t.get("action", "?"))
        price = t.get("price", "?")
        pnl = t.get("pnl", "")
        print(f"  {ts}  {side}  @ {price}  pnl={pnl}")
EOF
```

Report any dead processes, recent error patterns, or open positions needing attention.
