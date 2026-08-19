"""Polymarket collector (Tier 1).

Two products:
  1. A dated snapshot of current YES prices, volume and liquidity for every
     market in the tracked events (data/snapshots/polymarket/).
  2. Daily price history per tracked contract from the CLOB
     ``prices-history`` endpoint (data/processed/price_history.csv), which
     backfills the full life of each contract on every run.

Both APIs are public and keyless.
"""

from __future__ import annotations

import datetime as dt
import json
import logging

import pandas as pd
import requests

from newsom2028 import config

log = logging.getLogger(__name__)

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
TIMEOUT = 30


def _get(url: str, **params) -> list | dict:
    resp = requests.get(url, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def fetch_event_markets() -> pd.DataFrame:
    """Current state of every market in the tracked events."""
    rows = []
    now = dt.datetime.now(dt.timezone.utc)
    for slug in config.POLYMARKET_EVENT_SLUGS:
        try:
            events = _get(f"{GAMMA}/events", slug=slug)
        except Exception as exc:  # noqa: BLE001 - collector must not die
            log.warning("Polymarket event %s failed: %s", slug, exc)
            continue
        for event in events:
            for market in event.get("markets", []):
                prices = json.loads(market.get("outcomePrices") or "[]")
                tokens = json.loads(market.get("clobTokenIds") or "[]")
                if not prices:
                    continue
                rows.append(
                    {
                        "pulled_at": now.isoformat(),
                        "event_slug": slug,
                        "question": market.get("question"),
                        "candidate": market.get("groupItemTitle") or "",
                        "yes_price": float(prices[0]),
                        "volume": float(market.get("volumeNum") or 0),
                        "liquidity": float(market.get("liquidityNum") or 0),
                        "yes_token_id": tokens[0] if tokens else None,
                        "end_date": market.get("endDate"),
                    }
                )
    return pd.DataFrame(rows)


def fetch_price_history(token_id: str) -> pd.DataFrame:
    """Full daily price history for one CLOB token."""
    data = _get(
        f"{CLOB}/prices-history", market=token_id, interval="max", fidelity=1440
    )
    hist = data.get("history", [])
    if not hist:
        return pd.DataFrame(columns=["date", "price"])
    frame = pd.DataFrame(hist)
    frame["date"] = pd.to_datetime(frame["t"], unit="s", utc=True).dt.date
    frame = frame.rename(columns={"p": "price"})[["date", "price"]]
    return frame.groupby("date", as_index=False).last()


def collect() -> pd.DataFrame:
    """Run the full Polymarket collection; returns the current snapshot."""
    snapshot = fetch_event_markets()
    if snapshot.empty:
        log.warning("Polymarket snapshot came back empty")
        return snapshot

    out_dir = config.SNAPSHOT_DIR / "polymarket"
    out_dir.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat()
    snapshot.to_csv(out_dir / f"{today}.csv", index=False)

    # Price history for tracked candidates in the two primary events.
    tracked = snapshot[
        snapshot["candidate"].isin(config.TRACKED_CANDIDATES)
        & snapshot["event_slug"].isin(config.POLYMARKET_EVENT_SLUGS[:3])
        & snapshot["yes_token_id"].notna()
    ]
    histories = []
    for _, row in tracked.iterrows():
        try:
            hist = fetch_price_history(row["yes_token_id"])
        except Exception as exc:  # noqa: BLE001
            log.warning("history failed for %s: %s", row["question"], exc)
            continue
        hist["candidate"] = row["candidate"]
        hist["event_slug"] = row["event_slug"]
        histories.append(hist)
    if histories:
        history = pd.concat(histories, ignore_index=True)
        config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        history.to_csv(config.PROCESSED_DIR / "price_history.csv", index=False)
    return snapshot
