"""Static Plotly dashboard, regenerated on every pipeline run.

Output: dashboard/index.html — fully self-contained (plotly.js inlined), so
it renders from a file:// open, a GitHub Pages deploy, or any static host.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from newsom2028 import config

LAYOUT = dict(
    template="plotly_white",
    font=dict(family="Georgia, serif", size=13),
    margin=dict(l=60, r=30, t=60, b=50),
    height=420,
)

CANDIDATE_COLORS = {
    "Gavin Newsom": "#1f6feb",
    "Alexandria Ocasio-Cortez": "#8250df",
    "Jon Ossoff": "#1a7f37",
    "Kamala Harris": "#9a6700",
    "Pete Buttigieg": "#cf222e",
    "JD Vance": "#57606a",
}


def _fig_price_history() -> go.Figure | None:
    path = config.PROCESSED_DIR / "price_history.csv"
    if not path.exists():
        return None
    hist = pd.read_csv(path)
    hist = hist[hist["event_slug"] == "democratic-presidential-nominee-2028"]
    fig = go.Figure()
    for candidate, group in hist.groupby("candidate"):
        fig.add_trace(
            go.Scatter(
                x=group["date"], y=100 * group["price"], mode="lines",
                name=candidate,
                line=dict(
                    color=CANDIDATE_COLORS.get(candidate),
                    width=3 if candidate == config.SUBJECT else 1.4,
                ),
            )
        )
    fig.update_layout(
        title="Democratic nominee 2028 — Polymarket price history",
        yaxis_title="YES price (¢)", **LAYOUT,
    )
    return fig


def _fig_fair_vs_market(record: dict) -> go.Figure:
    s = record["summary"]
    rows = [
        ("Nomination", record["prices"]["nominee"], s["nominee"]),
        ("Presidency", record["prices"]["president"], s["president"]),
    ]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=[r[0] for r in rows], y=[100 * r[1] for r in rows],
            name="Market price", marker_color="#57606a", width=0.35,
        )
    )
    fig.add_trace(
        go.Bar(
            x=[r[0] for r in rows], y=[100 * r[2]["median"] for r in rows],
            name="Model fair value (median)", marker_color="#1f6feb", width=0.35,
            error_y=dict(
                type="data", symmetric=False,
                array=[100 * (r[2]["p90"] - r[2]["median"]) for r in rows],
                arrayminus=[100 * (r[2]["median"] - r[2]["p10"]) for r in rows],
            ),
        )
    )
    fig.update_layout(
        title="Model fair value vs market price (bars: median, whiskers: 80% CI)",
        yaxis_title="Probability (%)", barmode="group", **LAYOUT,
    )
    return fig


def _fig_posteriors() -> go.Figure | None:
    path = config.PROCESSED_DIR / "posterior_draws.npz"
    if not path.exists():
        return None
    draws = np.load(path)
    fig = go.Figure()
    for key, color in [
        ("nominee", "#1f6feb"), ("conditional", "#1a7f37"), ("president", "#cf222e"),
    ]:
        fig.add_trace(
            go.Histogram(
                x=100 * draws[key], name=f"P({key})", opacity=0.55,
                marker_color=color, nbinsx=80, histnorm="probability",
            )
        )
    fig.update_layout(
        title="Posterior distributions (ensemble Monte Carlo)",
        xaxis_title="Probability (%)", yaxis_title="Density",
        barmode="overlay", **LAYOUT,
    )
    return fig


def _fig_conditionals(record: dict) -> go.Figure:
    rows = record["implied_conditionals"]
    fig = go.Figure(
        go.Bar(
            x=[r["candidate"] for r in rows],
            y=[100 * r["implied_conditional"] for r in rows],
            marker_color=[
                "#1f6feb" if r["candidate"] == config.SUBJECT else "#8b949e"
                for r in rows
            ],
        )
    )
    fig.add_hline(y=50, line_dash="dot", line_color="#cf222e",
                  annotation_text="coin flip")
    fig.update_layout(
        title="Market-implied P(wins general | nominated) — the conditional anomaly",
        yaxis_title="Implied conditional (%)", **LAYOUT,
    )
    return fig


def _fig_verdict_history() -> go.Figure | None:
    path = config.PROCESSED_DIR / "verdict_history.csv"
    if not path.exists():
        return None
    hist = pd.read_csv(path)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist["as_of"], y=100 * hist["nominee_price"], name="Market price (nominee)",
        mode="lines+markers", line=dict(color="#57606a"),
    ))
    fig.add_trace(go.Scatter(
        x=hist["as_of"], y=100 * hist["nominee_fair_median"],
        name="Model fair value (nominee)", mode="lines+markers",
        line=dict(color="#1f6feb"),
    ))
    fig.add_trace(go.Scatter(
        x=pd.concat([hist["as_of"], hist["as_of"][::-1]]),
        y=pd.concat([100 * hist["nominee_fair_p90"], 100 * hist["nominee_fair_p10"][::-1]]),
        fill="toself", fillcolor="rgba(31,111,235,0.12)",
        line=dict(width=0), name="80% CI", showlegend=True,
    ))
    fig.update_layout(
        title="Model vs market through time (nomination contract)",
        yaxis_title="Probability (%)", **LAYOUT,
    )
    return fig


def _fig_attention() -> go.Figure | None:
    path = config.PROCESSED_DIR / "wikipedia_views.csv"
    if not path.exists():
        return None
    views = pd.read_csv(path)
    views["views_7d"] = views.groupby("candidate")["views"].transform(
        lambda s: s.rolling(7, min_periods=1).mean()
    )
    fig = go.Figure()
    for candidate, group in views.groupby("candidate"):
        fig.add_trace(go.Scatter(
            x=group["date"], y=group["views_7d"], mode="lines", name=candidate,
            line=dict(color=CANDIDATE_COLORS.get(candidate),
                      width=3 if candidate == config.SUBJECT else 1.2),
        ))
    fig.update_layout(
        title="Attention proxy: Wikipedia pageviews, 7-day average "
              "(Tier 3 — excluded from fair value)",
        yaxis_title="Daily views", **LAYOUT,
    )
    return fig


def build(record: dict) -> None:
    nom = record["contracts"]["nominee"]
    pres = record["contracts"]["president"]
    verdict_color = {"BUY": "#1a7f37", "SPECULATIVE VALUE": "#9a6700",
                     "FAIR": "#57606a", "OVERVALUED": "#cf222e"}

    header = f"""
    <div style="font-family: Georgia, serif; max-width: 1100px; margin: 2rem auto 0;">
      <h1 style="margin-bottom:0.2rem;">Newsom 2028 — quantitative valuation</h1>
      <p style="color:#57606a; margin-top:0;">As of {record['as_of']} ·
         auto-generated · methodology and limitations in the
         <a href="https://github.com/">repository docs</a></p>
      <div style="display:flex; gap:1rem; flex-wrap:wrap; margin:1rem 0 1.5rem;">
        <div style="border:1px solid #d0d7de; border-radius:8px; padding:1rem 1.4rem;">
          <div style="color:#57606a; font-size:0.85rem;">NOMINATION ({100*nom['market_price']:.1f}¢)</div>
          <div style="font-size:1.6rem; font-weight:bold; color:{verdict_color.get(nom['verdict'], '#000')};">{nom['verdict']}</div>
          <div style="font-size:0.9rem;">fair {100*nom['fair_median']:.1f}¢ ({100*nom['fair_p10']:.1f}–{100*nom['fair_p90']:.1f})</div>
        </div>
        <div style="border:1px solid #d0d7de; border-radius:8px; padding:1rem 1.4rem;">
          <div style="color:#57606a; font-size:0.85rem;">PRESIDENCY ({100*pres['market_price']:.1f}¢)</div>
          <div style="font-size:1.6rem; font-weight:bold; color:{verdict_color.get(pres['verdict'], '#000')};">{pres['verdict']}</div>
          <div style="font-size:0.9rem;">fair {100*pres['fair_median']:.1f}¢ ({100*pres['fair_p10']:.1f}–{100*pres['fair_p90']:.1f})</div>
        </div>
      </div>
    </div>
    """

    figures = [
        _fig_fair_vs_market(record),
        _fig_price_history(),
        _fig_posteriors(),
        _fig_conditionals(record),
        _fig_verdict_history(),
        _fig_attention(),
    ]
    parts = [header]
    first = True
    for fig in figures:
        if fig is None:
            continue
        parts.append(
            f'<div style="max-width:1100px; margin:0 auto;">'
            + fig.to_html(
                full_html=False,
                include_plotlyjs="inline" if first else False,
            )
            + "</div>"
        )
        first = False

    config.DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    html = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>Newsom 2028 Valuation</title></head><body>"
        + "".join(parts)
        + "</body></html>"
    )
    (config.DASHBOARD_DIR / "index.html").write_text(html)
