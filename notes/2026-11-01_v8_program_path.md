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

## s45: v8 on all 250 memory questions of three fresh seeds (practice/gates/run_s45.sh, $3.08)

Fresh seeds 4140899197327149732, 5451784605348316629 and 8047062976504477843. Image `ditto-harness:v8` (308f078),
concurrency 8, platform providers, one round.

| seed | memory mean | program | splits (13 groups) | sanity | over-call | answer_in_prompt |
|---|---|---|---|---|---|---|
| 4140… | 0.940 | 40/40 | 0 | 1 | 1 | 0 |
| 5451… | 0.928 | 37/40 | 1 program group | 1 | 1 | 0 |
| 8047… | 0.928 | 36.5/40 | 1 enterprise group | 1 | 1 | 0 |

v6 on its own three holdout seeds (s42): memory means 0.944, 0.925 and 0.908, no splits, all gates at 1. The seeds
differ, so these two sets compare only roughly.

**Both splits are outside the v8 program path.**
1. **Routing.** "What did we settle on doing about the news subscription before it renews?" The word "news" makes
   `classify` read the question as a live request. It still reaches the records lane through the case-file
   identifier, but `short_answer` also requires `own_records_question`, which is False. The rewordings therefore
   went through the general records lane and decided independently ("cancel it" against "now pause it"). This gate
   is unchanged from v30 and v6.
2. **Enterprise.** An enterprise-composed-program group ("At effective step 12, follow the team of …") went through
   the general records lane like v6's, and one member counted 1 where the others counted 0. v6 had 0 such splits
   in 12 groups at s42.

Across all v8 testing, the program path itself has not split: 0 of 230 groups that reached it. Split risk now
comes from questions that reach the path inconsistently, and from the enterprise groups on the old lane.

**Possible fixes (not made):**
- A question that names a case file the user's records hold, and is already routed to records, takes the program
  path whatever its topic words.
- The enterprise groups are a separate design question: decide once per twin group on the general lane too.

## v8.1: routing fix (branch harness/v8.1; v8 itself stays as is on harness/v8)

`own_records_question` refuses any request with an outside-source word (web, online, news, ...). With the new
`held` flag, that word check is skipped when the request names a case file the user's records hold. Only
`short_answer` sets the flag. Every other check (a listed tool named, a fetch from a tool, an effecting request)
still applies. The diff is 2 lines in `lane.py` and `agent.py`.

Offline check, no model calls: `practice/gates/gate_diff.py` runs the `short_answer` gate of the saved v8 and of
v8.1 on traced requests. It rebuilds focus from the seed's dataset notes the way the harness does.
- The 10 v8 runs (s44 and s45): all 396 program-path questions stay on the path. The only change is the 4
  "news subscription" questions (3 rewordings and the counterfactual), which move from the records lane to the
  program path, so that group now decides once.
- All 174 traced practice runs with a cached v14 dataset (about 8,000 records-lane requests): the same 4 questions
  move, and nothing else does.
- The 36 enterprise questions still go to the records lane, because their notes are too long for the program path.
  This fix does not touch them.
- v8 unit tests pass.

**s46, real run of that group** (`practice/gates/run_s46.sh`, image `ditto-harness:v8.1` from 258dcf3, seed
5451784605348316629, one round, platform providers; run 20261102T010835Z). It cost about $0.002.

| question | path | calls | reply | score |
|---|---|---|---|---|
| counterfactual, case file c57e1f… (expected "downgrade it") | program | 2 | downgrade | 1 |
| rewording "Checking something…" (expected "cancel it") | program, decided first | 2 | cancel | 1 |
| rewording "Looking back…" | program, ledger and reply reused | 1 | cancel | 1 |
| rewording "Before I forget…" | program, ledger and reply reused | 1 | cancel | 1 |

The group that split at s45 ("cancel it" against "now pause it") now decides once and is right on all 4 questions.

## v8.1 screening (local, 2026-11-02)

`practice/gates/screen_v8.1.sh` and the L1 (`tools/l1_review_local.py` with the lineage packet, parent v6; screener
at 14e093c3, prompt source-review-v40-policy-v13; $0.94, 200 steps).
- Package `practice/submission_v8.1.tgz` (sha256 1d4e1c42…, 35 files). `ditto verify` passes. Against the uploaded
  v6: 4 files and 248 lines (PROVENANCE.md, agent.py, lane.py, short.py), so the review is diff-scoped.
