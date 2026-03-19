# Ramsey & Lampart (1998) — The Decomposition of Economic Relationships by Time Scale Using Wavelets

**Full Citation:** Ramsey, J.B. & Lampart, C. (1998). "The Decomposition of Economic Relationships by Time Scale Using Wavelets: Expenditure and Income." *Studies in Nonlinear Dynamics & Econometrics*, 3(1), 23–42. DOI: 10.2202/1558-3708.1039

**Scores:** Relevance=4, Rigor=4, Implementability=4, Total=12/15

## Key Findings
Ramsey and Lampart demonstrate that economic relationships that appear stable in aggregate can have fundamentally different characteristics at different time scales. Using DWT decomposition with Daubechies wavelets:
1. Marginal propensity to consume varies dramatically across scales — high-frequency relationship qualitatively different from low-frequency
2. Establishes rigorous framework for scale-by-scale regression analysis
3. Introduces "wavelet correlation" — computing standard correlations between wavelet coefficients at each scale, revealing hidden co-movement structures
4. Shows that a single predictive model conflates dynamics that should be modeled separately

## Key Insight for Crypto Research
At 15-min resolution, this motivates building SEPARATE predictive models for each wavelet scale:
- Scale 1-2 (noise/microstructure): model with order flow features
- Scale 3-4 (intraday momentum): model with trend/momentum features
- Scale 5-6 (daily trend): model with macro/sentiment features

Then combine scale predictions via a meta-model.

## Key Methods & Formulas

**Scale-by-scale regression:**
```
D_j^Y = beta_j * D_j^X + epsilon_j     for each wavelet scale j
```

**Wavelet correlation:**
```
rho_j = Corr(D_j^X, D_j^Y)
```
Reveals scale-dependent lead-lag relationships between two financial series.

**ANOVA-like decomposition** of total explained variance by scale contribution:
```
R^2_total = sum_j R^2_j * (Var(D_j^Y) / Var(Y))
```

**Boundary handling:**
Discard L_j = (2^j - 1)(L-1) + 1 coefficients at boundaries where L is filter length.

## Application to Feature Engineering
For each wavelet scale j at 15-min:
1. Compute D_j (detail at scale j) for target series (future return)
2. Compute D_j for predictor series (volume, OFI, cross-asset)
3. Train scale-specific model: predict sign(D_j^{return}_{t+1}) from features
4. Combine: final_signal = weighted_sum(scale_j_signal for j in 3..5)

## Paywall Status
Open (De Gruyter, often freely accessible via institutional access).

## Tags
wavelet, DWT, scale-regression, wavelet-correlation, Ramsey, Lampart, multi-model, feature-engineering
