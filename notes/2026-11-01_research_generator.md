# SN118 bench v14 program questions: how they are generated and graded

Read-only research, 2026-11-01. No model calls and no credits spent; no repository files changed.

**Sources**
- Generator: `repos/ditto-subnet/research/dittobench-datagen/universe/` (v13_contract.go, personal.go, v13_calendar.go, v14_supersession.go, v14_supersession_families.go, v14_temporal_families.go, v14_process_family.go, v14_membership_family.go, v14_role_families.go, v14_family_mix.go)
- Surface noise: `gen/v13_surface.go`
- Grader: `grade/` (v13.go, v13_claims.go, v13_claim_set.go, v13_text.go, v13_quantity.go, v14.go, grade.go)
- Scorer: `services/dittobench-api/internal/scorer/` (scorer.go, v7.go, twins_v13.go) and `cmd/dittobench-api/` (v13_claim_provenance.go, v13_twins.go)
- Real examples: the 36 cached `/home/bittensor/ditto/.cache/datasets/v14_s*_salt0_full.json` datasets.

**How the claims were checked**
- I compiled the real grader offline: a scratch Go module with a `replace` directive pointing at the repo, `GOPROXY=off`. I graded about 45 hand-written reply variants against generator-built cases from 10 seeds. The results are marked "(probe)" below.
- Scratch tools:
  - Go probe: `C:\Users\Administrator\AppData\Local\Temp\claude\--wsl-localhost-ubuntu-24-04-home-bittensor-minos\3adafca1-9457-4695-b456-d48686e6121d\scratchpad\probe\main.go`
  - Per-shape example dumper: `C:\Users\Administrator\AppData\Local\Temp\claude\--wsl-localhost-ubuntu-24-04-home-bittensor-minos\3adafca1-9457-4695-b456-d48686e6121d\scratchpad\shapes_examples.py`
  - FNV parity check: `C:\Users\Administrator\AppData\Local\Temp\claude\--wsl-localhost-ubuntu-24-04-home-bittensor-minos\3adafca1-9457-4695-b456-d48686e6121d\scratchpad\parity.py`

**The earlier note `notes/2026-11-01_v14_generator_review.md` checks out.** The shape table, the 12-shape coupling, "filing order = story order" and the twin structure all hold. New in this report:
- the grader's exact zeroing lexicon (decline phrases, past markers, correction openers);
- the date, time and process traps;
- the note-number trap;
- the typo rules;
- the "the old" grader quirk.

---

## 1. Shared mechanics (every program family)

### 1.1 A group, its members and its scopes

- **Groups per seed.** There are 4 business groups (`v13-open-program`) and 6 personal groups (`v13-personal-program`). Each group has 4 members: base, renderer_invariant, distractor_invariant and causal_counterfactual. All members are rendered from one draw (`GenerateV13ProgramsForVersion`, v13_contract.go:977ff; `GenerateV13PersonalProgramsForVersion`, personal.go:555ff).
- **Business slots.**
  - Group 0 is owner-after-correction and group 1 is standing-status (both chains).
  - Group 2 is the temporal slot: one of event sequence, process or channel as-of (`V14TemporalFamily`).
  - Group 3 is the role slot: one of client-vs-vendor, custody (holder-vs-actor) or identity-join (`V14FamilyFor`, v14_role_families.go:87). Each draw is uniform over its three families.
  - Records-disagree sits at cycle slot 6, so it never reaches a scored run.
- **Personal domains.** The 6 personal groups take 6 of the 7 domains through a seeded permutation (personal.go:563). The school domain is the membership fold; the other six are supersession chains.
- **Case-file scope.**
  - Every row is prefixed `Case file <scope>: ` and every question starts `Use only case file <scope>.`
  - `v13ProgramRecordScope` (v13_contract.go:1198) gives base, renderer and distractor one scope (world 0) and the counterfactual a second scope (world 1).
  - All rows of all members go to the same user ("miner"), all in wave 0.
- **Pooled evidence.** A twin question's scope therefore holds every story row three times (once per renderer) plus the distractor member's decoy. The counterfactual scope holds one copy of the flipped story.
- **Same timestamps in both worlds.** Base and counterfactual rows carry identical timestamps, because they share one calendar timeline per group. Only the case-file ID separates two contradictory worlds.
  - Example (seed 897500335867350922, group 0): the base "For the record, the belorvale on kestumgate is Maximus Bennett." and the counterfactual "… is Orianna Allen." are both stamped 2025-04-09T11:13.

### 1.2 Filing order and timestamps

- **Rows are shuffled for presentation but stamped in story order.** `v13CaseFileSlot` (v13_calendar.go:33): from v14 the timestamp of a row is its story position.
  - Business story order: glossary A, glossary B, binding row, state record 0, state record 1, chain extras, neutral record, temporal-family extras (v13_contract.go:1127).
  - Personal story order: Records[0], Records[1], chain extras, neutral record, fold extras, then the decoy row last (personal.go:595-600).
- **Story order is the order the oracle folds.** Sorting a scope's rows by timestamp (filing date) therefore gives the exact order to fold.
- **Trap: the visible row numbers are presentation positions, not story order.** The numbers are "Subject: workstream note N", "Pasted table row N", "operations_dump[N]", "Shared calendar entry N" and "(photo transcription, line N)".
  - Real example: "workstream note 8" is the *first* status record (`fennadset's kestilora opened as amber`, 2025-01-28), and "workstream note 3" is a later change.
  - Never order by these numbers.
- **Dates written inside a record override filing order where the family uses them.**
  - Event sequence: the filing order is a random permutation independent of event dates (`s.Log`, v14_temporal_families.go:173ff).
  - Channel as-of: changes are filed in date order, with the neutral row anywhere among them.
  - Plan dates (milestone checkpoint, renewal, appointment) are future dates and are not filing dates.

### 1.3 Renderers and decoys

- **Business renderer.** `renderV13Record` (v13_contract.go:1021) uses four renderers: conversation lead, email ("Subject: workstream note N\nFrom: operations@example.invalid"), pasted table row, and `operations_dump[N] { … }`. The ops renderer rewrites `"; "` to `", "`, so plan lists use commas there.
  - Acknowledgement responses such as "Later revisions will govern; I'll take the superseding entry." are boilerplate, not evidence.
- **Personal renderer** (personal.go:530): chat note, shared calendar entry, forwarded text (quoted), and fridge-list photo transcription.
- **Renderer per member.** Each member gets `v10Renderers[(group+variant)%4]`, so the three twins use three different renderers.
- **Business decoy.** The distractor member appends to its *binding* row: `Separately, an unrelated workstream <entityLabel>=<decoyAlias> handles <decoy remit>. <family decoy clause>`. The decoy clause is, for example, `Its belorvale is Callie Bush.` or `Its kestilora is cobalt.`
  - The decoy value is always a `distractor_answers` entry.
