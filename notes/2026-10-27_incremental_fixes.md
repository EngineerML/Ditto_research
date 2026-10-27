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

Seen while testing, for later fixes: the "Scratch that ... same scratchpad note" update can be drawn to a
newer plan or decision record about the project (v4d and v5a both, about 2 in 30 updates); the routing
question still gives up after list_workflows or creates a workflow first (fix 3's target); a clarifying
question can leave out the slot name ("Which do you prefer: ...") (fix 4's target).
