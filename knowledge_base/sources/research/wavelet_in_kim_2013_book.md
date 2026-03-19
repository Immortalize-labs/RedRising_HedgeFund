# In & Kim (2013) — An Introduction to Wavelet Theory in Finance

**Full Citation:** In, F. & Kim, S. (2013). *An Introduction to Wavelet Theory in Finance: A Wavelet Multiscale Approach*. Singapore: World Scientific Publishing. ISBN: 978-981-4397-83-5.

**Scores:** Relevance=5, Rigor=4, Implementability=5, Total=14/15

## Key Findings
Most comprehensive textbook dedicated specifically to wavelet applications in finance — both mathematical reference and practical guide:
1. Covers DWT, MODWT, continuous wavelet transform, wavelet coherence, and wavelet-based regression
2. Applies to asset pricing, portfolio optimization, risk measurement, and cointegration testing
3. Unified treatment of multi-horizon analysis: shows how wavelet MRA can decompose virtually any financial relationship
4. Detailed worked examples with equity, bond, and FX data
5. Covers wavelet-based ANOVA and hypothesis testing for comparing financial relationships across scales

## Key Formulas

**Wavelet-based hedge ratio at scale j:**
```
h_j* = gamma_tilde_{XY}(tau_j) / gamma_tilde_X^2(tau_j)
```

**Wavelet Sharpe ratio decomposition:**
```
SR_j = E[d_tilde_{j,t}] / sqrt(nu_hat^2(tau_j))
```

**MODWT-based multi-scale variance decomposition:**
```
Var(X) ≈ sum_{j=1}^{J} nu_X^2(tau_j) + nu_{V_J}^2
```
where nu_{V_J}^2 captures residual long-run variance.

## Key Takeaways for Our System
- The book provides explicit worked examples for building scale-specific signals
- Wavelet Sharpe ratio by scale: if high-frequency scales have low SR_j → don't trade at those scales
- Multi-horizon optimization framework: combine scale-j signals with scale-j-specific position sizing

## Paywall Status
Closed (book, ~$80-110). Select chapters on Google Books. No free preprint.

## Tags
wavelet, finance, MODWT, textbook, In-Kim, primary-reference, hedge-ratio, Sharpe-ratio, multi-scale
