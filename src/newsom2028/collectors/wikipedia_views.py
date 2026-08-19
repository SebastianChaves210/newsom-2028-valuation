"""Wikipedia pageview collector (Tier 3 - attention proxy ONLY).

Pageviews measure attention, not electoral strength; at a 27-month horizon
attention spikes are dominated by news cycles.  This feed powers the momentum
panel of the dashboard and is deliberately excluded from fair-value models.
"""

from __future__ import annotations

import datetime as dt
import logging

import pandas as pd
import requests

from newsom2028 import config

log = logging.getLogger(__name__)

API = (
    "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
    "en.wikipedia/all-access/user/{page}/daily/{start}/{end}"
)
HEADERS = {"User-Agent": "newsom2028-research/0.1 (public research project)"}


def collect(days: int = 365) -> pd.DataFrame:
    end = dt.date.today() - dt.timedelta(days=1)
    start = end - dt.timedelta(days=days)
    rows = []
    for candidate, page in config.WIKIPEDIA_PAGES.items():
        url = API.format(
            page=page, start=start.strftime("%Y%m%d"), end=end.strftime("%Y%m%d")
        )
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            for item in resp.json().get("items", []):
                rows.append(
                    {
                        "date": dt.datetime.strptime(
                            item["timestamp"][:8], "%Y%m%d"
                        ).date(),
                        "candidate": candidate,
                        "views": item["views"],
                    }
                )
        except Exception as exc:  # noqa: BLE001
            log.warning("pageviews failed for %s: %s", candidate, exc)
    frame = pd.DataFrame(rows)
    if not frame.empty:
        config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        frame.to_csv(config.PROCESSED_DIR / "wikipedia_views.csv", index=False)
    return frame
