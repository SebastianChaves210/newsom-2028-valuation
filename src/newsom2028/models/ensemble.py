"""Ensemble: Dirichlet-weighted linear opinion pool over the model lanes.

For every Monte Carlo draw we (1) sample lane weights from a Dirichlet whose
concentrations encode relative trust (config.ENSEMBLE), (2) pick one lane
per leg by categorical draw, and (3) take that lane's sampled probability.
This is a proper mixture: if the lanes disagree, the posterior gets WIDER.
Averaging lane draws instead would smuggle in false precision - the classic
ensemble mistake.

Output: joint draws of P(nominee), P(general | nominee) and their product
P(president), plus per-lane summaries for the report.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from newsom2028 import config
from newsom2028.models import analog, base_rate, fundamentals, market_structure


def _percentiles(draws: np.ndarray) -> dict:
    q = np.percentile(draws, [5, 10, 25, 50, 75, 90, 95])
    return {
        "mean": float(draws.mean()),
        "p5": float(q[0]),
        "p10": float(q[1]),
        "p25": float(q[2]),
        "median": float(q[3]),
        "p75": float(q[4]),
        "p90": float(q[5]),
        "p95": float(q[6]),
    }


@dataclass
class EnsembleResult:
    nominee_draws: np.ndarray
    conditional_draws: np.ndarray
    president_draws: np.ndarray
    lane_summaries: dict = field(default_factory=dict)

    def summary(self) -> dict:
        return {
            "nominee": _percentiles(self.nominee_draws),
            "conditional": _percentiles(self.conditional_draws),
            "president": _percentiles(self.president_draws),
        }


def run(
    nominee_price: float,
    president_price: float,
    early_rank: int = 2,
) -> EnsembleResult:
    cfg = config.ENSEMBLE
    rng = np.random.default_rng(cfg.seed)
    n = cfg.n_draws

    # --- Leg 1: P(nominee) --------------------------------------------------
    lane_base = base_rate.run(early_rank, rng, n)
    lane_analog = analog.run(rng, n, profile={"early_poll_rank": early_rank})
    lane_market = market_structure.run(nominee_price, rng, n)

    nom_lanes = np.column_stack([lane_base.draws, lane_analog.draws, lane_market.draws])
    nom_weights = rng.dirichlet(cfg.nominee_weights, n)
    nom_choice = (nom_weights.cumsum(axis=1) > rng.random((n, 1))).argmax(axis=1)
    nominee_draws = nom_lanes[np.arange(n), nom_choice]

    # --- Leg 2: P(general | nominee) ---------------------------------------
    lane_fund = fundamentals.run(rng, n)
    lane_implied = fundamentals.market_implied_conditional(
        nominee_price, president_price, rng, n
    )
    cond_lanes = np.column_stack([lane_fund.draws, lane_implied])
    cond_weights = rng.dirichlet(cfg.conditional_weights, n)
    cond_choice = (cond_weights.cumsum(axis=1) > rng.random((n, 1))).argmax(axis=1)
    conditional_draws = cond_lanes[np.arange(n), cond_choice]

    president_draws = nominee_draws * conditional_draws

    lane_summaries = {
        "base_rate": {
            **_percentiles(lane_base.draws),
            "k": lane_base.k,
            "n": lane_base.n,
        },
        "analog": {
            **_percentiles(lane_analog.draws),
            "weighted_win_rate": lane_analog.weighted_win_rate,
            "effective_n": lane_analog.effective_n,
            "top_analogs": lane_analog.top_analogs.to_dict("records"),
        },
        "market_structure": {
            **_percentiles(lane_market.draws),
            "market_price": nominee_price,
        },
        "fundamentals": {
            **_percentiles(lane_fund.draws),
            "raw_base_rate": lane_fund.raw_base_rate,
            "shrunk_base_rate": lane_fund.shrunk_base_rate,
        },
        "market_implied_conditional": _percentiles(lane_implied),
    }
    return EnsembleResult(nominee_draws, conditional_draws, president_draws, lane_summaries)
