# dan0l v24 vs combined, full runs on seed 3590624429364033488, after re-runs

Both agents ran the full set (350 questions) on dan0l v24's own scored seed with the same
providers (deepinfra, parasail, akashml in that order, no fallbacks), concurrency 2, traced.
Questions a provider problem may have spoiled were then re-run and merged back in.

## What was re-run

- Flagged: a failed model call (429, proxy 429, timeout), a call cut at its token limit, a
  search pass skipped or cut for time, or no answer (tools/flag_failed_calls.py).
- The combined full run was cut short at 282 of 350: the 2 h poll limit ran out (dan0l took
  1 h 53, combined averages 50 s a question against 25 s). Its 277 graded answers were saved
  from the still-running scorer; partial entries equal final per-case rows (checked on dan0l:
  same scores, only twin post-pass notes differ). The 68 unreached questions were re-run.
- Re-run scorer: the practice scorer's own upstream revision (115ca38f) with a case filter; all
  waves and the tool prerequisite world are still seeded (tools/build_subset_scorer.py). The
  agents' tool-phase memory writes (dan0l 6, combined 5) are replayed after the first seed,
  matched by record text since ids are blinded per run. A kept tool case that runs after a
  mutation brings that case along; only the listed cases are merged.
- Merged scores are re-aggregated with the official AggregateForVersion (.cache/ditto-rescore),
  which reproduces dan0l's original report exactly (0.854746 and every gate).
- Round 1: dan0l 18 questions, combined 22 + 68 unreached. Round 2: the three that lost the
  point while hitting a provider problem again (practice/rerun_round2.sh).

## Result

| | dan0l v24 | combined |
|---|---|---|
| composite | 0.8649 (0.8547 before re-runs) | 0.8598 |
| tool | 0.8592 | 0.8692 |
| memory | 0.8807 | 0.8600 |
| tool efficiency | 0.9963 | 0.9963 |
| consistency | 1 (13 groups, 0 split) | 1 (13 groups, 0 split) |
| memory over-call | 0.9979 | 0.9981 |
| conversation | 1 | 1 |
| re-run cost | $0.05 + $0.01 | $0.16 + $0.01 |

Provider failures that had cost points: dan0l's timer and file-convert decoys (0 -> 1), its
absence-cross-user (1 -> 0 in round 1 under a 429, 1 in round 2), combined's
absence-false-premise (0 -> 1). combined's injection-classic stays 0 on a clean re-run.

Remaining noise: questions that still hit a provider problem but scored 1 were left as they
are. combined's enterprise-composed-program questions skip search passes for time in most
runs; that looks like its own budget, not the provider, and is for the inspection.

Merged runs: practice/20261026T021053Z_ditto-harness-dan0l-v24-trace_full_merged2,
practice/20261026T040314Z_ditto-harness-combined-trace_full_merged2; comparison in
practice/compare-full (summary, twins, gates, cases).
