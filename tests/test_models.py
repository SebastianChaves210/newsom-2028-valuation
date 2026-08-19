"""Model-lane and ensemble behavior tests (no network required)."""

import numpy as np
import pytest

from newsom2028.models import analog, base_rate, ensemble, market_structure
from newsom2028.models.market_structure import _logit, _sigmoid


@pytest.fixture(scope="module")
def rng():
    return np.random.default_rng(0)


def test_base_rate_cell_counts(rng):
    result = base_rate.run(2, rng, 10_000)
    # top-2 standing candidates (Trump 2024 excluded): known panel counts
    assert result.n == 35
    assert result.k == 12
    assert 0.2 < result.mean < 0.5


def test_base_rate_quasi_incumbent_toggle(rng):
    with_trump = base_rate.run(2, rng, 1_000, include_quasi_incumbent=True)
    assert with_trump.n == 36 and with_trump.k == 13


def test_analog_effective_n_reasonable(rng):
    result = analog.run(rng, 10_000)
    assert 3 < result.effective_n < 90
    assert 0.05 < result.weighted_win_rate < 0.5
    # the closest analogs should include a top-2 sitting governor
    top_names = {r["candidate"] for r in result.top_analogs.to_dict("records")[:5]}
    assert top_names & {"Ron DeSantis", "Scott Walker", "George W. Bush", "Michael Dukakis"}


def test_market_lane_neutral_when_unbiased():
    # with a = 0 and b = 1 the correction is the identity
    price = 0.1565
    assert _sigmoid(1.0 * _logit(price)) == pytest.approx(price, abs=1e-9)


def test_market_lane_longshot_direction(rng):
    result = market_structure.run(0.10, rng, 50_000)
    # b > 1 must shrink a longshot price downward on average
    assert result.calibrated_mean < 0.10


def test_ensemble_product_identity_and_bounds():
    result = ensemble.run(0.15, 0.08, early_rank=2)
    assert np.allclose(
        result.president_draws, result.nominee_draws * result.conditional_draws
    )
    for draws in (result.nominee_draws, result.conditional_draws, result.president_draws):
        assert draws.min() >= 0 and draws.max() <= 1
    # presidency must be rarer than nomination
    assert result.president_draws.mean() < result.nominee_draws.mean()
