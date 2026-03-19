# Ramsey (1999) — The Contribution of Wavelets to the Analysis of Economic and Financial Data

**Full Citation:** Ramsey, J.B. (1999). "The Contribution of Wavelets to the Analysis of Economic and Financial Data." *Philosophical Transactions of the Royal Society of London. Series A: Mathematical, Physical and Engineering Sciences*, 357(1760), 2593–2606. DOI: 10.1098/rsta.1999.0450

**Scores:** Relevance=4, Rigor=4, Implementability=3, Total=11/15

## Key Findings
This foundational paper introduces wavelet analysis as a tool for economic and financial time series, arguing that traditional Fourier-based spectral methods are inadequate for non-stationary financial data. Ramsey demonstrates that the Discrete Wavelet Transform (DWT) enables time-scale decomposition, revealing hidden structure at multiple horizons simultaneously. He illustrates applications including variance decomposition by scale, the detection of structural breaks, and the separation of signal from noise. The paper establishes that different economic forces operate at different time scales — a principle that underpins all subsequent wavelet applications in finance. Ramsey specifically highlights the Daubechies family of wavelets as particularly well-suited for financial data due to their compact support and asymmetry properties.

## Relevance to 15-min Crypto Prediction
Provides the theoretical foundation for multi-scale decomposition. The principle that different market participants (HFT, intraday traders, swing traders) operate at different scales maps directly to decomposing 15-min crypto bars into scales representing ~30min, ~1hr, ~2hr, ~4hr, ~8hr+ dynamics.

## Key Methods & Formulas

**DWT via Mallat's pyramid algorithm:** Recursive filtering with high-pass (detail) and low-pass (smooth) filters, downsampled by 2 at each level.

**Wavelet variance decomposition:**
```
Var(X) = sum_{j=1}^{J} Var(D_j) + Var(S_J)
```
where D_j is the detail at scale j and S_J is the smooth.

**Daubechies LA(8)** (least asymmetric, 8 taps) — recommended wavelet for financial data.

**Scale-to-period mapping:** Scale j corresponds to changes at periodicity 2^j to 2^{j+1} bars.

**For 15-min bars:**
- j=1: 15-30 min (microstructure)
- j=2: 30-60 min
- j=3: 1-2 hr
- j=4: 2-4 hr
- j=5: 4-8 hr (session effects)
- j=6: 8-16 hr (daily)

## Pitfalls Identified
- Traditional Fourier analysis assumes stationarity — invalid for financial data
- DWT requires dyadic sample sizes (N = 2^J); MODWT preferred for arbitrary N

## Paywall Status
Closed (Royal Society). Working knowledge sufficient from this summary.

## Tags
wavelet, DWT, multi-scale, financial-time-series, Ramsey, foundational
