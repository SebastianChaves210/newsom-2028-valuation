"""GDELT news collector (Tier 3 - media attention & tone).

GDELT monitors worldwide news media in near-real-time, keyless.  For each
tracked candidate we pull two daily series:

  * volume  - share of all monitored articles mentioning the candidate
  * tone    - average tone of that coverage (negative = hostile coverage)

Like all Tier 3 signals these are FIREWALLED from fair value: media tone
27 months out measures news cycles, not electability.  They exist to
(a) contextualize price moves on the dashboard and (b) accumulate the
dataset for the planned lead-lag study (does tone move before price?),
which is the only route by which sentiment could ever earn its way into
the model - see notebooks/README.md.

GDELT enforces ~1 request / 5 seconds per IP, so requests are serialized.
"""

from __future__ import annotations

import datetime as dt
import logging
import time

import pandas as pd
import requests

from newsom2028 import config

log = logging.getLogger(__name__)

API = "https://api.gdeltproject.org/api/v2/doc/doc"
HEADERS = {"User-Agent": "newsom2028-research (public research project)"}
RATE_SLEEP = 7  # seconds between requests (GDELT limit: 1 per 5s)
RETRY_SLEEP = 30  # backoff after a 429 before the single retry
# GDELT unit quirk: "6months" and "6m" are both misparsed (m = minutes).
# Weeks are unambiguous: 26w ~ 6 months, returned at daily resolution.
TIMESPAN = "26w"


def _timeline(query: str, mode: str) -> pd.DataFrame:
    for attempt in (1, 2):
        resp = requests.get(
            API,
            params={"query": f'"{query}"', "mode": mode, "timespan": TIMESPAN,
                    "format": "json"},
            headers=HEADERS,
            timeout=60,
        )
        if resp.status_code == 429 and attempt == 1:
            time.sleep(RETRY_SLEEP)
            continue
        break
    resp.raise_for_status()
    payload = resp.json()  # non-JSON (rate-limit text) raises ValueError
    series = payload.get("timeline", [])
    if not series:
        return pd.DataFrame(columns=["date", "value"])
    frame = pd.DataFrame(series[0]["data"])
    frame["date"] = pd.to_datetime(frame["date"], utc=True).dt.date
    # sub-daily resolutions are collapsed to daily means
    return frame.groupby("date", as_index=False)["value"].mean()


def collect(candidates: list[str] | None = None) -> pd.DataFrame:
    candidates = candidates or list(config.WIKIPEDIA_PAGES)
    rows = []
    for candidate in candidates:
        for mode, column in (("timelinevol", "volume"), ("timelinetone", "tone")):
            try:
                frame = _timeline(candidate, mode)
            except Exception as exc:  # noqa: BLE001 - collector must not die
                log.warning("GDELT %s/%s failed: %s", candidate, mode, exc)
                time.sleep(RATE_SLEEP)
                continue
            frame["candidate"] = candidate
            frame["metric"] = column
            rows.append(frame)
            time.sleep(RATE_SLEEP)
    if not rows:
        return pd.DataFrame()
    out = (
        pd.concat(rows, ignore_index=True)
        .pivot_table(index=["date", "candidate"], columns="metric", values="value")
        .reset_index()
    )
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(config.PROCESSED_DIR / "gdelt.csv", index=False)
    return out


def latest_summary(days: int = 30) -> list[dict]:
    """Per-candidate mean tone/volume over the trailing window, for reports."""
    path = config.PROCESSED_DIR / "gdelt.csv"
    if not path.exists():
        return []
    frame = pd.read_csv(path, parse_dates=["date"])
    cutoff = frame["date"].max() - pd.Timedelta(days=days)
    recent = frame[frame["date"] >= cutoff]
    out = []
    for candidate, group in recent.groupby("candidate"):
        out.append(
            {
                "candidate": candidate,
                "avg_tone": round(float(group["tone"].mean()), 2)
                if "tone" in group else None,
                "avg_volume": round(float(group["volume"].mean()), 4)
                if "volume" in group else None,
            }
        )
    return sorted(out, key=lambda r: -(r["avg_volume"] or 0))
