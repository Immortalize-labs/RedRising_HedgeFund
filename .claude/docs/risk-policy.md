# Risk Policy Reference

> Source: `config/risk_policy.yaml`

## Signal Validation Gate
| Parameter | Value |
|-----------|-------|
| Min passing signals | 3 |
| Min abs IC | 0.01 |
| Max permutation p-value | 0.05 |
| Max stability delta | 0.02 |

## Backtest Gate
| Parameter | Value |
|-----------|-------|
| Min OOS Sharpe | 0.5 |
| Min OOS days | 30 |
| Min decay ratio (OOS/IS) | 0.3 |
| Max drawdown | 5.0% |
| Min trades | 50 |
| Min Calmar | 1.0 |
| Max daily turnover | 10.0 |

## Paper -> Live Gate
| Parameter | Value |
|-----------|-------|
| Max slippage delta | 2.0 bps |
| Min fill rate | 80% |
| Max risk incidents | 0 |
| Min paper days | 7 |

## Live Trading Risk
| Parameter | Value |
|-----------|-------|
| Max position USD | $500 |
| Max exposure USD | $2,000 |
| Max daily loss USD | $50 |
| Max drawdown (live) | 2.0% |
| Max open orders | 8 |

## Kill Switch
| Parameter | Value |
|-----------|-------|
| Adverse selection window | 10 trades |
| Min win rate (trigger) | 20% |

## Execution Defaults
| Parameter | Value |
|-----------|-------|
| Maker cost | -1.0 bps (rebate) |
| Taker cost | 5.0 bps |
| Size per symbol | $500 |
| Entry z-score | 1.8 |
| Exit z-score | 0.36 |
| Min hold time | 3,600s (60 min) |
