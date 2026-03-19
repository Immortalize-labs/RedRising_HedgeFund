# In & Kim (2006) — The Hedge Ratio and the Empirical Relationship Between the Stock and Futures Markets

**Full Citation:** In, F. & Kim, S. (2006). "The Hedge Ratio and the Empirical Relationship Between the Stock and Futures Markets: A New Approach Using Wavelet Analysis." *Journal of Business*, 79(2), 799–820. DOI: 10.1086/499141

**Scores:** Relevance=4, Rigor=5, Implementability=4, Total=13/15

## Key Findings
In and Kim apply MODWT multi-resolution analysis to estimate optimal hedge ratios between stock indices and futures contracts at different time scales. They demonstrate:
1. Hedge ratio is not constant across scales — short-horizon hedgers face fundamentally different optimal ratios than long-horizon hedgers
2. Hedging effectiveness improves monotonically with scale (lower frequencies): short-term microstructure noise degrades hedging at high frequencies
3. The LA(8) wavelet and MODWT provide a template for scale-dependent relationship estimation between any pair of financial time series
4. Scale-specific betas reveal the true nature of lead-lag relationships between markets

## Relevance to 15-min Crypto Prediction
Directly applicable to modeling scale-dependent relationships between crypto pairs (BTC-ETH), between spot and perpetual futures, or between crypto and macro factors. At 15-min resolution, this tells us which cross-asset signals are informative at which scales.

## Key Methods & Formulas

**Scale-to-period mapping for 15-min bars:**
```
j=1: 15-30 min (microstructure/noise)
j=2: 30-60 min (short-term momentum)
j=3: 1-2 hours
j=4: 2-4 hours (intraday patterns)
j=5: 4-8 hours (session effects)
j=6: 8-16 hours (~daily)
```

**Scale-dependent beta estimation:**
```
beta_j = Cov(D_tilde_j^spot, D_tilde_j^futures) / Var(D_tilde_j^futures)
```

**Hedging effectiveness at scale j:**
```
HE_j = 1 - Var(D_tilde_j^hedged) / Var(D_tilde_j^unhedged)
```

**MODWT-MRA reconstruction** ensuring perfect reconstruction:
```
X_t = sum_j D_tilde_{j,t} + S_tilde_{J,t}
```

## Application to Feature Engineering
For cross-asset crypto prediction at 15-min:
1. Compute MODWT of BTC, ETH, SOL, etc. at J=6 levels
2. Compute wavelet correlation between assets at each scale j
3. Build feature: wavelet_corr_j(BTC, ETH) — scale-specific correlation
4. Build feature: wavelet_lead_lag_j — cross-correlation at +/- 1 lag at scale j
5. Scale-specific momentum: sign(D_tilde_j_{t-1}) — direction of recent wavelet detail

## Pitfalls
- Scale-specific estimates need sufficient non-boundary coefficients — enforce minimum window sizes
- Bootstrap confidence intervals needed for scale-specific betas (asymptotic theory breaks at high scales with short history)

## Paywall Status
Closed (University of Chicago Press / JSTOR).

## Tags
wavelet, MODWT, hedge-ratio, cross-asset, scale-dependent-beta, In-Kim, crypto-applicable, lead-lag
