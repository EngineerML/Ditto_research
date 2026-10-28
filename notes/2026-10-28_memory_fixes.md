# Incremental memory fixes for v14 (2026-10-28)

Same method as the tool fixes (notes/2026-10-27_incremental_fixes.md): one change at a time, from what the
v14 trajectories show (notes/2026-10-28_v14_memory_review.md); check where it reaches; test only the
questions it touches, paired against the build before it, on fresh v14 seeds (BENCH=14); keep or drop.

| # | Change | Test | Result | Kept |
|---|---|---|---|---|
| M1 | Records lane: a message routed as a statement gets a note asking the reply to say back what was kept | conversational-declarative + statement-path guards, fresh seeds 5502918374460173285, 2718364059918274631, 7640012583396271049, v6a vs v5g | 0.940 vs 0.974 (29 questions); the note never fired: the one declarative miss (both builds) went to the action lane; v6a's other miss was a decline phrased differently, no note | folded into M1b |
| M1b | A completed save_memory / update_memory result (both lanes) asks for one short sentence of the model's own naming what was kept and its value, not repeating the user's message | declarative + save + update + follow-up questions, fresh seeds 3874019265530918471, 6120847739265810593, 1493028576612047385, 8807364512093318277 | declarative replies v6c 12/12, v5g 11/12, first wording 11/12: "with each value written as the message writes it" made the model echo the whole message (graded 0 as an echo) | yes (7073f52) |

Seen while testing, for later: some real requests ("Walk me through the vendor changes, earliest first.")
are routed as statements, which also skips deliberation; the records lane keeps effort low for every turn
after one truncated turn (as the action lane did before tool fix 2); the update question can still pick
the wrong record (both builds on seed 1493028576612047385).