- **Personal decoy.** The distractor member adds one extra row, filed last: "Separately, mowing the lawn is Lauren Aguilar's job.", "Unrelated: Jace Gregory's orthodontist fitting is on 13 June 2026.", "Separately, the Edinburgh weekend leaves at 1.25 pm." and so on. It always names a *different subject* (chore, appointment, trip, service, event, list).
- **Neutral record.**
  - Business: "… has its next checkpoint on <date>", "The first milestone review for … is pencilled in for …" or "A progress read-out on … is scheduled for …".
  - Personal: "<relation> asked me to remind everyone about the family calendar…", the shared shopping list, or the MOT.
  - It is never evidence. It carries a date, which matters for the date-typed answers (§3).

### 1.4 Glossary indirection (business only)

- **Made-up labels.** Each seed draws made-up labels for 11 roles: entity, alias, owner, status, event, client, vendor, action, responsible, channel and correction (`generateV13Schema`, v13_contract.go:97).
- **Two glossary rows define them** (`v13Glossary`, v13_contract.go:960ff). They are filed first, with a seeded rotation and a split point. Examples:
  - "belorvale is whoever is accountable for it"
  - "lumaawire is the party that pays us for it"
  - "ulmaojor means a replacement of prior state, newest wins"
- **Status alias legend.** Status groups add one: "Status shorthand in this workspace: amber means approved, tundra means on hold, …". From v14 it covers all four group classes plus the extra counterfactual class. Status values appear in records *only* as these jargon words (amber, slate, ember, cobalt, harbour, quartz, tundra, velvet).
- **Binding row.** `<entityLabel>=<alias>; <aliasLabel>=<alias>. Its remit is <purpose>.` The question names the subject by remit only, for example "the workstream in this batch covering the holdback hiring loop".
- **Personal records have no glossary.**

### 1.5 Question assembly and the three rewordings

- **Business:** `v13Question` (v13_contract.go:656). **Personal:** `v13PersonalQuestion` (personal.go:522).
- **The body is the same for all four members.** The `qform` index is keyed per group (`qform-<group>`).
- **Only the opener and the closer vary per variant.**
  - Business openers include "Work only from this batch's own field meanings." and "Resolve the workstream by its remit, then answer."
  - Personal openers include "Quick one from my own notes." and "Before I forget —".
  - Closers include "Just the name is fine." / "Give the person's name." / "Answer with the name only."
- **Final shape:** `Use only case file <scope>. <opener> <Body> <closer>`.
- **So the three twin questions ask the identical question over identical evidence.** Any split is pure sampling noise.

### 1.6 Typo noise (`gen/v13_surface.go`)

- **Coverage.** About 70% of memory questions and about 70% of seeded pair prompts get 1 to 4 token edits, at one edit per 12 words (`v13TypoSurfaceBps = 7000`, line 78; budget at line 84).
- **Protected text is never edited.** That is the union of every case's graded values and its `WritingProtected` (names, values, scope IDs and the labels the run uses; `v13GlobalProtected`, line 282).
- **Unprotected text is edited.** This includes remits ("the hopdbeck horing loop"), "Case file" ("Czse file"), cue and operation words ("turned dpwn", "lgoged in eror", "reutrned to the previous arrangement", "Ucpate:") and question wording ("Whech day …").
- **Each twin question gets its own typos.**
- **Answer values, scope hex IDs and person names are always intact.** Match the scope ID exactly; match everything else fuzzily.

### 1.7 Counterfactual and the scorer

- **The counterfactual changes exactly one record** of the same story; the answer must move (generation fails otherwise, v13_contract.go:985).
- **Correctness threshold.** A case is correct when its score is at least 0.5 (scorer.go:890).
- **Metamorphic consistency.** Groups are counted by `TwinGroup` over base, renderer and distractor, which each carry `twin_group`; the counterfactual carries none. The fraction of split groups enters the v7+ composite at max penalty 0.40 (`v7MetamorphicMaxPenalty`, v7.go:66; `compositeGateV7`).
  - With 13 groups per run (10 program and 3 enterprise), one split costs about 0.40/13 ≈ 3.1%.
- **Twin post-pass** (twins_v13.go:247). If the counterfactual's normalized asserted answer equals the base's, the base and counterfactual pair is marked `counterfactual_insensitive`. The default posture is *observe*: annotation only. An honest harness never trips it, because the worlds differ.
- **Claim provenance** (v13_claim_provenance.go). The credited span must be model-emitted text, not harness-authored prompt text. It runs in shadow unless enforce is set.

---

## 2. Families

The "Distractors" line in each family matters: for value-typed claims, only the expected forms and the `distractor_answers` are visible to the grader (§3.3).

### 2.1 Supersession chains (business owner and status; personal household, hobbies, appointments, milestones, subscriptions, travel)

Code: v14_supersession.go and v14_supersession_families.go.

#### Story

- **The initial record is the family's v13 first record**, for example:
  - "kestumgate was first assigned to Maximus Bennett as its belorvale."
  - "fennadset's kestilora opened as amber."
  - "Mercedes Dooley has the dog walk on the chores rota."
  - "Our eldest's vaccination booster was booked for 2026-05-16."
  - "Renewal for the gym membership lands 19 February 2026 — I'd decided to cancel it."
  - "For the visit to Grandma the train leaves at 08:20."
- **Then come 2 or 3 state records from a template** (v14_supersession.go:76-95). They replace v13's single announced correction.

#### Ops and the fold

Ops: S = adopted set, P = proposal, W = proposal turned down, A = proposal accepted, E = latest adopted change logged in error, C = confirmed.

`v14ChainFold` (line 99):
- The adopted values form a stack.
- **S** pushes a value.
- **P** sets a pending value. **A** pushes the pending value. **W** clears it.
- **E** pops the latest adopted value.
- **C** is a no-op.
- The answer is the top of the stack.

#### Templates

| template | base steps → answer | counterfactual steps → answer |
|---|---|---|
| revert | S B, S A → **A** | S B, S D → D |
| revert-to-middle | S B, S C, S B → **B** | S B, S C, S D → D |
| change-then-declined | S B, P C, W C → **B** | S B, P C, A C → C |
| declined | P B, W B → **A** (initial) | P B, A B → B |
| change-logged-in-error | S B, E B → **A** (initial) | S B, C B → B |
| second-change-logged-in-error | S B, S C, E C → **B** | S B, S C, C C → C |

A is the initial value; D is a fourth value used only by the counterfactual (`ExtraPerson`, `ExtraClass`, `ExtraDate`, `ExtraTime`).

#### Record wordings

The `%[1]s` subject is a "voice":
- business: "the belorvale on kestumgate" / "the kestilora of fennadset";
- personal: "the person doing the dog walk", "the organiser of the book club", "the date of our eldest's vaccination booster", "the status of my neighbour's wedding", "the plan for the gym membership is to …", "the departure time of the train for the visit to Grandma".

