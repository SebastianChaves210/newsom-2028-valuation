"""FRED collector (Tier 2) via the keyless fredgraph.csv endpoint.

DGS2 (2-year Treasury yield) sets the carry cost in the EV engine; the other
series feed the fundamentals context panel.
"""

from __future__ import annotations

import datetime as dt
import io
import logging

import pandas as pd
import requests

from newsom2028 import config

log = logging.getLogger(__name__)

URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"


def collect() -> pd.DataFrame:
    frames = []
    for series_id in config.FRED_SERIES:
        try:
            resp = requests.get(URL, params={"id": series_id}, timeout=30)
            resp.raise_for_status()
            frame = pd.read_csv(io.StringIO(resp.text))
            date_col = frame.columns[0]
            frame = frame.rename(columns={date_col: "date", series_id: "value"})
            frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
            frame["series"] = series_id
            frames.append(frame.dropna())
        except Exception as exc:  # noqa: BLE001
            log.warning("FRED %s failed: %s", series_id, exc)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(config.PROCESSED_DIR / "fred.csv", index=False)
    return out


def current_risk_free() -> float:
    """Latest 2-year Treasury yield as a decimal, with a configured fallback."""
    path = config.PROCESSED_DIR / "fred.csv"
    if path.exists():
        frame = pd.read_csv(path)
        dgs2 = frame[frame["series"] == "DGS2"].dropna(subset=["value"])
        if not dgs2.empty:
            return float(dgs2.iloc[-1]["value"]) / 100
    return config.FALLBACK_RISK_FREE
