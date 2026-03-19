# /redeem — Redeem Settled Positions

Execute redemption for all settled Polymarket positions across both wallets.

```bash
cd /path/to/your/project

echo "=== Redeeming settled positions ==="
python scripts/redeem_positions.py --execute

echo ""
echo "=== Done. Check output above for USDC redeemed. ==="
```

**Safety note**: `--execute` submits real on-chain transactions.
Omit `--execute` (dry-run mode) to preview what would be redeemed first.

After execution, check `data/paper_trading/trades.jsonl` and dashboard for updated balances.