| op | wordings (v14_supersession.go:180-250) |
|---|---|
| S plain | "X is V." / "For the record, X is V." / "Noting that X is V." |
| S announced | "Update: X is now V, replacing the earlier entry." / "From now on X is V instead; the newest entry governs." / "Change logged: X is now V, and the previous entry no longer stands." |
| P plain | "There is a proposal to change X to V." / "Someone suggested changing X to V." / "A request came in to switch X to V." |
| P cued (misplaced mode only) | "Draft update for sign-off: X is now V, replacing the current entry." / "Proposed change, pending agreement: from now on X would be V instead." / "Update requested: X to become V, superseding what is on file." |
| W | "The proposal to change X to V was turned down." / "We did not go ahead with changing X to V." / "The request to switch X to V was dropped." |
| A | "…was accepted." / "We went ahead with changing X to V." / "…was approved." |
| E | "The note that X is V was logged in error and never took effect." / "Disregard the entry saying X is V; it was a mistake." / "That entry about X being V was wrong and has been struck." |
| C | "The note that X is V was checked and stands." / "Double-checked the entry saying X is V; it is right." / "That entry about X being V was verified and holds." |
| unnamed revert, previous (plain) | "X went back to the entry before the last change." / "X is back to what it was before the most recent change." / "X returned to the previous arrangement." |
| unnamed revert, previous (cued) | "Update: X goes back to the previous entry, replacing the last change." / "From now on X reverts to the previous entry instead; the newest entry governs." / "Change logged: X is back to the previous entry, and the last change no longer stands." |
| unnamed revert, original | "went back to what it was originally" / "back to the original entry" / "returned to the first arrangement on file" (plus cued variants). **Never renders today** (§4). |

**E, W and A always restate the value they refer to**, so each of these records is self-contained.

#### Cue modes

Drawn per group (`drawV14ChainPlan`, line 148; `renderV14Chain`, line 257):
- **announced:** every S uses the announced forms.
- **cue-free:** every S is plain, so only filing order tells precedence.
- **misplaced:** every S *except the governing one* uses the announced forms, and every P uses the cued forms. The governing record is plain. Line 268: `announce := Cue==announced || (Cue==misplaced && i != governing)`.

#### Unnamed revert

Under unnamed revert, an S whose value equals the *previous* adopted value renders as "back to the previous entry", without restating the value. It means: undo the latest standing change, so the value before the current one. In revert-to-middle that is **B**, not C.

#### Real examples

- **revert-to-middle, announced** (seed 8975…, status): "opened as amber" → "From now on … is tundra instead" → "… is harbour instead" → "From now on the kestilora of fennadset reverts to the previous entry instead; the newest entry governs."
  - Answer: tundra = **on hold**.
- **declined, misplaced** (seed 1682…, status): "opened as amber" → "Draft update for sign-off: the orinynelle of belenline is now velvet, replacing the current entry." → "The proposal to change … to velvet was turned down."
  - Answer: amber = **in review**.
- **second-error, announced** (seed 1682…, travel): "9:50am" → "Update: … now 11:40 am, replacing the earlier entry." → "Change logged: … now 4:25pm, and the previous entry no longer stands." → "That entry about … being 4:25 pm was wrong and has been struck."
  - Answer: **11:40**.
- **revert, cue-free** (seed 8975…, subscriptions): "I'd decided to cancel it." → "The plan … is to upgrade it." → "Noting that the plan … is to cancel it."
  - Answer: **cancel it**. Counterfactual: "… is to pause it" → pause it.

#### Questions (qforms)

They mean "the value in force now, after every record":
- **Owner:** "who currently holds the L role on S?" / "after every recorded reassignment, who is the L for S?" / "for S, which person stands as L today?"
- **Status:** "what L currently stands for S?" / "after the recorded revision, what is the standing L of S?" / "for S, which L governs now?"
- **Household:** "after the swap, who is on X now?" / "whose job is X these days?" / "who has X on the rota as it stands?"
- **Hobbies:** "who runs X now?" / "who is organising X these days?" / "after the handover, who's in charge of X?"
- **Appointments:** "when is R's X now?" / "what date did R's X end up on after the change?" / "which day is R's X, as it stands?"
- **Milestones:** "what's the status of R's X now?" / "is R's X still on — what did it end up as?" / "where does R's X stand after the latest message?"
- **Subscriptions:** "what did we settle on doing about X before it renews?" / "what's the next action on X, as it stands?" / "remind me — what are we doing with X?"
- **Travel:** "what time does our L for X leave now?" / "after the rebooking, when does the L for X depart?" / "which L time are we on for X?"

Phrases such as "after the swap", "after the rebooking" and "after the recorded revision" presuppose v13's single change. In v14 they mean *final state after all records*.

#### Claims and accept lists

- **Owner, household, hobbies:** person, the full name only.
- **Status (business):** the alias term of the answer class **or** the class's plain synonyms. For example, on hold accepts "tundra", "on hold", "paused", "parked", "suspended", "frozen".
- **Milestones:** status. For example, postponed accepts "postponed", "pushed back", "delayed", "moved to a later date"; cancelled also accepts "called off" and "not happening".
- **Subscriptions:** action. For example, "cancel it" accepts "cancel", "cancellation", "stop paying for it", "end the subscription"; "switch it to annual billing" accepts "annual billing", "go yearly", "pay for the year". The v14 progressive forms ("pausing it") are also accepted.
- **Appointments:** **date** kind, day granularity, parsed (§3.4).
- **Travel:** time. Accept forms are `HH:MM`, `h:MM am/pm`, `h:MMam/pm`, `h.MM am/pm`, `h:MM AM/PM`, `HHMM`, and bare `h:MM` only when the hour is below 10 (`V13TimeAccept`, personal.go:160).

#### Distractors

Only the decoy value is a distractor:
- business owner: the decoy person; status: the decoy class canonical plus the decoy alias;
- personal: the decoy person, the decoy date accept forms, the decoy time forms, or the decoy class.

**Older chain values are *not* distractors.** For value kinds they are invisible to the grader. For dates they still count, because every date is extracted.

#### Surface variety

- The same time or date is printed in different forms in different records. `v13TimeProse` and `v13CalendarProse` pick a form per record key; for example "7:25pm" in a proposal and "19:25" in its withdrawal.
- Normalize before comparing values across records.

### 2.2 Membership fold (school packing list)

Code: v14_membership_family.go.

#### Story

