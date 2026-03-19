# Trading Rules — Immortalize Labs HF

## Scope & AI Model
Full-scope trading decisions are handled by DeepSeek:
- Direction (long / short)
- Position size
- Risk per trade
- Take profit level
- Stop loss level
- Optimal portfolio value / allocation

## Portfolio Constraint
| Parameter | Value |
|-----------|-------|
| Total notional | $1,000 |
| Margin (10x leverage) | $100 |
| Max per-trade risk | Determined by DeepSeek per cycle |

## Time Zone
All timestamps and scheduling use **GMT-5 (New York / Eastern Standard Time)**.
Do not confuse with UTC or other offsets.

## Cycle Logic
Every minute the platform must:
1. Pull latest market data
2. Get AI (DeepSeek) suggestion for direction + sizing
3. Compare suggestion against current open positions
4. If suggestion does not align with open position -> investigate cause and fix automatically

## Bug Policy
If a bug or issue is found at any point, investigate and fix immediately — no permission required.

## Alignment Check
Every cycle verify that the AI suggestion matches the open position.
Misalignments must be auto-resolved without manual intervention.
