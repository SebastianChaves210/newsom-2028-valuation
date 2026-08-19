"""Phase-2 modules: endorsements weighting, venue consensus, GDELT summary."""

import pandas as pd

from newsom2028 import config, endorsements, venues
from newsom2028.collectors import gdelt


def test_endorsement_weights_538():
    assert endorsements.WEIGHTS == {"governor": 10, "senator": 5, "representative": 1}


def test_endorsement_points(tmp_path, monkeypatch):
    ref = tmp_path / "reference"
    ref.mkdir()
    (ref / "endorsements.csv").write_text(
        "date,endorser,office,state,candidate,source_url\n"
        "2027-01-01,A,governor,PA,Gavin Newsom,http://x\n"
        "2027-01-02,B,senator,GA,Gavin Newsom,http://x\n"
        "2027-01-03,C,representative,CA,Jon Ossoff,http://x\n"
        "2027-01-04,D,mayor,TX,Jon Ossoff,http://x\n"  # unweighted office
    )
    monkeypatch.setattr(config, "REFERENCE_DIR", ref)
    table = endorsements.points()
    assert table[0] == {"candidate": "Gavin Newsom", "points": 15, "endorsements": 2}
    assert table[1]["points"] == 1  # mayor contributes 0


def test_endorsements_empty_by_default():
    # the committed file is armed but empty (no declared candidates yet)
    assert endorsements.points() == []


def test_venue_comparison_merge(monkeypatch):
    def fake_snapshot(source):
        if source == "polymarket":
            return pd.DataFrame(
                {
                    "event_slug": ["democratic-presidential-nominee-2028"] * 2,
                    "candidate": ["Gavin Newsom", "Jon Ossoff"],
                    "yes_price": [0.16, 0.14],
                }
            )
        if source == "manifold":
            return pd.DataFrame(
                {
                    "contest": ["dem_nominee"] * 2,
                    "candidate": ["Gavin Newsom", "Jon Ossoff"],
                    "probability": [0.19, 0.13],
                }
            )
        return pd.DataFrame()

    monkeypatch.setattr(venues, "_latest_snapshot", fake_snapshot)
    table = venues.dem_nominee_comparison()
    newsom = next(r for r in table if r["candidate"] == "Gavin Newsom")
    assert newsom["polymarket"] == 0.16
    assert newsom["manifold"] == 0.19
    assert abs(newsom["spread"] - 0.03) < 1e-9


def test_gdelt_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROCESSED_DIR", tmp_path)
    pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-08-01", "2026-08-02"] * 2),
            "candidate": ["Gavin Newsom"] * 2 + ["JD Vance"] * 2,
            "volume": [0.2, 0.4, 0.6, 0.8],
            "tone": [-2.0, -4.0, 1.0, 3.0],
        }
    ).to_csv(tmp_path / "gdelt.csv", index=False)
    summary = gdelt.latest_summary(days=30)
    assert summary[0]["candidate"] == "JD Vance"  # higher volume sorts first
    assert summary[0]["avg_tone"] == 2.0
    assert summary[1] == {"candidate": "Gavin Newsom", "avg_tone": -3.0, "avg_volume": 0.3}
