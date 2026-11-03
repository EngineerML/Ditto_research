# 2026-11-03 — horizon v8 (drp23v15) live misses, first two runs

Agent 31ad3a16, bench 15. Runs: seed 2190058953981709433 → 0.9395, seed 6007065558233246269 → 0.9329. Status
`below_score_floor` (dashboard "Low-priority completion"): the better of two scores is under the fifth-place floor
0.9402 (nanodevs v10, after DrPresident v29 entered at 0.954), so the third run is queued at low priority.
Free analysis only: public `provisional_scores[].case_results`, regenerated datasets, our mock and paid traces.
Data: `live/2026-11-03/compare/` (pipelines of the top agents), `live/2026-11-03/horizon_v8_telemetry/` (timings
only, no transcript text).

## Lost points per run (1 tool point ≈ 0.005 composite, 1 memory point ≈ 0.002)

| | v8 | DrP v23 @15 | Orsentra v21 | DrP v29 | dan0l v35 | nanodevs v10 |
|---|---|---|---|---|---|---|
| tool | 3.46 | 5.22 | 1.48 | 1.33 | 1.13 | 2.30 |
| memory | 17.50 | 15.50 | 10.50 | 16.67 | 18.83 | 18.11 |

- Every agent loses about 8 memory points a run on parser-divergence (reported speech, negation, retraction: about 2
  each) and conversational-chitchat (3 × 0.5). Orsentra too. Not a lever.
- v8 above the others: absence-near-miss 2.5 a run (DrP v23 0.33), record-quantity-cf-base 1.75 (0.33),
  cf-variant 0.75 (0), world-story-next-action 1.0 (0.33). The same code (DrP v23) with the same routing as ours
  (bench 14, no connectors) lost 0.5 of 18 cf-base and 0 of 18 cf-variant, so these read as seed variance over two
  runs, not the step. DrP v23's own bench-15 runs spread 0.897 to 0.960.
- Tool misses are single cases: decoy_issue_create (1 of 2 each run; no other top agent misses it), decoy_timer_start,
  discovery_accent_set, v13_mutation_follow_up_read, v10_state_dependent_routing. parallel_web_image missed in both
  runs with extra calls (1 and 4), which also pulls tool efficiency (0.9967, 0.9852); DrP v23 scored 1.0 on it.

## Checks on the connector step

- Regenerated both live seeds (`.cache/dittobench-generate-v15`, built from datagen afe95eec; surface salt 0, so the
  text is not the platform's exact bytes): the step leaves out 200 of 235 tools, and no tool case's expected tool is
  among them.
- Mock runs, plain v23 @15 vs drp23v15 @15, three seeds: 10 records/action moves per seed, nearly all record-quantity
  questions ("What is currently owed on X's account?") that plain v23 sends to the action lane. The missed tool
  categories take the same lane in both builds.

## Reading

No v8-specific defect shows in the public data. The gap to fifth place (~0.004) is within one seed's spread. The
realistic route to the top five is a stronger released base (DrPresident v29, 0.954, embargoed) with the same step.
