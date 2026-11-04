# 2026-11-04 — bench 16 (dueling): scoring, crown, incentive, first live runs

The rollout opened at about 04:10 UTC (Peyton, Discord). v15 keeps paying until the flip: each of the top 5 inherited
cohort positions needs a full 3-score v16 quorum, then the whole ledger switches at once. The switch isn't
retroactive and can be rolled back. Sources: repos/ditto-subnet at f220cecd
(`research/dittobench-datagen/docs/dueling-bench.md`, `docs/title-duels.md`, `docs/VALIDATOR.md` "Generator track",
`services/dittobench-api/internal/scoregates/priced_cost.go`) and the public API.

## A run

All 350 questions are v16; v15 runs (100 tool + 250 memory) continue in parallel until the flip.

| Half | Cases | Source | Graded by |
|---|---|---|---|
| Datagen | 175: 50 tool, 125 memory | official generator, seeded per run | v15 grader and gates |
| Generator slice | 175 memory, 5 columns × 35 | the season's top 5 generators, one per owner; public default fills gaps | each pack's declared policy (14–16, grades as 15) |

Unlike v15, v16 connectors carry no "Needs the X connector" marker, so `available.py` filters nothing. Each seed links
2–4 apps, and some cases need a linked one; others name an unlinked app, or an app where a product tool is right.

## The score

```
composite = gate × (0.5 × datagen + 0.1 × each counted column) × cost factor
datagen   = 0.5 × tool + 0.5 × memory          (datagen half only)
cost factor = 1 − 0.4 × (priced cost − $1), floor 0.6 at $2
```

- **Weights:** tool 25%, datagen memory 25%, generator columns 50% (10% each).
- **Masking:** an owner's own column is masked, and its 10% returns to the datagen half. The crown test masks both
  owners' columns.
- **Gates:** generator cases never reach a zeroing gate. Metamorphic splits are charged against 13 groups (#3388), so
  one split costs about 3.1%.
- **Priced cost:** the whole run, at locked gpt-oss-20b rates: $0.07/M prompt, $0.15/M completion, $0.004/M
  embeddings, $0.042/M Jev input.

## Seasons and the crown

- **Seasons:** one 4-epoch generator round, about 4.8 h. Everyone in a season faces the same 5 generators on their
  own seeds, and only same-season scores are compared. At each rotation the champion is retested first, then the
  cohort.
- **Title duel** (`docs/title-duels.md`, behind `crown_duel_mode`): each season the top 5 run 3 seeds shared with the
  king. Paired differences accumulate over the newest 15 pairs. A challenger is crowned only when n ≥ 3 and its mean
  lead > max(margin × decay, c(n) × se), with c(3) = 6.97 down to c(15) = 2.62.
  - A lead of about 0.03 wins within a day; under about 0.015 almost never wins.
  - Most per-seed noise is run noise (paired sd 0.024–0.045), so steadiness counts as much as the mean.

## Incentive (live weight vector, block 9432096)

| Bucket | Share | Split |
|---|---|---|
| Agent track | 56% | rank 1 to 5: 50 / 20 / 13 / 10 / 7% of the track (Hades 28%, dan0l 11.2%, DrPresident 7.28%, Orsentra 5.6%, crown-v207 3.92%); rank 6 and below get nothing |
| Generator track | 24% | 40 / 25 / 15 / 12 / 8% by latest round score (9.6, 6, 3.6, 2.88, 1.92%) |
| uid 21 | 20% | on neither board; most likely burn or the service bucket |

- **Generator pay:** rounds only. Round credit comes from cases top agents fail but at least 2 owners solve, with a
  bonus when the champion fails them; unsolvable cases are penalised.
- **Why generators exist:** the official generator gets mapped and overfitted (scores bunched at 0.94–0.97), so half
  of each run is now fresh miner-written cases.

## First v16 rollout runs (public scores, `gate_evidence.priced_cost`)

| Agent | Tool | Datagen memory | Generator | Cost | Factor | Requests | Composite |
|---|---|---|---|---|---|---|---|
| Hades v26 | 0.993 | 0.96–0.97 | 0.87–0.89 | $1.15 | 0.94 | ~715 | 0.86–0.87 |
| dan0l v38 | 0.95–0.97 | 0.92–0.96 | 0.86–0.88 | $1.37 | 0.85 | ~940 | 0.77 |
| horizon v8 | 0.973 | 0.956 | 0.897 | $1.52 | 0.794 | 1111 | 0.729 |
| DrPresident v27 | 0.88–0.99 | 0.95–0.97 | 0.90–0.92 | $1.52 | 0.79 | ~1125 | 0.67–0.73 |
| crown-v207 | 0.92–0.95 | 0.92–0.93 | 0.82–0.87 | $1.70 | 0.71 | ~1130 | 0.61–0.65 |

horizon v8's quality before cost was about 0.918, against Hades's 0.930. Nearly the whole gap is the cost factor:
3.2 model calls per case against Hades's 2.0, with prompt tokens 87% of the price. At ≤ $1.00 the same quality
would score about 0.918.

## Local tooling (built 2026-11-04 from f220cecd)

- `.cache/dittobench-api-v16` (official scorer, benches up to 16), `.cache/dittobench-api-subset-v16` and
  `.cache/ditto-rescore-v16`, `.cache/dittobench-generate-v16` (`-bench-version 16`), `.cache/challenge-scorer`
  (has `reproduce-slice`).
- The v15 binaries are untouched, so earlier A/Bs stay reproducible.
- `tools/practice_docker.py` doesn't send a dueling slice yet. A bench-16 request without one is refused
  ("dueling slice required"), so v16 practice needs the kit's `uv run ditto practice --bench-version 16` or a slice
  step added to our tool.
