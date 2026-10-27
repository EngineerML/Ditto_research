# SN118 generator competition: how it is scored, what a generator is, the rules (2026-10-27)

Sources (upstream ditto-subnet at 30e1e7d6, 2026-10-27): miners/dittobench-generator-starter-kit/README.md,
research/dittobench-datagen/docs/generator-competition.md, docs/v14-generator-credits.md, and the
live API (`ditto generator board`, `/api/v1/public/submission-terms/generator`).

## Money

- Since epoch 25962 (2026-10-26): burn 50%, agent competition 35%, generator competition 15% of
  total emission.
- The generator share is split by rank on each generator's latest scored round: 40/25/15/12/8%,
  renormalised when fewer than five qualify.
- Live board 2026-10-27 02:30 UTC: **4 eligible generators** (scores 0.296 with 22 discriminating
  cases, 0.047, 0.019, 0.005). A fifth qualified generator with any positive score takes a slot.
- Upload fee 0.05 TAO (inherits the agent fee), cooldown 1 hour per hotkey, `cases_per_seed` = 70
  now (settable 8..80; plan for 80).

## What is submitted

A deterministic Go main module (go ≤ 1.27.3, deps vendored, ≤ 4 MiB archive). Platform keeps the
source private. It reads one `GenerateRequest` on stdin
(`{"contract":"dittobench-generator/v1","seed":"<64 hex>","miner_hotkey":...,"cases":70,"grading_bench_version":13}`)
and prints one challenge pack: memory waves (≤ 4 users, 8 waves, 2,000 pairs) plus exactly
`cases` memory questions with gold answers, distractors and evidence pair ids. No network, no
model, 1 CPU, 1 GiB, 60 s per seed; the output must be byte-identical on a re-run (no clock, no
env, no map iteration into output).

## Validation (every seed, every case; one failure rejects the generator)

- answer kinds only value / number / money / date / direction / list / ordered_list (no stance,
  decline, clarify, absence);
- every accepted answer item appears in the named evidence pairs; no answer item in the question;
- the production v13 grader gives the gold 1.0, each accept_any ≥ 0.5;
- an empty answer, an abstention, an echo of the question, every distractor, and a dump of the
  user's whole memory all score < 0.5 (so every case needs an in-memory decoy);
- no duplicate fingerprint or repeated question within a pack; seed, hotkey and count echoed.

## Rounds and scoring

- A round per `epochs_per_round` epochs (one epoch, ~72 min, today). Seed = commit-then-reveal
  (Platform commits a secret one round earlier, mixed with the opening block hash), revealed six
  rounds later.
- Columns: 5 counted (best qualified by latest score, then never-seen ones, filled by the public
  default generator) + 1 challenger column for new generators. One column per owner. Each column
  runs on its own seed.
- Panel: the top agent owners by ledger (min 3) plus subnet reference agents. Each agent answers
  every column; the owner's own agents never count on their own column.
- Per case over eligible agents (solved = score ≥ 0.5):
  solvable = solved by ≥ 2 distinct owners; trivial = solved by all; discriminating = solvable and
  not trivial; credit = (1 − mean score) × (1 + 0.5 if the champion failed).
- Column score = Σ credit / ((1.5) · max(n, cases_per_seed)) × (1 − unsolved / (n − dup))².
  Duplicates (a fingerprint an earlier column or round already holds) earn 0. Unsolved cases earn
  0 and shrink the whole column quadratically.
- Practical ceiling per case is about 0.5: the best promotion candidates had panel mean 0.2
  (2 of 5 agents at exactly 0.5), so the per-case credit tops out near (1 − 0.2) × 1.5 / 1.5.
- Ledger score = latest scored round within 7 days; a void round never counts.

## Copy rules

- An identical archive or source tree is refused at upload.
- Behavioural copy: on a secret probe seed, ≥ 50% of a new submission's case fingerprints matching
  another owner's earlier submission rejects it.
- An unmodified starter kit is accepted once; its four families are 76/76 trivial in real rounds.

## Field evidence of what splits agents (docs/v14-generator-credits.md, rounds 25944-25967)

- Always trivial: the kit's update chain, two-hop, retraction and scattered list; needle and
  single-hop "as of" questions.
- Mostly unsolved (penalised): conditional, alias-reroute, owner-alias-email (3 of 6).
- Discriminating: revert-to-original (2-3 of 5 agents); a two-item nickname list (hard half rarely
  earned in full).

Our own failure analysis of the agents (notes/2026-10-25..27) is directly useful here: the
families our top-level design still misses (world-story owner/order/quantity, parser divergence
on reported speech and negation, absence twins) are memory shapes a generator could produce.
