# Data sources

## Live collectors (append-only snapshots under `data/snapshots/`)

| Source | Endpoint | Cadence | Tier | Notes |
|---|---|---|---|---|
| Polymarket | `gamma-api.polymarket.com/events`, `clob.polymarket.com/prices-history` | daily (Actions) | 1 | current prices, volume, liquidity for 4 tracked events; full daily price history per tracked contract; keyless |
| Kalshi | `api.elections.kalshi.com/trade-api/v2/markets` | daily | 1 | cross-venue consistency check (series `KXPRESNOMD`, `KXPRESNOMR`, ...); keyless |
| 2028 Dem primary polling | Wikipedia nationwide-polling page (structured tables) | daily | 1 | pollster-level rows; used only to establish Newsom's early rank |
| FRED | `fred.stlouisfed.org/graph/fredgraph.csv` | daily | 2 | DGS2 (carry), UNRATE, UMCSENT; keyless |
| Wikipedia pageviews | `wikimedia.org/api/rest_v1/metrics/pageviews` | daily | 3 | attention proxy; dashboard only, firewalled from fair value |

All collectors degrade gracefully (a failed source logs a warning and the pipeline
continues on the last good snapshot).

## Hand-curated reference panels (`data/reference/`)

### `nomination_contests.csv`

Every open (non-incumbent) major-party presidential nomination contest 1972–2024, top
candidacies per contest. Coding rules:

- **Scope.** Post-McGovern–Fraser reform cycles only; contests with a sitting president
  seeking re-nomination excluded (different process). 2024 R included with Trump flagged
  quasi-incumbent (excluded from base rates by default).
- **`early_poll_rank`.** Approximate rank among candidates who ultimately ran, in national
  primary polling roughly 18–30 months before the first primary — the equivalent of
  "mid-2026" in each cycle. Sources: Gallup historical primary polling archives and the
  cycle-specific Wikipedia polling pages. Candidates absent from early polls (e.g. Trump
  pre-June-2015) are ranked at the bottom with a note. Precision is ±1 rank on several
  rows; the models therefore use rank only as a coarse cell selector (≤2) and a smooth
  kernel, never as an exact feature.
- **Non-runners excluded.** Poll leaders who never entered (Ted Kennedy '76, Mario Cuomo
  '92) are absent, which slightly *inflates* measured front-runner conversion rates —
  a bias that favors the thesis and is therefore acceptable to the skeptic's side of the
  ledger, noted here for honesty.
- **Flags.** `sitting_governor`, `former_governor`, `sitting_vp`, `prior_nominee`,
  `prior_run` at time of candidacy; `won_nomination`, `won_general` outcomes.

### `open_seat_generals.csv`

Post-WWII general elections with no incumbent on the ballot (1952, 1960, 1968, 1988,
2000, 2008, 2016, 2024-flagged). `out_party_won` = 1 when the non-White-House party won
the presidency (2000 counted as an out-party win via the Electoral College; noted).

## Deliberately excluded (and why)

- **X/Twitter, Reddit, YouTube, podcast sentiment** — API access is paywalled or
  unstable, and no credible evidence links 27-months-out social sentiment to nomination
  probability. The architecture leaves a Tier 3 slot if that changes.
- **Google Trends** — no stable public API (pytrends is unmaintained and rate-limited);
  Wikipedia pageviews serve the same attention-proxy role more reliably.
- **Campaign finance (FEC)** — no 2028 presidential committees exist yet; the collector
  slot is planned for when filings begin (money primary is a genuine Tier 1 signal
  *once it exists*).
- **Newsom approval ratings** — deferred: scraping state approval series reliably is
  error-prone, and the conditional leg encodes the qualitative stance (slightly negative
  national favorability) as a wide prior instead of falsely precise point data.
