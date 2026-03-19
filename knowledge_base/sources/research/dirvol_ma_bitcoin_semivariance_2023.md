# Ma et al. (2023) — Forecasting Bitcoin Volatility: Signed Realized Semivariances

**Full Citation:** Ma, F., Zhang, Y., Wahab, M.I.M., & Lai, X. (2023). "Forecasting the volatility of Bitcoin: The importance of jumps and signed realized semivariances." *European Journal of Finance*, 29(12), 1367–1385. DOI: 10.1080/1351847X.2022.2135737

**Scores:** Relevance=5, Rigor=4, Implementability=5, Total=14/15 — CRYPTO-SPECIFIC VALIDATION

## Key Findings
Applies Barndorff-Nielsen et al. (2010) semivariance decomposition to HIGH-FREQUENCY BITCOIN DATA:
1. **RS- (downside semivariance) is substantially more informative** than RS+ or total RV for forecasting future Bitcoin volatility
2. HAR-RS-J model significantly outperforms standard HAR-RV and HAR-RV-J benchmarks
3. **Directional asymmetry is MORE PRONOUNCED in cryptocurrency** than in equity or FX markets
4. Consistent with stronger leverage-type effects driven by RETAIL SENTIMENT in crypto
5. Confirmed via Model Confidence Set (MCS) procedure + volatility-timing portfolio exercise

## This is our best crypto-specific validation for directional volatility signals.

## Key Formulas

**HAR-RS-J model for Bitcoin:**
```
RV_{t+1} = beta_0
          + beta_1^+ * RS^+_t   + beta_1^- * RS^-_t
          + beta_2 * RV_t^{(w)} + beta_3 * RV_t^{(m)}
          + beta_4 * J_t
          + epsilon_{t+1}
```

**Signed realized semivariances (using 5-min returns):**
```
RS^+_t = sum_{j=1}^M r_{t,j}^2 * 1(r_{t,j} > 0)
RS^-_t = sum_{j=1}^M r_{t,j}^2 * 1(r_{t,j} < 0)
```

**Significant jump variation:**
```
J_t = max(RV_t - BV_t, 0) * 1(z_{J,t} > Phi^{-1}_{1-alpha})
```

## Key Finding for Our System
Directional asymmetry MORE PRONOUNCED in Bitcoin than equities:
- This validates that RS- features will be strong predictors for our 15-min crypto system
- The effect (RS- > RS+ in predictive power) is persistent across BTC market regimes
- HAR-RS-J outperforms all benchmarks in MCS at all horizons (1-day, 5-day, 22-day)

## Adaptation for 15-min Prediction (DIRECTION not VARIANCE)
Replace RV prediction with SIGN prediction:
```
P(r_{t+1} > 0) = sigmoid(
    alpha_0
    + alpha_1^+ * RS^+_t + alpha_1^- * RS^-_t
    + alpha_2 * SJV_t                            # signed jump variation
    + alpha_3 * SJV_t^{(1h)}                     # 1-hour SJV average
    + alpha_4 * J_t * sign(r_t)                  # signed significant jump
)
```

## Paywall Status
Closed (Taylor & Francis). Check SSRN for working paper version.

## Tags
Bitcoin, cryptocurrency, realized-semivariance, HAR-RS-J, directional-volatility, Ma, crypto-specific, validated
