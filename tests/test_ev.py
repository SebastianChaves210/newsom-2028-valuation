"""EV engine: gate logic, carry, Kelly."""

import datetime as dt

import numpy as np

from newsom2028 import ev

TODAY = dt.date(2026, 8, 18)
RESOLUTION = dt.date(2028, 11, 8)


def _evaluate(price, draws):
    return ev.evaluate(
        "test", price, draws, RESOLUTION,
        risk_free=0.04, round_trip_cost=0.01,
        edge_ratio=1.5, gate_percentile=10, today=TODAY,
    )


def test_buy_when_both_gates_pass():
    draws = np.random.default_rng(0).normal(0.30, 0.02, 100_000).clip(0, 1)
    result = _evaluate(0.10, draws)
    assert result.verdict == "BUY"
    assert result.kelly_fraction > 0


def test_fair_when_price_matches_model():
    draws = np.random.default_rng(0).normal(0.10, 0.03, 100_000).clip(0, 1)
    result = _evaluate(0.10, draws)
    assert result.verdict == "FAIR"


def test_overvalued_when_price_above_p90():
    draws = np.random.default_rng(0).normal(0.05, 0.01, 100_000).clip(0, 1)
    result = _evaluate(0.20, draws)
    assert result.verdict == "OVERVALUED"
    assert result.kelly_fraction == 0.0


def test_speculative_when_only_ratio_passes():
    # median 2x price but a fat left tail that fails the p10 gate
    rng = np.random.default_rng(0)
    draws = np.concatenate([
        rng.normal(0.20, 0.01, 80_000), rng.normal(0.02, 0.005, 20_000),
    ]).clip(0, 1)
    result = _evaluate(0.10, draws)
    assert result.verdict == "SPECULATIVE VALUE"


def test_carry_reduces_npv():
    draws = np.full(10_000, 0.12)
    result = _evaluate(0.10, draws)
    # fair 12c on a 10c contract, but >2 years of carry + 1c cost: NPV ~ 0
    assert result.npv_median < 0.02


def test_kelly_zero_without_edge():
    assert ev._kelly(0.10, 0.10) == 0.0
    assert ev._kelly(0.05, 0.10) == 0.0
    assert 0 < ev._kelly(0.20, 0.10) < 1
