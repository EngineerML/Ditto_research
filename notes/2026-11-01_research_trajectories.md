# Why v14 program answers fail and why twin groups split — evidence from every saved trajectory

Date: 2026-11-01. Read-only analysis. No model calls, no runs, no repo or git changes.
Model in all traces: `openai/gpt-oss-20b`, reasoning effort medium. Temperature and seed are unset.

## 0. Data and files

- **Scope:** every `practice/2026*_ditto-harness-*` folder with a `report.json` and bench_version 14 that has program
  cases. That is 140 runs and 4,259 program-case rows. 4,139 of the rows are joined to their trace; the v8a runs
  without a trace are the exception. Every row is mapped to its exact generator shape through `v14_oracle.shapes(seed)`.
  All case ids matched.
- **Key designs (November):**
  - v30-released: 6 runs on the 3 king seeds.
  - v6-f123: 6 runs on the king seeds.
  - v6-hold: 6 runs, on the 3 holdout seeds plus 3 × seed 897500335867350922.
  - v7-prog: 3 runs, with the ledger-echo bug.
  - v7-prog2: 7 runs, one on each s44 seed.
  - v7-1: 6 runs. The seventh, on seed 5704, had no report yet.
  - v6-f2b: 3 one-group runs.
- **October bench-14 designs (secondary):** combined-v5g…v9g (47 runs), v5-* (41 runs) and dan0l-v28-trace (6 runs).
  These used an older harness. Their notes had no filing dates (an ordering call was used), some served distractor
  questions were typo'd, and several runs had timeouts. They are used here for cross-design patterns only.
