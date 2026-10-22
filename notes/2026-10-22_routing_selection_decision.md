# Routing and record selection: offline comparison (2026-10-22)

Lab: `lab/eval_offline.py`, result `lab/results/20261022T150344Z_offline_salt7.json`.
Test: seeds 101-103 at surface salt 7 (1,050 questions, none seen in training). kNN
examples: seeds 11-14 at salts 0 and 3. Embeddings only, $0.0041 in total, no chat calls.

## Routing (does the question go to the records lane or the action lane?)

| router | right | memory-type kept in records lane | tool kept in action lane |
|---|---|---|---|
| Hades v6 word rules | 90.9% | 689 / 772 | 243 / 253 |
| kNN on meaning (9 nearest labelled questions) | 98.9% | 768 / 772 | 246 / 253 |
| combo: kNN when at least 80% sure, Hades rules otherwise | **99.1%** | 766 / 772 | 250 / 253 |

Hades loses mostly "history in order", "next step", hypothetical wording and plain
statements to the action lane, which is where off-lane tool calls on memory questions
come from. The 25 tool questions that must end with no call go to the action lane under
every router; only the model reading the records gets them right.

## Selection (given the right lane)

"complete" = every record the answer needs is in the pack. Tokens = characters / 4.

| design | records lane complete | tokens (median / p90) | action lane complete | tokens (median / p90) |
|---|---|---|---|---|
| Hades pack, words only | 89.2% | 2.9k / 5.5k | 88.7% | 3.8k / 5.5k |
| Hades pack with meaning (as released) | 92.0% | 3.1k / 6.5k | 88.7% | 3.8k / 5.5k |
| nearest 32 by meaning | 67.6% | 3.5k / 15.1k | 84.5% | 5.9k / 12.1k |
| overhorizon rebuild | 88.6%* | 1.9k / 3.0k | 96.9% | 10.6k / 17.2k |
| **union**: Hades pack + 12 nearest by meaning + 8 full-text hits, 48k chars max | **93.7%** | 5.3k / 8.6k | 95.9% | 6.2k / 9.7k |

*counts a long record as present when only some of its paragraphs were kept.

Hades's 24,000 limit is characters, not tokens: about 6k tokens, and the median pack is
about 3k tokens.

## Decision

- Routing: **combo**. One embedding per question (validators serve embeddings free), with
  Hades's rules as the fallback when the neighbours disagree. The fallback matters: the
  examples come from today's generator, and a new question family would land near nothing.
- Selection: **union** in both lanes. In the action lane it keeps almost all of the
  overhorizon recall at 60% of the tokens; in the records lane it is the most complete.
  Long case files stay whole (program questions replay every event).
- The no-call traps are a prompt and loop problem, not a routing one.
