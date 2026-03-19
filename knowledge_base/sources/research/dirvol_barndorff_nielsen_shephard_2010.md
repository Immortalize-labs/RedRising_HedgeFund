# Barndorff-Nielsen, Kinnebrock & Shephard (2010) — Measuring Downside Risk: Realised Semivariance

**Full Citation:** Barndorff-Nielsen, O.E., Kinnebrock, S., & Shephard, N. (2010). "Measuring Downside Risk — Realised Semivariance." In T. Bollerslev, J. Russell, & M. Watson (Eds.), *Volatility and Time Series Econometrics: Essays in Honor of Robert Engle*. Oxford University Press. DOI: 10.1093/acprof:oso/9780199549498.003.0007. Earlier working paper: SSRN 1151141 (2008).

**Scores:** Relevance=5, Rigor=5, Implementability=5, Total=15/15 — FOUNDATIONAL REFERENCE

## Key Findings
This foundational paper introduces the concept of realized semivariance (RS) by decomposing realized variance into upside (RS+) and downside (RS-) components.
1. As sampling frequency increases, RS converges to a quantity capturing both continuous (diffusive) semivariance and a signed jump component
2. RS- captures negative jumps; RS+ captures positive jumps — enables disentangling directional jump risk from continuous volatility
3. RS+ − RS- (signed jump variation) provides a consistent estimator of the net directional jump component with significant predictive power for future returns and volatility
4. Complete asymptotic theory under the semimartingale framework, including feasible central limit theorems for inference

## Key Definitions & Formulas

**Realized Semivariances:**
```
RS^-_t = sum_{j=1}^{M} r_{t,j}^2 * 1(r_{t,j} < 0)    (downside / "bad" volatility)
RS^+_t = sum_{j=1}^{M} r_{t,j}^2 * 1(r_{t,j} >= 0)   (upside / "good" volatility)
```
where r_{t,j} = log return of j-th intra-period observation within bar t, M = number of sub-periods.

**Realized Variance:**
```
RV_t = RS^+_t + RS^-_t
```

**Signed Jump Variation (SJV):**
```
SJV_t = RS^+_t - RS^-_t = Delta_J_t
```

**Relative Downside Proportion:**
```
RDP_t = RS^-_t / RV_t    in [0, 1]
```
RDP > 0.5 means downside dominated; < 0.5 means upside dominated.

## Application for 15-min Crypto Bars
Given 1-minute sub-returns within each 15-min bar (M=15):
```python
def compute_semivariance(sub_returns):
    """sub_returns: array of M log returns within a 15-min bar"""
    sq = sub_returns ** 2
    rs_plus  = sq[sub_returns >= 0].sum()   # upside semivariance
    rs_minus = sq[sub_returns < 0].sum()    # downside semivariance
    rv = rs_plus + rs_minus
    sjv = rs_plus - rs_minus
    rdp = rs_minus / rv if rv > 0 else 0.5
    return rs_plus, rs_minus, rv, sjv, rdp
```

## Predictive Power
Literature shows SJV has significant directional predictability:
- SJV_t > 0 (upside dominated) → positive next-bar return
- SJV_t < 0 (downside dominated) → negative next-bar return
- Effect decays over 1-4 hours in equity markets; potentially stronger in crypto

## Paywall Status
Book chapter closed (Oxford). Working paper freely available: https://www.ssrn.com/abstract=1151141

## Tags
semivariance, realized-variance, signed-jump-variation, Barndorff-Nielsen, Shephard, downside-risk, foundational