- **Files** (all in the scratchpad `…\scratchpad\`):
  - `program_cases.json` / `program_cases.csv`: the per-case table. Columns: run label, seed, run, case id, shape,
    domain/group, relation, score, decided_first (read an earlier draft or reply = False), notes hash, answer, expected,
    events.
  - `program_calls.json`: every model call per case (full messages and reply).
  - `stages.json`: per case, what the shared draft, ledger or earlier reply said, and whether it was right.
  - `miss_causes.json`: the root cause assigned to every miss in the key designs.
  - `briefs/*.txt`: compact readable dumps of every failing twin group (notes once, then each member's calls).
  - Scripts: `build_table.py`, `stages.py`, `flips.py`, `classify.py`, `phrases.py`, `qforms.py`, `hazards.py`,
    `perseed.py`, `shapes_tab.py`.

Costing convention used throughout: a wrong program answer costs ≈ 0.2 points of composite, and a split twin group costs
≈ 3.1 points.

## 1. Headline findings

1. **The three rewordings see byte-identical input.** In every November design, the notes block of the deciding call is
   identical across base, renderer and distractor. This holds for 60/60 groups in v6 and 70/70 in v7-prog2. In v30, 3
   groups differ only by where the shared draft is placed. The system prompts are identical too. The served questions
   differ only in opener and closer, and error rates are flat across relations: v6-hold 10/11/10 and v7-1 8/8/5 misses
   out of 60 for base/renderer/distractor. **So a split is never caused by the input. It is caused by a member re-deciding
   on a knife-edge item.**
2. **Most losses come from a handful of cue templates, not from shapes as such.** The clearest case is the unnamed
   going-back. The template "From now on X **reverts to the previous entry instead; the newest entry governs**" is
   right in **9 of 86** twin answers across all designs (10 %). Every other going-back wording is right 87–100 % of the
   time; for example "returned to the previous arrangement" is right 145/166. The revert-to-middle shape is hard only in
   this one wording.
3. **The model can do the bookkeeping; the free-form reply then undoes it.** On that hard wording, single-reading
   designs get the shared draft right 0/27 times (v6) and 0/6 times (v30). v7's before→after ledger gets it right
   **18/21** times, yet the reply after the ledger ships the right value only **6/21** times. The reply is told "the
   entries decide wherever the ledger differs". It re-reads the raw sentence and returns to its prior reading.
4. **Every split in the key designs is a member departing from a shared artifact.** The artifact is the shared draft,
   the earlier reply or the final check. The departures go both ways:
   - v30: the final check flipped a right process answer twice (2 splits in 6 runs);
   - v7-1: the later rewording overrode a correct earlier reply in 4 of its 5 harmful departures;
   - v6-hold: the deciding call corrected a wrong draft for only one member (fixes 7, harms 2).

   In the v6/v30 shape (one shared draft, then a check per member), most misses are the draft being wrong and every
   member keeping it. That is deterministic and costs 3 × 0.2. Splits come from the check sampling differently per member.
5. **The remaining misses are deterministic reading defaults of a 20B model on generator phrasings.** Each fails the
   same way in every run of every design:
   - "the plan was to pause it **before then**": 16/16 answers that kept the timing scored 0;
   - "**After every recorded reassignment**, what contact…": 2/18 and 2/6 right for the hardest forms, against 100 % for
     "Who currently holds…";
   - "**After the school's change**": the model applies only the one change made by the school;
   - a struck entry after "the previous entry **no longer stands**": read as erasing the item ("not stated", "none");
   - a glossary label returned instead of its value ("joraelfin").
6. **Counterfactual members are structurally easy.** They name the final value outright ("is Sheridan Kenney instead"),
   carry one copy of each row (4–9 records against 13–27) and have no decoy row. They are right 100 % in v30/v6-f123 and
   95–98 % elsewhere, so they tell us little about twin difficulty. The decoy rows ("Separately, …") were never chosen as
   an answer, except when v7-prog's echo bug served the whole ledger.
7. **Design ranking on the same seeds, misses and splits per run.**
   - King seeds: v6-f123 has 0.8 misses and 0.17 splits per run. v30 has 1.5 misses and 0.33 splits, the splits coming
     from its final check. v7-prog2 has 2.2 points lost and 0.33 splits per run.
   - Holdout seeds plus seed 897: v7-prog2 has 0.25 splits per run. v6-hold has 0.67 splits and v7-1 has 1.25; v7-1's
     later rewording re-checks and flips.

## 2. Design-level numbers

All program cases. s = split twin groups, w = groups wrong on all three rewordings.

| design | runs | acc (all) | twin acc | cf acc | splits/run | all-wrong groups |
|---|---|---|---|---|---|---|
| v30-released | 6 | 0.963 | 0.950 | 1.000 | 0.33 | 2 |
| v6-f123 | 6 | 0.979 | 0.972 | 1.000 | 0.17 | 1 |
| v6-hold | 6 | 0.858 | 0.828 | 0.950 | 0.67 | 8 |
| v7-prog (echo bug) | 3 | 0.733 | – | – | 5.67 | 1 |
| v7-prog2 | 7 | 0.896 | 0.881 | 0.943 | 0.29 | 7 |
| v7-1 | 6 | 0.908 | 0.883 | 0.983 | 0.83 | 5 |
| v5-* (Oct) | 41 | 0.940 | 0.939 | – | 0.34 | 19 |
| combined-* (Oct) | 47 | 0.820 | 0.816 | 0.917 | 0.45 | 78 |
| dan0l-v28 (Oct) | 6 | 0.694 | 0.694 | – | 0.83 | 16 |

Same seeds, score out of 40 with splits and all-wrong groups (`perseed.py`):

| seed | v30 | v6-f123 | v6-hold | v7-prog2 | v7-1 |
|---|---|---|---|---|---|
| 3374… (king) | 37 w1, 37 w1 | 37 w1, 38 s1 | | 36.5 w1 | 34 w2 |
| 4137… (king) | 38 s1, 39 s1 | 40, 40 | | 39.5 | 40 |
| 5704… (king) | 40, 40 | 40, 40 | | 37.4 s1 w1 | – |
| 897500… | | | 34 s1 w1, 32 s1 w2, 29 s2 w2 | 34 s1 w1 | 32 s2 w2 |
| 2330… | | | 40 | 40 | 39 s1 |
| 9174… | | | 37 w1 | 36 w1 | 37 w1 |
| 4249… | | | 34 w2 | 31 w3 | 36 s2 |

Seed 897500335867350922 is the seed of the live run 3 (0.854). Locally it reproduces the live result: v6 split 1–2 groups
there in all three runs. The live split groups match the local ones. They are the standing-status revert (the hard
wording), membership ("after the school's change") and the milestones struck entry.

## 3. Root causes of wrong answers (every miss in the key designs read from its calls)

Counts are misses in v30 / v6-f123 / v6-hold / v7-prog2 / v7-1 (v7-prog is listed separately). Points per run use
0.2 per miss and 3.1 per split.

### C1. Unnamed going-back read as "the entry just before this one"

- **Where:** 38 misses and 7 splits in the five key designs (v7-prog adds 2 misses and 1 split).
- **Notes as shown** (seed 3374, chores):
  1. "the recycling run is Makenzie Greene's job" (A)
  2. "Change logged: … now Ariana Wilcox, and the previous entry no longer stands" (B)
  3. "Update: … now Vincent Nelson, replacing the earlier entry" (C)
  4. "**From now on the person doing the recycling run reverts to the previous entry instead; the newest entry governs**"
- **Expected:** Ariana Wilcox. **Answer every time:** "Vincent Nelson", so the change note is read as a no-op.
- **Template specific** (`phrases.py`, all designs):

  | going-back wording | right |
  |---|---|
  | reverts to the previous entry instead; the newest entry governs | **9/86** |
  | returned to the previous arrangement | 145/166 |
  | went back to the entry before the last change | 64/70 |
  | is back to the previous entry, and the last change no longer stands | 49/54 |
  | goes back to the previous entry, replacing the last change | 22/24 |
  | is back to what it was before the most recent change | 25/25 |

  The hard template is the generator's ordinary "From now on X is Y instead; the newest entry governs" with Y = "the
  previous entry". "Newest entry governs" plus "previous entry" points the model at the most recent prior entry. Where
  the wording adds "and the last change no longer stands", it gets B.
- **Not caused by renderer copies:** v7 shows each statement once (`once_each`, 16 → 6 notes) and the single reading is
  no better.
- **What works:** an explicit before → after line per entry. The ledger wrote "[M4] Vincent Nelson -> Ariana Wilcox"
  in 18/21 hard cases. A ledger line of the form "Vincent Nelson -> Vincent Nelson (changed)" is a visible
  self-contradiction (a change that changes nothing).
- **What breaks it:** the reply turn. Examples:
  - v7-prog2 seed 3374: the ledger said "NOW the recycling run: Ariana Wilcox". The reply said "The recycling run is
    currently assigned to Vincent Nelson". The two later rewordings read that reply and repeated it, so the group was
    consistently wrong.
  - v7-1 seed 4249: ledger and first reply were both "Kathryn Choate". The later base rewording was told to "check the
    reply above against the entries" and answered "Nicholas Floyd", which split the group.
- **Frequency:** the hard template appears in 0.19 twin groups per seed (36 cached seeds).

### C2. A struck entry read as erasing the item

- **Where:** 4 misses, 2 splits.
- **Example A:** "Change logged: the status … is now tentative, and **the previous entry no longer stands**", then
  "That entry … being tentative was wrong and has been struck". Two v6-hold members answered "not stated" and
  "No status". The shared draft had been right ("postponed"), and the per-member check undid it.
- **Example B (v7-prog2, seed 5704):** the ledger tracked "person behind the allotment society" and "organiser of the
  allotment society" as two items. Striking the organiser left "organiser: none", and the reply was "The allotment
  society currently has no organiser". **Root cause: the same slot is worded differently across entries** (person
  behind / organiser / run by), and the struck entry's "previous entry no longer stands" is read literally.

### C3. A proposal taken as the change, and the dropped request not linked to its item

- **Where:** v7-1, 3 misses, all three members wrong.
- **Example (seed 3374):** "Draft update for sign-off: the date … is now 13 January 2026", then "The request to switch
  the date … to January 13, 2026 was dropped".
- **Ledger:** "[M2] fitting: 19 December 2025 -> 13 January 2026 (changed)". The drop became a separate item, "The
  request to switch …: none -> dropped". Answer: "13 January 2026", which is also the counterfactual's value, so the
  twin post-pass flagged it counterfactual_insensitive.
- **Same shape elsewhere:** v30 and v6 read the raw notes in one pass and were right 12/12 here. v7.1's "whole values,
  word for word" ledger wording made whole sentences into item names, and that broke the linking.

### Q1. "After the X's change" read as one particular change

- **Where:** 5 misses, 2 splits.
- **Example (seed 897, camp list):** the notes are "packed lunch, spare socks, art smock, water bottle" → "The school
  took the spare socks off" → "Scratch the earlier change … spare socks is back" → "The school added a torch" → "swap
  the water bottle for a bus pass". The question is "**After the school's change**, what does my niece need…?" The
  answer was "packed lunch, art smock, water bottle", which applies only the first school change and stops.
- **Pattern:** the v13 question form presupposes one change, and the model honours the presupposition. The form is
  usually fine (35/36 for some list names) and fails on this group (10/18 across designs). It is stochastic, so it
  produces splits.

### Q2. "After every recorded reassignment" answered once per change

- **Where:** 11 misses.
- **Answers:** "@lumen-80 ; @plinth-45", "D. Joseph ; N. Haas", "egret.77@… ; spindle.73@…".
- **By question form:** "After every recorded reassignment, what contact…" was right 2/18, 2/6 and 25/39. "Who
  currently holds the … role" was right 100 %.

### L1, L2, L3. Label indirection: the glossary and the directory

- **Where:** 14 misses.
- **L1, label for value:** "what contact should I use to reach the belorvale" was answered with "joraelfin". The
  glossary entry "joraelfin is the standing way to reach them" was taken as the answer.
- **L2, stopped one hop early:** the answer was the name ("Nicholas Haas") rather than the directory handle
  "@corvid-31". The chain is "N. Haas now holds belorvale" → "@corvid-31 is Nicholas Haas".
- **L3, client and vendor swapped (v7 only, 6 misses):** both ledgers listed "dovaibion: Oakhurst Logistics" and
  "NOW weraynmark: Kestrel Studio". The reply took the weraynmark ("the organisation billing us") for "commissions the
  work and pays us". v7-1's ledger even recorded both label meanings correctly, and the reply still picked Kestrel.
  v6-hold read the raw notes and was 4/4.
- **Lesson:** restructuring the notes into label lines separates each label's meaning from its value. The reply then
  anchors on the first label-shaped NOW line.

### V1, V2. Value boundary: the shipped value is not the generator's value

- **Where:** 13 misses plus 5 partial credits.
- **V2, timing kept:** "The audiobook plan renews on Jan 15, 2026; the plan was to pause it before then". The answer
  is "pause it". **Every one of the 16 answers that kept "before then" or "before renewal" scored 0.** "pause" alone was
  accepted. This is deterministic in every design: v6-hold 6/6 wrong, v7-1, v5-full.
- **V1, shortened in v7:** answers like "collect signatures", "book venue" and "permission slip" got 0.5 or 0.8. The
  ledger paraphrased the value and the reply copied the paraphrase.
- **What the grader rejects:** the parsed ANSWER never failed on punctuation or format. The grader accepts date and
  time format variants, the glossary code ("tundra" for "on hold") and the name "pause". It rejects:
  - added content (a timing qualifier);
  - a second candidate value (a list of owners, or an earlier value);
  - any distractor or earlier chain value that appears in the served text (see E).

### Q3. The asked field misread

- **Where:** v7-prog2, 3 misses (v7-prog adds 2). "What's the next action on the audiobook plan" was answered "Renew on 15 January 2026". The
  ledger's NOW lines put "renewal date" first, and the reply took it as the action.

### P1. A later pass overruling a right answer

- **Where:** v30, 3 misses, 2 splits.
- **Example (seed 4137, process):** the reopening "the step to draft the proposal failed its check and is open again"
  sits after an unrelated checkpoint note. The draft and the deciding reply were right ("draft the proposal ; Ella
  Sheldon"). The "One last check … its last line first" call rewrote two members to "collect the signatures ; Shawn
  Lawrence".
- **Status:** v6's F1 (the final check only when no ANSWER line) removed this mechanism: 12/12.

### E. The served text carried more than one candidate value

- **Where:** v7-prog only, 23 misses and 16 splits, about 18 pts per run.
- **What happened:** the reply repeated the ledger, so earlier values and decoys were in the served text. In 21 of
  these cases the parsed ANSWER was exactly right ("@corvid-31", "08:20", "Joel Gonzalez") and still scored 0
  ("critical claim … not satisfied"). The fix (v7-prog2) removed the cause entirely: 0 such misses afterwards.

### October-only causes (older harness)

- **Format-variant linking failure, deterministic:** the struck entry quoted "6:30 pm" but the entry it strikes said
  "18:30". The model never linked the two and answered "18:30" 12/12 (v5), 19/21 (combined) and 6/6 (dan0l).
- **"empty response / no response from harness":** 3 per run in several combined runs.
- **chain:error/free:** 48/84 and 71/120 right in October, against 12/12 in November.

## 4. Which pass makes the error

Each first-stage artifact is compared with what the case finally shipped (`stages.py`, `flips.py`).

| design | artifact right → final right | artifact right → final wrong (overrule) | artifact wrong → final wrong (kept) | artifact wrong → final right (fix) |
|---|---|---|---|---|
| v30 (shared draft) | 216 | 2 | 6 | 0 |
| v6-f123 (shared draft) | 220 | 0 | 5 | 1 |
| v6-hold (shared draft) | 181 | 2 | 29 | 7 |
| v7-prog2 (ledger) | 222 | 11 | 3 | 0 |
| v7-1 (ledger) | 187 | 10 | 6 | 0 |
| v7-prog2 (earlier reply, later rewordings) | 122 | 2 | 15 | 1 |
| v7-1 (earlier reply, later rewordings) | 102 | 4 | 11 | 1 |

The ledger rows use a substring test, which over-credits the ledger on V2 cases ("pause it" ⊂ "pause it before
then"). The C1 counts were checked by hand.

- **v6/v30:** almost every miss originates in the single shared reading and is kept by every member, so it is
  consistent. The per-member check fixes a few, but only for some members. Those are the v6 splits.
- **v7:** the ledger is the most reliable artifact in the pipeline (C1: 18/21). Most of v7's misses are the reply
  overruling a right ledger, or the first reply's error being faithfully copied by the later rewordings. The later
  rewordings' re-check harms about 4× more often than it fixes (v7-1: 4 to 1).
- **Older designs:** October v5 and combined show the same shape at scale. Fixes 21 / 12, harms 11 / 11, and 60 / 99
  wrong drafts kept.

## 5. Deterministic or stochastic

- **Deterministic:** wrong in every run of every design, all three members.
  - The hard going-back wording on chores 3374: v30 6/6, v6 5/6, v7 6/6.
  - "pause it before then" (9174, 4249).
  - Contact by initials (897): no run of any design gets all three members right; most runs get 0/3.
  - October: the format-variant struck time.

  These cost about 0.6 per group per run and almost never split.
- **Stochastic:** right in some runs, wrong in others, and the source of splits.
  - The hard going-back on status 897: v6-hold right 1/3, 0/3 and 1/3; v7-prog2 3/3; v7-1 0/3.
  - Membership "after the school's change" on 897: v6-hold 3/3, 2/3 and 0/3.
  - Struck after "no longer stands" (milestones 897): v6-hold 3/3, 3/3, 1/3.
  - Process reopen in v30.
  - In v7 only, "returned to the previous arrangement" (897 chores): v6 9/9 right, while v7's later rewordings flipped
    it.
- **Where splits come from:** items where the model's own probability of the right reading is somewhere between about
  20 % and 80 %. Every additional per-member decision on such an item is another draw. With identical inputs, the
  chance of a split is set entirely by how many independent draws the design takes per group, and by whether later
  draws are allowed to move.

## 6. v30-released and v6 on the same seeds

- **Same reading, same draft:** v6 inherits v30's shared draft and single reading. On the king seeds both fail the same
  group the same way (the chores 3374 revert, "Vincent Nelson"). v6-f123 once corrected it for one member, which split
  the group; v30 kept it wrong on all members.
- **Only difference that mattered:** v30's unconditional final check flipped a right process answer twice (−2 splits
  in 6 runs, ≈ −1.1 pts per run). v6's F1 removed it.
- **v6 does not fix:** C1, Q1, Q2, L1/L2 and V2. All of them showed up on the holdout seeds (v6-hold), and the v6-hold
  losses are almost all these causes.

## 7. What the notes look like when it fails

- **Size:** twin scopes hold 13–27 records (every row three times, from three renderers, plus one decoy). The
  counterfactual holds 4–9. With `once_each` this drops to 5–9 shown in v7. Size did not predict failure.
  Deduplication did not change the C1 rate.
- **Glossary files** (business groups) add 3–6 definition rows. Failures there are L1/L2/L3 (label for value, label
  meaning detached from value).
- **Where the cue sits:**
  - The hard cue is always the last change row, followed by 1–2 unrelated rows and the decoy.
  - "Misplaced" cues (the cue sits away from the change it refers to) are not harder than announced ones (145/166 and
    64/70 against 9/86 for the one bad announced wording).
  - The process reopen that v30's final check missed sits after an unrelated checkpoint row.
- **Decoys and renderer copies:** the decoy row is never the cause on its own. Renderer copies ("Shared calendar entry
  3", "From the fridge list (photo transcription, line 2)", email headers, table rows) never caused a miss by
  themselves.

## 8. Core principles

**Why answers fail (in order of cost):**

1. **The model's default reading of a few generator phrasings is wrong, and it is the same default every time.** The
   phrasings are:
   - "reverts to the previous entry instead; the newest entry governs";
   - "the plan was to X before then";
   - "after the X's change" and "after every recorded reassignment";
   - "previous entry no longer stands", then struck;
   - "is the standing way to reach them".

   No amount of re-asking fixes a default reading; it only resamples it. These are fixable only by changing *how the
   answer is computed*, not by asking again. Telling the model the rule once inside a long system prompt failed too
   (F2: 0/9).
2. **Structured state tracking is more reliable than free reading, but only if it is final.** An explicit before → after
   line per entry, with one current value per item, gets the hard going-back right 86 % of the time where free reading
   gets 0 %. The value of that structure is lost when a later free-form step is told the raw notes "decide wherever they
   differ". That step re-reads the ambiguous sentence and reverts to the default.
3. **Splits are created by per-member decisions on knife-edge items, never by the input.** Every extra call that can
   change a member's answer is an independent draw, the same for both directions of change: v6's per-member check,
   v30's final check and v7's later-rewording re-check all behave this way. A good design keeps the number of draws
   per group that can move the answer at one. Where a later pass exists, it must not be able to quietly flip a decided
   value. (The rule line still holds: the model writes every reply, and nothing host-side substitutes answers.)
4. **The served text must contain exactly one candidate value, in the generator's exact span.** The grader zeroes any
   reply that also carries an earlier value, a decoy, a timing qualifier or a second owner. It gives partial credit for
   shortened spans. Any intermediate representation (ledger, draft) that paraphrases or quotes multiple values leaks
   into the reply unless the reply is built from the value alone.
5. **Item identity and label indirection must be resolved before reasoning about change.** The generator words the
   same slot several ways (person behind / organiser / run by; renews / plan; "January 13, 2026" / "13 January 2026";
   "6:30 pm" / "18:30") and names fields through a per-file glossary. A design that keys state on surface wording
   splits one item into two, and then a strike or a drop applies to the wrong one. A design that separates a label's
   meaning from its value loses the client/vendor or contact/channel distinction.

**Properties a design needs:**

- one model-derived reading per twin group, which all three members reuse, with no per-member re-derivation step that
  can flip it;
- an explicit, checkable per-entry state transition (before → after, with "a change must change the value"), whose
  final state is what the reply carries, rather than an advisory "first reading";
- question forms that presuppose a change ("after the X's change", "after every reassignment") read as "the state now,
  one value";
- value extraction that returns the generator's span (the action without its timing, the handle rather than the name or
  label), and a reply that contains nothing else;
- slot and label resolution that happens before the change bookkeeping (map glossary codes, aliases and format
  variants onto one item).

**Estimated cost per run, by cause** (0.2 per miss, 3.1 per split, measured on the key designs; expected per random
seed using the 36-seed hazard frequencies):

| cause | where seen | cost per occurrence | frequency per seed | expected pts per run |
|---|---|---|---|---|
| C1 hard going-back wording (single reading) | v30, v6 | 0.6 all-wrong; ~25 % split, +3.1 | 0.19 | ≈ 0.25 |
| C1 overruled by a reply or re-check | v7 | ~1.5–2 | 0.19 + flips on easy wordings | ≈ 0.7–1.0 (v7-1 measured 1.85) |
| Per-member re-check flips (any shape) | v30 final check, v7 later rewording, v6 check | split 3.1 | — | v30 1.1; v7-1 ≈ 2.1 (4 splits in 6 runs); v6 ≈ 0.5 (king seeds) to 2 (holdout) |
| Q1 "after the X's change" (membership) | all | ~10 % split | 0.69 | ≈ 0.25 |
| Q2/L1/L2 contact via initials and "after every reassignment" | all | 0.4–0.6 | 0.36 | ≈ 0.2 |
| C2 struck after "no longer stands" | v6, v7 | ~30 % split | 0.11 | ≈ 0.1–0.4 |
| V2 timing kept ("before then") | all | 0.6, deterministic | 0.22 | ≈ 0.13 |
| V1 shortened via ledger, L3 client/vendor via ledger, Q3 field misread, C3 proposal (ledger designs only) | v7 | 0.1–0.6 | — | ≈ 0.3–0.6 together (v7 only) |
| E echo of the ledger | v7-prog | — | — | ≈ 18 (fixed) |

Measured totals per run in the key designs are:

| design | pts per run |
|---|---|
| v30 | 1.33 |
| v6-f123 | 0.68 (king seeds) |
| v6-hold | 3.20 (harder holdout seeds) |
| v7-prog2 | 1.62 |
| v7-1 | 3.32 |

The split terms dominate whenever a design lets members re-decide. The removable part for the v6 line is about 1–1.5
points per run on average, with a tail of 3–10 points on seeds that carry two or three knife-edge groups (live run 3).
Roughly half of it is splits; the other half is the deterministic C1/V2/Q2 readings.

