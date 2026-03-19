# /health — EC2 Health Check

Quick health check of all services on EC2. Also shows automated health monitor status.

**Automated monitoring**: `health-monitor` service runs 24/7 on EC2, checks every 60s, alerts via Telegram on failures/recovery.

```bash
EC2_HOST="${EC2_HOST:-}"
KEY_PATH="${EC2_KEY_PATH:-data/your-ec2-key.pem}"
SSH_CMD="ssh -o StrictHostKeyChecking=no -i $KEY_PATH ubuntu@$EC2_HOST"

echo "=== Service Status ==="
$SSH_CMD "for svc in polymarket-eth-trader polymarket-xrp-trader polymarket-btc-15m-trader polymarket-eth-15m-trader polymarket-xrp-15m-trader health-monitor telegram-watch drawdown-monitor ops-bridge polymarket-redeemer; do
  status=\$(sudo systemctl is-active \$svc 2>/dev/null || echo 'not-found')
  printf '  %-30s %s\n' \$svc \$status
done"

echo ""
echo "=== RISK_KILL Status ==="
$SSH_CMD "cat /home/ubuntu/trader/data/RISK_KILL 2>/dev/null || echo '  Not present — trading active'"

echo ""
echo "=== Disk / Memory ==="
$SSH_CMD "df -h / | tail -1; echo ''; free -h | head -2"

echo ""
echo "=== Recent Errors (last 5 min) ==="
$SSH_CMD "sudo journalctl --since '5 min ago' -p err --no-pager -q 2>/dev/null | tail -10 || echo '  None'"

echo ""
echo "=== Health Monitor Log (last 5 lines) ==="
$SSH_CMD "tail -5 /home/ubuntu/trader/data/health_monitor.log 2>/dev/null || echo '  Not running'"
```

Report any down services, active KILL file, disk/memory issues, or recent errors.
