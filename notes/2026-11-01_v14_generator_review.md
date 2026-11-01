# 2026-11-01 — v14 program generator, read against our misses

Source: repos/ditto-subnet at 4a187e62, `research/dittobench-datagen/universe/` (v13_contract.go,
personal.go, v14_supersession*.go, v14_process_family.go, v14_membership_family.go,
v14_temporal_families.go, v14_role_families.go, v14_family_mix.go). Grader: `grade/v13_claim_set.go`.
Review precedents: `.agents/skills/backroom-review/references/precedents/`.

Tools (analysis only, never in a harness):
- `practice/gates/v14_oracle.py` recomputes each program case's exact shape from the seed (the same
  FNV/sha256/splitmix draws as the generator). It matched all 40 program cases of seed 897500335867350922.
- `practice/gates/v14_shapes.py` tabulates every local bench-14 run by shape (`--census`, `--misses SHAPE`).

No model calls, no credits spent.

## How a program case is built

- **One case file per group, four members.** base, renderer-invariant and distractor-invariant share
  one record scope; the counterfactual has its own scope. All members' records go to one user
  ("miner"), so each twin question sees the same pooled notes: every row three times, once per renderer,
  plus the distractor member's decoy (business: a "Separately, an unrelated workstream…" clause in the
  binding row; personal: a "Separately, …" row filed last).
- **The three rewordings differ only in an opener and a closer.** The question body (`qform`) is drawn
  per group, so the evidence and the asked sentence are identical across a twin group. A split is pure
  sampling noise on identical input.
- **Filing order is story order** at v14 (`v13CaseFileSlot`): timestamps follow the row's place in the
  story, so "oldest first by filing day" is the right reading order for every family. Dates written
  inside a record (sequence, as-of) override filing order.
- **Per seed: 10 twin groups** (4 business, 6 personal) plus 3 enterprise groups = the 13 the
  metamorphic gate counts. A split costs ×(1 − 0.40/13) ≈ −3.1 %; a group wrong on all three costs
  about 3 × 0.2 %.

### Shapes per seed (36 seeds, `v14_shapes.py --census`)

| shape | groups / seed |
|---|---|
| supersession chain (owner, status, 5 of the 6 personal domains) | 7.0 |
| membership fold (school list) | 0.97 |
| client vs vendor | 0.47 |
| identity join (name 0.22, contact 0.17) | 0.39 |
| process (first open step + owner) | 0.39 |
| event sequence (nth / before / after, relative dates) | 0.33 |
| channel as of a date | 0.25 |
| custody (holder or actor) | 0.15 |

Business groups 0–1 are always owner and status chains; group 2 draws one temporal family
(sequence / process / as-of); group 3 draws one role family (client-vendor / custody / identity).

### The chain space is smaller than the code suggests

`drawV14ChainPlan` draws the template (`% 6`), the cue mode (`% 4`) and the unnamed-revert coin (`% 2`)
with `v13Index`. FNV-1a's low bit is the parity of its input bytes, so for one group the three low bits
differ by a fixed constant (the `v14Coin` comment admits the same defect elsewhere). Result, checked over
3000 random seeds:

- **"Back to the original" never renders.** The `revert` template (A, B, A) always names A again.
- **`revert-to-middle` (A, B, C, then back) is always unnamed:** "goes back to the previous entry",
  "reverts to the previous entry instead", "is back to the previous entry", or the plain "went back to the
  entry before the last change", "is back to what it was before the most recent change", "returned to the
  previous arrangement". The answer is B.
- Cue modes pair with templates: revert, change-then-declined and error come announced or cue-free;
  revert-to-middle, declined and second-error come announced or misplaced. Milestones (3 values) have
  only change-then-declined/free, declined/misplaced, error/announced, second-error/announced.

So there are 12 chain shapes (4 for milestones). The coupling is a generator defect and can be fixed at
any time, so nothing we build may rely on it. It only tells us which shapes our runs have actually met.

## Where v6's line (v30 → v6) loses, by exact shape

Local runs with traces: v30-released ×6, v6-f123 ×6, v6-hold ×6 (holdout + s43).

| shape | v30 | v6-f123 | v6-hold | reading |
|---|---|---|---|---|
| chain revert-to-middle / announced | 2/8 | 3/8 s1 | 14/24 s2 | "previous entry" read as the entry just before the revert note, so C instead of B |
| identity contact (initials) | – | – | 4/16 | "after every recorded reassignment" read as one answer per reassignment; names or the channel field given instead of the handle |
| chain declined / misplaced | 16/16 | 16/16 | 22/28 | all six misses are "pause it before then" (timing copied from "the plan was to pause it before then") |
| chain error / announced | 32/32 | 32/32 | 10/12 s1 | struck "Change logged … previous entry no longer stands": one rewording gave "not stated" |
| membership | 24/24 | 24/24 | 20/24 s1 | "after the school's change" applied as one change: the re-add, the addition and the swap were dropped |
| process reopened | 13/16 s2 | 16/16 | – | fixed by F1 |
| all other shapes | all right | all right | all right | as-of, sequence, custody, client-vendor, identity name, other chains |

