# Incremental memory fixes for v14 (2026-10-28)

Same method as the tool fixes (notes/2026-10-27_incremental_fixes.md): one change at a time, from what the
v14 trajectories show (notes/2026-10-28_v14_memory_review.md); check where it reaches; test only the
questions it touches, paired against the build before it, on fresh v14 seeds (BENCH=14); keep or drop.

| # | Change | Test | Result | Kept |
|---|---|---|---|---|
| M1 | Records lane: a message routed as a statement gets a note asking the reply to say back what was kept | conversational-declarative + statement-path guards, fresh seeds 5502918374460173285, 2718364059918274631, 7640012583396271049, v6a vs v5g | 0.940 vs 0.974 (29 questions); the note never fired: the one declarative miss (both builds) went to the action lane; v6a's other miss was a decline phrased differently, no note | folded into M1b |
| M1b | A completed save_memory / update_memory result (both lanes) asks for one short sentence of the model's own naming what was kept and its value, not repeating the user's message | declarative + save + update + follow-up questions, fresh seeds 3874019265530918471, 6120847739265810593, 1493028576612047385, 8807364512093318277 | declarative replies v6c 12/12, v5g 11/12, first wording 11/12: "with each value written as the message writes it" made the model echo the whole message (graded 0 as an echo) | yes (7073f52) |
| M2 | Program short path: statement groups in filing-date order, the order pass's reading of the words only breaks ties; lead header says "in the order they were filed". v14 files case-file rows in story order (generator test TestV14CaseFileDatesFollowTheStory, ditto-subnet#3088); v13 dated rows by their shuffled position, which is why the order pass ignored dates | open + personal program: seed 3555 v7a vs the v5g full run; fresh seed 1139645001622862899 v7a vs v6c | 3555: 0.900 vs 0.725 (+9 -2; the two losses: a final check misread the case-file id and abstained over a right answer, and a swap not applied on a correct order); fresh: 1.000 vs 0.875 (+5 -0). About $0.04 per 40 questions | yes |
| M3 | Topic path: owner = the person last handed the thread; "who has the ball" = the latest open action even when the thread is later done or dropped (THREAD_STATE, plus a clause in the latest-passages draft) | all world-story families, fresh seed 5989349192384850320, v7b (M3+M4+M5) vs v7a; $0.28 for 78 x 2 | owner-current 10/13 vs 9/13, next-action 10/13 both (+1 -1), x-owner-email 9/13 vs 10/13. The latest-passages draft still names the open-action holder for owner questions and the decide copies it; the next-action loss overrode a right draft | no |
| M4 | Topic path: asked whether the notes agree, each one's status, then whether they agree | same run | status-disagree 0/2 both: the model listed every record's content, and in one said "no disagreement"; no conflict word on either ANSWER line | no |
| M5 | Topic path: a figure the notes say how to work out: work it out, only the result on the ANSWER line | same run | quantity 7/9 vs 6/9 (+1 -0); weak evidence | yes |

Seen while testing, for later: some real requests ("Walk me through the vendor changes, earliest first.")
are routed as statements, which also skips deliberation; the records lane keeps effort low for every turn
after one truncated turn (as the action lane did before tool fix 2); the update question can still pick
the wrong record (both builds on seed 1493028576612047385).

World-story mechanisms seen in the M3 run, for the next increments (generator oracles in
universe/questions_v13.go: owner = latest handoff, next action = latest follow-up, status-disagree =
both statuses plus a conflict word):
- the latest-passages draft answers owner questions with whoever holds the open action, and the decide
  follows it (4/13 owner-current misses on both builds);
- the ANSWER line drops an asked part that the prose gives ("Caden Ogden; email" without "share the
  final headcount"), 2 next-action misses on both builds;
- x-owner-email: the owner is named right but the email held in other records is not joined.

M2 costs v13 program questions (their dates are shuffled); v14 is the scoring version for any new upload.

Parser divergence (negation, retraction, reported speech) is capped at 1 in 3 for any agent: the
generator seeds all three rounds into one store and asks the same question each round with a different
key (one bank, dentist or door code per round), so only the round whose note is latest can be right.
Hypothetical rounds name different projects and score 3/3. Answering the latest note every time gives
the 1/3; at most one question per run to gain, so no change for it.
