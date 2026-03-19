# Bollerslev, Li & Todorov (2016) — Roughing up Beta

**Full Citation:** Bollerslev, T., Li, S.Z., & Todorov, V. (2016). "Roughing up Beta: Continuous versus Discontinuous Betas and the Cross-Section of Expected Stock Returns." *Journal of Financial Economics*, 120(3), 464–490. DOI: 10.1016/j.jfineco.2016.02.001

**Scores:** Relevance=4, Rigor=5, Implementability=4, Total=13/15

## Key Findings
Provides highly refined methodology for separating continuous and jump components of realized variance, and decomposing jumps by sign at high frequency:
1. Downside (negative) jump betas carry significant risk premia in the cross-section
2. Upside jump betas and continuous betas have different pricing implications
3. Truncated realized semivariance estimators are robust to microstructure noise
4. Threshold-based methods distinguish jumps from continuous moves

## Critical Contribution: Truncated Semivariance (Noise-Robust)
Standard semivariance can be corrupted by microstructure noise at high frequencies. Truncated version:

```
RS^{-,c}_t = sum_{j=1}^{M} r_{t,j}^2 * 1(r_{t,j} < 0) * 1(r_{t,j}^2 <= alpha * V_hat_{t,j} * Delta_M)
```

where:
- V_hat_{t,j} = local volatility estimate at time j
- alpha = threshold parameter (typically 4 or 5)
- Delta_M = 1/M = sampling interval

**Computing local volatility for truncation:**
```python
def truncated_semivariance(sub_returns, alpha=4.0):
    """
    sub_returns: M intra-bar returns
    alpha: truncation threshold (4 = exclude 4-sigma moves as pure jumps)
    """
    M = len(sub_returns)
    # Local vol estimate using BPV on adjacent pairs
    adj_bpv = np.sqrt(2/np.pi)**(-2) * np.abs(sub_returns[:-1]) * np.abs(sub_returns[1:])
    V_local = np.concatenate([[adj_bpv[0]], adj_bpv])  # pad start

    threshold = alpha * V_local / M
    continuous_mask = sub_returns**2 <= threshold

    rs_minus_c = np.sum(sub_returns**2 * (sub_returns < 0) * continuous_mask)
    rs_plus_c  = np.sum(sub_returns**2 * (sub_returns >= 0) * continuous_mask)

    # Jump components (violations of threshold)
    jump_mask = ~continuous_mask
    rs_minus_j = np.sum(sub_returns**2 * (sub_returns < 0) * jump_mask)
    rs_plus_j  = np.sum(sub_returns**2 * (sub_returns >= 0) * jump_mask)

    return rs_minus_c, rs_plus_c, rs_minus_j, rs_plus_j
```

## Application to Crypto
Crypto has significant microstructure effects (exchange-specific latency, varying tick sizes, fragmented liquidity). The truncation methodology is especially important:
- Prevents exchange outage "fake" volatility from corrupting semivariance estimates
- Separates liquidation cascade jumps from continuous order flow pressure
- Enables cleaner prediction of continuous vs. jump-driven directional moves

## Feature Set
1. `rs_minus_continuous` — downside continuous semivariance (diffusion)
2. `rs_plus_continuous` — upside continuous semivariance
3. `rs_minus_jump` — signed negative jump contribution
4. `rs_plus_jump` — signed positive jump contribution
5. `jump_direction` — sign(rs_plus_jump - rs_minus_jump)
6. `continuous_imbalance` — rs_plus_c / (rs_plus_c + rs_minus_c)

## Paywall Status
Closed (JFE). Available on SSRN: https://ssrn.com/abstract=1725551 (earlier version).

## Tags
truncated-semivariance, jump-detection, microstructure-robust, Bollerslev, Todorov, JFE, continuous-jump-decomposition
