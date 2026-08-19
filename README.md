# Newsom 2028: A Quantitative Prediction-Market Valuation

**Is Gavin Newsom's 2028 presidential contract undervalued, fairly valued, or overvalued?**

This repository is a reproducible, continuously updated quantitative research project that
prices Gavin Newsom's 2028 Polymarket contracts — the Democratic-nomination contract and the
presidency contract — against an ensemble of independent statistical models, and issues a
pre-registered BUY / SPECULATIVE VALUE / FAIR / OVERVALUED verdict with credible intervals.

The latest verdict is always in [`reports/latest.md`](reports/latest.md); the interactive
dashboard is [`dashboard/index.html`](dashboard/index.html). Both regenerate automatically
via a scheduled GitHub Actions run.

## The investment thesis under test

> Newsom is currently underpriced by prediction markets, and buying his 2028 contract has
> positive expected value.

The project's job is to test that thesis as rigorously as possible — **not** to confirm it.
The verdict rule, edge thresholds, and model structure were fixed before the first model run
(see [Pre-registration](#pre-registration-the-decision-rule)), so the conclusion is whatever
the evidence says it is.

## Core architecture: the decomposition

Everything is built around one identity:

```
P(president) = P(nominee) × P(wins general | nominee)
```

The two legs are very different problems (a crowded-primary problem and a general-election
problem), are informed by different evidence, and can be mispriced independently — the
market itself prices both legs for every candidate, so the ratio of a candidate's presidency
price to their nominee price is the market's implied conditional, and cross-candidate spreads
in that ratio are a key relative-value diagnostic.

## Model lanes

Four independent lanes produce posteriors; a Dirichlet-weighted **linear opinion pool**
(a true mixture — disagreement between lanes *widens* the final interval) combines them,
and 200,000 Monte Carlo draws propagate every layer of uncertainty into the verdict.

| Lane | Leg | Question it answers |
|---|---|---|
| **Historical base rate** | P(nominee) | Across all open nomination contests 1972–2024, how often did a candidate with Newsom's early standing win? (Outside view; knows nothing about Newsom.) |
| **Historical analogs** | P(nominee) | How did candidates with Newsom's *full* structural profile — top-2 early standing, sitting big-state governor, first run — actually fare? |
| **Market structure** | P(nominee) | What is the price itself worth as evidence, after correcting for the favorite-longshot bias documented in long-horizon political markets? |
| **Fundamentals** | P(general \| nominee) | Open-seat general-election base rates, shrunk for small-sample bias, shifted by a Newsom-specific adjustment with wide uncertainty. |

The market-implied conditional (presidency ÷ nominee price) enters as a fifth lane on the
conditional leg. Full derivations: [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md).

## Pre-registration: the decision rule

Fixed in `src/newsom2028/config.py` before the first run:

- **BUY** requires **both**: ensemble median fair value ≥ **1.5×** market price, **and** the
  10th-percentile fair value still clears price + carry (2-year Treasury) + 1¢ round-trip cost.
- Exactly one condition met → **SPECULATIVE VALUE** (not actionable).
- Neither, with price inside the 80% credible interval → **FAIR**; price above the 90th
  percentile → **OVERVALUED**.

Kelly fractions are reported for any BUY, with half-Kelly recommended.

## Data sources, tiered by evidentiary weight

| Tier | Sources | Role |
|---|---|---|
| 1 | Polymarket (prices + full contract history), Kalshi, Manifold (play money), Metaculus (forecaster crowd, token-gated), Wikipedia's structured 2028-primary polling tables, hand-curated 1972–2024 nomination panel, endorsement tracker (armed) | Drives fair value / cross-venue consensus |
| 2 | FRED (2-yr Treasury for carry, macro context) | Priors and economics |
| 3 | Wikipedia pageviews, GDELT news volume + tone (media sentiment) | Dashboard context **only** — firewalled from fair value, accumulating data for a price-lead-lag study |

Every collector is append-only: each run snapshots into `data/snapshots/<source>/<date>.csv`,
so the repository accumulates its own history. The hand-curated historical panel and its
coding rules are documented in [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md).

## Reproducing

```bash
# --no-editable is deliberate: some Python builds mishandle uv's editable .pth files
uv run --no-editable --extra dev newsom2028 run    # collect + model + report + dashboard
uv run --no-editable --extra dev newsom2028 model  # re-model from existing snapshots (offline)
uv run --no-editable --extra dev pytest            # test suite
```

Optional: set `METACULUS_TOKEN` (free account → API token) to enable the Metaculus
collector; everything else is keyless.

## Repository layout

```
src/newsom2028/
  collectors/        append-only data collectors (Polymarket, Kalshi, polling, FRED, pageviews)
  models/            the four lanes + ensemble
  ev.py              carry-adjusted EV, Kelly sizing, verdict gate, exit scenarios
  pipeline.py        orchestration; verdict history time series
  report.py          dated markdown research reports
  dashboard.py       self-contained Plotly dashboard
data/reference/      hand-curated historical panels (1972–2024)
data/snapshots/      dated raw pulls (append-only)
data/processed/      derived series: price history, verdict history, posteriors
docs/                METHODOLOGY, ASSUMPTIONS, LIMITATIONS, DATA_SOURCES
reports/             dated verdicts; latest.md is current
dashboard/           index.html, regenerated every run
```

## Intellectual honesty

- **The single-event problem.** 2028 happens once. The outcome can neither validate nor
  refute this model; only the *method* is testable, against 1972–2024 history. A Newsom win
  would not prove the model right, and a loss would not prove it wrong.
- **The strongest documented market bias cuts against the thesis.** Favorite-longshot bias
  implies low-priced political contracts tend to be *over*priced. It is modeled, not ignored.
- **The historical sample is small.** ~18 open contests, ~95 candidacies. Intervals are wide
  because the evidence is thin; any narrower would be false precision.
- **Attention ≠ probability.** Search/pageview/social signals are collected but firewalled
  from fair value; at a 27-month horizon they measure news cycles.
- Every tunable assumption lives in `config.py`, is documented in
  [`docs/ASSUMPTIONS.md`](docs/ASSUMPTIONS.md), and is stress-tested there.
  What this project cannot tell you is catalogued in [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md).

## Disclaimer

This is a research project, not investment advice. Prediction-market trading may be
restricted in your jurisdiction. Position sizes implied by Kelly fractions assume the model
is correct, which — see above — cannot be established.