1. The first list of 4 items: "Packing list for my niece's camp week — packed lunch, spare socks, art smock, water bottle."
2. Then, in seeded order:
   - **remove** one original item: "The school took the spare socks off the camp week list." / "Update for the X: no Y needed any more.";
   - a later **re-add** of the same item: "Scratch the earlier change for the X: the Y is back on the list." / "The school changed its mind again — the X does need the Y after all.";
   - **replace** one other original item: "For the X, swap the B for a Y." / "The X list now has a Y instead of the B.";
   - optionally a plain **add**: "One more for the X: they want a Z too." / "The school added a Z to the X list.";
   - optionally a **no-op**: "The school says no N for the X; it was never on our list anyway, so nothing changes." / "They mentioned a N is not needed for the X, but we never had one on the list.";
   - the neutral row anywhere.

The re-add always follows its removal.

**Answer:** original 4, minus the replaced item, plus the swap item, plus the added item if present. That is 4 or 5 items, or 5 or 6 with the add.

**Counterfactual:** the replace record swaps a *different* original item, so two members change.

**Question:** "what is on R's X list now?" / "after the school's change, what does R need for the X?" / "list everything currently required for R's X." Closers: "Every item, please." / "Give the full current list." / "All of the items."

**Claims:** one `set_member` claim per item, weight 1/n and not critical. The score is the fraction hit; the case is correct at ≥ 0.5.

**Distractors:**
- the replaced item;
- the decoy list's item ("Separately, Eric Ross's sports day list is just a library book.");
- the no-op item.

**Any of these asserted in an eligible clause zeroes every member claim** (probe: "<list>. The unrelated workstream has water bottle." → 0). Probe "packed lunch, …, torch; no water bottle." → 0: ";" splits sentences, and a sentence that *starts* with "No" is a correction opener that retracts the whole previous sentence, which is the list (§3.2).

The grader has a set-only exception: a clause ending in "X was removed" or "has been removed (from the list)" reads as historical (v13_claims.go segment rules; `removedThenPlaceV14`). Probe: "…, torch. The water bottle was removed." → 1.0.

Real example, seed 8975…: answer "packed lunch; spare socks; art smock; bus pass; torch". The spare socks were removed and re-added, the water bottle was swapped for a bus pass, and a torch was added.

### 2.3 Client vs vendor (v13-carried)

Code: v13_contract.go:803.

- **Story:** two rows, "<alias>'s <clientLabel> is ORG." and "<alias>'s <vendorLabel> is ORG.", in three forms each. The glossary defines:
  - the client label as "is the organisation that commissions it and pays us" / "names our paying customer for it" / "is the party that pays us for it";
  - the vendor label as "is the supplier we pay" / "names the outside party we pay" / "is the organisation billing us".
- **Question:** "on S, which organisation commissions the work and pays us — as opposed to the supplier we pay?" / "…our paying customer rather than our supplier." / "which organisation is the commissioning party on S (not the one we pay)?"
- **Answer:** the client organisation. **Counterfactual:** the client is re-recorded as another organisation.
- **Distractors:** the vendor organisation and the decoy client organisation.
- **Trap:** naming the vendor in an eligible clause ("the vendor is X") zeroes the case. Write "not X" or omit it.
- **Example** (seed 1382…): "Saltmarsh Analytics is logged as the zoriarline on dovaeora." / "dovaeora's kestujor is Bellweather Logistics." Answer: **Saltmarsh Analytics**.

### 2.4 Identity join (name / contact / contact with initials)

Code: v14_role_families.go:422.

#### Story

- **Two owner records in v13 announced wording:**
  - "X was first assigned to … as its L." / "At the outset the L on X was …" / "… took X as L when it opened.";
  - "Under this batch's <corrLabel>, the L on X passed to …; the earlier assignment no longer stands." / "A later <corr> hands X's L to … — the newest entry governs." / "<corr> note: … now holds L on X, replacing whoever held it before."
- **There is no chain.** The second record is the current owner.
- **A directory row lists four entries:** first owner, current owner, decoy owner and a near-miss person. Forms: "Contact directory for this batch: @pylon-11 belongs to Evan Peterson, …" / "@lumen-80 is David Joseph" / "Kayla Richardson uses plinth.40@deck.example.invalid".
- **Handles:** `@stem-NN` or `stem.NN@domain.example.invalid`. The near miss reuses the current owner's stem with a number that differs in both digits (`@corvid-31` vs `@corvid-70`).

#### Modes

- **name:** the owner records use handles; the question asks for the *person's name* ("Give the person's name, not their contact").
- **contact:** the owner records use full names; the question asks for the handle ("Give the contact exactly as the directory lists it").
- **contact with initials:** the owner records say "D. Joseph" or "N. Haas". Resolve by surname; surnames and given names are unique within a seed.

**Answer:** the current owner (record 2), mapped through the directory to the asked side.

**Counterfactual:**
- name mode: the current owner's handle is rebound to another person in the directory;
- contact mode: the current owner gets a different handle.

**Claims:** person (name mode) or value (the handle, exact).

**Distractors:**
- name mode: the near-miss name, the first owner's name and the decoy's name;
- contact mode: the near-miss handle, the first owner's handle and the decoy's handle.

Names are not distractors for contact questions and handles are not distractors for name questions, so "@corvid-31 (Nicholas Haas)" is safe.

**Example** (seed 8975…, contact with initials): "D. Joseph took peraipath as belorvale when it opened." → "ulmaojor note: N. Haas now holds belorvale on peraipath …" → directory "@corvid-70 is Channing Thomas; @corvid-31 is Nicholas Haas". Answer: **@corvid-31**.

### 2.5 Multi-step process (first open step and owner)

Code: v14_process_family.go:130, 216.

#### Story

1. **The plan record, always filed first**, lists 3 to 5 steps with planned owners: "The <actionLabel> sequence on X runs strictly in this order: (1) collect the signatures, <respLabel> Madeline Fuentes; (2) test the backup restore, <respLabel> Skyler Robertson; (3) …".
2. **Then closures in step order:**
   - done: "Update on X: P tested the backup restore, so that step is closed." / "P <past> for X; that step is complete." / "On X, P has now <past>.";
   - exactly one dropped step when possible: "The step to X on A has been dropped: it is no longer needed and counts as closed." / "We are skipping the step to …; treat it as closed.".
3. **Inserted at seeded positions:**
   - an optional early finish of a later step: "Ahead of the plan, P already <past> for X." / "P <past> for X early, out of turn; that step is complete.";
   - one reassignment: "Under this batch's <corr>, the <resp> for the step to X on A is now P." / "<corr>: P takes over as <resp> for the step to X on A.";
   - the neutral row.

#### Modes

- **untouched:** the answer step (index ≥ 2) is never mentioned again; every step before it is closed.
  - Counterfactual: the done record of the step just before becomes "P has started to X on A but has not finished; that step is still open." / "… is under way with P and not yet complete."
- **reopened:** the answer step is reported done and then reopened: "The step to X on A has been reopened: it has to be done again." / "On A the step to X failed its check and is open again."
  - Counterfactual: the reopen becomes "… was checked again and stays closed." / "A second look … confirmed it is finished; it stays closed." The next step answers.
