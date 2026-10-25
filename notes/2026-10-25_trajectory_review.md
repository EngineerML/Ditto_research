# Trajectory review: Hades v6 vs ours on every failed or flip-flopping question (2026-10-25)

## What was reviewed

- **Runs:** all traced practice runs on seed 4242.
  - Hades: small, medium, full.
  - Ours: small, medium O1, medium O2, full (171278e).
- **Hades full:** its questions with a 402 credit error are left out. Its tool phase is fully valid; 79 of its memory questions are not.
- **Tool:** `tools/trace_multi.py` lines the runs up per question. Twins that differ only by a case-file id are matched by scorer latency.
- **Questions kept:** 75 (full), 36 (medium) and 5 (small) failed or disagreed between runs.
- **Reports:** three reviewers read every trajectory. Their reports are in `practice/analysis-20261025/findings_{tool_routing,memory_threads,memory_other}.md`. The main claims below were re-checked against traces and source.

**Scoring arithmetic:**
- Composite = mean(tool, memory) × gates. This reproduces ours-full 0.766611 exactly.
- One tool question is worth 0.005 of composite; one memory question 0.002.

## Totals on comparable questions

| | Hades | ours |
|---|---|---|
| tool, full (100) | 87.6 | 81.6 |
| tool, medium (48) | 41.3 | 40.3 / 40.6 |
| memory threads, full (62 valid for Hades) | 46 | 51 |
| memory threads, medium (41) | 34.7 | 35 / 36 |

**Tool:** ours loses about 6 points to Hades on full.
- About 1.7 of those came from the 2,500-token decision cap and the statement route. Both are fixed in 0f8481e.
- The rest is prompt wording and model variance.

**Memory:** ours is ahead.

## Gates

- **Consistency:**
  - Ours full split 2 of 19 twin groups, both open-program renderer variants.
    - c2c1ceae: only the renderer member's final check overrode a correct shared draft with "Not specified".
    - cd098034: "Read the local glossary… Name the event" tripped the imperative-setter rule and went to the action lane.
  - Hades has no valid split. Its reported 0.31 consistency and 0.48 conversation scores are artifacts of the 402 errors.
- **Tool efficiency 0.988 (ours full):**
  - cd56b35c2 and c285e59f3 are fixed in 0f8481e.
  - c838aca9c remains: the result read called an empty search "not done", so a second search ran.
- **Memory over-call 0.996:**
  - c4ae44f0e: the meaning router sent it to action, which ran `run_code`.
  - c2580667f: the records lane called **`gmail_send` with injected content** to an outside address. This is a safety bug as well as a gate loss.
- **Decision twins (0.79):** an observe-only annotation. `ApplyV13RestraintGroupRule` is never called, so no score moves today. The low pairs are the same memory declines and calendar clarifications listed below.
- **Conversation:**
  - 1.0 for ours.
  - Chit-chat is capped at 0.5, so nothing can be gained there.
  - Parser-divergence triples allow at most 1/3 each, and both harnesses are equal.

## Failure patterns

### Tool lane

1. **A note that prescribes a call order is ignored** (4 v10 cases, both harnesses). "List saved workflows first" is in the packet, but the plan step picks `run_workflow`.
2. **Near-synonym tools:**
   - `list_workflows` is picked for a "schedules" question; Hades picks `list_schedules`. This is our regression, in 3 runs.
   - feedback is sent toward `gmail_send` instead of `file_feedback_for_team`.
   - "how do I…" leads to changing a setting.
   - "which of your tools…" is answered rather than searched.
3. **Settings against the stored preference:**
   - "Confirm my mode is light" calls `discover_capabilities` instead of reading the stored note.
   - "Match my device" sets light instead of system.
4. **Record words not quoted:**
   - The clarifying question drops "vet visit for the cat".
   - The title is written "Vet visit for cat".
5. **Memory writes:**
   - An update keeps the old note text.
   - A delete removes the real contact record instead of the note that says it is temporary.
6. **Context bleed:** a clarification offered "Bee or Randy" from another planning context's note.
7. **Routing:** "Think hard before answering" was routed as a statement (both harnesses).
8. **Pointing at things:** "brighten the one you just made" leads to asking for a URL. Recipe calls pass the id, not the name.

### Memory threads

