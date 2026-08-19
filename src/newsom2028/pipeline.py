"""End-to-end pipeline: collect -> model -> value -> report -> dashboard.

Run via ``newsom2028 run`` (or ``newsom2028 model`` to re-model from the
latest snapshots without hitting any network source).  Every run appends one
row to data/processed/verdict_history.csv so the model's fair value and the
market price form comparable time series across the life of the project.
"""

from __future__ import annotations

import datetime as dt
import json
import logging

import pandas as pd

from newsom2028 import config, endorsements, ev, venues
from newsom2028.collectors import (
    fredseries,
    gdelt,
    kalshi,
    manifold,
    metaculus,
    polling,
    polymarket,
    wikipedia_views,
)
from newsom2028.models import ensemble, market_structure

log = logging.getLogger(__name__)


def collect_all() -> dict[str, pd.DataFrame]:
    log.info("collecting Polymarket ...")
    poly = polymarket.collect()
    log.info("collecting Kalshi ...")
    kal = kalshi.collect()
    log.info("collecting polling ...")
    polls = polling.collect()
    log.info("collecting Wikipedia pageviews ...")
    views = wikipedia_views.collect()
    log.info("collecting FRED ...")
    fred = fredseries.collect()
    log.info("collecting Manifold ...")
    mani = manifold.collect()
    log.info("collecting Metaculus (token-gated) ...")
    meta = metaculus.collect()
    log.info("collecting GDELT (rate-limited, ~1 min) ...")
    news = gdelt.collect()
    return {"polymarket": poly, "kalshi": kal, "polling": polls,
            "views": views, "fred": fred, "manifold": mani,
            "metaculus": meta, "gdelt": news}


def latest_polymarket_snapshot() -> pd.DataFrame:
    snap_dir = config.SNAPSHOT_DIR / "polymarket"
    files = sorted(snap_dir.glob("*.csv"))
    if not files:
        raise FileNotFoundError("no Polymarket snapshot; run `newsom2028 collect` first")
    return pd.read_csv(files[-1])


def latest_polling_snapshot() -> pd.DataFrame:
    snap_dir = config.SNAPSHOT_DIR / "polling"
    files = sorted(snap_dir.glob("*.csv"))
    return pd.read_csv(files[-1]) if files else pd.DataFrame()


def newsom_prices(snapshot: pd.DataFrame) -> tuple[float, float]:
    nom = snapshot[
        (snapshot["event_slug"] == "democratic-presidential-nominee-2028")
        & (snapshot["candidate"] == config.SUBJECT)
    ]
    pres = snapshot[
        (snapshot["event_slug"] == "presidential-election-winner-2028")
        & (snapshot["candidate"] == config.SUBJECT)
    ]
    if nom.empty or pres.empty:
        raise ValueError("Newsom contracts missing from Polymarket snapshot")
    return float(nom.iloc[0]["yes_price"]), float(pres.iloc[0]["yes_price"])


def polling_rank(polls: pd.DataFrame) -> tuple[int, pd.Series | None]:
    """Newsom's rank by mean share across scraped 2028 primary polls."""
    if polls.empty:
        return 2, None
    means = polls.groupby("candidate_lastname")["pct"].mean().sort_values(ascending=False)
    names = list(means.index)
    rank = names.index("Newsom") + 1 if "Newsom" in names else 2
    return rank, means


def run_models(as_of: dt.date | None = None) -> dict:
    as_of = as_of or dt.date.today()
    snapshot = latest_polymarket_snapshot()
    polls = latest_polling_snapshot()
    nominee_price, president_price = newsom_prices(snapshot)
    early_rank, poll_means = polling_rank(polls)

    result = ensemble.run(nominee_price, president_price, early_rank=early_rank)
    summary = result.summary()
    risk_free = fredseries.current_risk_free()

    contracts = {
        "nominee": ev.evaluate(
            "Democratic nomination", nominee_price, result.nominee_draws,
            config.NOMINEE_RESOLUTION, risk_free, config.ROUND_TRIP_COST,
            config.EDGE_RATIO, config.GATE_PERCENTILE, today=as_of,
        ),
        "president": ev.evaluate(
            "Presidency", president_price, result.president_draws,
            config.PRESIDENT_RESOLUTION, risk_free, config.ROUND_TRIP_COST,
            config.EDGE_RATIO, config.GATE_PERCENTILE, today=as_of,
        ),
    }
    scenarios = ev.exit_scenarios(
        nominee_price, contracts["nominee"].fair_median, risk_free,
        config.ROUND_TRIP_COST, today=as_of,
    )
    conditionals = market_structure.implied_conditionals(snapshot)

    # Downsampled posterior draws for the dashboard's distribution panels.
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    import numpy as np

    keep = slice(0, len(result.nominee_draws), max(1, len(result.nominee_draws) // 20_000))
    np.savez_compressed(
        config.PROCESSED_DIR / "posterior_draws.npz",
        nominee=result.nominee_draws[keep],
        conditional=result.conditional_draws[keep],
        president=result.president_draws[keep],
    )

    run_record = {
        "as_of": as_of.isoformat(),
        "prices": {"nominee": nominee_price, "president": president_price},
        "early_rank": early_rank,
        "poll_means": poll_means.to_dict() if poll_means is not None else {},
        "risk_free": risk_free,
        "summary": summary,
        "lanes": result.lane_summaries,
        "contracts": {k: vars(v) for k, v in contracts.items()},
        "scenarios": scenarios,
        "implied_conditionals": conditionals.to_dict("records"),
        "venues": venues.dem_nominee_comparison(),
        "gdelt": gdelt.latest_summary(),
        "endorsements": endorsements.points(),
        "gate": {
            "edge_ratio": config.EDGE_RATIO,
            "gate_percentile": config.GATE_PERCENTILE,
            "round_trip_cost": config.ROUND_TRIP_COST,
        },
    }
    _append_history(run_record)
    _write_json(run_record)
    return run_record


def _append_history(record: dict) -> None:
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    path = config.PROCESSED_DIR / "verdict_history.csv"
    row = pd.DataFrame(
        [
            {
                "as_of": record["as_of"],
                "nominee_price": record["prices"]["nominee"],
                "nominee_fair_median": record["summary"]["nominee"]["median"],
                "nominee_fair_p10": record["summary"]["nominee"]["p10"],
                "nominee_fair_p90": record["summary"]["nominee"]["p90"],
                "nominee_verdict": record["contracts"]["nominee"]["verdict"],
                "president_price": record["prices"]["president"],
                "president_fair_median": record["summary"]["president"]["median"],
                "president_fair_p10": record["summary"]["president"]["p10"],
                "president_fair_p90": record["summary"]["president"]["p90"],
                "president_verdict": record["contracts"]["president"]["verdict"],
            }
        ]
    )
    if path.exists():
        hist = pd.read_csv(path)
        hist = hist[hist["as_of"] != record["as_of"]]
        row = pd.concat([hist, row], ignore_index=True)
    row.to_csv(path, index=False)


def _write_json(record: dict) -> None:
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.PROCESSED_DIR / "latest_run.json", "w") as fh:
        json.dump(record, fh, indent=2, default=str)


def full_run() -> dict:
    collect_all()
    record = run_models()
    from newsom2028 import dashboard, report  # deferred: plotly import is slow

    report.write(record)
    dashboard.build(record)
    return record
