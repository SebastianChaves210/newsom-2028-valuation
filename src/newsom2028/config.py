"""Central configuration: market identifiers, model parameters, file layout.

Every tunable assumption in the models lives here so that sensitivity analysis
and documentation (docs/ASSUMPTIONS.md) reference a single source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def _find_root() -> Path:
    """Locate the repository root regardless of how the package is installed.

    Priority: NEWSOM2028_ROOT env var; else walk up from the working directory
    looking for data/reference (the pipeline is normally run from the repo);
    else fall back to the source-tree heuristic (src/newsom2028/config.py).
    """
    import os

    if env := os.environ.get("NEWSOM2028_ROOT"):
        return Path(env).resolve()
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if (candidate / "data" / "reference").is_dir():
            return candidate
    return Path(__file__).resolve().parents[2]


ROOT = _find_root()
DATA_DIR = ROOT / "data"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
REFERENCE_DIR = DATA_DIR / "reference"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = ROOT / "reports"
DASHBOARD_DIR = ROOT / "dashboard"

# ---------------------------------------------------------------------------
# Subject of the analysis
# ---------------------------------------------------------------------------
SUBJECT = "Gavin Newsom"

# Polymarket event slugs we track. The GOP nominee market and the party-winner
# market are collected for cross-market consistency checks, not direct pricing.
POLYMARKET_EVENT_SLUGS = [
    "democratic-presidential-nominee-2028",
    "presidential-election-winner-2028",
    "republican-presidential-nominee-2028",
    "which-party-wins-2028-us-presidential-election",
]

# Candidates whose contracts we snapshot in full (price history + conditionals).
# Used for the cross-candidate conditional-probability consistency analysis.
TRACKED_CANDIDATES = [
    "Gavin Newsom",
    "Alexandria Ocasio-Cortez",
    "Jon Ossoff",
    "Kamala Harris",
    "Pete Buttigieg",
    "Josh Shapiro",
    "Mark Kelly",
    "Andy Beshear",
    "Gretchen Whitmer",
    "JD Vance",
    "Marco Rubio",
]

# Wikipedia pages used as the attention proxy (Tier 3 signal only).
WIKIPEDIA_PAGES = {
    "Gavin Newsom": "Gavin_Newsom",
    "Alexandria Ocasio-Cortez": "Alexandria_Ocasio-Cortez",
    "Jon Ossoff": "Jon_Ossoff",
    "Pete Buttigieg": "Pete_Buttigieg",
    "JD Vance": "JD_Vance",
}

# Wikipedia polling page for the 2028 Democratic primary (Tier 1 polling source).
WIKI_POLLING_PAGE = (
    "https://en.wikipedia.org/wiki/"
    "Nationwide_opinion_polling_for_the_2028_Democratic_Party_presidential_primaries"
)

# FRED series pulled via the keyless fredgraph.csv endpoint.
FRED_SERIES = {
    "DGS2": "2-Year Treasury Constant Maturity Rate",
    "UNRATE": "Unemployment Rate",
    "UMCSENT": "University of Michigan Consumer Sentiment",
}

# ---------------------------------------------------------------------------
# Contract economics
# ---------------------------------------------------------------------------
# Approximate resolution dates used for discounting locked capital.
NOMINEE_RESOLUTION = date(2028, 8, 31)   # after the Democratic convention
PRESIDENT_RESOLUTION = date(2028, 11, 8)  # day after the general election

# Round-trip transaction cost assumption, in probability points (spread +
# slippage; Polymarket currently charges no explicit trading fee).
ROUND_TRIP_COST = 0.01

# Fallback annual risk-free rate if the FRED pull fails (checked against DGS2).
FALLBACK_RISK_FREE = 0.04

# ---------------------------------------------------------------------------
# Decision rule: the edge + uncertainty gate (pre-registered)
# ---------------------------------------------------------------------------
# BUY requires BOTH:
#   1. ensemble median fair value >= EDGE_RATIO * market price, AND
#   2. the GATE_PERCENTILE-th percentile of the fair-value posterior still
#      exceeds market price + carry + round-trip cost.
# Exactly one condition met  -> "SPECULATIVE VALUE" (not actionable).
# Neither                    -> FAIR (within interval) or OVERVALUED (below).
EDGE_RATIO = 1.5
GATE_PERCENTILE = 10

# ---------------------------------------------------------------------------
# Model parameters (each is documented and stress-tested in ASSUMPTIONS.md)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MarketStructureParams:
    """Favorite-longshot bias correction for long-horizon political markets.

    Calibrated probability = sigmoid(a + b * logit(price)).  b > 1 stretches
    the distribution away from the center: low prices shrink toward 0, high
    prices toward 1, matching the documented pattern that long-dated political
    longshots resolve YES less often than their price implies (Page & Clemen
    2013; Rothschild 2009).  Parameters are literature-derived, not fitted by
    this project - see docs/METHODOLOGY.md #market-structure.
    """

    b_mean: float = 1.15   # logit slope (1.0 = perfectly calibrated market)
    b_sd: float = 0.10     # uncertainty over the slope
    a_mean: float = 0.0    # logit intercept
    a_sd: float = 0.05


@dataclass(frozen=True)
class FundamentalsParams:
    """P(wins general | nominated) building blocks.

    The base rate comes from open-seat general elections (data/reference/
    open_seat_generals.csv) shrunk toward 0.5, then shifted by a
    candidate-specific adjustment for Newsom (national favorability deficit,
    'California brand' penalty).  The adjustment is centered slightly negative
    with wide uncertainty because the historical evidence for home-state brand
    effects is weak - see docs/ASSUMPTIONS.md #candidate-adjustment.
    """

    base_rate_shrinkage: float = 0.5      # weight on 0.5 vs the raw base rate
    candidate_shift_mean: float = -0.03   # prob-space shift for Newsom
    candidate_shift_sd: float = 0.08
    conditional_sd_floor: float = 0.07    # minimum posterior sd on the leg


@dataclass(frozen=True)
class EnsembleParams:
    """Ensemble weights (Dirichlet-sampled so weight uncertainty propagates).

    Concentrations express relative trust: the market-structure lane gets the
    most weight because market prices aggregate more information than our
    small-sample historical lanes; the base-rate and analog lanes discipline
    it with outside-view history.
    """

    n_draws: int = 200_000
    seed: int = 20280
    # (base_rate, analog, market_structure) concentrations for P(nominee)
    nominee_weights: tuple[float, float, float] = (2.0, 2.0, 4.0)
    # (fundamentals, market_implied) concentrations for P(general | nominee)
    conditional_weights: tuple[float, float] = (3.0, 3.0)


MARKET_STRUCTURE = MarketStructureParams()
FUNDAMENTALS = FundamentalsParams()
ENSEMBLE = EnsembleParams()
