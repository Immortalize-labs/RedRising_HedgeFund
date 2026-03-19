# Patton & Sheppard (2015) — Good Volatility, Bad Volatility: Signed Jumps and the Persistence of Volatility

**Full Citation:** Patton, A.J. & Sheppard, K. (2015). "Good Volatility, Bad Volatility: Signed Jumps and the Persistence of Volatility." *Review of Economics and Statistics*, 97(3), 683–697. DOI: 10.1162/REST_a_00503

**Scores:** Relevance=5, Rigor=5, Implementability=5, Total=15/15 — KEY REFERENCE

## Key Findings
Extends the HAR-RV model (Corsi 2009) by incorporating the realized semivariance decomposition:
1. Negative semivariance (RS-) has SIGNIFICANTLY GREATER predictive power for future volatility than positive semivariance (RS+)
2. This asymmetry is statistically and economically significant across all horizons (daily, weekly, monthly)
3. Signed jump variation provides additional predictive power beyond semivariance levels
4. HAR-RS model outperforms both standard HAR-RV and asymmetric GARCH alternatives in out-of-sample forecasting

## The HAR-RS Model
The Heterogeneous Autoregressive Realized Semivariance model:

```
RV_{t+1} = beta_0
          + beta_1^- * RS^-_t   + beta_1^+ * RS^+_t        (daily)
          + beta_2^- * RS^-_{t,w} + beta_2^+ * RS^+_{t,w}  (weekly average)
          + beta_3^- * RS^-_{t,m} + beta_3^+ * RS^+_{t,m}  (monthly average)
          + epsilon_{t+1}
```

**Typical estimated coefficients:** beta_1^- > beta_1^+ (downside more persistent)

## Adaptation for 15-min Crypto Prediction
Replace daily/weekly/monthly with intraday horizons:

```
RS_1h_t  = avg(RS^{-,+} over last 4 bars)    # 1-hour
RS_4h_t  = avg(RS^{-,+} over last 16 bars)   # 4-hour
RS_24h_t = avg(RS^{-,+} over last 96 bars)   # 24-hour
```

**For DIRECTION prediction** (sign of next return), adapt to logistic regression:
```
P(r_{t+1} > 0) = sigma(alpha_0
                       + alpha_1 * SJV_t
                       + alpha_2 * SJV_{t,1h}
                       + alpha_3 * SJV_{t,4h}
                       + alpha_4 * RS^-_t / RV_t)
```

## Key Findings Specific to Our Task
- **RS- is the dominant predictor**: downside variance is more informative than upside
- **Short-term SJV**: signed jump variation at t-1 has strong predictive power at t+1
- **Asymmetry is not captured by GARCH**: EGARCH/GJR-GARCH miss the jump-direction signal

## Out-of-Sample Validation
- Loss functions: QLIKE, MSE, MAE
- Model Confidence Set (MCS) procedures applied
- HAR-RS dominates at all horizons tested
- Effect most pronounced at 1-day horizon; likely amplified at intraday in crypto

## Paywall Status
Closed (MIT Press / RES). Working paper available on Kevin Sheppard's Oxford website.

## Tags
semivariance, HAR-RS, signed-jump-variation, Patton, Sheppard, volatility-forecasting, asymmetric-volatility, crypto-applicable
