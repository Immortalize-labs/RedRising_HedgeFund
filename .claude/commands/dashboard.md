# /dashboard — Launch Unified Dashboard

Kill any existing dashboard process and start a fresh instance on port 8888.

```bash
# Kill existing dashboard on port 8888 (if any)
lsof -ti:8888 | xargs kill -9 2>/dev/null || true

# Start unified dashboard with tick sync enabled
cd /path/to/your/project
python scripts/unified_dashboard.py --port 8888 --sync &

echo "Dashboard starting at http://localhost:8888"
echo "PID: $!"
```

Wait ~3 seconds then open http://localhost:8888 in the browser.
If `unified_dashboard.py` doesn't accept `--sync`, check `scripts/unified_dashboard.py` for the correct flags.
