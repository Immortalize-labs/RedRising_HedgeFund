# Christoffersen & Diebold (2006) — Financial Returns, Direction-of-Change Forecasting, and Volatility Dynamics

**Full Citation:** Christoffersen, P.F., & Diebold, F.X. (2006). "Financial asset returns, direction-of-change forecasting, and volatility dynamics." *Management Science*, 52(8), 1273–1287. DOI: 10.1287/mnsc.1060.0520

**Scores:** Relevance=5, Rigor=5, Implementability=4, Total=14/15 — THEORETICAL FOUNDATION

## Key Findings
Establishes a fundamental theoretical link between VOLATILITY DYNAMICS and the forecastability of DIRECTION (sign) of returns:
1. Even when conditional mean return is zero or unpredictable, VOLATILITY DYNAMICS make SIGN PREDICTABLE
2. Under a symmetric distribution with time-varying variance, the probability of positive return varies over time whenever unconditional mean is nonzero
3. Out-of-sample directional forecast accuracy of ~58-60% using GARCH-based volatility models (S&P 100)
4. This is NOT due to mean predictability but purely to VARIANCE DYNAMICS
5. Bridges volatility forecasting and market timing literatures

## This paper provides the theoretical justification for our entire directional volatility research program.

## Key Formulas

**Sign predictability from variance dynamics:**
```
Under r_t = mu + sigma_t * eps_t, with eps_t ~ symmetric(0,1):
P(r_t > 0 | F_{t-1}) = 1 - F_eps(-mu / sigma_t)
```
Since sigma_t is F_{t-1}-measurable and time-varying, the conditional probability varies over time even with constant mu.

**Optimal direction-of-change forecast:**
```
I_hat_t = 1[P(r_t > 0 | F_{t-1}) > 0.5]
         = 1[mu / sigma_hat_t > 0]
```
For mu > 0 (long-only assets): ALWAYS predict up direction. But:
- When sigma_t is HIGH: P(r>0) is closer to 0.5 → weaker directional signal
- When sigma_t is LOW: P(r>0) is further from 0.5 → stronger directional signal

**Key implication:** VOLATILITY COMPRESSION signals stronger directional predictability!

**Practical metric for our system:**
```python
def christoffersen_signal_strength(sigma_t, mu=0.0001):
    """
    Higher return = stronger directional signal this bar.
    Use as confidence weight for semivariance directional prediction.
    """
    from scipy.stats import norm
    p_up = 1 - norm.cdf(-mu / sigma_t)
    signal_strength = abs(p_up - 0.5)  # 0 = no signal, 0.5 = perfect
    return p_up, signal_strength
```

## Integration with Semivariance
Combine with RS+/RS- framework:
1. Christoffersen-Diebold: low sigma_t → stronger directional edge from any signal
2. Patton-Sheppard: RS-/RS+ ratio → predicted direction
3. Combined: weight RS direction signal by (1/sigma_t) — higher confidence when vol is low

## Application to Crypto
In crypto (mu > 0 over long run):
- During LOW VOLATILITY periods: bias to long is stronger → our signals have better edge
- During HIGH VOLATILITY periods (spikes): signals weaker → reduce position size (aligns with risk policy vol regime scaling)

## Paywall Status
Closed (INFORMS/Management Science). Working paper available via Wharton Research Data Services.

## Tags
direction-of-change, sign-forecasting, volatility-dynamics, Christoffersen, Diebold, theoretical-foundation, GARCH, regime