- **Reassignment** targets the base answer's step or the counterfactual answer's step, so one member's owner comes from the plan and the other's from the reassignment.

#### Question, answer and claims

- **Question:** "following the recorded order of its L steps, which step on S is the first one still open, and who is its R now?" / "name the earliest L step in the planned order that is not yet closed, and the person currently named R for it." / "which L step on S comes first in the plan among those still open, and who owns it after every recorded change?"
- **Answer:** first step in plan order whose final state is open, plus its current owner (reassigned owner if that step was reassigned, else the planned owner).
- **Claims:** action (0.5) and person (0.5), neither critical. One half right gives 0.5, which counts as *correct*. Action accept forms are verb phrases only ("test the backup restore", "run the restore test"); past-tense narration such as "tested the backup restore" never matches.

#### Distractors

Every *other* step's canonical, the decoy person, and the decoy step. Both claims see all of them.
- Probe: "X, owned by Y. The <other step> step is closed." → **0.0**.
- Probe: "X, owned by Y. Someone already did the earlier one." → 1.0.

#### Examples

- **reopened/3** (seed 3374…): collect the signatures (dropped), test the backup restore (done, then "failed its check and is open again"), book the venue (reassigned to Joshua Patton).
  - Answer: **test the backup restore; Skyler Robertson**.
  - Counterfactual: book the venue; Joshua Patton.
- **untouched/3** (seed 3874…): migrate (dropped), close the old account (done by Randy Garcia), create the test accounts (reassigned to Henry Salcido).
  - Answer: **create the test accounts; Henry Salcido**.

### 2.6 Event sequence (nth / immediately before / immediately after)

Code: v14_temporal_families.go:173, 359.

#### Story

- **5 to 8 dated events,** 2 to 6 days apart, all in the year before filing.
- **One relatively dated event (two when there are 7 or more)**, written as "N days after/before the <event>". The anchor is the nearest absolutely dated event within 27 days. A relative event is never the answer, the partner or the named event; anchors are never relative.
- **Absolute event forms:** "On D, A logged a L: EVENT." / "A's L entry dated D reads EVENT." / "A L for A — EVENT — is on record for D."
- **Relative event forms:** "A logged a L: EVENT, 5 days before the design sprint." / "… reads EVENT, held N days after the X." / "… is on record for N days after the X."
- **Dates use the year forms only:** ISO, "Month D, YYYY", "Mon D, YYYY" or "D Month YYYY".
- **Filing order is a random permutation** (`s.Log`). The answer's record is never filed first or last (`v14KeepInterior`, line 285).

#### Question and answer

- **nth:** "counting from the earliest, which L was the <k-th> one on S?" / "in date order, what was the <k-th> L…?" / "putting every dated L on S in order from the earliest, which comes <k-th>?". The ordinal is 1-based ("second" = index 1) and is never the first or the last.
- **after:** "which L on S came immediately after the X?" / "directly followed the X?" / "what was the next L after the X?"
- **before:** "came immediately before the X?" / "directly preceded the X?" / "what was the last L before the X?"
- **Answer:** sort by actual date (resolve relative dates first) and pick the asked position. The answer is never the first or the last event by date.
- **Counterfactual:** moves the answer event's date just past its neighbour (the partner), which then answers.

#### Claims and distractors

- **Claim:** event; the accept forms are small synonym sets.
- **Distractors:** every other event of the sequence *except the named one*, plus the decoy event. Listing the timeline zeroes the case. The named event may be echoed ("right after the audit came …").

#### Example (seed 1139…, "directly preceded the vendor swap")

| event | date |
|---|---|
| reference call | 9/29 |
| incident | 10/5 |
| vendor swap | 10/10 |
| handoff | 10/14 |
| kickoff (5 days before the design sprint) | 10/20 |
| design sprint | 10/25 |
| pricing workshop (4 days after the design sprint) | 10/29 |

Answer: **incident**.

### 2.7 Channel as of a date

Code: v14_temporal_families.go:309, 461.

#### Story

- **Four channel changes** (email, phone, Slack, ticket portal, video meeting), 9 to 30 days apart. They are filed in date order, with the neutral row anywhere among them.
- **The first record:** "A's L was set up as C on D." / "On D, A opened its L over C." / "The L first agreed for A, on D, was C."
- **Later records:** "From D, A's L moved to C." / "On D the L for A switched to C." / "A changed its L to C with effect from D."

#### Question, answer and counterfactual

- **Question:** "which L was in force for S on Q?" / "on Q, which L did S use to reach the other side?" / "for S, what L applied on Q?"
- **Q lies strictly inside interval K**, where K is 1 or 2 (neither the first value's interval nor the last's), and at least 2 days after `Days[K]`.
- **Answer:** the channel of the latest change dated ≤ Q. Q never equals a change date.
- **Counterfactual:** moves change K to just after Q (answer K−1) or change K+1 to just before Q (answer K+1).

#### Distractors and example

- **Distractors:** every other channel plus the decoy channel. Giving the history ("it moved to phone, then video meeting …") zeroes the case.
- **Example** (seed 8975…, Q = 2024-10-13): email 8/25, phone 9/19, video meeting 10/7, ticket portal 10/18. Answer: **video meeting**. The counterfactual moves video meeting to Oct 14, so the answer is phone.

### 2.8 Custody (holder or actor; 1 or 2 hops)

Code: v14_role_families.go:317.

#### Story

- **Record 0, the first hop.** A performs a step and B receives the item. The sentence order varies, so "last name wins" fails:
  - "A <step> on X and passed ITEM to B.";
  - "Once A had <step> for X, ITEM went over to B.";
  - "B collected ITEM for X from A, who had <step>."
- **Record 1, the second hop (2-hop).** A different person C performs a step while B hands the item to D. The item is named only by its bare noun:
  - "C <step2>, and B handed the pouch for X on to D.";
  - "With C having <step2>, D took the pouch for X over from B.";
  - "B passed the pouch for X to D after C <step2>."
- **Record 1 (1-hop).** C performs a step and never takes the item:
  - "C <step2> on X; the folder did not change hands.";
  - "Later C <step2> for X without taking the folder.";
  - "C <step2> on X, and the folder stayed where it was."

#### Questions

- **holder:** "who has ITEM for S now?" / "after every recorded handover, who is holding ITEM on S?" / "for S, which person currently has ITEM?" The answer is the final recipient (B for 1 hop, D for 2 hops).
- **actor:** "who <step> on S?" / "on S, which person <step>?" / "name the person who <step> for S." The answer is the doer of that step (A or C), never the recipient.

#### Distractors

- holder questions: both actors, plus the first recipient for 2 hops, plus the decoy;
- actor questions: the holders plus the decoy.

The decoy clause is "Its copy of ITEM sits with E." or "There, E <step>." Naming the giver beside the answer ("D, who got it from B") zeroes the case.

