"""Fundamentals lane: P(wins general | nominated).

Built from three pieces, each with explicit uncertainty:

1. **Open-seat base rate.**  In post-WWII open-seat presidential elections
   the non-White-House party won 7 of 8 (data/reference/open_seat_generals.csv).
   This is a small, arguably selection-biased sample (open seats cluster
   after unpopular second terms), so it is shrunk toward 0.5 by
   ``base_rate_shrinkage`` before use.
2. **Candidate adjustment.**  Newsom-specific shift for national
   favorability deficit and the 'California brand' attack surface -
   centered slightly negative, wide, because rigorous evidence for
   home-state-brand effects is thin.
3. **A variance floor** so the lane can never claim precision the
   evidence doesn't support.

2024 is counted as an out-party win but flagged quasi-open; the sensitivity
appendix reruns the lane without it.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from newsom2028 import config


@dataclass
class FundamentalsResult:
    raw_base_rate: float
    shrunk_base_rate: float
    draws: np.ndarray

    @property
    def mean(self) -> float:
        return float(self.draws.mean())


def run(
    rng: np.random.Generator,
    n_draws: int,
    include_quasi_open: bool = True,
) -> FundamentalsResult:
    params = config.FUNDAMENTALS
    seats = pd.read_csv(config.REFERENCE_DIR / "open_seat_generals.csv")
    if not include_quasi_open:
        seats = seats[seats["year"] != 2024]

    k = int(seats["out_party_won"].sum())
    n = int(len(seats))
    raw = k / n
    shrunk = (1 - params.base_rate_shrinkage) * raw + params.base_rate_shrinkage * 0.5

    # Beta around the shrunk rate with effective n (small by construction),
    # then the candidate-specific shift, then the variance floor.
    alpha = shrunk * n + 1.0
    beta = (1 - shrunk) * n + 1.0
    base_draws = rng.beta(alpha, beta, n_draws)
    shift = rng.normal(params.candidate_shift_mean, params.candidate_shift_sd, n_draws)
    draws = np.clip(base_draws + shift, 0.02, 0.98)

    if draws.std() < params.conditional_sd_floor:
        extra = np.sqrt(params.conditional_sd_floor**2 - draws.std() ** 2)
        draws = np.clip(draws + rng.normal(0, extra, n_draws), 0.02, 0.98)
    return FundamentalsResult(raw, shrunk, draws)


def market_implied_conditional(
    nominee_price: float,
    president_price: float,
    rng: np.random.Generator,
    n_draws: int,
    rel_sd: float = 0.10,
) -> np.ndarray:
    """The market's own view of the conditional leg, with price-noise spread."""
    ratio = president_price / nominee_price
    draws = ratio * (1 + rng.normal(0, rel_sd, n_draws))
    return np.clip(draws, 0.02, 0.98)
