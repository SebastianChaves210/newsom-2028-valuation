"""Base-rate lane (outside view): P(nominee) from historical standing.

The question this lane answers: "across all open nomination contests since
1972, how often did a candidate with Newsom's *early standing* (top-2 in
national polls / markets at roughly this point in the cycle) win the
nomination?"  It knows nothing about Newsom himself - that is the point.
It is the Kahneman outside view that disciplines candidate-specific
storytelling.

Posterior: Beta(k + 1, n - k + 1) over the matching historical cell
(uniform prior).  With n around 36 the interval is wide, which is honest.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from newsom2028 import config


@dataclass
class BaseRateResult:
    k: int
    n: int
    alpha: float
    beta: float
    draws: np.ndarray

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)


def load_contests() -> pd.DataFrame:
    frame = pd.read_csv(config.REFERENCE_DIR / "nomination_contests.csv")
    return frame[frame["ran"] == 1].copy()


def run(
    early_rank: int,
    rng: np.random.Generator,
    n_draws: int,
    include_quasi_incumbent: bool = False,
) -> BaseRateResult:
    """Posterior for P(nomination | early rank <= max(early_rank, 2)).

    ``include_quasi_incumbent=False`` drops Trump 2024 (prior nominee running
    as de-facto incumbent), the closest thing to a contaminated observation
    in the panel; the sensitivity appendix reports both.
    """
    contests = load_contests()
    if not include_quasi_incumbent:
        contests = contests[
            ~((contests["cycle"] == 2024) & (contests["candidate"] == "Donald Trump"))
        ]
    cell = contests[contests["early_poll_rank"] <= max(early_rank, 2)]
    k = int(cell["won_nomination"].sum())
    n = int(len(cell))
    alpha, beta = k + 1.0, n - k + 1.0
    return BaseRateResult(k, n, alpha, beta, rng.beta(alpha, beta, n_draws))
