# v5 deep review: every trajectory, lane by lane (2026-10-29)

v5 as uploaded (horizon v5, agent c8b23c9f) scored 15 official samples, mean 0.9205 (range 0.853-0.952), rank 3 behind dan0l v30 (0.930). This review reads every local v5 trajectory, passed and failed, before choosing the next change. No model was called.

Data: 623 trajectories of the exact v5 build: the seven s39 re-check runs (39 consistency cases each) and the full 350-case run on seed 7429735794480221645. practice/gates/v5_master.py builds practice/gates/v5_deep/master.jsonl and one dossier per case; practice/gates/v5_tables.py the tables. Four read-only reviews, one per stage, wrote practice/gates/v5_deep/report_lanes.md, report_program_topic.md, report_records.md and report_action.md (scripts beside them). The program/topic review regraded intermediate replies with the official grader offline (agrees with the run on 303/311).

## Environment facts settled on the way
- The harness is served clean question text locally and on the platform. Practice (/v1/submit) and validators (/v2/score) both run runSizeJob (dittobench-api main.go:1398, its only call site), which builds the salt-0 artifact with typos only to hash it (main.go:1602-1611) and serves the pre-surface cases (main.go:1651-1658). Private datasets, which would serve the artifact's text, are bench 13 only (private_dataset.go:45). Record texts keep their own authored misspellings ("reschdeule", "eail").
- `delivered_failed` on memory tools is the platform's toolexec behaviour ("tool not available via this endpoint"); the call is still observed.
- The public pipeline's provisional_scores[].case_results give per-case category, score and notes for every scored run.
- master.jsonl caveat: composed-program twins differ only in a case-file id, so the text matcher swaps some of their traces (13 rows; report_records.md §0).

## What the model does well (keep)
- Program path (239 traces, 0.953, 2.7 calls, 9k tokens): filing order and "latest holds" have 0 misses in 76 replacement/withdrawal cases; the earlier-reply note is kept in 146/154 and corrects 4 of the 8 times it changes; twins never split path; 75 of 80 twin groups all right.
- Records retrieval: every needed record is in the packet in 175/177 labelled traces.
- Action loop: the first call is right in 89/92; arguments come from the records; the result read does the real work (variant mapping, second steps).
- Restraint in the memory phase: 19/19.

## Where the points go (local full run plus re-checks)
Capped by the benchmark, not worth work: conversational-chitchat (any clean reply is 0.5, grade.go:182-224; still counts for the sanity gate) and parser-divergence negation/retraction (one store holds all three rounds, ceiling 1/3). The platform's 3 chitchat and 2-per-family divergence misses every run are exactly these ceilings.

Fixable, by mechanism:
1. Answer-line form (program and topic): qualifiers added to the value ("Switch to annual billing before 6 December 2025", from short.py:30 "Write any date in full ... even when the message asks for less"; "... before the end of the month"), and misspellings copied from the notes (VALUE_VERBATIM "in their words"). 6 misses, 1 all-wrong twin group; counterfactual regrades turn each to 1.
2. Revert and withdrawal reading (program): "back to the previous entry" read as the value the last change set; a withdrawn value written in another form ("8:45 pm logged in error" vs "20:45") not linked. 6 misses, 2 all-wrong twin groups. The same structures pass elsewhere, so the model is unstable here, not blind.
3. Final checks: program fixed 2, broke 3 (both twin splits come from it); topic dropped a "disagree". Records path has none. It is still the thing that adds missing ANSWER: lines (9 traces).
4. Absence grounding (records): NO_RECORD_REPLY "without repeating its contents" and the deliberation brief "say only ..." contradict HANDLE_NOTE/LEG_NOTE; the follow-up rewrite drops the body in 19/93 rewrites. 3 misses; the follow-up question is the only grounding in 12 of 21 passing declines.
5. Composed programs (records): the final turn at effort low overrides unanimous or majority-correct search notes (3 of 4 misses); all 18 cases over 100 s are these.
6. Topic thread semantics: owner vs next-action holder (one story, 4 of 10 topic misses), disagreement's second state outside the two-passage window.
7. Arithmetic without calculate (3 cases across paths; calculate ran 6 times in ~600 traces).
8. Action: setter lane skips the result read (font variant miss), paraphrased re-search after a bare "Done." (calendar 0.667), restraint lookup despite "make no call" (1), and the run_workflow name-vs-id ambiguity that fits the platform's recipe_apply 0.6.

Cost: search passes are 68.6% of records-path completion tokens; 57 order passes are discarded by construction (personal-program dates all distinct); the action verdict call is 75 calls for a one-word answer (7 of 32 OPENs false); records-lane recall sends ~118 observed memory calls per run, which matches the platform's ~120-129 "unexpected executions" and is the likely source of memory_over_call 0.996-0.998.

## Candidate changes, in the order I would test them
All are general prompt or gating changes; the host never compares or swaps the graded answer; no wording-keyed tables. Each is A/B'd only on the traces it reaches.
1. Answer-line rules shared by program and topic: the value only (no when/why/where unless asked; a date in full only when a date is asked); ordinary words spelled correctly, names/codes/addresses/coined labels copied exactly. Reach ~107 traces.
2. PROGRAM_CURRENCY spells out reverts (restore the value the last change replaced) and withdrawals (match the withdrawn value by meaning, whatever its written form). Reach 79 traces; 12 passing groups at risk.
3. Final check limited to form, with the asked parts and values kept unless the notes contradict them; only together with 2.
4. Absence contract: decline by saying what the records do hold about the subject (never the withdrawn or asked-for value); the follow-up rewrite keeps every sentence and adds the question after the body. Reach ~50 absence cases and twins.
5. Composed final turn: no forced low effort; depart from agreeing notes only by quoting the record they misread; 3 search passes instead of 5 (majority of the first 3 was right in 60/61).
6. Action: result read in the setter lane; a second call to the same read tool after a completed call goes through the repeat check; fill both name and id when a schema accepts either.
7. Zero-risk cost: skip the order pass when every group's first note has a distinct date; verdict at low effort with a small cap; cap or retry the timeline pass on length.

Not pursued: chitchat, negation/retraction, re-routing world-story, more phrases in request_kinds/guide_records.
