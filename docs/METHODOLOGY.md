# Methodology

This document derives every number that appears in a verdict report. The companion
documents are [ASSUMPTIONS.md](ASSUMPTIONS.md) (tunable parameters and their sensitivity)
and [LIMITATIONS.md](LIMITATIONS.md) (what this analysis cannot establish).

## 1. The decomposition

All pricing is built on:

```
P(president) = P(nominee) × P(wins general | nominee)
```

The two legs are estimated separately because they are different problems with different
evidence bases, and because the market prices both legs directly (nominee contract;
presidency contract), letting us localize any mispricing to a leg.

## 2. Lane 1 — historical base rate (outside view)

**Data:** `data/reference/nomination_contests.csv` — every open (non-incumbent) major-party
nomination contest 1972–2024 (the post-McGovern–Fraser primary era; earlier contests were
decided by conventions and are a different process), with each candidacy coded for early
national standing and structural traits. Coding rules in
[DATA_SOURCES.md](DATA_SOURCES.md).

**Estimator:** Among candidacies with early poll rank ≤ 2 (Newsom's current standing:
rank 2 by scraped 2026 primary polling means, rank 2 by market price), count nomination
winners `k` of trials `n`, and take the posterior

```
P(nominee) ~ Beta(k + 1, n − k + 1)
```

with a uniform prior. Trump 2024 (prior nominee running quasi-incumbent) is excluded by
default and included in sensitivity. Current cell: **k = 12, n = 35** → posterior median
≈ 34.9%, 80% CI ≈ [25%, 45%].

This lane deliberately knows nothing about Newsom. It is the Kahneman outside view that
disciplines candidate-specific narratives, and it is the lane most favorable to the thesis.

## 3. Lane 2 — historical analogs (profile view)

Similarity-weighted outcomes over the same panel. Weight for historical candidacy *i*:

```
w_i = exp(−(rank_i − rank_N)² / 2σ²) × 0.55^(# mismatched flags)
```

with σ = 1.5 and flags {sitting governor, former governor, sitting VP, prior nominee,
prior run}. Newsom's profile: rank 2, sitting governor, no prior national run.

The weighted win rate and Kish effective sample size `(Σw)²/Σw²` map to a Beta posterior,
so sparse analog support yields wide intervals. Sitting governors with strong early
standing are genuinely bimodal history — George W. Bush 2000 converted; Scott Walker 2016
and Ron DeSantis 2024 collapsed — and this lane is where that evidence bites: median
≈ 20%, notably below the pure base-rate lane.

## 4. Lane 3 — market structure (the price as evidence)

A market price with $1B+ matched volume is itself powerful evidence and gets the largest
default ensemble weight. But long-horizon political markets exhibit **favorite-longshot
bias**: low-priced contracts resolve YES less often than their price implies (Page &
Clemen 2013, *Do Prediction Markets Produce Well-Calibrated Probability Forecasts?*;
Rothschild 2009 on de-biasing market forecasts). We map price → calibrated probability:

```
p_cal = σ(a + b·logit(p)),   a ~ N(0, 0.05),  b ~ N(1.15, 0.10)
```

`b > 1` stretches probabilities away from the center. At b = 1.15 a 15.65¢ contract
calibrates to ≈ 12.6%; parameters are literature-derived (not fitted here — see
LIMITATIONS #5) and sampled so their uncertainty propagates. **Direction check:** this
correction pushes *against* the undervaluation thesis, which is precisely why it must be
present; a model that omitted it would be quietly rigged toward BUY.

## 5. Lane 4 — fundamentals (the conditional leg)

`P(wins general | nominee)` from:

1. **Open-seat base rate.** In the 8 post-WWII open-seat elections
   (`data/reference/open_seat_generals.csv`) the non-White-House party won 7 — but the
   sample is small and selection-biased (open seats cluster after unpopular second
   terms), so the raw 87.5% is shrunk halfway to a coin flip → 68.8%.
2. **Candidate adjustment** for Newsom: N(−3pp, 8pp) — centered slightly negative for
   the national favorability deficit and the "California brand" attack surface, wide
   because rigorous evidence on home-state-brand effects is thin.
3. **A variance floor** (σ ≥ 7pp) so the lane cannot claim unearned precision.

Result: median ≈ 62.9%, 80% CI ≈ [40%, 83%].

A fifth input, the **market-implied conditional** (presidency price ÷ nominee price,
currently 51% for Newsom), enters the conditional leg with equal weight. Note the
cross-candidate table in each report: the market currently implies Newsom converts the
nomination at 51% versus AOC 66% and Ossoff 71% — a spread that is hard to justify with
fundamentals and is the project's main relative-value diagnostic.

## 6. Ensemble

Per Monte Carlo draw (n = 200,000, fixed seed):

1. Sample lane weights from Dirichlet(2, 2, 4) for the nomination leg (base rate, analog,
   market structure) and Dirichlet(3, 3) for the conditional leg.
2. Select ONE lane per leg by categorical draw and take that lane's sampled value —
   a **linear opinion pool** (mixture). Averaging lane draws instead would shrink the
   spread mechanically and manufacture false confidence; with a mixture, lane
   disagreement widens the posterior, as it should.
3. `P(president) = P(nominee) × P(general | nominee)` per draw.

The dependence assumption between legs is discussed in LIMITATIONS #4.

## 7. Expected value, carry, and the verdict gate

For a contract at price `q` resolving at date `T`:

```
NPV = E[fair] · (1 + r)^−T − q − c
```

with `r` = current 2-year Treasury yield (FRED DGS2, the carry benchmark for locked
capital) and `c` = 1¢ round-trip spread/slippage. The pre-registered gate:

- **BUY**: median fair ≥ 1.5 × q **and** 10th-percentile fair value clears q + carry + c.
- One of two → **SPECULATIVE VALUE**; neither → **FAIR**, or **OVERVALUED** if q exceeds
  the 90th-percentile fair value.

Kelly fraction `f* = (bp − (1−p))/b` with `b = (1−q)/q` is reported for sizing; half-Kelly
is recommended because `p` is a model estimate, not a known probability.

Exit scenarios (mark-to-market at announcement / early states / Super Tuesday) assume the
price converges a fraction κ ∈ {0.25, 0.5, 0.75} toward model fair value. These are
assumptions about **other traders' future beliefs**, not about Newsom, and are labelled
speculative wherever they appear.

## 8. What "backtesting" means here

The 2028 outcome cannot test this model (single event). What is tested against history:

- the base-rate cell counts (fully reproducible from the reference panel);
- the analog machinery (leave-one-cycle-out: apply the profile weighting as of each past
  cycle and compare weighted predictions to outcomes — planned, see ROADMAP in README);
- the calibration correction's direction and rough magnitude (literature-based).

The honest statement of scope: this project estimates a *disciplined, uncertainty-honest
fair value*, and asks whether the market price sits outside that fair value's credible
range — it does not, and cannot, "predict the 2028 election."
