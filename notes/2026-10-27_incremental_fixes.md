# Incremental tool fixes from the failure review (2026-10-27)

One change at a time, from notes/2026-10-27_tool_failure_review.md. For each: read the evidence, the
grader rule and the code; check where the change reaches (note fire matrix over 8 seeds, memory
questions must stay untouched); test only the family it touches, paired against the build before it,
on question instances never seen before (fresh seeds below 2^63); keep it or drop it.

| # | Change | Test | Result | Kept |
|---|---|---|---|---|
| 1 | Correcting note: the new content starts with the note's own opening words (project, client), then the corrected facts | memory-write questions, fresh seeds 6610391857202546183 and 1847720635591104429, v5a vs v4d | 20/22 vs 18/22; follow-up reads 2/2 vs 0/2; every update 79-131 chars | yes (ce6e27b) |
| 1b | The named kind of note is "the record whose own words call it that", not a newer plan or decision record | updates and follow-ups, fresh seeds 4471029386615503217, 7730192845561840093, 2905518374460921786, v5b vs v5a | 15/18 vs 18/18: "own words" collided with fix 1's "own opening words" and the model copied the whole placeholder note three times (over the length limit) | no |
| 2 | A cut-off empty turn is retried at the same effort with 12000 tokens; later turns and drafts keep the effort | the four questions that truncated most, 2 runs each, v5c vs v5a; plus a fake-model test | every v5c truncation retried at medium/12000 and stayed medium; the v5a truncation dropped to low and gave up; untruncated runs identical | yes (4563a0e) |
| 3 | Routing note runs the workflow by the note's name; v4d's "say so" suffix clause only when the user asked to be told a value | routing + decoy add-on questions, fresh seeds 5938014472610385517 and 3317946052817731099, v5d vs v5c | routing 18/20 both, decoys 20/20 both; the remaining give-up is decided at the last turn after the listing result, in dan0l's result-read closing | yes, neutral (5745fe3) |
| 4a | The effort clarification names the setting and "the options exactly as the note words them" | restraint-effort + set-effort, fresh seeds 6202847719305518841 and 1590366248871024497, two passes, v5e vs v5d | 19/20 vs 20/20: v5d named the setting in all 10 clarifications (the omission is rarer than the review's sample), and "the note" was read as our own advisory note, so the options came from it instead of the user's record | no |
| 6 | Listed-option note: qualifier rule first (variant/cut/edition/shade/version), closeness as fewest single-letter changes; drops v4c's "most letters in the same places" | discovery questions, fresh seeds 1203948576610294837 and 6874412098361759203, v5f vs v5d (a guard test: the expected gain is below what 16 questions show) | 15/16 both, the same miss (Itufit -> Fira Sans: the model does not count edits reliably); every variant and shade question right in both | yes, neutral (653ab20) |

Seen while testing, for later fixes: the "Scratch that ... same scratchpad note" update can be drawn to a
newer plan or decision record about the project (v4d and v5a both, about 2 in 30 updates); the routing
question still gives up after list_workflows about 1 time in 10 (a fix would have to act on the listing
result itself, which is tool-specific: deferred).

Lesson so far: two of the four wording changes (1b, 4a) failed by colliding with words already in the
prompt ("own words", "the note"). Before each new wording, grep the deciding prompt for its key words.
