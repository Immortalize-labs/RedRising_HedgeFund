# Literature Review: Wavelets & Directional Volatility for 15-min Crypto Prediction
# Immortalize Labs HF — Research Stream R1 + R2
# Compiled: 2026-03-19
# Author: Mustang (Research Director)
# Status: COMPLETE — 19 sources ingested, 61 KB chunks

---

## Summary Table: All Sources, Quality Scores

### R1 — Wavelet Decomposition

| # | Citation | Rel | Rig | Impl | Total | Status |
|---|----------|-----|-----|------|-------|--------|
| 1 | Ramsey (1999) Philosophical Trans Royal Society | 4 | 4 | 3 | **11** | Keep |
| 2 | Ramsey & Lampart (1998) Studies in Nonlinear Dynamics | 4 | 4 | 4 | **12** | Keep |
| 3 | Gençay, Selçuk & Whitcher (2002) book | 5 | 5 | 5 | **15** | PRIMARY |
| 4 | Percival & Walden (2000) book | 4 | 5 | 4 | **13** | Keep |
| 5 | In & Kim (2006) Journal of Business | 4 | 5 | 4 | **13** | Keep |
| 6 | Gençay, Selçuk & Whitcher (2005) JIMF | 5 | 5 | 4 | **14** | Keep |
| 7 | In & Kim (2013) book | 5 | 4 | 5 | **14** | Keep |
| 8 | Bouri et al. (2020) QREF | 5 | 4 | 4 | **13** | Keep |
| 9 | Rua & Nunes (2009) JEF | 5 | 4 | 4 | **13** | Keep |

All 9 wavelet sources scored >= 11/15. All kept.

### R2 — Directional Volatility

| # | Citation | Rel | Rig | Impl | Total | Status |
|---|----------|-----|-----|------|-------|--------|
| 1 | Barndorff-Nielsen, Kinnebrock & Shephard (2010) OUP | 5 | 5 | 5 | **15** | PRIMARY |
| 2 | Patton & Sheppard (2015) RES | 5 | 5 | 5 | **15** | PRIMARY |
| 3 | Barndorff-Nielsen & Shephard (2006) JFEC | 5 | 5 | 5 | **15** | PRIMARY |
| 4 | Bollerslev, Li & Todorov (2016) JFE | 4 | 5 | 4 | **13** | Keep |
| 5 | Corsi (2009) JFEC | 5 | 5 | 5 | **15** | BACKBONE |
| 6 | Glattfelder, Dupuis & Olsen (2011) QF | 5 | 5 | 4 | **14** | Keep |
| 7 | Andersen, Dobrev & Schaumburg (2012) JE | 4 | 5 | 4 | **13** | Keep |
| 8 | Ma et al. (2023) EJF — BITCOIN SPECIFIC | 5 | 4 | 5 | **14** | Keep |
| 9 | Christoffersen & Diebold (2006) MS | 5 | 5 | 4 | **14** | THEORY |

All 9 directional vol sources scored >= 13/15. All kept.

**Total: 18 sources kept (19 including implementation guide). 0 rejected.**

---

## R1 — WAVELETS: What the Literature Says

### What Works

**1. MODWT is the right transform for financial time series.**
Gençay et al. (2002) and Percival & Walden (2000) establish MODWT as definitively superior to DWT for production financial applications:
- Shift-invariant: adding one new 15-min bar does NOT shift historical coefficients
- Handles arbitrary sample sizes
- Asymptotically more efficient variance estimates
- Proper confidence intervals available (chi-squared distribution)

*Verdict: Use MODWT (SWT in pywt) with sym8 or db8 wavelet at J=6-7 levels.*

**2. Signal lives in the middle frequencies (D3-D5 for 15-min bars).**
Multiple papers (Ramsey 1999, In & Kim 2006, DeepSeek synthesis) confirm that for short-horizon return prediction:
- D1-D2 (15-60 min): dominated by microstructure noise, typically not predictive
- D3-D5 (1-8 hr): primary signal zone — momentum, news reactions, session effects
- D6-D7 (daily+): useful as regime filter only, not direct 15-min prediction signal

*Verdict: Build features from D3, D4, D5. Use D6-D7 as regime conditioning variable.*

**3. Scale-by-scale regression outperforms single-model approach.**
Ramsey & Lampart (1998) demonstrate that regressing at each scale separately — then combining — outperforms a single model that conflates dynamics across scales. In & Kim (2006) shows this for hedge ratios; the principle generalizes.

*Verdict: Build separate scale-specific signals, then combine via meta-model or weighted ensemble.*

**4. Wavelet variance/energy ratio is a volatility regime indicator.**
At each scale j, wavelet variance nu_j = mean(D_j^2) measures the power in that frequency band. When energy shifts from low scales (D3) to high scales (D6), the market is transitioning from intraday noise to trend-driven. This is a regime detection signal.