Group splits over program twin groups: v30 2/60, v6-f123 1/60, v6-hold 4/60, which is about 0.4 per
full run, or −1.2 % on average. The live run 3 (0.854) had three: the revert-to-middle status group, the
membership group and the milestones error group, all three shapes above.

The draft/check pair: in 702 program answers the deciding call kept the draft's answer 622 times
(94 % right). It changed it 80 times, mostly to reformat. Real corrections: 8 identity-name (handle →
name), 4 process. Real harm: 2 process. So the check is worth keeping, but it also follows a wrong
draft (membership above).

## Root causes, stated generally

1. **Rewordings decide independently over identical input.** Each of the three runs its own deciding call,
   and the SHARED_DRAFT_NOTE invites disagreement ("it has not been checked … check the draft"). Any
   wobble on a hard group becomes a split.
2. **The v13 question forms presuppose a single change; v14 renders chains.** "after the swap", "after
   the rebooking", "after the school's change", "after the recorded revision", "after every recorded
   reassignment/change/handover". The model reads them as one particular change, or as "one answer per
   change". They mean: now, with every recorded change applied, one current value (or the one current list).
3. **Unnamed going-back.** "Back to the previous entry" means undoing the latest change still standing,
   so the value before it. A going-back note always moves away from the value that held just before it.
   F2 put this as one clause inside CHAIN_NOTE and failed (0/9). The model needs to see the before/after
   of each change, not only be told the rule.
4. **Value hygiene.** A plan or step is the action alone, without when it is due ("before then"). A
   contact is the handle or address the notes list for that person, found through the directory when the
   notes name the person another way. It is not a channel or medium.

## Proposed general fixes (not started; code and credits only on the user's go-ahead)

- **G1: one checked answer per twin group, prompt-only.** The first rewording to reach a key runs the
  deciding call as now. Its checked reply goes to the later rewordings' deciding calls as prompt text:
  "an earlier reply to this same question over these same notes, already checked against them: give the
  same value, replying to the message as asked". The model writes every reply. Host code never compares,
  retries, overwrites or substitutes.
  - **Allowed:** this is the shape the 2026-10-29 ruling cleared (precedent
    `october-29-reused-draft-no-disagree-clause`: a reused model-sampled answer entering the prompt only
    as text, even with an "answers must agree" note).
  - **Not allowed:** host code that ships the earlier reply as this case's final text would be I3/I4
    under the same precedent.
  - **Effect:** removes most of the splits (≈ +1.2 % average, and the 0.854-type tail) on every seed.
  - **Cost:** the later rewordings wait for the first decision instead of the draft only. That is about
    one extra call's latency, well inside 300 s.
- **G2: "after the change" reading**, one sentence in PROGRAM_SYSTEM. It reaches every chain, membership,
  custody and identity question on every seed.
- **G3: before → after lines in the shared draft.** The draft writes one short line per note that changes
  the thing asked (what held before it, what holds after it), then the ANSWER line. "Back to the previous
  entry" then reads off the last line's "before". The same lines fold a list (membership), step states
  (process), a holder (custody) and an owner (identity). This is model-written reasoning in the draft
  only; the deciding call still replies briefly.
- **G4: value hygiene**, two clauses: an action without when it is due; a contact is the listed handle.
  F6 folds into G4.

F7 (temperature 0, fixed seed) is superseded by G1: scored calls go through OpenRouter's choice of
provider (Bedrock about 87 %, Groq 13 %), so a seed would not hold across calls anyway.

## Test plan (when approved)

- **Questions:** only the program questions (40 per seed) on the seven seeds with v6 traces:
  897500335867350922, the holdout seeds 2330430686809638580, 9174290677768307797 and
  4249690561755544879, and the king seeds 4137466957291471344, 3374597426558320626 and
  5704156236337906855.
- **Runs:** two rounds of the candidate. Platform providers, concurrency 8.
- **Baseline:** the saved v6 traces, so nothing is re-run.
- **Measures:** splits, whole-group misses by shape (`v14_shapes.py`), and no loss on the shapes that
  are right today.
- **Cost:** about 560 cases, roughly $0.6. Balance $5.75.
