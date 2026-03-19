# Andersen, Dobrev & Schaumburg (2012) — Jump-Robust Volatility Estimation: MedRV and MinRV

**Full Citation:** Andersen, T.G., Dobrev, D., & Schaumburg, E. (2012). "Jump-robust volatility estimation using nearest neighbor truncation." *Journal of Econometrics*, 169(1), 75–93. DOI: 10.1016/j.jeconom.2012.01.011

**Scores:** Relevance=4, Rigor=5, Implementability=4, Total=13/15

## Key Findings
Develops MedRV (Median Realized Variance) and MinRV estimators that are robust to both finite-activity jumps and microstructure noise:
1. Taking medians or minimums of adjacent squared returns eliminates jump-contaminated observations asymptotically
2. Achieves optimal convergence rate O_p(n^{-1/2}) — matches bipower variation
3. Outperforms bipower variation in finite samples when jumps are large or clustered
4. Complete asymptotic distribution theory enables feasible inference
5. Truncation principle can be applied separately to + and - returns → jump-robust realized semivariances

## Key Formulas

**Median Realized Variance:**
```
MedRV = (pi / (6 - 4*sqrt(3) + pi)) * (n/(n-2)) * sum_{i=2}^{n-1} med(|r_{i-1}|, |r_i|, |r_{i+1}|)^2
```

**MinRV (Nearest Neighbor Truncation):**
```
MinRV = (pi/(pi-2)) * (n/(n-1)) * sum_{i=1}^{n-1} min(|r_i|, |r_{i+1}|)^2
```

**Asymptotic distribution:**
```
sqrt(n) * (MedRV - IV) ~ N(0, Omega_med)
where Omega_med = c_med * integral_0^1 sigma^4(s) ds
c_med ≈ 0.96
```

## Jump-Robust Semivariance (Derived from this framework)
Apply the median/min approach to signed returns:

```python
def medrv_semivariance(sub_returns):
    """
    Jump-robust realized semivariance using median of adjacent squared returns.
    """
    n = len(sub_returns)
    c = np.pi / (6 - 4*np.sqrt(3) + np.pi) * n/(n-2)

    # Compute median of adjacent triples
    med_sq = np.array([
        np.median([sub_returns[i-1]**2, sub_returns[i]**2, sub_returns[i+1]**2])
        for i in range(1, n-1)
    ])

    # Split by sign of middle return
    signs = sub_returns[1:-1]
    rs_plus_robust  = c * np.sum(med_sq[signs >= 0])
    rs_minus_robust = c * np.sum(med_sq[signs < 0])

    return rs_plus_robust, rs_minus_robust
```

## When to Use
- Use MedRV semivariance when: crypto data has exchange-specific spikes, API errors, or irregular ticks
- Provides cleaner signal than raw RS during high-frequency microstructure noise periods
- MedRV is the preferred alternative to BPV for noisy crypto data

## Paywall Status
Closed (Elsevier). NBER Working Paper version available via CREATES website.

## Tags
MedRV, MinRV, jump-robust, realized-variance, semivariance, Andersen, Dobrev, microstructure-robust, crypto-applicable
