# Glattfelder, Dupuis & Olsen (2011) — Patterns in High-Frequency FX Data: 12 Empirical Scaling Laws

**Full Citation:** Glattfelder, J.B., Dupuis, A., & Olsen, R.B. (2011). "Patterns in high-frequency FX data: Discovery of 12 empirical scaling laws." *Quantitative Finance*, 11(4), 599–614. DOI: 10.1080/14697688.2010.505943. ArXiv: 0809.1040

**Scores:** Relevance=5, Rigor=5, Implementability=4, Total=14/15

## Key Findings
Introduces the Directional Change (DC) framework — an alternative to fixed-interval sampling:
1. DC events defined as cumulative price moves exceeding a threshold delta
2. Discovers 12 empirical scaling laws relating DC frequency, overshoot length, and return magnitudes
3. Remarkable universality across multiple FX pairs and thresholds
4. Expected overshoot length equals expected DC length (coastline symmetry)
5. Number of DC events scales as power law of threshold: deviations from power=2 indicate fat tails

## Key Formulas

**Directional Change Event Definition:**
```
Upturn DC occurs at t_DC when:
(p(t_DC) - p(t_ext)) / p(t_ext) >= delta

Downturn DC occurs at t_DC when:
(p(t_ext) - p(t_DC)) / p(t_ext) >= delta
```
where p(t_ext) is the price at the last local extreme.

**Scaling Law 1 (Number of DC events):**
```
E[N_DC(delta)] proportional to delta^{-E1}
E1 ≈ 2 for random walk; empirical deviations signal fat tails/clustering
```

**Scaling Law 9 (Overshoot Symmetry):**
```
E[|omega_OS|] = E[|omega_DC|]
```
where omega denotes log-price move during respective regime.

## Application to 15-min Crypto as a Feature

**Directional Change features:**
```python
def compute_dc_features(price_series, delta=0.001):
    """
    price_series: close prices
    delta: threshold for directional change (0.1% default)
    Returns: DC rate, overshoot length, DC imbalance
    """
    dc_events = []
    overshoots = []
    direction = None
    extreme_price = price_series[0]

    for i, p in enumerate(price_series[1:], 1):
        if direction is None:
            if (p - extreme_price) / extreme_price >= delta:
                direction = 'up'; dc_events.append(('up', i))
            elif (extreme_price - p) / extreme_price >= delta:
                direction = 'down'; dc_events.append(('down', i))
        else:
            if direction == 'up' and (extreme_price - p) / extreme_price >= delta:
                direction = 'down'; dc_events.append(('down', i))
                extreme_price = p
            elif direction == 'down' and (p - extreme_price) / extreme_price >= delta:
                direction = 'up'; dc_events.append(('up', i))
                extreme_price = p

    # DC imbalance: ratio of up DC to down DC in recent window
    recent_dc = dc_events[-20:]
    up_count = sum(1 for d, _ in recent_dc if d == 'up')
    down_count = len(recent_dc) - up_count
    dc_imbalance = (up_count - down_count) / len(recent_dc) if recent_dc else 0

    return {'dc_rate': len(dc_events) / len(price_series),
            'dc_imbalance': dc_imbalance}
```

**DC features for prediction:**
1. `dc_imbalance` — ratio of up-DCs to down-DCs in last N events
2. `dc_frequency` — how many DC events per unit time (volatility proxy)
3. `dc_in_overshoot` — binary: is current bar in an overshoot period?
4. `dc_overshoot_magnitude` — size of current overshoot relative to typical

## Paywall Status
Partially open. ArXiv preprint: https://arxiv.org/abs/0809.1040

## Tags
directional-change, DC-events, scaling-laws, high-frequency, Glattfelder, Olsen, event-based-sampling, crypto-applicable
