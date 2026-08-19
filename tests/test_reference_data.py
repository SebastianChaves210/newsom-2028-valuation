"""Integrity checks on the hand-curated historical panels."""

import pandas as pd
import pytest

from newsom2028 import config


@pytest.fixture(scope="module")
def contests() -> pd.DataFrame:
    return pd.read_csv(config.REFERENCE_DIR / "nomination_contests.csv")


def test_exactly_one_winner_per_contest(contests):
    winners = contests.groupby(["cycle", "party"])["won_nomination"].sum()
    assert (winners == 1).all(), winners[winners != 1]


def test_general_winner_also_won_nomination(contests):
    bad = contests[(contests["won_general"] == 1) & (contests["won_nomination"] == 0)]
    assert bad.empty


def test_ranks_start_at_one(contests):
    firsts = contests.groupby(["cycle", "party"])["early_poll_rank"].min()
    assert (firsts == 1).all()


def test_flags_are_binary(contests):
    for col in [
        "ran", "sitting_governor", "former_governor", "sitting_vp",
        "prior_nominee", "prior_run", "won_nomination", "won_general",
    ]:
        assert contests[col].isin([0, 1]).all(), col


def test_open_seat_generals():
    seats = pd.read_csv(config.REFERENCE_DIR / "open_seat_generals.csv")
    assert len(seats) == 8
    assert seats["out_party_won"].isin([0, 1]).all()
    assert int(seats["out_party_won"].sum()) == 7
