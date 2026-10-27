# Tool failures across every traced run: noise or design (2026-10-27)

Every practice run with a trace (dan0l v24 through v4d, 8 seeds, about 2,300 tool-question runs)
was laid side by side per missed question with `tools/trace_many.py`, and six reviewers read the
decisive calls family by family. Per-family write-ups with quoted evidence are in
practice/deep/findings/ (local, not committed); this is the summary.

## The answer

Most of what is still being lost is design or fragile design, not noise. True noise (same lane,
same records, same notes, the decisive call simply went the other way) is a handful of runs: about
5 routing misses, the notes3 refactor job, single spelling picks. Several things earlier called
"noise" or "artifact" in this work were wrong, notably the follow-up read after a mutation.

## Design causes still live in v4d, by estimated gain (questions per 100 tool questions)

| # | Cause | Where | Fix (all before the model answers) | Gain |
|---|---|---|---|---|
| 1 | "Correcting a saved note" says to write only the corrected facts; update_memory replaces the note, so it loses its project name; the follow-up read then finds nothing, and later updates pick the wrong bare note (13 of 14 follow-up misses; combined-guide, which kept the heading, answered) | ours/guidance.py | keep the note's opening words, drop the placeholder sentence, stay under the grader's 8x length limit (about 85-110 chars) | 1.0-1.3 |
| 2 | One empty finish=length turn sends every later turn (and drafts) to low effort; low-effort turns act on undecided notes, give up, drop arguments (20 of 23 such runs failed in restraint families; 6 misses in workflows) | action.py | retry once at the same effort with more tokens; go back to medium after one good turn | 1.0-1.5 |
| 3 | Agreed-work routing: list_workflows never shows the note's workflow, run_workflow with that name succeeds; the note says "the name it lists", the suffix says "the listed option", and v4d's "say so" line makes the model give up (v4d 2/2, v4b 2/10, horizon 0/10) | guidance.py, action.py suffix | run by the note's name and let the result say whether it exists; limit v4d's "say so" to questions, not actions | 0.5-1 (2-4 vs v4d) |
| 4 | Restraint: clarifications drop the slot word or shorten the record's title; setting checks land on the records lane (no notes); v4 wording "an older setting does not stop it" fights the setting check; reply check reads "check that X is Y" as a live lookup | guidance.py, agent.py lanes, action.py | clarifications name what they are for and copy names verbatim; keep setting checks on the action lane; a "no note keeps a value: set it" branch; scope the v4 sentence to change requests; reply-check reasons | 1.5-2 |
| 5 | Background work: "have a worker build ... in the background" goes to artifacts (router ranks artifacts first, no note) | action routing / guidance | treat delegated/background work as an agent job (prompt line rather than more cue words) | 0.5-1 |
| 6 | Spelling picks: the model anchors on the first letter (Qsap -> Questrial); v4c's "most letters in the same places" turned "blue variant of nay" into navy | guidance.py | one rule (75/75 on every discovery question seen): a named qualifier means the option made of name + qualifier; otherwise fewest single-letter changes, first letter included | 0.2-0.6 |
| 7 | Deletes pulled onto the email record when the disposable note never says "email" (one question 5/5 failed in every version) | guidance.py | the note to remove is the one that calls itself temporary; contact records stay | 0.3-0.5 |
| 8 | Calendar "already booked": the duplicate-check note ends "or send the call again" and the bare "Done." search lets the duplicate out | action.py | the note says report where it is; drop "send again" (wording, not a block) | 0.3-0.5 |
| 9 | A misspelled tool name loops ("fazerun_" for "fizerun_"): the unknown-tool message doesn't name the closest listed tool | action.py | name the closest listed tool in that message | 0.3-0.5 |
| 10 | Result read frames "the id the user asked to be told" as an undone tool action; the drafts-note tail produces "I'll send the reply as it is." | action.py prompts | "what the user asks to be told is not a tool action"; "send your reply as it is, written out in full" | 0.4-0.6 |
| 11 | Web: re-search after an off-topic preview; the records lane's own web loop (no suffix, 12 turns) on "what's the latest" about something the user told us; "send to them" note firing when a recipient is named; reply check returning no verdict (10 of 208) with no retry | lane routing, records engine, guidance, action.py | suffix and a turn cap on the records lane's live calls; skip the "them" note when the recipient is named; one retry when the check returns no verdict (shape, not content) | 0.4-0.7 |

The estimates overlap and come from small samples (often one or two runs per question). Fixed in
v4/v4b already and worth keeping: the notes header (describing instead of doing: 43 runs before v4,
0 in 424 after), instruction-now, figures to run_code, job list, crawl, schedules, tool preferences.

## Artifacts found

Local 429 rate limits (3 runs); case ids that collide between the small and full datasets (3
runs); older reruns that replayed writes already holding the question's own end state (8 update
misses).

## Screening notes on the fixes

All are context the deciding model reads before it answers. Two suggestions were rejected: a host
computed "closest spelling" hint in the tool result (I4 derived-value authority reaches tool
arguments) and blocking an identical resend (I3). New cue words are phrase-table style; prefer the
prompt-line forms.
