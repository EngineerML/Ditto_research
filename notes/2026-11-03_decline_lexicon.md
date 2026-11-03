# 2026-11-03 — decline phrases in answerable replies: measured, no change made

Grader rule (`grade/v13.go:104`): on an answerable kind, the Abstain flag or any phrase of the decline lexicon
(`declinePhrases` + `declineV13EN`, about 70 entries: "there is no", "no record", "don't have", "not available",
"was never", …) anywhere in the slot or the reply scores 0, noted "abstained on an answerable question".

## Measured (`practice/gates/decline_hits.py`, every local real-model full run: 15 runs, benches 13–15)

- 30 answerable cases zeroed this way, 2.0 per run. Only 2 of the 30 had the expected value in the reply; the rest are
  wrong declines (the model said it had no record when the value was there), not a stray phrase beside a right
  answer. Largest group: absence-twin-stale-removed (11), then story owner-current (5, "it was canceled, so no one").
- Nearly all of those come from older builds (dan0l- and v5-era). On v8's own runs (3 live + seed 5119): 3 such zeros
  in 4 runs, one of them parser-divergence (structural), two absence-twin-false-premise.
- v8 on the abstention families and their twins, 4 runs: false-premise 15/16, twin 15/16, stale-removed 16/16, twin
  16/16, insufficient-composition 16/16, twin 15/16, point-in-time trip-leg 16/16. DrPresident's handle, balance and
  place-days hints (qtype.py) already route these well; the place-days hint carries both branches (decline when the
  place is not on the trip, days otherwise) and the model took the wrong one once in 16.

## Decision

No change. Stripping decline sentences in the host would recover about 0.1 case a run and edits the model's reply
(I3/I4 exposure). Rewording the place-days hint could gain at most about 0.25 case a run (0.0005 composite) against a
15/16 balance on both sides, too small to see in any affordable A/B.
