# Assumptions and sensitivity

Every tunable parameter lives in `src/newsom2028/config.py`. This document lists each,
the reasoning, and — where it matters — the measured effect of moving it. Sensitivity
numbers below were produced with the 2026-08-18 snapshot (nominee 15.65¢, presidency
8.05¢) and are refreshed when materially stale.

## Headline sensitivity result

**The FAIR verdict is robust across every variant tested.** The single most
thesis-favorable configuration (equal lane weights, i.e. distrusting the market price as
much as the small-sample historical lanes) moves the nomination fair value to 20.1¢ —
1.28× price, still below the 1.5× BUY gate — and the presidency to 11.1¢ (1.38×).
Under the default weights the medians are 15.6¢ and 9.2¢.

## Nomination leg

| Parameter | Value | Rationale | Sensitivity |
|---|---|---|---|
| Early-standing cell | rank ≤ 2 | Newsom is #2 in scraped 2026 polling means (16.4%, behind Harris 27.0%) and #2 by market price | rank ≤ 1 cell would be ~56% but does not describe Newsom today |
| Exclude Trump 2024 | yes | prior nominee ran quasi-incumbent; different process | including: base-rate median 34.9% → 36.6% (immaterial) |
| Analog rank kernel σ | 1.5 | rank differences of 1–2 are materially similar standings | wider σ pulls toward the unconditional ~13% candidacy win rate |
| Flag mismatch penalty | 0.55 | each structural mismatch roughly halves relevance | 0.4–0.7 moves the analog median ≈ ±2pp |
| Longshot-bias slope b | N(1.15, 0.10) | literature range for multi-year political markets | b=1.0 (no bias): market lane 15.7¢; b=1.3: 10.1¢ |
| Ensemble weights | Dirichlet(2,2,4) | $1B-volume price is the strongest single evidence source | equal weights: nomination fair 15.6¢ → 20.1¢ — **still FAIR** |

## Conditional leg

| Parameter | Value | Rationale | Sensitivity |
|---|---|---|---|
| Open-seat shrinkage | 0.5 toward 0.5 | n=8 and selection-biased; raw 87.5% is not credible as a forward rate | no shrinkage would push conditional lane to ~80%+, which we judge indefensible |
| Include 2024 as open seat | yes (flagged) | incumbent withdrew pre-convention | excluding: fundamentals median 62.9% → 61.9% (immaterial) |
| Newsom adjustment | N(−3pp, 8pp) | national favorability deficit; "California brand" attack surface; wide because home-state-brand evidence is thin | the −3pp center is a judgment call; even at 0 the verdict is unchanged |
| Conditional σ floor | 7pp | forbids unearned precision 27 months out | — |
| Market-implied conditional noise | ±10% relative | price ratio of two noisy prices | — |

## Economics

| Parameter | Value | Rationale |
|---|---|---|
| Carry benchmark | FRED DGS2 (currently ~4.19%) | 2-yr Treasury ≈ the term of locked capital; fallback 4% if the pull fails |
| Round-trip cost | 1¢ | Polymarket has no explicit fee; this covers spread + slippage at current book depth |
| Resolution dates | 2028-08-31 (nomination), 2028-11-08 (presidency) | convention / day after election |

## The decision gate (pre-registered — do not tune after looking at results)

| Parameter | Value | Rationale |
|---|---|---|
| Edge ratio | 1.5× | a 27-month model of a small-sample domain must clear a high bar before "BUY"; 1.1× edges are indistinguishable from model noise |
| Tail gate percentile | 10th | even a pessimistic read of the model should not lose money after carry |
| Kelly | half-Kelly recommended | model probability ≠ true probability |

Changing gate parameters after observing results would be p-hacking the verdict; the gate
is versioned in git history precisely so any such change is visible.
