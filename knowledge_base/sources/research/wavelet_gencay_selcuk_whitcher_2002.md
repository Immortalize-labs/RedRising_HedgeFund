# Gençay, Selçuk & Whitcher (2002) — An Introduction to Wavelets and Other Filtering Methods in Finance and Economics

**Full Citation:** Gençay, R., Selçuk, F. & Whitcher, B. (2002). *An Introduction to Wavelets and Other Filtering Methods in Finance and Economics.* Academic Press (Elsevier). ISBN: 978-0-12-279670-2. DOI: 10.1016/C2009-0-22332-0

**Scores:** Relevance=5, Rigor=5, Implementability=5, Total=15/15 — PRIMARY REFERENCE

## Key Findings
This is the definitive textbook on wavelet methods for economics and finance. It covers DWT, MODWT, wavelet packet transforms, and continuous wavelet transforms with rigorous mathematical treatment alongside financial applications. Key contributions include:
1. Establishing MODWT as superior to DWT for financial applications due to its shift-invariance and ability to handle arbitrary sample sizes
2. Demonstrating wavelet-based multi-scale beta estimation for CAPM
3. Introducing wavelet variance and covariance estimators with confidence intervals
4. Systematic treatment of the choice between Haar, Daubechies, and LA wavelets for different financial data characteristics

The book provides extensive empirical examples with foreign exchange and equity data.

## Relevance to 15-min Crypto Prediction
PRIMARY REFERENCE for implementation. The MODWT methodology is directly applicable to 15-min crypto bars. The shift-invariance of MODWT is critical for real-time prediction where we need the most recent decomposition to not change with the addition of new data points.

## Key Methods & Formulas

**MODWT (Maximal Overlap DWT):** Non-decimated transform using rescaled filters:
```
h_tilde_j = h_j / 2^{j/2}
g_tilde_j = g_j / 2^{j/2}

W_tilde_{j,t} = sum_{l=0}^{L_j-1} h_tilde_{j,l} * X_{t-l mod N}   (wavelet/detail coefficients)
V_tilde_{j,t} = sum_{l=0}^{L_j-1} g_tilde_{j,l} * X_{t-l mod N}   (scaling/smooth coefficients)
```

**Wavelet variance:**
```
nu_X^2(tau_j) = (1/N_j) * sum_{t=L_j-1}^{N-1} W_tilde_{j,t}^2
```

**Wavelet covariance/correlation** between two series at each scale.

**Multi-Resolution Analysis (MRA):**
```
X_t = sum_{j=1}^{J} D_tilde_{j,t} + S_tilde_{J,t}
```
where details and smooth are reconstructed in the time domain (perfect reconstruction guaranteed).

**Optimal J selection:**
```
J <= floor(log_2(N))
Practical: J = floor(log_2(N/(L-1) + 1))
```

**LA(8) filter** — recommended for financial data (least asymmetric, 8 taps, Daubechies family).

## Advantages of MODWT over DWT
- Shift-invariant: adding one new observation does not shift all coefficients
- Handles arbitrary N (not just powers of 2)
- Provides N coefficients per level (not N/2^j)
- Asymptotically more efficient wavelet variance estimates
- Better boundary handling with periodic extension

## Pitfalls Warned
- Circular boundary conditions at beginning/end: discard L_j = (2^j - 1)(L-1)+1 coefficients
- Scale aliasing if J chosen too large for sample size

## Paywall Status
Closed (book). Key algorithms available in R package `waveslim`. Python: `pywt` library.

## Implementation Notes
Python: `import pywt; coeffs = pywt.swt(x, 'sym8', level=7)`  (SWT = MODWT equivalent)
R: `waveslim::modwt(x, wf="la8", n.levels=7)`

## Tags
wavelet, MODWT, DWT, multi-scale, financial-econometrics, Gencay, Selcuk, Whitcher, primary-reference, crypto-applicable
