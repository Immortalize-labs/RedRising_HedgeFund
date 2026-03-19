# Gençay, Selçuk & Whitcher (2005) — Multiscale Systematic Risk

**Full Citation:** Gençay, R., Selçuk, F., & Whitcher, B. (2005). "Multiscale systematic risk." *Journal of International Money and Finance*, 24(1), 55–70. DOI: 10.1016/j.jimonfin.2004.10.003

**Scores:** Relevance=5, Rigor=5, Implementability=4, Total=14/15

## Key Findings
Decomposes market beta (systematic risk) across multiple wavelet timescales using MODWT applied to stock portfolios and market indices:
1. Beta is NOT scale-invariant: systematic risk estimates vary significantly across investment horizons
2. Short-horizon betas tend to be noisier and often lower for large-cap portfolios
3. Longer-horizon betas converge toward CAPM-consistent values
4. Wavelet-based betas provide the first rigorous decomposition showing single-beta assumption masks meaningful heterogeneity

## Key Formulas

**Scale-dependent beta:**
```
beta_j = Cov_j(R_i, R_m) / Var_j(R_m)
       = nu_{X,Y}(tau_j) / nu_X^2(tau_j)
```
where nu_{X,Y}(tau_j) is the wavelet covariance at scale tau_j.

**MODWT wavelet variance estimator:**
```
nu_hat_X^2(tau_j) = (1/N_tilde_j) * sum_{t=L_j-1}^{N-1} w_tilde_{j,t}^2
```
where w_tilde_{j,t} are MODWT wavelet coefficients and N_tilde_j is the number of boundary-unaffected coefficients.

## Application to Crypto
For cross-asset prediction at 15-min, compute scale-dependent beta between each crypto (BTC, ETH, SOL) and the "market" (BTC or total crypto market cap index):
- High-frequency beta_j=1,2 — microstructure-driven, noisy, typically low predictive value
- Medium-frequency beta_j=3,4 — intraday momentum contribution
- Low-frequency beta_j=5,6 — systematic trend component

**Feature idea:** When beta_j=3 diverges from beta_j=5, it signals a potential reversion at the intraday scale.

## Paywall Status
Closed (Elsevier/JIMF). Gençay's working papers partially available via Simon Fraser University.

## Tags
wavelet, MODWT, beta, systematic-risk, multiscale, Gencay, Selcuk, Whitcher, CAPM, cross-asset