#### Examples

- **holder/2-hop** (seed 5502…): "Jonah Roberts reconciled the manifest on lumaovwire and passed the courier pouch to Autumn Rodriguez." → "Henrry Alonzo booked the courier, and Autumn Rodriguez handed the pouch for lumaovwire on to Liam Chenault."
  - Answer: **Liam Chenault**.
- **actor/2-hop** (seed 3702…): asked "who countersigned the handover form" → **Elliott Humphrey**, not the holders Faythe Landry or Giovanni Carranza.

### 2.9 Families that do not reach a scored run

- **records-disagree** (cycle slot 6) and the v13 single-correction forms of latest-event, current-channel and next-action never reach a scored run.
- From v14 those three slots always render as sequence, as-of or process (`drawV14Temporal`, v14_temporal_families.go:145).
- No v14 program question needs "the records disagree".

---

## 3. How the grader decides (v14 policy)

### 3.1 Pipeline

`memoryV13`, grade/v13.go:51. The v14 policy is at grade.go:188. Steps, in order:

1. **Reply rewrites.** Fold typographic hyphens; read markdown as rendered (bold, bullets, headings and code ticks are removed; `PlainReplyTextV14`); rewrite a hyphen-joined multi-word value to spaces.
2. **Empty reply** → 0.
3. **Decline anywhere** → 0 for the whole case: `if resp.Abstain || anyPhraseV13(full, lex.decline)` (v13.go:104). The lexicon (grade.go:1154 plus v13_claims.go:162) includes:
   - "not stated", "i'm not sure", "don't know", "don't have", "no record", "no information", "can't find";
   - "no entry", "not recorded", "never recorded", "was never", "were never";
   - "there is no", "there's no", "there are no", "there isn't";
   - "no note(s)", "no mention", "no value", "no such";
   - "not available", "unavailable", "nothing about", "nothing for", "i have no", "have nothing", "can't confirm";
   - "never mentioned", "never told", "never gave", "never provided", "no longer have", "unable to find" and others.
   - Probes: "X; there is no later change." → 0. "X, because the change was never adopted." → 0. "X (later value not stated)." → 0.
4. **Claim set** (`gradeClaimSetV13`, v13_claim_set.go:16). Each claim is graded as its own value, date or time case (`memoryForClaimV13`, line 146).
   - The case's `distractor_answers` stay attached to every claim.
   - A *critical* claim (weight 1) that is not exactly 1.0 zeroes the case (line 113).
   - Partial-weight claims (process 0.5 and 0.5; membership 1/n) add their share.

### 3.2 Turning a reply into asserted candidates

`analyzeV13` and `segmentSentenceV13`, v13_claims.go:332, 397.

**Sentences.**
- Text is split at `. ! ? ; \n`. A period between digits is not a split.
- A sentence ending in "?" asserts nothing. Probe: "Is it X?" → 0.

**Clauses.** Commas, `)`, `:`, standalone dashes, an opening "(", and the contrast/boundary words ("but", "however", "whereas", "although", "though", "yet", "while", "instead", "and", …) split a sentence into clauses.

**A clause is ineligible (its values do not count) when it is:**
- **rejected:** opened by a rejection word up to the next clause boundary. The words are "not", "no", "never", "without", "rather than", "instead of", "except", "other than", "as opposed to", "unlike", "nor", "neither", any "-n't" form, …
  - "X, not D" is safe (probe → 1.0).
- **past:** contains a strong past marker outside the claim value itself. The markers are "used to", "previously", "formerly", "before", "before that", "before the", "earlier", "originally", "initially", "at first", "in the past", "back then", "old value", "prior to", "the old", "the previous", "the earlier", "the original", "outdated", "superseded" (except when it is the status value), "obsolete", "had been", "at the time", "no longer" (v13_claims.go:96).
  - Probes: "X before then." → 0. "It is back to the original entry X." → 0. "It is X, back to the original entry." → 1.0, because the marker sits in another clause. "X (as initially recorded)." → 1.0, because the parenthesis is its own clause.
- **echo:** contains "whether", "you asked", "your question", "the question", "if it", "asked me" or "you wanted to know".

**Correction opener.** A sentence *starting* with a correction word rejects the whole previous sentence (line 337). The words are "actually", "no", "rather", "sorry", "wait", "hmm", "oops", "correction", "i mean", "my mistake", "to be precise", "on reflection", "on second thought", "scratch that", "strike that", "let me correct", "i misspoke", "correcting myself".
- Probes: "X. No other change applies." → 0. "X. Actually, that is the current one." → 0.

**Weak past ("was", "were", "had").** A clause containing only a weak past marker, and no current marker such as "now", "currently", "today", "latest" or "current", is dropped *only if* another non-weak candidate exists (line 715).
- Probe: "It is X. D was the other one." → 1.0.
- Probe: "X. The unrelated workstream has D." → 0.

**Answer slot.** When `resp.Answer` is filled, it is authoritative (`collect`, line 609):
- a slot holding no known value → 0, even if the prose is right;
- prose present but not restating the slot value → `slot_not_in_prose` → 0;
- distractors are scanned only in the slot and in prose sentences that contain the slot value, so a distractor in *another* sentence is tolerated (probe "slot+prose-decoy-other-sentence" → 1.0);
- without a slot, every eligible clause of the whole reply is scanned.

### 3.3 Value-typed claims

Kinds: person, status, channel, organisation, action, event, value (handle), set_member and time. Code: `claimSpecV13` value branch (v13.go:627) and `knownValueExtractor` (v13_claims.go:910).

**Which values the grader can see.**
- Only two kinds of strings are recognized: the expected value with its accept forms (one key), and each `distractor_answers` entry (its own key).
- Any other string in the reply is invisible. That includes an older chain value that is not a distractor, a name not in the case, or a step not listed.

**Matching.**
- Matching is a case-insensitive, word-bounded substring test after folding (`foldV13`): typographic quotes to ASCII, NFKC-style ligatures, and whitespace collapse. Articles are not stripped and none are needed, since "the PE kit" contains "pe kit".
- Single common words are never matched.
- Pure numbers use number-token bounds.
- The progressive form of an action is also accepted ("pausing it").

**Zeroing rules.**
- Any distractor asserted in an eligible clause → 0 (v13.go:312).
- Hedging between the expected value and a distractor ("Either X or D") → 0.
- Two different keys → 0 (inconsistent); three or more → 0 (stuffing).
- Extra prose is harmless when it contains no other known value and no marker words.

**Time** (a value kind with `V13TimeAccept` forms):

| hour | accepted forms | fail |
|---|---|---|
| AM, hour < 10 | "8:20", "08:20", "8:20 am", "8:20 a.m." (because "8:20" is accepted) | "8am" |
| 10 to 12 | "11:40", "11:40 a.m.", "12:15 p.m." (the 24h form is the bare number) | "11am", "12pm" |
| PM, hour ≥ 13 | "17:55", "5:55 pm", "5:55pm", "5.55 pm", "5:55 PM" | **"5:55 p.m."**, "5:55", "5pm" |

