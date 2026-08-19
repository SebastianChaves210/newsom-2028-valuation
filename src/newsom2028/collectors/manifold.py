"""Manifold Markets collector (Tier 1 - cross-venue consensus).

Manifold is a play-money forecasting market with a free public API.  Because
no capital is locked up for 27 months, its prices carry no carry-cost
discount and plausibly less favorite-longshot bias than real-money venues -
which makes disagreement between Manifold and Polymarket informative in
both directions.

We pin the highest-liquidity multiple-choice markets for the 2028 Dem
nomination and the 2028 presidency (slugs verified 2026-08), with a search
fallback in case they close or are superseded.
"""

from __future__ import annotations

import datetime as dt
import logging

import pandas as pd
import requests

from newsom2028 import config

log = logging.getLogger(__name__)

API = "https://api.manifold.markets/v0"
TIMEOUT = 30

PINNED = {
    "dem_nominee": "2028-democratic-nominee",
    "president": "who-will-win-the-2028-us-presidenti",
}
SEARCH_FALLBACK = {
    "dem_nominee": "2028 democratic nominee",
    "president": "who will win the 2028 US presidential election",
}


def _market_by_slug(slug: str) -> dict | None:
    resp = requests.get(f"{API}/slug/{slug}", timeout=TIMEOUT)
    return resp.json() if resp.status_code == 200 else None


def _search_best(term: str) -> dict | None:
    resp = requests.get(
        f"{API}/search-markets", params={"term": term, "limit": 10}, timeout=TIMEOUT
    )
    if resp.status_code != 200:
        return None
    candidates = [
        m for m in resp.json()
        if m.get("outcomeType") == "MULTIPLE_CHOICE" and not m.get("isResolved")
    ]
    if not candidates:
        return None
    best = max(candidates, key=lambda m: m.get("totalLiquidity") or 0)
    return _market_by_slug(best["slug"])


def collect() -> pd.DataFrame:
    now = dt.datetime.now(dt.timezone.utc)
    rows = []
    for contest, slug in PINNED.items():
        market = _market_by_slug(slug)
        if not market or not market.get("answers"):
            log.warning("Manifold pinned slug %s missing; falling back to search", slug)
            try:
                market = _search_best(SEARCH_FALLBACK[contest])
            except Exception as exc:  # noqa: BLE001
                log.warning("Manifold search failed: %s", exc)
                market = None
        if not market:
            continue
        for answer in market.get("answers", []):
            matched = [
                c for c in config.TRACKED_CANDIDATES
                if c.lower() in answer.get("text", "").lower()
            ]
            if not matched:
                continue
            rows.append(
                {
                    "pulled_at": now.isoformat(),
                    "contest": contest,
                    "question": market.get("question"),
                    "slug": market.get("slug"),
                    "candidate": matched[0],
                    "probability": float(answer.get("probability") or 0),
                    "liquidity": market.get("totalLiquidity"),
                }
            )
    frame = pd.DataFrame(rows)
    if not frame.empty:
        out_dir = config.SNAPSHOT_DIR / "manifold"
        out_dir.mkdir(parents=True, exist_ok=True)
        frame.to_csv(out_dir / f"{dt.date.today().isoformat()}.csv", index=False)
    else:
        log.warning("Manifold collector found no markets")
    return frame
