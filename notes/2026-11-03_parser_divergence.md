# 2026-11-03 — parser-divergence: why every agent loses about 6 points a run

Free investigation from the paid run `practice/20261103T003809Z_ditto-harness-drp23v15_full` (seed 5119, bench 15)
and its regenerated dataset `.cache/datasets/v15_s5119792693744740612_salt0_full.json`.

## What the cases are

`gen/divergence.go` (bench v12 countermeasure C11): twelve cases in a full run, three rounds of four types.

| type | question (verbatim, every round) | evidence per round | v8 on seed 5119 |
|---|---|---|---|
| negation | "Who is my current dentist? Just the name is fine." | "my dentist is not Dr. A. My current dentist is Dr. B." | 1 of 3 |
| retraction | "Which bank do I use now?" | "you used to have me down as banking with A … B is my bank now" | 1 of 3 |
| reported speech | "What is my front-door code?" | "X insisted the code was A, but my own note says it is B" | 1 of 3 |
| hypothetical | "How many seats were actually booked for the <event> …?" | "if … we would have booked A … actually booked is B" | 3 of 3 |

- Every memory wave belongs to the one user (`miner`), and all three rounds are in the store when the questions are
  asked (traces #189, #248, #254 each carry all three dentist notes in the packet).
- The three rounds of a type ask the same words and each expects a different round's value (Claire Jensen, Kyren
  Ellis, Paul Watson). v8 answers the latest note each time (Paul Watson, the 6029 code, Young Credit Union), so it
  scores the last round and misses the other two.
- Hypothetical cases name a different event each round, so they are answerable and v8 gets all three.
- Nothing on the wire tells the rounds apart: same system prompt, same words, no date. The generator's own oracle
  (`internal/parserprobe/memory.go:230`) says so: "the parser-divergence questions repeat verbatim within a run, so
  position is the only wire-visible binding to the k-th record".

## Reading

- An honest reader can get one of three per type at best. That is the 2 points per type per run every top agent
  loses (Orsentra, Hades, dan0l, DrPresident, crown, nanodevs all at about 2.0).
- The only way to score more is to answer by the question's position in the run (k-th asking → k-th note). That keys
  on the benchmark's case structure, not the request: I5/I8 territory, and runs are concurrent anyway. Not to be
  built.
- If the operator fixes it (distinct wording per round, or one round per user), every agent gains about the same, so
  it would not change ranks. Worth a short report as a benchmark bug, not a harness change.
