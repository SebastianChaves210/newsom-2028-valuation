"""Historical-analog lane: P(nominee) from Newsom's full profile.

Where the base-rate lane conditions on one variable (early standing), this
lane matches on the whole structural profile - early rank, sitting-governor
status, prior runs, VP/nominee history - using a similarity-weighted
average of historical outcomes.  Sitting governors with strong early
standing are a genuinely mixed bag (George W. Bush converted; Scott Walker
and Ron DeSantis collapsed), and this lane is where that evidence enters.

The weighted win rate is converted to a Beta posterior through the Kish
effective sample size, so a profile with few good analogs yields a wide
posterior instead of false confidence.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from newsom2028 import config
from newsom2028.models.base_rate import load_contests

# Newsom's structural profile, mid-2026 (~20 months before the first primary).
NEWSOM_PROFILE = {
    "early_poll_rank": 2,      # overridden with live polling rank when available
    "sitting_governor": 1,
    "former_governor": 0,
    "sitting_vp": 0,
    "prior_nominee": 0,
    "prior_run": 0,
}

RANK_KERNEL_WIDTH = 1.5   # gaussian width on poll-rank distance
FLAG_MISMATCH_PENALTY = 0.55  # weight multiplier per mismatched binary flag


@dataclass
class AnalogResult:
    weighted_win_rate: float
    effective_n: float
    top_analogs: pd.DataFrame
    draws: np.ndarray


def _similarity(row: pd.Series, profile: dict) -> float:
    rank_term = np.exp(
        -((row["early_poll_rank"] - profile["early_poll_rank"]) ** 2)
        / (2 * RANK_KERNEL_WIDTH**2)
    )
    weight = rank_term
    for flag in (
        "sitting_governor",
        "former_governor",
        "sitting_vp",
        "prior_nominee",
        "prior_run",
    ):
        if int(row[flag]) != profile[flag]:
            weight *= FLAG_MISMATCH_PENALTY
    return float(weight)


def run(
    rng: np.random.Generator,
    n_draws: int,
    profile: dict | None = None,
) -> AnalogResult:
    profile = {**NEWSOM_PROFILE, **(profile or {})}
    contests = load_contests()
    contests["weight"] = contests.apply(_similarity, axis=1, args=(profile,))

    weights = contests["weight"].to_numpy()
    outcomes = contests["won_nomination"].to_numpy()
    win_rate = float(np.average(outcomes, weights=weights))
    effective_n = float(weights.sum() ** 2 / (weights**2).sum())

    alpha = win_rate * effective_n + 1.0
    beta = (1 - win_rate) * effective_n + 1.0
    top = (
        contests.sort_values("weight", ascending=False)
        .head(12)[["cycle", "party", "candidate", "weight", "won_nomination"]]
        .reset_index(drop=True)
    )
    return AnalogResult(win_rate, effective_n, top, rng.beta(alpha, beta, n_draws))
