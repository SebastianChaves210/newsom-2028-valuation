# Notebooks

Exploratory analyses, one notebook per research question. Notebooks consume the same
snapshots and modules as the pipeline (`from newsom2028 import ...`) so results are
reproducible from committed data.

Planned / open research questions:

1. **Calibration re-estimation** — collect resolved Polymarket political contracts and
   re-fit the favorite-longshot parameters (a, b) instead of importing literature values.
   Highest-value improvement on the roadmap.
2. **Leave-one-cycle-out backtest** — run the analog lane as of each historical cycle and
   score its Brier/log loss against realized nominations.
3. **Conditional anomaly deep-dive** — can any fundamentals story justify the market
   implying AOC (66%) and Ossoff (71%) convert nominations far better than Newsom (51%)?
4. **Cross-venue arbitrage** — Polymarket vs Kalshi spreads on identical contracts over
   time.
