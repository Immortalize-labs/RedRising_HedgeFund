# Bouri et al. (2020) — Bitcoin, Gold, and Commodities as Safe Havens: Wavelet Analysis

**Full Citation:** Bouri, E., Shahzad, S.J.H., Roubaud, D., Kristoufek, L., & Lucey, B. (2020). "Bitcoin, gold, and commodities as safe havens for stocks: New insight through wavelet analysis." *Quarterly Review of Economics and Finance*, 77, 156–164. DOI: 10.1016/j.qref.2020.03.004

**Scores:** Relevance=5, Rigor=4, Implementability=4, Total=13/15

## Key Findings
Applies continuous wavelet transform (CWT) coherence analysis to examine time-frequency dynamics of Bitcoin vs. gold vs. equities:
1. Bitcoin exhibits LOW wavelet coherence with equity markets at most time-frequency combinations
2. Coherence spikes during specific crisis periods, particularly at medium-to-long frequencies (32-128 day scales)
3. Bitcoin's diversification benefit is REGIME-DEPENDENT and FREQUENCY-DEPENDENT
4. When coherence occurs, Bitcoin often LEADS equities at short scales but LAGS at longer scales

## Key Formulas

**Continuous Wavelet Transform:**
```
W_x(u, s) = integral x(t) * (1/sqrt(s)) * psi_conj((t-u)/s) dt
```
where psi is the mother wavelet, u is time position, s is scale.

**Wavelet Coherence:**
```
R_xy^2(u,s) = |S(s^{-1} W_xy(u,s))|^2
               / (S(s^{-1}|W_x(u,s)|^2) * S(s^{-1}|W_y(u,s)|^2))
```
where S(.) is a smoothing operator in both time and scale.

**Phase Difference:**
```
phi_xy(u,s) = arctan(Im{S(s^{-1}W_xy)} / Re{S(s^{-1}W_xy)})
```
Phase arrows: right = in-phase, left = anti-phase, up = x leads y, down = y leads x.

## Application to 15-min Crypto
Use CWT coherence as a REGIME FILTER:
1. Compute wavelet coherence between BTC and ETH at different scales
2. High coherence at scale j=3-4 (1-2 hr): both assets co-moving → reduce size (crowded trade)
3. Low coherence: idiosyncratic moves → increase confidence in individual asset signals
4. Phase difference: if BTC leads ETH at j=3, use BTC_D3 as leading indicator for ETH

**Python:** `import pycwt` for CWT coherence analysis.
**Note:** CWT is computationally heavy for production. Better to use MODWT-based correlation as proxy.

## Paywall Status
Closed (Elsevier). Working paper available on ResearchGate.

## Tags
wavelet-coherence, CWT, cryptocurrency, Bitcoin, cross-asset, regime-detection, lead-lag, Bouri, Kristoufek
