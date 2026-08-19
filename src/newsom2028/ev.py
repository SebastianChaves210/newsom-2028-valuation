"""Expected-value engine and the pre-registered verdict gate.

Hold-to-resolution NPV per $1 contract bought at price q:

    NPV = E[fair] / (1 + r)^T  -  q  -  cost

where r is the current 2-year Treasury yield (carry: the same dollar parked
in T-bills), T is years to resolution, and cost is the round-trip
spread/slippage assumption.  Kelly fraction uses the posterior mean; verdict
uses the pre-registered edge + uncertainty gate from config.py.

Scenario analysis (mark-to-market exits) lives here too and is labelled
speculative: it assumes partial convergence of price toward model fair
value at named milestones, which is an assumption about OTHER TRADERS, not
about Newsom.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np


@dataclass
class ContractEV:
    label: str
    market_price: float
    fair_median: float
    fair_p10: float
    fair_p90: float
    years_to_resolution: float
    risk_free: float
    npv_per_dollar_of_price: float
    npv_median: float
    npv_p10: float
    kelly_fraction: float
    verdict: str
    gate_detail: str


def _years_until(target: dt.date, today: dt.date | None = None) -> float:
    today = today or dt.date.today()
    return max((target - today).days / 365.25, 0.0)


def _kelly(p: float, q: float) -> float:
    """Kelly fraction for a binary contract bought at price q, win prob p."""
    if p <= q:
        return 0.0
    b = (1 - q) / q  # net odds per dollar staked
    return max((b * p - (1 - p)) / b, 0.0)


def evaluate(
    label: str,
    market_price: float,
    fair_draws: np.ndarray,
    resolution: dt.date,
    risk_free: float,
    round_trip_cost: float,
    edge_ratio: float,
    gate_percentile: float,
    today: dt.date | None = None,
) -> ContractEV:
    years = _years_until(resolution, today)
    discount = (1 + risk_free) ** -years

    npv_draws = fair_draws * discount - market_price - round_trip_cost
    fair_median = float(np.median(fair_draws))
    fair_p10 = float(np.percentile(fair_draws, gate_percentile))
    fair_p90 = float(np.percentile(fair_draws, 100 - gate_percentile))

    ratio_ok = fair_median >= edge_ratio * market_price
    # Gate 2: even the pessimistic (p10) fair value must clear price after
    # carry and costs.
    tail_ok = fair_p10 * discount - market_price - round_trip_cost > 0

    if ratio_ok and tail_ok:
        verdict = "BUY"
    elif ratio_ok or tail_ok:
        verdict = "SPECULATIVE VALUE"
    elif fair_p90 * discount < market_price:
        verdict = "OVERVALUED"
    else:
        verdict = "FAIR"

    gate_detail = (
        f"median/price = {fair_median / market_price:.2f}x "
        f"(gate {edge_ratio:.1f}x: {'PASS' if ratio_ok else 'FAIL'}); "
        f"p{gate_percentile:.0f} NPV = {fair_p10 * discount - market_price - round_trip_cost:+.3f} "
        f"({'PASS' if tail_ok else 'FAIL'})"
    )
    mean = float(fair_draws.mean())
    return ContractEV(
        label=label,
        market_price=market_price,
        fair_median=fair_median,
        fair_p10=fair_p10,
        fair_p90=fair_p90,
        years_to_resolution=years,
        risk_free=risk_free,
        npv_per_dollar_of_price=float(np.mean(npv_draws)) / market_price,
        npv_median=float(np.median(npv_draws)),
        npv_p10=float(np.percentile(npv_draws, gate_percentile)),
        kelly_fraction=_kelly(mean, market_price + round_trip_cost),
        verdict=verdict,
        gate_detail=gate_detail,
    )


def exit_scenarios(
    market_price: float,
    fair_median: float,
    risk_free: float,
    round_trip_cost: float,
    today: dt.date | None = None,
) -> list[dict]:
    """Speculative mark-to-market exits: price converges fraction kappa toward
    model fair value by each milestone.  Reported as scenarios, not forecasts."""
    today = today or dt.date.today()
    milestones = [
        ("Candidacy announcement window", dt.date(2027, 6, 30), 0.25),
        ("Post early states (IA/NH/SC)", dt.date(2028, 2, 15), 0.50),
        ("Post Super Tuesday", dt.date(2028, 3, 15), 0.75),
    ]
    rows = []
    for name, when, kappa in milestones:
        years = _years_until(when, today)
        exit_price = market_price + kappa * (fair_median - market_price)
        gross = exit_price - market_price - round_trip_cost
        ret = gross / market_price
        annualized = (1 + ret) ** (1 / years) - 1 if years > 0 and ret > -1 else ret
        rows.append(
            {
                "milestone": name,
                "date": when.isoformat(),
                "convergence_kappa": kappa,
                "assumed_exit_price": round(exit_price, 4),
                "return_pct": round(100 * ret, 1),
                "annualized_pct": round(100 * annualized, 1),
                "beats_carry": annualized > risk_free,
            }
        )
    return rows
