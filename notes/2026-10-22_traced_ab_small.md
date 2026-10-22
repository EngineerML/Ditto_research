# Traced A/B on the small profile (2026-10-22)

Seed 4242, small (6 tool + 27 memory). Both images carry the same practice-only trace hooks
(`tools/add_trace.py`, `tools/trace/trace.py`); comparison by `tools/trace_compare.py`.

| run | composite | tool | memory | cost | prompt tokens | model calls |
|---|---|---|---|---|---|---|
| Hades v6, traced (`practice/20261022T155006Z_...hades-v6-trace_small`) | 0.972 | 1.000 | 0.944 | $0.121 | 1.39M | 212 |
| ours, traced (`practice/20261022T155639Z_...dev-trace_small`) | 0.870 | 0.833 | 0.907 | $0.137 | 1.57M (+13%) | 222 |

Same seed, same images, one hour earlier: Hades 0.511, ours 0.769. Run-to-run variance on one
image is larger than the gap between images, so single small runs decide nothing.

## The two cases we lost

1. **decoy_file_convert_result_usage** ("Convert my export on the Pilot protocol with Befo and tell
   me the exact figure..."). Lane and catalog identical. Our action packet was widened with
   records the request does not need, so the plan-first call got 7,940 prompt tokens against
   Hades's 4,601. It reasoned until the 6,000-token output cap (`finish=length`), produced no
   decision, and the next turn asked the user for a file path instead of calling
   `befo_file_converter`. Hades named the tool, called it and answered. (Hades lost this same
   question in its first run in the same way, so it is a fragile case that the longer prompt tipped.)
2. **world-trip-changed-leg-current** ("how many days in Japan after the change?", answer 13 = 10 + 3).
   Identical 47-record packets; all 3 needed records present in both. The timeline pass got the
   same prompt (9,968 vs 9,980 tokens) but wrote 6,342 tokens for Hades and 1,481 for us
   (provider nondeterminism at temperature 0). Our answer drifted to 9, a figure from a sibling
   trip with the same shape (another trip "in the year before the move" with a 9-day stay). The
   two 0.7 drafts said 9 and 12; the final kept 9. Hades lost this question in its first run.

## What the traces say overall

- Selection was not the limit on this profile: wherever the answer key names evidence, both
  packets held all of it. The small store has only 76 records, so Hades's 24,000-character pack
  already covers nearly everything; widening only adds length.
- Widening made prompts longer where it cannot help: chit-chat decide calls 7.5k vs 5.2k tokens,
  behaviour questions 11.5k vs 2.3k characters of records, case-file questions 39.9k vs 20.0k
  characters. That matches the owner's point that the 20B model degrades on long prompts and is
  why Hades caps the pack at 24,000 characters.
- Routing changes (meaning router) moved 4 cases to the other lane; all 4 still scored 1, with
  more model calls in 2 of them.
- Chit-chat is capped at 0.5 by the grader for every harness.

## Next

- Widening must stay inside Hades's 24,000-character pack (fill unused room, never grow past it),
  and should not run for chit-chat or requests that need no records.
- Cap the plan-first call's output (it ran to 6,000 tokens) so it cannot eat the turn.
- Measure on the full store offline first (lab), then a medium paid run.
