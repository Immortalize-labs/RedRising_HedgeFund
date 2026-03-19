# Corsi (2009) — A Simple Approximate Long-Memory Model of Realized Volatility (HAR-RV)

**Full Citation:** Corsi, F. (2009). "A Simple Approximate Long-Memory Model of Realized Volatility." *Journal of Financial Econometrics*, 7(2), 174–196. DOI: 10.1093/jjfinec/nbp001

**Scores:** Relevance=5, Rigor=5, Implementability=5, Total=15/15 — BACKBONE MODEL

## Key Findings
Introduces the Heterogeneous Autoregressive model of Realized Volatility (HAR-RV), motivated by the Heterogeneous Market Hypothesis (Müller et al. 1997) — traders at different horizons create a cascade structure in volatility dynamics.
1. Despite simplicity (additive, non-nested cascade of AR components), HAR-RV captures long-memory properties of volatility remarkably well
2. Outperforms fractionally integrated models in out-of-sample forecasting (4,000+ citations)
3. Parsimonious specification: only 4 parameters (intercept + 3 horizon betas)
4. The workhorse model in realized volatility literature — foundation for HAR-RS (Patton-Sheppard), HAR-CJ (Andersen et al.), HAR-GARCH (Shephard-Sheppard)

## The HAR-RV Model

```
RV_{t+1} = beta_0 + beta_d * RV_t^(d) + beta_w * RV_t^(w) + beta_m * RV_t^(m) + eps_{t+1}
```

Where:
- RV_t^(d) = daily realized variance (sum of squared intraday returns over 1 day)
- RV_t^(w) = weekly RV = (1/5) * sum(RV_{t-4}...RV_t)
- RV_t^(m) = monthly RV = (1/22) * sum(RV_{t-21}...RV_t)

**Typical estimates for equities:**
```
beta_d ~ 0.37
beta_w ~ 0.34
beta_m ~ 0.28
```
(all significantly positive, sum < 1 for stationarity)

## Adaptation for 15-min Crypto (INTRADAY HAR)

Replace daily/weekly/monthly with:
```
RV_{t}^(1h)  = avg(RV of last 4 bars)     # 1-hour
RV_{t}^(4h)  = avg(RV of last 16 bars)    # 4-hour
RV_{t}^(24h) = avg(RV of last 96 bars)    # 24-hour
```

**HAR-RV for 15-min crypto:**
```
RV_{t+1} = beta_0 + beta_1h * RV_t^(1h) + beta_4h * RV_t^(4h) + beta_24h * RV_t^(24h) + eps
```

**Log-HAR-RV** (better normality, often preferred):
```
log(RV_{t+1}) = beta_0 + beta_1h * log(RV_t^(1h)) + beta_4h * log(RV_t^(4h)) + beta_24h * log(RV_t^(24h)) + eps
```

## Feature Engineering from HAR Framework
The HAR cascade structure provides a natural feature decomposition:
1. `rv_1h` — short-horizon realized variance
2. `rv_4h` — medium-horizon realized variance  
3. `rv_24h` — long-horizon realized variance
4. `rv_ratio_sh_lh = rv_1h / rv_24h` — vol regime indicator (>1 = vol spike, <1 = vol compression)
5. Combined with semivariance: separate each horizon into RS+ and RS- (→ HAR-RS)

## Python Implementation

```python
def compute_har_features(rv_series, bar_index):
    """
    rv_series: array of per-bar realized variance values
    bar_index: current bar index
    Returns: dict of HAR features
    """
    i = bar_index
    rv_1h  = np.mean(rv_series[max(0,i-3):i+1])       # last 4 bars
    rv_4h  = np.mean(rv_series[max(0,i-15):i+1])      # last 16 bars
    rv_24h = np.mean(rv_series[max(0,i-95):i+1])      # last 96 bars
    return {
        'rv_1h': rv_1h, 'rv_4h': rv_4h, 'rv_24h': rv_24h,
        'rv_ratio': rv_1h / max(rv_24h, 1e-10),
        'log_rv_1h': np.log(max(rv_1h, 1e-10)),
        'log_rv_4h': np.log(max(rv_4h, 1e-10)),
        'log_rv_24h': np.log(max(rv_24h, 1e-10))
    }
```

## Paywall Status
Closed (Oxford/JFEC). Working paper available on SSRN (University of St. Gallen).

## Tags
HAR-RV, realized-variance, long-memory, volatility-forecasting, Corsi, cascade, backbone-model, crypto-applicable
