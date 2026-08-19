"""Metaculus collector (Tier 1 - forecaster-crowd consensus). TOKEN-GATED.

Metaculus is a reputation-based forecasting community whose aggregate has a
strong published calibration record.  Its API now requires authentication:
set the ``METACULUS_TOKEN`` environment variable (free account -> API token)
locally or as a GitHub Actions secret.  Without a token the collector logs
one line and returns empty - the pipeline is unaffected.
"""

from __future__ import annotations

import datetime as dt
import logging
import os

import pandas as pd
import requests

from newsom2028 import config

log = logging.getLogger(__name__)

API = "https://www.metaculus.com/api/posts/"
SEARCHES = ["2028 democratic presidential nominee", "2028 presidential election winner"]
TIMEOUT = 30


def _latest_probabilities(post: dict) -> dict[str, float]:
    """Best-effort extraction of community probabilities per option."""
    question = post.get("question") or {}
    options = question.get("options") or []
    agg = (
        (question.get("aggregations") or {})
        .get("recency_weighted", {})
        .get("latest", {})
    )
    values = agg.get("forecast_values") or []
    if options and values and len(options) == len(values):
        return {str(o): float(v) for o, v in zip(options, values)}
    return {}


def collect() -> pd.DataFrame:
    token = os.environ.get("METACULUS_TOKEN")
    if not token:
        log.info("METACULUS_TOKEN not set; skipping Metaculus (see docs/DATA_SOURCES.md)")
        return pd.DataFrame()

    now = dt.datetime.now(dt.timezone.utc)
    headers = {
        "Authorization": f"Token {token}",
        "User-Agent": "newsom2028-research (public research project)",
    }
    rows = []
    for term in SEARCHES:
        try:
            resp = requests.get(
                API, params={"search": term, "limit": 10}, headers=headers,
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            posts = resp.json().get("results", [])
        except Exception as exc:  # noqa: BLE001
            log.warning("Metaculus search '%s' failed: %s", term, exc)
            continue
        for post in posts:
            for option, prob in _latest_probabilities(post).items():
                matched = [
                    c for c in config.TRACKED_CANDIDATES if c.lower() in option.lower()
                ]
                if not matched:
                    continue
                rows.append(
                    {
                        "pulled_at": now.isoformat(),
                        "question": post.get("title"),
                        "candidate": matched[0],
                        "probability": prob,
                    }
                )
    frame = pd.DataFrame(rows).drop_duplicates(subset=["question", "candidate"])
    if not frame.empty:
        out_dir = config.SNAPSHOT_DIR / "metaculus"
        out_dir.mkdir(parents=True, exist_ok=True)
        frame.to_csv(out_dir / f"{dt.date.today().isoformat()}.csv", index=False)
    return frame
