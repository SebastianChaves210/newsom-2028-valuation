"""Endorsement tracker (Tier 1 - the 'party decides' signal).

Weighted endorsements from party elites are political science's
best-documented early predictor of presidential nominations (Cohen, Karol,
Noel & Zaller, *The Party Decides*, 2008; FiveThirtyEight's 'endorsement
primary').  We use FiveThirtyEight's weights: governors 10, U.S. senators 5,
U.S. representatives 1.

The data lives in ``data/reference/endorsements.csv`` and is hand-curated -
endorsements are discrete public events, not scrapable feeds.  As of
2026-08 the file is empty because formal 2028 endorsements essentially do
not exist yet (no declared candidates); the tracker is armed so the signal
appears in reports the moment rows are added.  Add one row per endorsement:

    date,endorser,office,state,candidate,source_url
    2027-03-01,Jane Doe,senator,PA,Gavin Newsom,https://...

Valid offices: governor, senator, representative (anything else gets
weight 0 and a warning).  When declared candidates exist and endorsements
accumulate, this becomes a candidate fifth model lane - see
docs/METHODOLOGY.md.
"""

from __future__ import annotations

import logging

import pandas as pd

from newsom2028 import config

log = logging.getLogger(__name__)

WEIGHTS = {"governor": 10, "senator": 5, "representative": 1}


def load() -> pd.DataFrame:
    frame = pd.read_csv(config.REFERENCE_DIR / "endorsements.csv")
    if frame.empty:
        return frame
    unknown = set(frame["office"].str.lower()) - set(WEIGHTS)
    if unknown:
        log.warning("unweighted endorsement offices ignored: %s", unknown)
    frame["weight"] = frame["office"].str.lower().map(WEIGHTS).fillna(0)
    return frame


def points() -> list[dict]:
    """Endorsement points per candidate, FiveThirtyEight-weighted."""
    frame = load()
    if frame.empty:
        return []
    table = (
        frame.groupby("candidate")
        .agg(points=("weight", "sum"), endorsements=("endorser", "count"))
        .sort_values("points", ascending=False)
        .reset_index()
    )
    return table.to_dict("records")