The 24-hour `HH:MM` form is always accepted.

**Status.** Both the workspace jargon and the plain class are accepted. "superseded" is not treated as a past marker when it *is* the status.

### 3.4 Date-typed claims (appointments only)

Code: `dateMentionsV13` (v13_quantity.go:470) and the date `claimSpec`.

**Every date in an eligible clause is a candidate,** not only the known dates. Recognized forms are ISO, "Month D[, YYYY]", "D Month [YYYY]", "Month Dth", "Dth of Month", and unambiguous numeric forms.
- Mentions that are mutually compatible (equal wherever both specify a component) merge into one candidate.
- A missing year is compatible.

**So any second date in an asserted clause zeroes the case,** including an old booking or the neutral checkpoint date.
- Probe: "February 20, 2026 (moved from 16 May 2026)." → 0.
- Probe: "February 20, 2026, not 16 May 2026." → 1.0.
- Probe: "…; previously 16 May 2026." → 1.0.

**Grader quirk: an ISO date followed by a comma, or by a period that does not end the sentence, is not recognized** (line 488: a trailing `,` or `.` counts as "number-attached").
- Probe: "It is 2026-02-20, as rescheduled." → 0.
- The month-name form survives commas: "It is on February 20, 2026, as rescheduled." → 1.0.
- "Friday, February 20, 2026" → 1.0; "20 February" (no year) → 1.0.

### 3.5 What "not satisfied" means, per family

| family | claims (weight) | zeroed by |
|---|---|---|
| chains (person, status, action, time) | 1 critical | expected value absent from eligible clauses; decoy asserted; decline phrase; past marker or "before" in the answer clause; a correction-opener sentence after the answer |
| chain (appointment date) | 1 critical date | all of the above, **plus any other date** in an eligible clause |
| membership | n × 1/n | each missing item costs 1/n; any distractor item (replaced, no-op, decoy) asserted zeroes all; decline zeroes all |
| client vs vendor | 1 critical organisation | vendor or decoy organisation asserted |
| identity | 1 critical person or handle | near-miss, first-owner or decoy value of the asked side asserted; initials do not satisfy a name claim |
| process | 0.5 action + 0.5 person | any other step's canonical or the decoy asserted zeroes **both**; a wrong owner loses 0.5 (still "correct" at 0.5) |
| sequence | 1 critical event | any other sequence event except the named one; the decoy |
| as-of | 1 critical channel | any other channel of the history; the decoy |
| custody | 1 critical person | any actor (holder question) or holder (actor question); the decoy |

**Grader quirk ("the old"):** the step canonicals "close the old account" and "archive the old records" contain the past marker "the old". A clause naming them as *distractors* is therefore historical, and they never fire. When either is the *answer*, the claim-value masking keeps it eligible.

---

## 4. Generator quirks and defects

### 4.1 FNV parity coupling (chain plan)

`drawV14ChainPlan` draws the template (`v13Index % len(fit)`), the cue mode (`% 4`) and the unnamed-revert coin (`% 2`). All three use `v10Seed`, which is FNV-1a 64.

**Why the draws are coupled:**
- FNV-1a's low bit equals 1 XOR (the parity of the number of odd bytes in the input). The offset basis and the prime are both odd.
- Reducing by an even modulus keeps that bit.
- The salts `v14-chain-<d>-<g>`, `v14-cue-<d>-<g>` and `v14-revert-unnamed-<d>-<g>` differ by a fixed number of odd bytes ("chain" has 3, "cue" has 3, "revert-unnamed" has 7). So within one group, template-index parity = cue-index parity = unnamed coin.

**Verified over 4000 random seeds × groups** (`parity.py`):

