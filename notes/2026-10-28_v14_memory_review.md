# Why v14 scores lower: strict scorer or hard questions? (2026-10-28)

Current build (e1900b1, image combined-v5g) on the full v14 dataset of seed 3555973218589394111, the seed
horizon v1 was scored on by the platform under both v13 and v14. Local run
practice/20261028T014512Z_ditto-harness-combined-v5g_full (upstream at 20e82d9b, generator and scorer
rebuilt; the local v14 dataset matches the platform's case for case by category).

| | Tool | Memory | Composite | Gate factor |
|---|---|---|---|---|
| horizon v1, platform, v13 | 0.940 | 0.881 | 0.911 | 1.0 |
| horizon v1, platform, v14 | 0.917 | 0.865 | 0.800 | 0.898 (conversational sanity 0.874) |
| current build, local, v14 | 0.970 | 0.827 | 0.810 | 0.902 (conversational sanity 0.874, memory over-call 0.996) |

## 1. The per-question grader is not stricter

Every memory answer of the local run was graded again with the official grader
(`grade.Memory`, research/dittobench-datagen) once as bench 14 and once as bench 13 (/tmp/regrade).
The bench-14 regrade reproduces the run's own score on 244/250 questions (0.825 vs 0.827). The same answers
under bench-13 rules: 0.817. Only 2 answers grade differently, both in v14's favour (markdown bold and an
unusual hyphen in "**77-VOKA-DIPE**", a number followed by a word). 39 of the 46 memory misses have a final
answer that does not contain the expected answer at all.

## 2. Harder questions: the program families

On this seed only 130 of v14's 351 memory records have the same text as in v13: v14 adds 221 records, many
of them "case file" records with an invented local vocabulary ("read it with our local glossary: joraelkey
means a replacement of prior state, newest wins") and state changes with no cue words. 23 questions keep
their text but get a new answer (18 personal-program, 4 open-program). Same agent, both benchmarks:

| Family | v1 v13 | v1 v14 | current v14 |
|---|---|---|---|
| v13-open-program (16) | 1.00 | 0.62 | 0.62 |
| v13-personal-program (24) | 1.00 | 0.83 | 0.79 |

About 10 questions, roughly -0.04 of the memory mean. The other weak families (parser divergence 0.33,
world-story owner/order/quantity, absence near-miss) score about the same under v13 and v14: they are our
standing memory weaknesses, not v14 changes.

## 3. The biggest single cost: one conversational reply through the sanity gate

The conversational-sanity gate is the geometric mean of the pass rates of three slices (chitchat,
declarative acknowledgement, declarative behavior; services/dittobench-api/internal/scorer/scorer.go:653),
folded into the composite as `0.25 + 0.75 x metric` (v7ConvSanityFloor). One failed question out of three
in one slice makes the metric 0.874 and the factor 0.905: about -9.5% of the whole composite.

- local run: "One more thing: my personal Ditto accent is light blue green; client palettes don't change
  that." -> reply "Got it!" -> 0.25, "declarative acknowledgement without the stated value". Every
  declarative reply that restated the value scored 1.0.
- horizon v1 on the platform (v14, same seed): one declarative-behavior question failed, the same 0.874.

The gate formula is the same in v13 (the v7 floor); v1 passed every conversational question in its v13 run
of this seed. So this is a variance tail that v14 did not create, and probably also behind some of v1's
low v13 confirmation waves (0.725, 0.771).

## So

Not a strict scorer. Partly harder questions (the program families, about -0.02 composite), mostly the
conversational gate's sensitivity to a single reply that does not restate what the user just said (-0.09
composite when it happens). The cheapest high-value fix: when the user states a fact or preference to keep,
the reply acknowledges it by restating it ("Noted: your accent is light blue green."); it is general,
correct assistant behaviour and acts before the answer.
