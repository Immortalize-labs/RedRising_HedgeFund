# Wavelet & Directional Volatility Implementation Guide for 15-min Crypto
# Source: DeepSeek Reasoner synthesis + primary literature
# Date: 2026-03-19

## PART 1: WAVELETS — Implementation Decisions

### Transform Choice: MODWT (Maximal Overlap DWT)
**Why MODWT over DWT:**
- Translation-invariant: adding one new bar does NOT shift all existing coefficients
- Handles arbitrary sample sizes (not just powers of 2)
- Provides N coefficients per level (not N/2^j)
- Asymptotically more efficient variance estimates (Percival & Walden 2000)

**Why NOT CWT:** Overcomplete, computationally heavy, redundant for production feature pipeline.

### Wavelet Family: Symmlet-8 (sym8) or Daubechies-8 (db8)
- Need compact support (finite length) — good time localization
- Need near-symmetry — better localization of price moves than asymmetric Daubechies-4
- Haar is too simplistic — creates blocky artifacts in financial data
- LA(8) = Least Asymmetric 8 = near-identical to sym8 in practice

**Python command:**
```python
import pywt
# MODWT equivalent (Stationary Wavelet Transform in pywt):
coeffs = pywt.swt(x, 'sym8', level=7)
# coeffs[i] = (cA_i, cD_i) at level i+1
# cD_i = detail/wavelet coefficients at level i+1
# cA_i = approximation/smooth coefficients at level i+1
```

### Decomposition Levels for 15-min Bars (J=7)
```
Level 1 (D1): periodicity 2^1 * 15 = 30 min   (microstructure/noise)
Level 2 (D2): periodicity 2^2 * 15 = 60 min   (short-term)
Level 3 (D3): periodicity 2^3 * 15 = 2 hr     (*** SIGNAL ZONE ***)
Level 4 (D4): periodicity 2^4 * 15 = 4 hr     (*** SIGNAL ZONE ***)
Level 5 (D5): periodicity 2^5 * 15 = 8 hr     (*** SIGNAL ZONE ***)
Level 6 (D6): periodicity 2^6 * 15 = 16 hr    (daily structure)
Level 7 (D7): periodicity 2^7 * 15 = 32 hr    (trend)
S7: trend > 32 hr
```

**Most predictive bands for 15-min-ahead returns: D3-D5** (30 min to 8 hr scales)
- D1-D2: dominated by microstructure noise — typically NOT predictive
- D3-D5: where short-term momentum, news reactions, and regime signals live
- D6-D7: too slow for 15-min prediction, useful as regime filter only

### Lookback Window
- Minimum: 512 bars (~5.3 days of 15-min bars)
- Preferred: 1024 bars (~10.7 days)
- Rationale: need stable coefficients at level 5 (D5 requires ~480 non-boundary bars from 512-bar window)

### Boundary Effects — CRITICAL
For LA(8) filter (L=8), equivalent filter width at level j:
```
L_j = (2^j - 1) * (8 - 1) + 1
L_1 = 7 + 1 = 8
L_2 = 21 + 1 = 22
L_3 = 49 + 1 = 50
L_4 = 105 + 1 = 106
L_5 = 217 + 1 = 218
L_6 = 441 + 1 = 442
L_7 = 889 + 1 = 890
```
With 1024-bar window: level 6 has 1024-442 = 582 valid coefficients. Level 7 has 134.
With 512-bar window: level 5 has 512-218 = 294 valid. Level 6 has only 70.

**Rule:** Only use the MOST RECENT coefficient at each level (t=-1), which is valid as long as the window exceeds L_j.

### Data Leakage Prevention — CRITICAL
Wavelet filters are two-sided by default. MUST use causal implementation:

```python
def causal_wavelet_features(price_series, level=5, wavelet='sym8'):
    """
    Causal wavelet features for time t using data strictly up to t.
    Uses 'periodization' boundary (circular wrap) — ONLY valid when
    we take the last coefficient, not future ones.

    CORRECT approach: use the À-trous (SWT) with only past data.
    Never use future returns in the filter window.
    """
    # Ensure we're only using past bars
    x = np.log(price_series).diff().dropna().values  # returns
    x = x[-1024:]  # use last 1024 bars, all in the past

    coeffs = pywt.swt(x, wavelet, level=level)

    features = {}
    for j in range(1, level+1):
        _, cD = coeffs[level-j]  # detail at level j
        # ONLY use the last value (current time) — no lookahead
        features[f'wavelet_detail_{j}'] = cD[-1]
        features[f'wavelet_energy_{j}'] = np.mean(cD[-32:]**2)  # recent energy
        features[f'wavelet_sign_{j}'] = np.sign(cD[-1])
        features[f'wavelet_momentum_{j}'] = cD[-1] - cD[-2]  # direction of change

    return features
```

### Feature List (Priority Order)
For each level j in {3, 4, 5}:
1. `wavelet_sign_j` — sign of current detail coefficient (direction)
2. `wavelet_energy_j` — recent energy = mean(D_j^2 over last 32 bars) (volatility proxy)
3. `wavelet_energy_ratio_j` = wavelet_energy_j / sum(wavelet_energy_all_j) (relative power)
4. `wavelet_momentum_j` = D_j[t] - D_j[t-1] (rate of change)
5. Cross-asset: `wavelet_correlation_j(BTC, ETH)` over recent 64 bars

Regime features from low-frequency levels (D6, D7):
6. `wavelet_trend_direction` = sign(S_7[t])  (overall regime)
7. `wavelet_regime_vol` = energy(D6) / energy(D3) (ratio of slow to fast vol)

---

