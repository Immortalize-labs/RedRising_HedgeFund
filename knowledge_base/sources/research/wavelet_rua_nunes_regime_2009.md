# Rua & Nunes (2009) — International Comovement: Wavelet Regime Detection

**Full Citation:** Rua, A. & Nunes, L.C. (2009). "International comovement of stock market returns: A wavelet analysis." *Journal of Empirical Finance*, 16(4), 632–639. DOI: 10.1016/j.jempfin.2009.02.002

**Scores:** Relevance=5, Rigor=4, Implementability=4, Total=13/15

## Key Findings
Applies continuous wavelet coherence and wavelet phase analysis to study time-varying, frequency-dependent comovement among major stock markets:
1. International correlation REGIMES are jointly determined by both TIME and FREQUENCY
2. Traditional rolling-window correlation conflates structurally distinct phenomena at different scales
3. Wavelet coherence maps serve as REGIME DETECTION DEVICES — identify structural breaks as coherence "islands" or persistent bands
4. Long-run coherence (2-4 year cycles) increased substantially post-1990s; short-run coherence remains crisis-driven
5. Phase difference arrows reveal whether lead-lag relationships shift across regimes

## Key Formulas

**Morlet Mother Wavelet (standard for regime detection):**
```
psi_0(eta) = pi^{-1/4} * exp(i * omega_0 * eta) * exp(-eta^2 / 2)
omega_0 = 6   (central frequency, balances time/frequency localization)
```

**Smoothing Operator:**
```
S(W) = S_scale(S_time(W))
```
- S_time: Gaussian kernel along time axis
- S_scale: boxcar filter along scale axis

**Monte Carlo Significance Testing:**
Against AR(1) red noise null (more realistic than white noise for financial data):
```
r_hat_1 = sum_{t=2}^N (x_t - x_bar)(x_{t-1} - x_bar) / sum_{t=1}^N (x_t - x_bar)^2
```
Generate 10,000 AR(1) surrogate time series, compute coherence for each.
95th percentile of surrogate coherence = significance threshold.

## Application to Crypto Regime Detection
Use wavelet coherence map as a REGIME INDICATOR for our trading system:

```python
# Pseudo-code for regime detection via wavelet coherence
def get_regime(btc_returns, eth_returns, scale_band=(3,5)):
    """
    Returns: 'coupled' (high coherence = trend following)
             'decoupled' (low coherence = mean reversion regime)
    """
    # Compute MODWT-based rolling correlation as CWT proxy (faster)
    btc_d = modwt_detail(btc_returns, levels=scale_band)
    eth_d = modwt_detail(eth_returns, levels=scale_band)
    coherence = rolling_correlation(btc_d, eth_d, window=64)
    return 'coupled' if coherence > 0.7 else 'decoupled'
```

**Regime signal ideas:**
1. `regime_coherence_j` — rolling wavelet correlation between BTC and ETH at scale j
2. `regime_phase_j` — which asset is leading at scale j
3. `regime_change_flag` — boolean: coherence changed significantly in last 4 bars

## Paywall Status
Closed (Elsevier). Template code available via Grinsted et al. (2004) MATLAB toolbox.

## Tags
wavelet-coherence, regime-detection, CWT, Morlet, Rua, Nunes, comovement, phase-analysis, crypto-applicable
