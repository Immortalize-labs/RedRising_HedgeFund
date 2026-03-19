# Percival & Walden (2000) — Wavelet Methods for Time Series Analysis

**Full Citation:** Percival, D.B. & Walden, A.T. (2000). *Wavelet Methods for Time Series Analysis.* Cambridge University Press. ISBN: 978-0-521-64068-4. DOI: 10.1017/CBO9780511841040

**Scores:** Relevance=4, Rigor=5, Implementability=4, Total=13/15

## Key Findings
The authoritative statistical reference for wavelet analysis of time series. Rigorously develops the DWT, MODWT, and their statistical properties. Key contributions:
1. Formal development of the MODWT wavelet variance estimator and its asymptotic distribution under various dependence assumptions
2. The concept of "wavelet-based analysis of variance" allowing hypothesis testing at each scale
3. Comprehensive treatment of boundary conditions and their impact on coefficient quality
4. Detailed comparison showing MODWT's advantages: shift-invariance, no dyadic length restriction, asymptotically more efficient wavelet variance estimates

The book provides the mathematical scaffolding upon which all applied wavelet work in finance is built.

## Relevance to 15-min Crypto Prediction
Essential for understanding statistical properties of the decomposition. Provides the rigorous foundations for confidence intervals on scale-specific statistics — critical for knowing which scales carry real signal vs. noise in crypto data.

## Key Methods & Formulas

**MODWT pyramid algorithm** with explicit handling of circular vs. reflection boundary conditions.

**Unbiased MODWT wavelet variance estimator:**
```
nu_hat^2(tau_j) = (1/N_hat_j) * sum_{t in T_j} W_tilde_{j,t}^2
```
where T_j excludes boundary-affected coefficients.

**Confidence intervals for wavelet variance:**
```
[N_hat_j * nu_hat^2 / chi^2_{N_hat_j, alpha/2},
 N_hat_j * nu_hat^2 / chi^2_{N_hat_j, 1-alpha/2}]
```
(Gaussian assumption; non-Gaussian adjustments provided)

**Equivalent filter widths at each scale:**
```
L_j = (2^j - 1)(L - 1) + 1
```
where L is the base filter width. This determines the number of boundary-corrupted coefficients.

**Wavelet-based hypothesis tests** for homogeneity of variance across time (regime detection).

## Critical Practical Rule
For an LA(8) filter (L=8) and J=6 levels:
- L_1 = 7, L_2 = 21, L_3 = 49, L_4 = 105, L_5 = 217, L_6 = 441
- With a 512-bar window, level 6 has 512 - 441 = 71 valid coefficients
- With a 1024-bar window, level 6 has 583 valid coefficients

**Implication for feature engineering:** With a rolling window of W bars and LA(8) filter, the maximum useful decomposition level is:
```
J_max = floor(log_2(W / (L-1)))
```
For W=512, L=8: J_max = floor(log_2(512/7)) = floor(log_2(73.1)) = 6

## Paywall Status
Closed (Cambridge). Python library `pywt` implements all algorithms. Chapter 8 (MODWT) is the most relevant.

## Tags
wavelet, MODWT, DWT, time-series, statistical-inference, Percival, Walden, boundary-effects, confidence-intervals
