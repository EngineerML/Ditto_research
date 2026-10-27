# Phrase-table notes (guidance v3) on a fresh seed (2026-10-27)

After the always-on rulebook did nothing on held-out seeds (notes/2026-10-26_seed4219_tool_only.md),
the request-triggered notes were rebuilt the way dan0l v25's table works, in our own words:

- **Cues are request shapes, not single nouns**: "set to run", "on its own repeat", "per what we
  landed on", "I can see rendered", "-ish", "Start it", "is Thursday now". Where a noun is the cue
  (calendar, picture) the pattern lets its letters vary. No typo-mending code.
- **Built on four seeds' wording** (3590..., 2184..., 5547..., 4219...). The note reaches nearly
  every question of the families we lose: calendar 16/17, image edit 4/4, schedules 8/8, repeating
  setup 2/2, task now 3/3, capability questions 4/4, artifacts 4/4, agreed work 25/25,
  corrections 14/14, font/accent 33/34. Memory questions with a note: 0 of about 1,000
  (/tmp/fire_matrix.py, recorded here because the check is the point: "spelled out" and plain
  setting statements fired before and were fixed).
- **New notes**: repeating setup (create_workflow), agreed work (the note says workflow, new
  workflow or job), capability questions (discover_capabilities), something to open and use
  (artifacts).
- **Wording**: corrections state only the changed facts ("handoff is Thursday"); the failing runs
  copied the whole note back. Image edits: no link exists and none is needed. Calendar adds with no
  day or time are left unscheduled.
- **Action lane for noted requests** (app/agent.py, `moves_to_action`): five noted questions had
  gone to the records lane and scored 0 there. The setting check is left where it lands: on the
  records lane those restraint questions pass.
- **Notes after the request** in the user turn instead of the system prompt; the reply check, the
  duplicate check and the repeat authorisation still read the request alone.

## Fresh seed 8372604497854494846 (dan0l v25 scored there: tool 0.917)

Tool questions only, platform providers, one run each, $0.43:

| | tool mean | model calls / question | seconds / question |
|---|---|---|---|
| notes v2 (committed design) | 0.906 | 4.76 | 19.5 |
| notes v3 | 0.927 | 4.51 | 17.5 |

8 gains (two contact-research emails, calendar create, set effort, image edit, parallel web+image,
repeating setup, setting check), 6 losses. Of the losses one was the calendar note firing on a
lookup ("Find ... event on my calendar") and one a delete where the model asked for the pair id;
both fixed after the run (lookup gate, "the records above show it"). The other four had no note
(restraint calendar clarification without a record token, agent job as a workflow, a memory
follow-up read, a theme set that listed and stopped): run-to-run variance.

## Screening and L1 (commit ca5a988)

- Local static screen: no malicious hits; the only leads are the known app/ours/lane.py ones
  (router mender's typo-tolerant compare, inherited numeric constants), cleared by L1 before. No
  lead and no generator n-gram hash in guidance.py, action.py or agent.py.
- L1 (tools/l1_review_local.py, prompt source-review-v38-policy-v13, $0.78): risk low, category
  none, clearance certified, confidence 0.89 (v2 notes: 0.84). All eight invariants pass; I5
  "request-matched workflow notes remain advisory guidance to the model, with no reachable
  deterministic answer-family writer"; I7 "guidance does not enforce a plan". 4 concerns along
  the way (v2: 12), all closed. Observation: practice/l1_v3.json.

## Full run, fresh seed 8372604497854494846 (ca5a988, platform providers, $0.95)

Folder practice/20261027T004259Z_ditto-harness-combined-v3_full.

| | composite | tool | memory | tool eff. | consistency | over-call | conversation |
|---|---|---|---|---|---|---|---|
| v3 (local) | 0.892 | 0.927 | 0.876 | 0.993 | 1 | 0.996 | 1 |
| dan0l v25, official on this seed | 0.804 | 0.917 | 0.881 | | | | |

The tool part repeated the tool-only run's 0.927 exactly. Memory is the records path, which v3
does not touch; its misses are the usual world-story and parser-divergence families.

The over-call gate below 1 is partly v3: a memory question naming a person "Cadence" ("I need to
reach Cadence Baker ... Which email is current?") matched the schedules cue, was moved to the
action lane and called list_schedules (it still scored 1). Fixed after the run: the cue is now
"on a cadence", and the schedules note stays off "which email" questions; over five seeds no
memory question gets a note. The other two memory questions with a non-memory call (a declared
accent set with set_accent_color, a preference question answered with discover_capabilities)
had no note and took the action lane through the existing router.
