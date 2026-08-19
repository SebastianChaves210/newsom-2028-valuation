"""Cross-venue consensus: the same contract priced by four crowds.

Merges the latest snapshots from Polymarket (real money, crypto), Kalshi
(real money, US-regulated), Manifold (play money) and Metaculus (reputation
forecasters) into one per-candidate table for the Democratic nomination,
with a disagreement measure (max - min probability across venues).

Diagnostic only in v2: fair value still comes from the model lanes.  Venue
disagreement on Newsom specifically is direct evidence about whether the
Polymarket price is an outlier or the consensus.
"""

from __future__ import annotations

import logging

import pandas as pd

from newsom2028 import config

log = logging.getLogger(__name__)


def _latest_snapshot(source: str) -> pd.DataFrame:
    snap_dir = config.SNAPSHOT_DIR / source
    files = sorted(snap_dir.glob("*.csv"))
    return pd.read_csv(files[-1]) if files else pd.DataFrame()


def dem_nominee_comparison() -> list[dict]:
    """Per-candidate Dem-nomination probability across all venues."""
    venues: dict[str, pd.Series] = {}

    poly = _latest_snapshot("polymarket")
    if not poly.empty:
        dem = poly[poly["event_slug"] == "democratic-presidential-nominee-2028"]
        venues["polymarket"] = dem.groupby("candidate")["yes_price"].max()

    kalshi = _latest_snapshot("kalshi")
    if not kalshi.empty:
        dem = kalshi[kalshi["series"] == "KXPRESNOMD"].copy()
        # midpoint of bid/ask where a real book exists, else last trade
        dem["prob"] = dem[["yes_bid", "yes_ask"]].mean(axis=1)
        dem.loc[dem["prob"] <= 0, "prob"] = dem["last_price"]
        venues["kalshi"] = dem.dropna(subset=["prob"]).groupby("candidate")["prob"].max()

    manifold = _latest_snapshot("manifold")
    if not manifold.empty:
        dem = manifold[manifold["contest"] == "dem_nominee"]
        venues["manifold"] = dem.groupby("candidate")["probability"].max()

    metaculus = _latest_snapshot("metaculus")
    if not metaculus.empty:
        dem = metaculus[
            metaculus["question"].str.contains("nominee", case=False, na=False)
        ]
        venues["metaculus"] = dem.groupby("candidate")["probability"].max()

    if not venues:
        return []

    table = pd.DataFrame(venues)
    table = table[table.max(axis=1) >= 0.02]  # drop noise-level candidates
    table["spread"] = table.max(axis=1) - table.min(axis=1)
    table = table.sort_values(by=list(venues)[0], ascending=False)
    out = []
    for candidate, row in table.iterrows():
        record = {"candidate": candidate}
        for venue in venues:
            value = row.get(venue)
            record[venue] = None if pd.isna(value) else round(float(value), 4)
        record["spread"] = round(float(row["spread"]), 4)
        out.append(record)
    return out
