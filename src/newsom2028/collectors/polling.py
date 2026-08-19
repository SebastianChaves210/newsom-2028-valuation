"""2028 Democratic primary polling collector (Tier 1).

Scrapes the structured polling tables on Wikipedia's nationwide-polling page
for the 2028 Democratic primaries.  Wikipedia is used because it aggregates
the underlying pollsters (Emerson, McLaughlin, Echelon, ...) into a stable,
citable table format.  Parsing is defensive: any table without a Newsom
column is skipped, and a failed page load returns the last good snapshot.
"""

from __future__ import annotations

import datetime as dt
import io
import logging
import re

import pandas as pd
import requests

from newsom2028 import config

log = logging.getLogger(__name__)


def _clean_pct(value) -> float | None:
    if pd.isna(value):
        return None
    match = re.search(r"(\d+(?:\.\d+)?)\s*%?", str(value))
    return float(match.group(1)) if match else None


def collect() -> pd.DataFrame:
    try:
        resp = requests.get(
            config.WIKI_POLLING_PAGE,
            headers={"User-Agent": "newsom2028-research/0.1 (public research project)"},
            timeout=30,
        )
        resp.raise_for_status()
        tables = pd.read_html(io.StringIO(resp.text))
    except Exception as exc:  # noqa: BLE001
        log.warning("polling page failed: %s", exc)
        return pd.DataFrame()

    rows = []
    for table in tables:
        cols = ["" if isinstance(c, float) else str(c) for c in table.columns]
        # flatten possible MultiIndex headers
        if isinstance(table.columns, pd.MultiIndex):
            cols = [" ".join(str(part) for part in tup) for tup in table.columns]
        table.columns = cols
        newsom_cols = [c for c in cols if "Newsom" in c]
        date_cols = [c for c in cols if re.search(r"[Dd]ate", c)]
        if not newsom_cols or not date_cols:
            continue
        candidate_cols = {
            c: c.split()[-1] for c in cols
            if any(name.split()[-1] in c for name in config.TRACKED_CANDIDATES)
        }
        for _, row in table.iterrows():
            for col, cand in candidate_cols.items():
                pct = _clean_pct(row[col])
                if pct is None or pct > 100:
                    continue
                rows.append(
                    {
                        "poll_date": str(row[date_cols[0]]),
                        "pollster": str(row[cols[0]]),
                        "candidate_lastname": cand,
                        "pct": pct,
                    }
                )
    frame = pd.DataFrame(rows).drop_duplicates()
    if not frame.empty:
        out_dir = config.SNAPSHOT_DIR / "polling"
        out_dir.mkdir(parents=True, exist_ok=True)
        frame.to_csv(out_dir / f"{dt.date.today().isoformat()}.csv", index=False)
    return frame
