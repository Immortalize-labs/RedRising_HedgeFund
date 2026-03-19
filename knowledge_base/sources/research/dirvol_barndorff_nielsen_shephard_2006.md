# Barndorff-Nielsen & Shephard (2006) — Econometrics of Testing for Jumps in Financial Economics Using Bipower Variation

**Full Citation:** Barndorff-Nielsen, O.E. & Shephard, N. (2006). "Econometrics of Testing for Jumps in Financial Economics Using Bipower Variation." *Journal of Financial Econometrics*, 4(1), 1–30. DOI: 10.1093/jjfinec/nbi022

**Scores:** Relevance=5, Rigor=5, Implementability=5, Total=15/15

## Key Findings
Develops theory and practical procedures for detecting jumps using the difference between realized variance and realized bipower variation (BPV):
1. BPV converges to integrated variance (the continuous component) even in presence of jumps
2. The test statistic for no-jump null has a feasible asymptotic distribution
3. Simulation shows good size and power at realistic sampling frequencies (5-minute returns)
4. Empirical application to equity data reveals frequent, economically significant jumps

## Key Formulas

**Bipower Variation (BPV):**
```
BPV_t = mu_1^{-2} * sum_{j=2}^{M} |r_{t,j-1}| * |r_{t,j}|
where mu_1 = sqrt(2/pi) = 0.7979...
```

**Jump component estimator:**
```
J_t = max(RV_t - BPV_t, 0)
```
(truncated at 0 to ensure non-negativity)

**Continuous component:**
```
C_t = RV_t - J_t = min(RV_t, BPV_t)
```

**Feasible jump test statistic:**
```
z_{tp} = (RV_t - BPV_t) / RV_t
         / sqrt((mu_1^{-4} + 2*mu_1^{-2} - 5) * (1/M) * max(1, TQ_t / BPV_t^2))
z_{tp} ~d N(0,1) under H0: no jumps
```
where TQ_t = realized tripower quarticity.

**Realized Tripower Quarticity:**
```
TQ_t = M * mu_{4/3}^{-3} * sum_{j=3}^{M} |r_{j-2}|^{4/3} |r_{j-1}|^{4/3} |r_j|^{4/3}
where mu_{4/3} = E[|Z|^{4/3}] = 2^{2/3} * Gamma(7/6) / Gamma(1/2)
```

## Application for 15-min Crypto Bars (using 1-min sub-returns)

```python
import numpy as np
from scipy.stats import norm

def detect_jump(sub_returns):
    """
    sub_returns: array of M=15 log returns (1-min) within a 15-min bar
    Returns: jump_flag, jump_magnitude, z_stat
    """
    M = len(sub_returns)
    mu_1 = np.sqrt(2/np.pi)

    RV = np.sum(sub_returns**2)
    BPV = mu_1**(-2) * np.sum(np.abs(sub_returns[:-1]) * np.abs(sub_returns[1:]))
    BPV = max(BPV, 1e-10)

    # Tripower quarticity
    mu_43 = 2**(2/3) * special.gamma(7/6) / special.gamma(1/2)
    TQ = M * mu_43**(-3) * np.sum(
        np.abs(sub_returns[:-2])**(4/3) *
        np.abs(sub_returns[1:-1])**(4/3) *
        np.abs(sub_returns[2:])**(4/3)
    )

    relative_jump = (RV - BPV) / RV
    se = np.sqrt((mu_1**(-4) + 2*mu_1**(-2) - 5) / M * max(1, TQ / BPV**2))
    z_stat = relative_jump / se if se > 0 else 0.0

    jump_flag = z_stat > 3.09  # ~0.1% significance
    jump_magnitude = max(RV - BPV, 0)

    return jump_flag, jump_magnitude, z_stat
```

## Feature Set from Jump Detection
1. `jump_flag_t` — binary: was there a significant jump in this bar?
2. `jump_magnitude_t` — size of jump component
3. `continuous_vol_t` — C_t = BPV (noise-robust volatility)
4. `jump_ratio_t` — J_t / RV_t (what fraction of variance is from jumps?)
5. `signed_jump_t` — sign of contemporaneous return when jump_flag=True

## Paywall Status
Open access via Oxford Academic: https://academic.oup.com/jjfinec/article/4/1/1/856454

## Tags
jump-detection, bipower-variation, realized-variance, Barndorff-Nielsen, Shephard, JFEC, open-access, crypto-applicable
