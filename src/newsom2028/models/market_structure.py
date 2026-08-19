"""Market-structure lane: what the price itself is worth as evidence.

Two jobs:

1. **Calibration-corrected price.**  Long-horizon political prediction
   markets exhibit favorite-longshot bias: low-priced contracts resolve YES
   somewhat less often than their price implies (Page & Clemen 2013;
   Rothschild 2009).  We map price -> calibrated probability with
   ``sigmoid(a + b * logit(price))`` and *sample* (a, b) so parameter
   uncertainty propagates into the posterior.  Note the direction: this
   correction works AGAINST the undervaluation thesis for a 8-16c contract,
   which is exactly why it must be in the model.

2. **Cross-market diagnostics** used by the report: implied
   P(general | nominee) per candidate (presidency price / nominee price),
   and Polymarket-vs-Kalshi spreads on the same contract.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from newsom2028 import config


def _logit(p: np.ndarray | float) -> np.ndarray | float:
    return np.log(p / (1 - p))


def _sigmoid(x: np.ndarray | float) -> np.ndarray | float:
    return 1 / (1 + np.exp(-x))


@dataclass
class MarketLaneResult:
    market_price: float
    calibrated_mean: float
    draws: np.ndarray


def run(market_price: float, rng: np.random.Generator, n_draws: int) -> MarketLaneResult:
    params = config.MARKET_STRUCTURE
    a = rng.normal(params.a_mean, params.a_sd, n_draws)
    b = rng.normal(params.b_mean, params.b_sd, n_draws)
    draws = _sigmoid(a + b * _logit(market_price))
    return MarketLaneResult(market_price, float(draws.mean()), draws)


def implied_conditionals(snapshot: pd.DataFrame) -> pd.DataFrame:
    """Market-implied P(wins general | nominated) per candidate.

    Computed as presidency price / nominee price from the same snapshot.
    Large cross-candidate spreads in this ratio are hard to justify with
    fundamentals and are the primary relative-value diagnostic.
    """
    named = snapshot[snapshot["candidate"].astype(str).str.len() > 0]
    nominee = (
        named[
            named["event_slug"].str.contains("democratic-presidential-nominee")
            | named["event_slug"].str.contains("republican-presidential-nominee")
        ]
        .groupby("candidate")["yes_price"].max()
    )
    president = (
        named[named["event_slug"] == "presidential-election-winner-2028"]
        .groupby("candidate")["yes_price"].max()
    )

    rows = []
    for candidate in president.index.intersection(nominee.index):
        p_nom, p_pres = float(nominee[candidate]), float(president[candidate])
        if p_nom < 0.02:  # ratio is noise below this
            continue
        rows.append(
            {
                "candidate": candidate,
                "nominee_price": p_nom,
                "president_price": p_pres,
                "implied_conditional": p_pres / p_nom,
            }
        )
    return (
        pd.DataFrame(rows)
        .sort_values("nominee_price", ascending=False)
        .reset_index(drop=True)
    )
