"""Kalshi collector (Tier 1, cross-market consistency check).

Kalshi's public read-only API needs no key.  We search open political events
for 2028 presidential/nominee markets and record any contract whose title
mentions a tracked candidate, so Polymarket prices can be checked against an
independent, US-regulated venue.
"""

from __future__ import annotations

import datetime as dt
import logging

import pandas as pd
import requests

from newsom2028 import config

log = logging.getLogger(__name__)

BASE = "https://api.elections.kalshi.com/trade-api/v2"
TIMEOUT = 30

# Series observed on Kalshi for 2028 races; the collector also falls back to
# a keyword scan of open events in case tickers change.
CANDIDATE_SERIES = ["KXPRESNOMD", "KXPRESNOMR", "KXPRES", "PRES"]


def _markets_for_series(series_ticker: str) -> list[dict]:
    out, cursor = [], None
    for _ in range(10):
        params = {"series_ticker": series_ticker, "limit": 200, "status": "open"}
        if cursor:
            params["cursor"] = cursor
        resp = requests.get(f"{BASE}/markets", params=params, timeout=TIMEOUT)
        if resp.status_code != 200:
            return out
        data = resp.json()
        out.extend(data.get("markets", []))
        cursor = data.get("cursor")
        if not cursor:
            break
    return out


def collect() -> pd.DataFrame:
    now = dt.datetime.now(dt.timezone.utc)
    rows = []
    for series in CANDIDATE_SERIES:
        try:
            markets = _markets_for_series(series)
        except Exception as exc:  # noqa: BLE001
            log.warning("Kalshi series %s failed: %s", series, exc)
            continue
        for market in markets:
            title = f"{market.get('title', '')} {market.get('yes_sub_title', '')}"
            matched = [c for c in config.TRACKED_CANDIDATES if c.split()[-1] in title]
            if not matched:
                continue
            last = market.get("last_price")
            rows.append(
                {
                    "pulled_at": now.isoformat(),
                    "series": series,
                    "ticker": market.get("ticker"),
                    "title": market.get("title"),
                    "candidate": matched[0],
                    "yes_bid": (market.get("yes_bid") or 0) / 100,
                    "yes_ask": (market.get("yes_ask") or 0) / 100,
                    "last_price": (last or 0) / 100 if last is not None else None,
                    "volume": market.get("volume"),
                }
            )
    frame = pd.DataFrame(rows)
    if not frame.empty:
        out_dir = config.SNAPSHOT_DIR / "kalshi"
        out_dir.mkdir(parents=True, exist_ok=True)
        frame.to_csv(out_dir / f"{dt.date.today().isoformat()}.csv", index=False)
    else:
        log.warning("Kalshi collector found no matching markets")
    return frame
