# 2026-11-01 — v8 program path: principles, build, graded replay

## Principles

From notes/2026-11-01_research_generator.md (the code) and notes/2026-11-01_research_trajectories.md (every
program trace, 140 bench-14 runs).

1. **A split is never caused by the input.** The three rewordings see byte-identical notes. Groups split only
   when a member decides on its own and flips a borderline reading: v30's final check, v7.1's "check the earlier
   reply", v6's per-member check.
2. **The model's misreadings are fixed for a given phrasing.** "Reverts to the previous entry instead; the newest
   entry governs" is right 9 times in 86. Asking again only resamples the same reading.
3. **Explicit before → after state per entry works, if it is the final word.** v7's ledger got that phrase right
   18 times in 21, but the replies, told that "the entries decide", shipped it 6 times in 21.
4. **The grader zeroes a reply that carries a second candidate value:**
   - an earlier value, a decoy or another step;
   - a past marker such as "before" in the value's clause;
   - a decline, correction or hedge.

   Times need 17:55 or 5:55 pm.

## v8 (harness/v8, 38d0f1e)

- **One ledger per case file,** read under general `READING_RULES`: order, labels, separate matters, changes,
  going back, lists, plans, roles, dates, people, values.
- **The ledger is the final word.** The reply takes the value from it in one plain sentence (`REPLY_NOTE`,
  `ANSWER_RULES`).
- **Later rewordings repeat the value.** They give the same value without a check that could overrule it.

## Graded replay (practice/gates/replay_v8.py, $0.14)

**Grading.** `practice/gates/grader_probe/grade_replies` is the bench's own `grade.Memory`, compiled offline. It
gives the scorer's exact score on 1280 of 1280 traced program replies.

**What the replay does.** For each of the seven s44 seeds it takes the notes and questions from the v7.1 traces,
then runs the v8 ledger and replies with gpt-oss-20b on the platform providers. It differs from a real run in
three ways: plain chat, no tools, no final check.

| design (runs) | score /40 | splits/run | all-wrong groups/run |
|---|---|---|---|
| v6 (12) | 36.75 | 0.42 | 0.75 |
| v7.1 (7) | 36.86 | 0.71 | 0.71 |
| v8 replay (7) | 37.71 | 0.00 | 0.57 |

**Per seed against v6:**
- better on 8975 (36 against 34, 32, 29), 4249 (37 against 34) and 3374 (38 against 37 and 38);
- equal on 2330 and 9174;
- 4137: 39.5 against 40;
- 5704: 36.5 against 40.

**Remaining misses: 4.5 groups, each consistent across its members.**
1. **One thing tracked under two names.** "plan: pause" against "renewal status: cancelled", and "person behind"
   against "organiser"; the reply picked the wrong one.
2. **A struck entry read as empty** ("organiser: <undefined>").
3. **Timing kept in a value** ("scheduled pause before Jan 15, 2026").
4. **Client and vendor reversed:** "the organisation billing us" was taken as the client.
5. **One revert-to-middle status in a glossary file** was still read wrong.

Replay outputs: practice/gates/s44/replay_v8_a.json (ledgers, replies, scores).

## A: reading rules for item identity, struck changes, money direction and bare actions (308f078)

Graded replay B (`replay_v8_b.json`, $0.12) against replay A on the same seven seeds:

| | score /40 | splits | all-wrong groups |
|---|---|---|---|
| replay A | 37.71 | 0.00 | 0.57 |
| replay B | 36.14 | 0.00 | 1.00 |

- **Fixed:** client-vs-vendor 12/12 (was 9/12), revert-to-middle announced 20/20 (was 17/20).
- **New misses in groups the change did not touch:** a time written "7.15pm", a dated sequence, an untouched
  plan step, a list with a swapped item, a struck entry still read as "none".
- **Conclusion:** the ledger varies between samples. On one seed the same design scored 34, 37 and 40, so one
  replay per design cannot resolve differences of about 1.5 points. Compare designs on two or three samples.

## B: real s44 round of v8 (bcd3312, one round, $0.34)

| design (runs) | score /40 | splits | all-wrong groups |
|---|---|---|---|
| v6 (12) | 36.75 | 0.42 | 0.75 |
| v7.1 (7) | 36.86 | 0.71 | 0.71 |
| v8 real (7) | 35.79 | 0.00 | 1.14 |
| v8, all three samples (21) | 36.55 | 0.00 | 0.90 |

**Splits.** v8 has no split in 210 group samples (two replays and one real round). At ≈3.1 % a split, that is
worth about +1.3 % composite per run against v6. The accuracy difference (−0.2 questions, ≈ −0.04 %) is within
noise.

**What the real v8 run lost.** Mostly the same thing tracked as two items. The generator words one slot differently
from entry to entry:
- the allotment society: "The person behind … is Edgar Barnhart", then "the organiser … is Stephanie Malinowski
  instead", then "that entry about the organiser … was wrong";
- the language app: "plan" and "decision";
- the client-vs-vendor file: two glossary labels.

The ledger keys items by those words, so a strike or a revert lands on one name only, and the reply picks the wrong
NOW line. The right value is often in the ledger ("NOW person behind the allotment society: Edgar Barnhart").

Renderer copies are not the cause: grouped by timestamp, the three copies of an event (calendar entry, forwarded
text, fridge list) wrap the same sentence, and `once_each` already merges them.

**Next (proposed).** Key ledger items by subject and attribute (the allotment society's person in charge), never by
the noun an entry uses. Check it with two graded replays.