## PART 2: DIRECTIONAL VOLATILITY — Implementation Decisions

### Data Requirements
- Need 1-minute sub-bar returns within each 15-minute bar
- If only 15-min OHLC available: use (H-O, O-C, C-L, L-C) as 4 pseudo-returns
- Best case: 1-min klines → 15 sub-returns per 15-min bar

### Core Feature Set

**Step 1: Per-bar semivariance (from 1-min sub-returns)**
```python
def bar_semivariance(sub_returns, alpha_truncate=None):
    """
    sub_returns: array of M log returns within current 15-min bar
    alpha_truncate: if set, use truncated version (Bollerslev et al. 2016)
    """
    sq = sub_returns ** 2

    if alpha_truncate is not None:
        # Local vol via BPV
        mu1 = np.sqrt(2/np.pi)
        bpv_local = mu1**(-2) * np.abs(sub_returns[:-1]) * np.abs(sub_returns[1:])
        V_local = np.concatenate([[bpv_local[0]], bpv_local])
        threshold = alpha_truncate * V_local / len(sub_returns)
        mask = sq <= threshold
        sq = sq * mask  # truncate outliers

    rs_plus  = np.sum(sq[sub_returns >= 0])
    rs_minus = np.sum(sq[sub_returns < 0])
    rv = rs_plus + rs_minus

    sjv = rs_plus - rs_minus                           # signed jump variation
    rdp = rs_minus / rv if rv > 1e-12 else 0.5        # relative downside proportion
    imbalance = rs_plus / rs_minus if rs_minus > 1e-12 else np.nan

    return {
        'rs_plus': rs_plus, 'rs_minus': rs_minus, 'rv': rv,
        'sjv': sjv, 'rdp': rdp, 'imbalance': imbalance
    }
```

**Step 2: Jump detection (Barndorff-Nielsen & Shephard 2006)**
```python
def jump_test(sub_returns, alpha=0.001):
    """Returns jump_flag (bool), jump_z, jump_magnitude"""
    M = len(sub_returns)
    mu1 = np.sqrt(2/np.pi)
    RV = np.sum(sub_returns**2)
    BPV = mu1**(-2) * np.sum(np.abs(sub_returns[:-1]) * np.abs(sub_returns[1:]))
    BPV = max(BPV, 1e-12)

    mu43 = 2**(2/3) * gamma(7/6) / gamma(1/2)  # ~0.8309
    TQ = M * mu43**(-3) * np.sum(
        np.abs(sub_returns[:-2])**(4/3) *
        np.abs(sub_returns[1:-1])**(4/3) *
        np.abs(sub_returns[2:])**(4/3)
    )

    rel_jump = (RV - BPV) / RV
    se = np.sqrt((mu1**(-4) + 2*mu1**(-2) - 5) / M * max(1, TQ / BPV**2))
    z = rel_jump / se if se > 0 else 0.0
    threshold = norm.ppf(1 - alpha)

    return z > threshold, z, max(RV - BPV, 0)
```

**Step 3: HAR-RS feature aggregation (Patton & Sheppard 2015)**
```python
def har_rs_features(rs_plus_arr, rs_minus_arr, t):
    """Multi-horizon semivariance features for prediction"""
    horizons = {'1h': 4, '4h': 16, '24h': 96}
    features = {}
    for name, bars in horizons.items():
        start = max(0, t - bars + 1)
        rsp = np.mean(rs_plus_arr[start:t+1])
        rsm = np.mean(rs_minus_arr[start:t+1])
        features[f'rs_plus_{name}'] = rsp
        features[f'rs_minus_{name}'] = rsm
        features[f'sjv_{name}'] = rsp - rsm
        features[f'imbalance_{name}'] = rsp / rsm if rsm > 1e-12 else np.nan
    return features
```

### Feature Priority Order
1. `sjv_t-1` — signed jump variation of last bar (strongest short-term predictor)
2. `rdp_t-1` — relative downside proportion (directional imbalance)
3. `imbalance_1h` — RS+/RS- ratio over last hour
4. `imbalance_4h` — RS+/RS- ratio over last 4 hours
5. `sjv_1h` / `sjv_4h` — signed jump at medium horizons
6. `jump_flag_t-1` — was there a significant jump last bar?
7. `rs_minus_1h` / `rs_plus_1h` — separate downside/upside persistence
8. `continuous_vol = BPV_t-1` — jump-robust volatility estimate

### Predictive Mechanism (Bollerslev, Patton & Quaedvlieg 2020)
- RS+/RS- > 1 → upside volatility dominates → predicts positive next-bar return
- RS+/RS- < 1 → downside volatility dominates → predicts negative next-bar return
- Effect is persistent for 1-4 bars (15 min to 1 hr) in equity markets
- In crypto: likely stronger (directional whale activity, liquidation cascades)
- Autocorrelation of SJV is negative at lag-1 (mean-reversion component)

### Pitfalls
1. **Microstructure noise at 1-min** → use truncated semivariance (alpha=4)
2. **Extreme crypto jumps** → winsorize at 99.9th percentile before squaring
3. **Non-stationarity** → use rolling feature normalization (z-score over 96-bar window)
4. **Data availability** → if no 1-min sub-data, degrade to OHLC-based semivariance

---

## Implementation Order (Priority)
1. RS features (trivial to compute, strong signal)
2. HAR-RS multi-horizon aggregation
3. Jump detection (BPV test)
4. MODWT features at D3-D5
5. Cross-asset wavelet correlation
6. Combined wavelet + semivariance model

## Tags
implementation-guide, wavelet, MODWT, semivariance, HAR-RS, directional-volatility, crypto-15min, feature-engineering
