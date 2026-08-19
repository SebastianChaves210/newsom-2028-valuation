# Limitations

What this project cannot tell you, stated as plainly as possible.

## 1. The single-event problem (the big one)

The 2028 election happens once. No outcome can validate or refute this model: if Newsom
wins from 8¢, that is one draw from *some* distribution — not proof the true probability
was high; if he loses, likewise. Only the **method** is testable, against 1972–2024
history, and even there the sample is ~18 open contests. Anyone — including us — claiming
their 2028 model is "validated" is overstating what is knowable.

## 2. The historical panel is small and hand-coded

~95 candidacies across ~18 open contests. `early_poll_rank` is coded from Gallup-era and
contemporary polling archives at *approximately* the equivalent point in each cycle;
reasonable coders could differ by ±1 rank on several rows (see DATA_SOURCES.md for coding
rules). The Beta posteriors are wide partly because we refuse to pretend this panel is
bigger than it is.

## 3. Regime stability is assumed

Using 1972–2024 base rates for 2028 assumes the nomination process still works roughly the
same way. The 2016 cycle (both parties) is evidence that regimes shift. If the process has
structurally changed — media environment, small-dollar fundraising, calendar changes — the
outside view is miscalibrated in an unknown direction.

## 4. Leg dependence is simplified

We sample P(nominee) and P(general | nominee) with independent lane choices. In reality
the states of the world where Newsom wins the nomination easily may correlate with the
states where he is a strong general-election candidate (or the opposite — a bruising
primary). The market-implied conditional lane partially absorbs this, but the joint
distribution is a modeling simplification.

## 5. The calibration correction is imported, not estimated

The favorite-longshot parameters (b ≈ 1.15) come from published studies of *other*
political markets, mostly shorter-horizon. Polymarket 2026 may be better or worse
calibrated than the literature venues. Re-estimating calibration on resolved Polymarket
contracts is the highest-value future improvement (see roadmap).

## 6. Polling 27 months out is weakly informative

Early primary polling mostly measures name recognition. It enters only through the rank
used to select the base-rate cell and analog profile — never as a probability itself.
Note the market itself agrees: Harris leads 2026 polling means (27%) yet trades at 7.5¢.

## 7. No inside information, no candidate-specific news model

Health, scandal, a Harris re-entry decision, a viable third-party bid, calendar changes —
none are explicitly modeled; they live inside the (wide) intervals, not as named risks.

## 8. Attention data is decorative by design

Wikipedia pageviews (and any future social/search signals) are firewalled from fair value.
They are on the dashboard because attention *context* is useful for reading price moves,
not because they predict nominations.

## 9. Market frictions are simplified

A flat 1¢ round-trip cost approximates spread + slippage for retail size. Large positions
would move these books. USDC custody risk, platform risk over a 27-month hold, and
jurisdiction/legality of access are real and unmodeled.

## 10. One subject, fixed decomposition

The pipeline prices Newsom. The cross-candidate conditional table hints at relative-value
trades (e.g., the market pricing AOC's and Ossoff's conditionals far above Newsom's), but
pricing *those* properly would require rerunning the full ensemble per candidate — a
straightforward but not-yet-done extension.