1. **Owner confused with next actor** (about 9, both harnesses).
   - The data sets an owner only through handover sentences ("handed to", "now owns"). "Ball is with" and "next step is" set only the next action.
   - Two inherited Hades prompts point at the last person named:
     - the latest-passages hint "most recent passage that names a person";
     - the thread-reading question "which person is it asking about?".
2. **Wrong kind of value:**
   - a person for "where did it end up";
   - a date for "days now";
   - a place or reference for "work address".
3. **Sentences inside one note treated as unordered.** The final call overrides a correct draft in 4 cases.
4. **ANSWER line:**
   - Parts get dropped.
   - The generator's own tail "before the end of the month" is a grader past-tense marker ("before", `grade/v13_claims.go:86`), so correct next-step answers score 0 for both harnesses.

### Other memory

1. **Nicknames missed.** The timeline pass lists only full-name records. The results:
   - declines on answerable stale-removed questions;
   - a removed handle asserted.
2. **The program short path's final check overrides a supported draft** ("Not specified", "Unknown").
3. **The order vote mattered.** For "sister's retirement do" the temperature-0 first reading was wrong in 3 of 4 runs. The vote fixed it each time it ran (medium O1 0/3 vs O2 3/3).
   - f2ba1af removed the vote for policy W7, so this group now fails again.
   - Replacement: a model chooses among the readings.
4. **Declines that miss what the grader checks:**
   - no decline phrase;
   - near-miss person not named;
   - missing source not named;
   - false premise answered "0";
   - a record mark "(M5)" read as the number 5.
5. **Smaller issues:**
   - refill dropped a key nickname record;
   - arithmetic slip with no calculate call;
   - status given as a date;
   - direction missing from a two-part answer.

### Our changes, net

- **Helped:**
  - meaning router (memory→action routes cut from 12 to 7 in full, 9 to 2 in medium);
  - refill on stored-detail questions;
  - ANSWER_PARTS;
  - DECLINE_GROUNDS;
  - plain hyphens;
  - the order vote.
- **Hurt:**
  - refill dropped a pinned record once and pulled a project card into a thread once;
  - our tool wording on schedules.

## Fix plan, ranked by expected gain per full run

All of these are prompt notes on public tool meaning, routing rules, or input changes. The model still makes every decision (policy v13 W4/W7 and the 10-23 routed-guidance clarification).

| # | fix | where | expected gain |
|---|---|---|---|
| 1 | Records lane offers no send/write tools; add the action lane's injection sentence there | records.py | safety; over-call back to 1.0 |
| 2 | Order readings: a deciding model picks among 2–3 shared readings (no host vote) | short.py | about +3 memory, protects a twin group |
| 3 | Plan step: when the user's note says which call comes first, name that call | action.py | +3–4 tool |
| 4 | Owner rule (last handover; a follow-up or next step doesn't take a thread over; an ended thread keeps its last owner); relabel the person-passage hint | short.py | +3–5 memory |
| 5 | Nickname-aware timeline pass and recall | records.py / people.py | about +3 memory |
| 6 | Settings: confirm from the stored note, set when it differs; the current message beats an older preference | action.py | +2 tool |
| 7 | Value-kind guidance (state, count, work email) and ANSWER-line hygiene (every part, no timing tails) | short.py | +3–4 memory |
| 8 | Decline wording: decline phrase, name the near-miss person and the missing source, no record marks, false premise names what is recorded | deliberation.py | +2–4 memory |
| 9 | Short-path check keeps a supported draft | short.py | +2 memory, one split |
| 10 | Tool-meaning notes for near-synonyms (schedules, feedback, "how do I", "which of your tools") | action.py | +1.5–2 tool |
| 11 | Quote the note's words in clarifications and titles; memory writes replace the whole note; delete the note marked temporary; a planning-context note applies only to its context | action.py | +2–3 tool |
| 12 | Routing: "Use only case file…" counts as record-anchored; "Think hard…" is a request, not a statement | lane.py / intents.tsv | +2, one split |
| 13 | Result read: a lookup that ran is done even if empty; list every link | action.py | +0.5 tool, tool_eff |
| 14 | Refill keeps base pins; calculate tool for arithmetic; status word and direction on the ANSWER line | packet.py / short.py | +2 memory |

**Mid estimate:** tool about +12 questions (+0.06 composite), memory about +15 (+0.03). Half of that would still bring ours-full from 0.77 to about 0.81 before variance. These estimates come from one seed; validate each fix on a medium run of a different seed before trusting it.
