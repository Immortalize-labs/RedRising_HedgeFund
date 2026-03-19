# /sync — Sync Settlement and Data

Run settlement checkers for active strategies and pull latest tick data from your infrastructure.

```bash
cd /path/to/your/project

echo "=== Settlement Check ==="
python scripts/settlement_checker.py

echo "=== Syncing latest data ==="
bash scripts/sync_data.sh
```

After sync completes, report:
- Any resolved positions found
- Latest data file dates
- Any settlement errors