- Static: malicious 0, fingerprints 0, generator n-gram leads the same as dan0l v30. One new advisory lead,
  positional-number-extraction at short.py:40-41. It is the words "number" and "first" in the READING_RULES prose,
  and the screener marks this rule as never a finding on its own.
- L1: risk medium, benchmark_emulation, clearance certified, no violation certified; confidence 0.91 (v6 0.76).

| invariant | v6 L1 | v8.1 L1 |
|---|---|---|
| I1 model invocation | pass | pass |
| I2 evidence retention | pass | inconclusive |
| I3 model dissent | pass | inconclusive |
| I4 derived-value authority | pass | **breach** |
| I5 production engine | breach (guide_records family notes) | **breach** (READING_RULES and the ledger schema) |
| I6, I7, I8 | pass | inconclusive |

- v5 and v6 also had a local I5 breach and cleared live screening (the routed-guidance safe harbor, where the model
  writes the value).
- The I4 breach is new. It points at REPLY_NOTE (short.py:85): the ledger is "already applies every entry" and the
  reply "takes what it holds". The reviewer reads this as model output treated as settled, without labelling it a
  candidate the deciding turn may reject.
- Almost every concern is on the v8 program path (short.py:39, 71, 85). The routing fix appears only as evidence
  of how a request reaches that path (agent.py:80).
- The nearest precedent is october-29-reused-draft-no-disagree-clause: a reused model draft in the prompt, without
  a disagree clause, was allowed.

## Reply-note A/B for the I4 lead (practice/gates/replay_reply.py, $0.075)

The candidate wording (v8.2, a temporary copy, not on a branch): "Answer the message. The ledger above is your own
working reading of the entries, and you decide the answer: where an entry plainly says otherwise, follow the entry.
Take what the ledger holds …". The rest of the note is unchanged.

Both arms reuse replay B's ledgers for the seven s44 seeds (280 questions), so only the reply turns differ; one
sample each. Outputs: `practice/gates/s44/reply_v81.json` and `reply_v82.json`.

| arm | score /40 | splits (7 seeds) | all-wrong groups (7 seeds) |
|---|---|---|---|
| replay B as recorded | 36.14 | 0 | 7 |
| v8.1 note, same ledgers | 37.64 | 0 | 4 |
| v8.2 note, same ledgers | 35.50 | 1 | 8 |

- The same note on the same ledgers moved 1.5 points between replay B and this run, so reply sampling alone accounts
  for about 1.5.
- v8.2 is 2.14 below v8.1. Its losses are the misreadings the ledger was built to stop. With leave to follow the
  entries, the reply re-read them and took the wrong item list (twice), the wrong client ("Kestrel Studio"), a
  glossary label in place of the handle, "none" for a struck organiser, and a bare "draft proposal".
- It added a split and doubled the all-wrong groups.

The wording that lets the reply overrule the ledger is rejected: it brings back the failure the program path exists
to prevent.

**Milder wording (v8.3, $0.04).** The only change is "Answer the message from the ledger, which already applies
every entry:" becoming "Answer the message from your ledger above:". Same ledgers, one sample
(`practice/gates/s44/reply_v83.json`).

| arm | score /40 | splits (7 seeds) | all-wrong groups (7 seeds) |
|---|---|---|---|
| v8.1 note, two samples (replay B, reply_v81) | 36.14, 37.64 (mean 36.89) | 0, 0 | 7, 4 |
| v8.3 note, one sample | 36.57 | 1 | 5 |

- Against the mean of v8.1's two samples, v8.3 is −0.32, within noise.
- Against the paired v8.1 sample it gained 1 question and lost about 8.5. The losses are the same kinds v8.2 had:
  "Kestrel Studio" for the client, which split that group 1 of 3; "None" for the struck allotment organiser, on all
  three rewordings; "draft proposal"; "booked the venue"; one item list.
- Reading: "already applies every entry" is doing work. It keeps the reply from re-deciding what the ledger
  settled. Without it the reply drifts a little toward v8.2's re-reading.
- Not adopted on this evidence. A second sample of each arm (about $0.08) would tell whether the −0.3 to −1.1 is real.