| domain | possible (template, cue, unnamed) combinations |
|---|---|
| business, and personal with 4 values | revert/{announced, free}/named; change-then-declined/{announced, free}; error/{announced, free}; revert-to-middle/{announced, misplaced}/**unnamed**; declined/{announced, misplaced}; second-error/{announced, misplaced}. 12 shapes, about 1/12 each. |
| milestones (3 values: `%4` on both draws, so the low two bits couple fully) | change-then-declined/free, declined/misplaced, error/announced, second-error/announced only |

**Consequences:**
- "Back to the original" never renders, and the revert template always restates A.
- revert-to-middle is always unnamed ("previous entry"), so the answer is B.
- Misplaced cues never meet the revert, change-then-declined or error templates.
- This is a defect that can be fixed at any time (the code comment on `v14Coin` already acknowledges the parity problem). Nothing should rely on it.
- The newer draws are not affected: process, membership coins and role-family draws use `v14Coin` (`%1000 < 500`) or `v14Mix` (splitmix).

### 4.2 Other quirks

1. **The questions presuppose one change.** "after the swap", "after the rebooking", "after the school's change", "after the handover", "after the recorded revision/change", "after every recorded reassignment/handover". The chains have 2 or 3 operations, some of them proposals or errors. The intended meaning is always the final state.
2. **Subscription records and questions carry "before".** The initial record says "the plan was to X before then" and the question says "before it renews". "before" is a strong past marker, so echoing it in the answer clause scores 0 (this explains the six earlier "pause it before then" misses).
3. **The misplaced cue makes a pending proposal look like an adopted update.** "Draft update for sign-off: … is now X, replacing the current entry." Only the prefix (Draft…/Proposed change, pending agreement/Update requested) and the later "turned down" resolve it. Conversely, the governing record is the only plain one.
4. **"Change logged: … the previous entry no longer stands"** can sit on a change that a later record strikes (second-error/announced).
5. **Process done-records name the doer as the *current* owner** (`p.Owner(ev.Step)`, v14_process_family.go:258), even when the reassignment is filed later. The grammar "has now ran" also appears. Neither affects the answer.
6. **The no-op membership record contains "was never on our list".** Echoing "was never" counts as a decline (score 0).
7. **Row numbers are presentation order** (§1.2). Ordering by them reverses chains.
8. **Base and counterfactual worlds** share timestamps and live in one user's memory. Only `Case file <id>` separates them.
9. **Typos hit remits, cue words and question wording, never values** (§1.6). The remit match must be fuzzy; values can be copied exactly.
10. **The identity family is not a chain.** Its second record is v13 "announced"; the difficulty is the join and exact copying of the handle (the near miss shares the stem).
11. **Grader quirks:** ISO date followed by a comma; the "p.m." form for PM times; "the old" in two step names; a sentence-initial "No/Actually/Rather/Sorry/Wait/Hmm" retracts the previous sentence; decline phrases anywhere zero the case (§3).
12. **The correctness threshold is 0.5.** Process half-credit (step only or owner only) and membership with at least half the items count as correct for the consistency gate.

---

## 5. Core principles

### 5.1 Reading the evidence (holds for every family)

1. **Scope first.** Keep only rows whose `<…> file <id>:` matches the question's case-file ID exactly; the ID is never typo'd. Ignore the identical-looking other world and every other group.
2. **Collapse the renderer copies.** The same story row appears up to three times, with different framing and different typos but the same timestamp. Deduplicate by timestamp.
3. **Remove the decoy.** Drop any sentence about a *different* subject: "Separately, an unrelated workstream …", "Separately, <other chore/trip/service/list>…", "Unrelated: …", "There, E <step>.", "Its copy of … sits with E". The decoy's value is always a graded distractor.
4. **Bind labels through the glossary (business).** Map made-up field names and status jargon to their meaning through the scope's glossary rows. Identify the subject by remit (fuzzy match). There is one target alias per scope.
5. **Order by timestamp (filing date), never by "note N / row N / line N / dump[N]".** Filing order equals story order. Where a record states its own event date (event sequence) or effective date (as-of channel), order those events by that date instead. Plan dates (checkpoints, renewals, appointments) are never ordering keys.
6. **Treat each record as an operation on state and fold all of them.** Never pick "the latest record" or "the record with change vocabulary": cue words are deliberately misplaced in a quarter of the chains.
   - A plain or announced statement of a value **sets** it.
   - A proposal ("there is a proposal", "someone suggested", "a request came in", "draft update for sign-off", "proposed change, pending agreement", "update requested") **changes nothing** until accepted ("was accepted", "went ahead", "was approved"). If declined ("turned down", "did not go ahead", "was dropped"), it is discarded.
   - "Logged in error", "disregard … it was a mistake" and "wrong and has been struck" **undo the most recent standing change**: the value that held before it returns. "Checked and stands" and "verified and holds" change nothing.
   - "Back to the previous entry / what it was before the most recent change / the previous arrangement" **undoes the latest standing change** (the value just before the current one, not the value named in the record before the revert note). "Back to the original / first arrangement" means the first value.
   - Membership: start from the first list; apply removals, re-adds, replacements (swap B for Y removes B and adds Y) and additions; ignore removals of items never on the list.
   - Steps: all are open at the plan. Done, dropped, early and "stays closed" close a step. Reopened, "failed its check" and "started but not finished" open it. The answer is the first open step in *plan order*. Its owner is the planned owner unless a later record reassigns *that* step.
   - Custody: the item moves only on explicit handovers (passed to, went over to, collected from, handed on to, took over from). The holder is the last recipient in the chain. The person who did a step is the actor and is never the holder unless a handover says so.
   - As-of: the value in force on date Q comes from the latest change dated on or before Q.
   - Sequence: resolve "N days before/after the X" against X's absolute date, sort all events by date, then take the k-th, or the neighbour of the named event.
   - Identity: find the current owner from the owner records, then convert it through the directory to the side the question asks for. Initials resolve by surname. Copy handles exactly.
   - Role labels: "the party that pays us / commissions it / our paying customer" is the client; "the supplier we pay / billing us" is the vendor.
7. **Read every question form as "the final state after every record, unless a date is named".** "After the swap/rebooking/change/revision/handover/every reassignment" never means one particular change and never "one answer per change".

### 5.2 Writing the reply, given the grader

These rules make all three rewordings grade identically.

8. **One plain declarative sentence that states only the answer value(s).** Example: "It is now X." Optionally restate X in an answer slot. If the slot is used, the prose must contain the same value.
9. **Name no other value of the same type.** No previous owners, other steps, other events, other channels, the vendor, the giver or recipient beside the actor/holder, the replaced list item, the decoy, or other dates. If one is unavoidable, put it in its own clause opened by "not".
10. **Keep the marker lexicon out of the answer clause.**
    - Past markers: before, earlier, previous, original, initially, at first, the old, no longer, previously, at the time, had been.
    - Decline phrases *anywhere*: not stated, there is no, was never, no record, not sure, don't know, unavailable, no change.
    - Correction words at the start of a later sentence: No, Actually, Rather, Sorry, Wait, Hmm.
    - Question marks, hedges and echo words: either, maybe, whether, the question.
    - Do not copy timing phrases from the records ("before then", "before it renews").
11. **Use one canonical form per type:**
    - full names exactly as written;
    - handles verbatim;
    - times in 24-hour `HH:MM`;
    - dates as "Month D, YYYY" (avoid an ISO date followed by a comma);
    - status as the plain class or the workspace word;
    - actions as the bare verb phrase ("cancel it");
    - list items comma-separated with "and", every item present;
    - process as "STEP, owned by NAME".

### 5.3 Which surface features signal which rule

| surface in the scoped notes | rule |
|---|---|
| several records restating one attribute of one subject (owner/status/person doing/organiser/date of/status of/plan for/departure time of) | supersession fold (5.1 step 6) |
| "proposal / suggested / request came in / draft … for sign-off / pending agreement" | pending proposal: no effect until resolved |
| "logged in error / disregard … mistake / struck" vs "checked and stands / verified" | undo the latest change vs no-op |
| "back to the previous entry / before the most recent change / previous arrangement" | undo the latest change; the answer is the value before the current one |
| a first list plus took off / back on / swap X for Y / added / "never on our list" | membership fold |
| "(1) …, (2) …" plan plus closed / dropped / early / reopened / failed its check / takes over as | step-state fold, first open step in plan order |
| events each with a date, some "N days after/before the X"; question with an ordinal or "immediately before/after" | resolve dates, sort by date, positional pick |
| "set up as / switched to / moved to … from <date>"; question "on <date>" | as-of interval lookup |
| passed / handed / went over to / collected from, with a step verb in the same sentence | custody: holder = last recipient; actor = step doer |
| a "Contact directory / Who's who" row; owner records using @handles or initials | identity join |
| glossary "pays us / commissions" vs "supplier we pay / billing us" | client vs vendor role mapping |

### 5.4 Structural guarantees an answerer can rely on today

Pinned by generator tests and comments, not by the parity accident:
- **Exactly one answer value per case.** Every proposal in a chain is resolved by a later record. Every error or confirm record names the value it refers to.
- **Values are never typo'd.** Scope IDs are never typo'd.
- **Subject names are unique.** Surnames and given names are unique within a seed. Handles are unique, and the near miss differs in both digits.
- **Timestamps never tie** within a group and strictly follow story order. Event dates in a sequence never tie. As-of question dates are never on a change date.
- **The answer is never the first or last item of its ordering:**
  - as-of interval: neither the first nor the last value;
  - sequence: neither the first nor the last event by date or by filing;
  - process: never step 1.
  "Latest" or "first record" heuristics are wrong by construction.
- **The three twins of a group** always share the question body and the evidence. The counterfactual always has a different case-file ID and a different answer.