*Verdict: Include energy_ratio_j = Var(D_j) / Var(D_j=3..7 total) as a feature.*

**5. Cross-asset wavelet correlation detects regime shifts.**
Bouri et al. (2020) and Rua & Nunes (2009) establish wavelet coherence as the standard tool for detecting time-frequency regime shifts. High coherence between BTC and ETH at scale j=3-4 signals coupled trending; low coherence signals idiosyncratic moves.

*Verdict: Compute rolling MODWT correlation between BTC and each paired asset at D3, D4, D5. Use as regime conditioning feature.*

### What Does NOT Work

**1. Raw DWT applied to non-dyadic windows.**
DWT requires N = 2^J exactly. Real-time rolling windows don't satisfy this constraint → use MODWT only.

**2. Using all J levels as features without boundary correction.**
Percival & Walden (2000) show that L_j = (2^j - 1)(L-1) + 1 boundary-affected coefficients are corrupted. With LA(8) and a 512-bar window, level 6 has only 70 valid coefficients. Use minimum 1024-bar window and only use the LAST (most recent) coefficient at each level.

**3. CWT for production feature engineering.**
CWT is overcomplete (more coefficients than data points), computationally expensive, and produces redundant features. Wavelet coherence via CWT is useful for ANALYSIS but MODWT-based rolling correlation is the practical production substitute.

**4. Data leakage via non-causal filtering.**
The most critical pitfall: standard SWT/MODWT uses circular convolution which wraps future data into past coefficients. MUST use an online/causal implementation where features at bar t use only data up to t. Implementation: compute MODWT on a rolling window ending at t, extract only the last coefficient.

**5. Haar wavelets.**
Haar creates blocky artifacts and poor frequency localization. Daubechies family (sym8, db8) with 8+ taps is required for clean financial signal extraction.

### Pitfalls Summary (R1)
1. Boundary effects: use min 1024-bar window, discard L_j boundary coefficients
2. Data leakage: causal implementation only — rolling window ending at current bar
3. Overcomplete features: D3+D4+D5 = 3*3 = 9 features max before regularization
4. Dyadic constraint: MODWT only, not DWT
5. Wavelet choice: sym8/db8 only, not Haar

---

## R2 — DIRECTIONAL VOLATILITY: What the Literature Says

### What Works

**1. Realized semivariance decomposition (RS+/RS-) is the foundational tool.**
Barndorff-Nielsen et al. (2010) and the subsequent citation count (1000+) establish RS+/RS- as the gold standard for directional volatility measurement. The decomposition is:
- Trivial to compute: just separate squared returns by sign
- Theoretically grounded: converges to well-defined limit under semimartingale framework
- Predictive: signed jump variation (RS+ - RS-) has documented return predictability

*Verdict: RS+, RS-, SJV = FIRST features to implement.*

**2. HAR-RS model dominates all alternatives (Patton & Sheppard 2015).**
The key finding: RS- (downside semivariance) has GREATER predictive power than RS+ for future volatility and direction. This asymmetry:
- Holds across daily, weekly, monthly horizons
- Is statistically and economically significant
- Outperforms EGARCH, GJR-GARCH, and standard HAR-RV

For direction prediction, replace HAR-RS volatility regression with logistic regression: predict sign(r_{t+1}) from {RS+_t, RS-_t, SJV_t, RS+_4h, RS-_4h}.

*Verdict: RS- should receive higher model weight than RS+. Asymmetry coefficient expected.*

**3. Crypto shows STRONGER directional asymmetry than equities (Ma et al. 2023).**
This is the bitcoin-specific validation we needed. Ma et al. find that the HAR-RS-J model works even better for Bitcoin than for equities, attributable to:
- Stronger leverage-type effects
- Retail sentiment amplification
- Liquidation cascade dynamics creating larger signed jumps

*Verdict: The RS-/RS+ asymmetry is real and amplified in our asset class.*

**4. Jump detection (Barndorff-Nielsen & Shephard 2006) separates regimes.**
The BPV-based jump test distinguishes jump-driven bars from continuous-diffusion bars. When a significant jump is detected:
- Use the jump direction as a predictor (momentum in direction of jump)
- Reduce confidence in subsequent RS features (jump may distort next-bar expectations)
- Flag for reduced position sizing (risk policy alignment)

*Verdict: Compute jump_flag, jump_z, jump_magnitude for each 15-min bar.*

**5. Low volatility → stronger directional signal (Christoffersen & Diebold 2006).**
Theoretical result: sign predictability derives from variance dynamics. When realized volatility is LOW relative to recent baseline, the directional signal from RS+/RS- is MORE reliable.

*Verdict: Weight RS-direction signals by (1/normalized_vol) or use vol_regime as gating variable.*

**6. MedRV provides jump-robust semivariance for noisy crypto data (Andersen et al. 2012).**
At 1-min frequency, crypto has bid-ask bounce and exchange-specific noise. Use MedRV-based semivariance for the "clean" continuous component. Raw RS for the combined estimate.

*Verdict: Compute both raw RS and MedRV-based RS. Use difference as noise measure.*

**7. Directional Change framework adds orthogonal signal (Glattfelder et al. 2011).**
DC events (threshold-based directional changes) provide an event-time view of directional pressure that is orthogonal to calendar-time RS features. DC imbalance (ratio of up-DCs to down-DCs) measures persistent directional intent.

*Verdict: Explore DC imbalance as an additional feature in the second experiment wave.*

### What Does NOT Work

**1. EGARCH/GJR-GARCH as the primary directional signal.**
Patton & Sheppard (2015) show that parametric asymmetric GARCH models are outperformed by the simple, non-parametric HAR-RS model. The realized measure is better because it directly observes the signed price moves rather than inferring variance from a parametric model.

**2. Using only daily/weekly RS horizons without intraday adaptation.**
The HAR framework uses daily/weekly/monthly. For 15-min prediction, we must adapt: {1h, 4h, 24h} as the three HAR horizons. This adaptation has not been explicitly validated in the literature for crypto but follows directly from the framework's logic.

**3. Computing RS from OHLC data alone.**
If only OHLC is available, semivariance computed from {O-H, H-L, L-C} is a poor proxy. The proper computation requires intra-bar sub-period returns. We MUST use 1-minute kline data for proper RS computation.

**4. Ignoring microstructure noise at 1-minute frequency.**
Raw 1-minute crypto returns include bid-ask bounce. Bollerslev et al. (2016) show truncated semivariance is necessary above ~50 observations/bar. With only 15 sub-periods (1-min in 15-min bar), noise is moderate but non-negligible. Apply alpha=4 truncation threshold.

**5. Not winsorizing extreme crypto returns before squaring.**
A single outlier return squared can dominate the entire RS estimate. Winsorize at 99.9th percentile before squaring. This is especially critical for crypto data with exchange outages, API errors, and wash-trade contamination.

### Pitfalls Summary (R2)
1. Must have 1-min sub-data: RS from OHLC only is a poor substitute
2. Microstructure noise: use truncated RS (alpha=4) or MedRV-based version
3. Outlier returns: winsorize at 99.9th percentile before squaring
4. Non-stationarity: normalize RS features (z-score over 96-bar rolling window)
5. HAR horizon adaptation: must use {1h, 4h, 24h} not {daily, weekly, monthly}

---

## Updated Hypotheses Grounded in Evidence

### H1: RS- is the strongest single-feature directional predictor [HIGH CONFIDENCE]
**Evidence:** Patton & Sheppard (2015) show RS- > RS+ in predictive power. Ma et al. (2023) confirm this is amplified in Bitcoin. Barndorff-Nielsen et al. (2010) provide the theoretical foundation.
**Prediction:** In IC testing, RS-_4h should rank top-3 among all features. Expected IC: 0.03-0.07.
**Test:** Run IC validation with gate_a_ic_test.py on {RS+_1h, RS-_1h, RS+_4h, RS-_4h, SJV_t-1} features.

### H2: D3-D5 wavelet details carry predictive signal at 15-min horizon [MEDIUM-HIGH CONFIDENCE]
**Evidence:** Ramsey (1999), DeepSeek synthesis, and the hierarchical market hypothesis all support signal at 1-8 hr scales. Not yet directly validated on crypto 15-min data.
**Prediction:** wavelet_sign_D4 IC > 0.01 (gate minimum). Energy_ratio_D3/D5 will distinguish trending from noise regimes.
**Test:** Run IC validation on {wavelet_sign_D3, wavelet_sign_D4, wavelet_sign_D5, energy_ratio_D4} vs. next-bar return direction.

### H3: Jump detection improves signal quality by regime separation [MEDIUM CONFIDENCE]
**Evidence:** Barndorff-Nielsen & Shephard (2006) provide the jump test. Ma et al. (2023) include J_t in the best Bitcoin volatility model. Christoffersen & Diebold (2006) show that vol-regime conditioning improves directional signals.
**Prediction:** Conditioning on jump_flag=True improves IC of contemporaneous RS features by 20-40%.
**Test:** Compute IC of RS+/RS- separately for jump vs. no-jump bars.

### H4: Wavelet-based regime detection improves EXISTING model performance [MEDIUM CONFIDENCE]
**Evidence:** Rua & Nunes (2009), Bouri et al. (2020) confirm wavelet coherence = regime detector. If coherence between BTC and ETH at D3-D5 is high, it signals trending regime; low coherence signals mean-reversion.
**Prediction:** Adding wavelet_regime_coherence as a feature conditioning variable reduces model turnover in low-signal environments.
**Test:** Backtest with and without wavelet regime gate on existing 7-strategy ensemble.

### H5: HAR-RS multi-horizon features add orthogonal signal beyond current features [MEDIUM CONFIDENCE]
**Evidence:** HAR-RS outperforms HAR-RV in all tested settings. Our current feature set (OFI, returns, volume) does not include realized semivariance. The decomposition is orthogonal to order flow.
**Prediction:** Adding RS+/RS- features increases OOS cross-asset IC by > 0.005 in IC test.
**Test:** Run gate_a_ic_test.py on combined existing features + HAR-RS features.

### H6: Data leakage is a major risk for wavelet features [HIGH CONFIDENCE — WARNING]
**Evidence:** DeepSeek synthesis and Percival & Walden (2000) both flag this explicitly. Causal implementation is required.
**Risk:** If causal constraint is not enforced in feature pipeline, wavelet features will show spuriously high IS IC that collapses OOS.
**Mitigation:** Strict rolling-window feature extraction with look-ahead lock. Validate with time-shuffled permutation test (p-value gate <= 0.05 per risk_policy.yaml).

---

## Specific Methods to Test (Priority-Ordered)

### Phase 1: Directional Volatility Features (Start Here)
1. **RS- and RS+ at {1h, 4h, 24h}** — from 1-min sub-returns
2. **SJV_t-1** — signed jump variation of last bar
3. **RDP_t** — relative downside proportion = RS-/RV
4. **Imbalance_4h** — RS+/RS- ratio over last 4 hours
5. **Jump detection flag** — BPV-based z-test at alpha=0.001
6. **MedRV-based RS** — truncated version for microstructure robustness
7. **HAR-RS-J logistic model** — logistic regression with all above as inputs

**Gate:** Each feature must achieve IC >= 0.01, permutation p-value <= 0.05.

### Phase 2: Wavelet Features
1. **wavelet_sign_D3, D4, D5** — sign of detail coefficient at signal scales
2. **wavelet_energy_D3, D4, D5** — rolling energy at each scale
3. **wavelet_energy_ratio_D4** — energy(D4) / energy(D3..D7)
4. **wavelet_momentum_D4** — D4[t] - D4[t-1]
5. **wavelet_coherence_D4(BTC, ETH)** — cross-asset coherence at intraday scale
6. **wavelet_regime_flag** — high-frequency energy > low-frequency energy

**Gate:** Same IC and p-value gates.

### Phase 3: Combined Model
1. Stack Phase 1 + Phase 2 features
2. Train XGBoost with time-series CV (WFO, 30-day OOS minimum)
3. Gate: OOS Sharpe >= 0.5, DD <= 5%, decay ratio >= 0.3

---

## KB Ingestion Report

- **Sources added:** 19 (10 wavelet, 9 directional vol)
- **Chunks added:** 61
- **Total KB chunks:** 2005 (up from 1944)
- **New source type:** paper (61 new chunks added to paper count: 248 → 309)
- **Directory:** `/Users/jtrk/Projects/Claude_HF/knowledge_base/sources/research/`

---

## References

### R1 — Wavelets (by importance for our task)
1. Gençay, Selçuk & Whitcher (2002) — PRIMARY IMPLEMENTATION REFERENCE
2. Percival & Walden (2000) — Statistical foundations, boundary handling
3. In & Kim (2013) — Finance-specific applications, worked examples
4. Gençay, Selçuk & Whitcher (2005) — Multiscale beta, cross-asset
5. In & Kim (2006) — Scale-specific betas, template methodology
6. Bouri et al. (2020) — Crypto-specific wavelet coherence
7. Rua & Nunes (2009) — Regime detection via coherence
8. Ramsey & Lampart (1998) — Scale-by-scale regression framework
9. Ramsey (1999) — Theoretical foundations

### R2 — Directional Volatility (by importance)
1. Barndorff-Nielsen, Kinnebrock & Shephard (2010) — Foundational RS theory
2. Patton & Sheppard (2015) — HAR-RS model, RS- dominance
3. Barndorff-Nielsen & Shephard (2006) — Jump detection (BPV)
4. Corsi (2009) — HAR-RV backbone model
5. Ma et al. (2023) — BITCOIN-SPECIFIC validation
6. Christoffersen & Diebold (2006) — Theoretical justification for directional prediction
7. Glattfelder, Dupuis & Olsen (2011) — Directional Change framework
8. Bollerslev, Li & Todorov (2016) — Truncated/noise-robust semivariance
9. Andersen, Dobrev & Schaumburg (2012) — MedRV jump-robust estimator
