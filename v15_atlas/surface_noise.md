# SN118 bench v15: how strange request and record text can get

Scope: the v15 generator (`research/dittobench-datagen`) and scorer (`services/dittobench-api`) as checked out under `/home/bittensor/ditto/repos/ditto-subnet`. Paths below are relative to those two folders. The numbers come from 60 seeds: 30 seeds at salts 0–3 from `.cache/datasets`, plus 30 more seeds at salt 0. Structured numbers are in `surface_noise.json`. The helper tools are in `/tmp/atlas_surf/`. `servedgen` regenerates the exact text the scorer sends a harness.

## 0. Read this first: the harness never sees the dataset's typos

There are two different texts, and most of the confusion comes from mixing them up.

| | where it comes from | typo-v2 pass | used for |
|---|---|---|---|
| **Served text** (what `/run` and `/seed` carry) | generator output (`cmd/dittobench-api/main.go:1542-1571`) | **no** | the harness |
| **Dataset artifact** (`cmd/generate`, `.cache/datasets/*.json`) | the same cases after `V13ApplyArtifactSurfacePass` | yes | hashing / disputes |

`BuildArtifactForVersion` (main.go:1605) runs the surface pass on clones (`gen/artifact.go:189,212`). It hashes the result and throws it away. The live cases go to `BuildHarnessProjection` without that pass.

I checked this on practice run `20261102T094901Z_…drp22v15_full` (seed 5451784605348316629):
- All 350/350 `user_input`s are byte-identical to the served dump.
- Only 118/350 match the dataset text.
- The report's `dataset_sha256` equals our local salt-0 artifact hash.
- Across 710 records, only 251 prompts and 461 responses are identical between dataset and served.

So the scorer does **not** re-noise. The dataset is noised, and the served text is the clean version. Section 5 has the details.

## 1. Typo model

### 1a. Typo v2: dataset artifact only

Source: `internal/textnoise/v2.go`; driver `gen/v13_surface.go:125-204`.

**Which items are hit.** `textnoise.Select` picks a stable 70% of each surface class, keyed by (seed, salt) (`v13TypoSurfaceBps=7000`, v13_surface.go:78). The classes are:
- tool prompts
- memory questions, except `answer_kind=chitchat`
- seeded pair prompts, from waves and tool prerequisites

Never touched: assistant responses, the catalog, and expected values. Enterprise-revision questions and their evidence pairs are restored verbatim afterwards (v13_surface.go:234-269).

**How many tokens.** The budget is `ceil(words/12)`, clamped to 1–4 per surface (v13_surface.go:82-92).

**How many edits per token.** One edit up to `floor(letters/3)` edits, clamped to 1–3, measured as OSA distance (v2.go:72-87). Each edit is drawn from:

| mechanism | share |
|---|---|
| keyboard neighbour | 30% |
| transposition | 20% |
| omission | 18% |
| duplication | 12% |
| phonetic digraph | 12% |
| vowel swap | 8% |

The phonetic digraphs include ph→f, ck→k, ie↔ei, ea↔ee, ou→ow, tion/sion→shun, er→ur, double letter→single, igh→i, ough→uff and que→k (24 rules, v2.go:339-344).

**Keyboard layout.** One layout per (seed, salt): QWERTY, AZERTY, QWERTZ or "mobile". Mobile has a reach of 2 keys, so it produces wider substitutions (v2.go:89-92, 407-414). Example: `cakendzr` for "calendar" on AZERTY.

**Acceptance rules.** An edit is kept only if:
- the first and last letters are unchanged;
- the result is not a real word in the 1,171-word list plus the meaning-critical set (so "form" can never become "from");
- the OSA distance stays within the bound.

It retries up to 6 times, then leaves the token alone (v2.go:251-284).

**Words that are never edited:**
- tokens shorter than 4 or longer than 22 letters;
- contractions and ALL-CAPS tokens;
- any whitespace segment containing a digit or any of `@ / $ = \ _ % # < > [ ] { } |` or `://`;
- text inside `"…"` or `“…”`;
- capitalised tokens mid-sentence, or next to another capitalised token (a proper-noun proxy);
- `ditto`, `dittocode`, `code`;
- **177 meaning-critical words** (v2.go:450-480): negations, before/after/current/latest/original, more/less, add/remove/delete/keep, weekdays, today/tomorrow, paid/owed/total, personal/business, start/stop/cancel and similar;
- **every word of ≥3 letters that appears in any graded value anywhere in the run**: expected answers, accept lists, distractors, dump guards, required args and fixture needles (`v13GlobalProtected`, v13_surface.go:282). That is at least 619–666 distinct words per run.

Because of that run-wide set, `email`, `note`, `send`, `contact`, `what`, `find`, `remember`, `latest`, `change`, `figure`, `value` and `phone` were protected in 30/30 seeds. `project` was protected in 28, `current` and `address` in 25, `open` in 7 and `dentist` in 3.

**Measured artifact noise** (salt 0, 60 seeds; salts 1–3 are within ±0.5 percentage points):

| class | items edited | typos per edited item | all tokens edited | 4+-letter tokens edited | distance 1 / 2 / 3 |
|---|---|---|---|---|---|
| tool prompts (6,000) | 69.1% | 1.80 | 7.4% | 12.4% | 75 / 22 / 3% |
| questions (15,000) | 65.6% | 2.37 | 6.4% | 10.7% | 81 / 17 / 2% |
| short pairs (37,739) | 65.8% | 2.28 | 1.7% | 3.3% | 78 / 20 / 3% |
| story pairs (5,205) | 53.5% (+4 each) | 4.0 | 0.24% extra | — | 78 / 20 / 2% |

Examples:
- `conditions→conditios`, `workflow→wokfolw`, `Remind→Remnd`
- `search blurb→siaech bllurb`, `accent→adcnet`, `Check where→Cneck whre`
- `when→wehn`, `work→wrk`, `they→thzy`, `summary→summqry`

Story pairs get noised twice in the artifact. v15 session ids are opaque hex, so `v13SkipPairNoise`'s `"story-"` prefix check (v13_surface.go:274) never fires. Artifact stories therefore get the story pass (6 tokens) plus the artifact pass (4 tokens).

**Harness keywords by distortion rate** (tool prompts and questions, salt 0; distorted occurrences / occurrences):

| band | keywords |
|---|---|
| ≥30% | remind 45% (189/421), save 42%, draft 38%, invoice 37%, calendar 35%, many 34%, make 32%, create 30% |
| 25–30% | update 29%, workflow 29%, status 29%, which 28%, look 28%, font 28%, notes 27%, please 27%, tell 26%, list 26%, receipt 26% |
| 15–25% | weather 25%, search 23% (128/566), color 22%, message 22%, page 22%, accent 21%, summary 20%, online 20%, options 18%, read 18%, check 15% |
| below 15% | dentist 13%, image 13%, memory 14%, address 10%, open 3.5%, trip 0.8% |
| 0% | email, current, note, remember, send, latest, project, handoff, find, contact, exact, figure, change, move, run, job, what, who, how |

In questions, the most often distorted words are short function words: which, with, work, this, case, many, have, about. In records they are case, work, they, forwarding, text, this. 4-letter words do get edited, e.g. `when→wehn`.

### 1b. Noise that does reach the harness live

1. **Stories.** `universe/story.go:516` runs typo v2 with **salt hard-coded to 0**, budget 6 tokens, and the seed's layout. Only the story's fact values are protected. There are about 87 story-like records per seed. My dictionary-proxy detector (an estimate and a lower bound) flags typo-like tokens in 72% of served stories, about 1.6 per story. The code target is up to 6 per story, out of a median 455 words.
2. **Isolation cases** (`gen/isolation.go:358`, the v1 projector in `textnoise.go`):
   - covers 25% per domain of the isolation questions (the "For this contact list:" prefix) and of the secondary-user wave pairs;
   - 1 edit, QWERTY, first and last letters kept;
   - a 32% chance that the single edit is instead a grammar rule: could of, should of, would of, suppose to, use to, alot, its, whose, doesnt, dont, im;
   - seen live: `disappezr`, `replaace`.
3. **Deliberate value misspellings.** These prompts name a font, accent or theme with the value misspelled on purpose: `discovery_font_set`, `discovery_accent_set`, `world_theme_discover_set`, plus the capability-mode prompts. That is 8.2% of tool prompts. They use `misspellAliasV13` (datagen.go:1767-1778, `Force=true` so capitalised names get misspelled too) or `catalog.AliasFor` (1–floor(len/3) edits, never equal to another option, inventory.go:211). Examples: `Domnie`, `lightt salmon`, `Coomorant`, `bufylood`, `teracota-ish`, `piriwinlke-ish`.
4. Everything else served is clean. The detector's false-positive rate is about 2–3% of short items, mostly names such as Finke, Cutler or Stanford.

## 2. Fillers, lead-ins, closers and voice (served text)

**Story texture** (`universe/story_events.go:322-366`). The pools are:
- 10 openers, e.g. "Between all that,", "Unrelated, but", "As an aside,", "Meanwhile,"
- 30 details and 9 second details
- 12 asides, e.g. "which explains the typos", "so bear with the detour"
- 6 tail notes, e.g. "Anyway.", "Back to the point.", "That is the background noise."
- 10 context lines

Frequencies per story-like record: 76.9% contain an opener (each opener appears in about 44%), 77.0% an aside ("which explains the typos" alone in 39%) and 76.7% a tail note.

**Record lead-ins:**

| lead-in | share of records |
|---|---|
| v13 conversation leads, e.g. "Filing this under the same workstream set: " (v13_contract.go:272) | 4.7% |
| glossary openers, e.g. "Before the data lands, note that" | 5.1% |
| top 3-word record heads: "Forwarding a text", "From the fridge", "Subject: workstream note", "Pasted table row", "Shared calendar entry", "Contact-maintenance receipt for" | 4.5–4.8% each |

There are 7,276 distinct 3-word record heads in 37,739 records.

**Question prefixes:**

| prefix | share of questions |
|---|---|
| `Use only case file c<16hex>. …` (universe/v13_contract.go:1154, personal.go:626) | 20.8% |
| workspace openers, e.g. "Work only from this batch's own field meanings." | 6.4% |
| personal openers, e.g. "Before I forget —", "From my household notes:" | 9.6% |
| "For this contact list:" | 3.5% |

Common question closers: "…before I hit send.", "Just the name.", "…counts as zero."

**Tool prompts:**
- 8.2% start with `For planning context c<16hex>: ` (datagen/v13_tool_semantics.go:596).
- About 8.4% end with a bare imperative: "Go.", "Begin.", "Proceed.", "Start now."
- 12% contain a polite marker: please 4.6%, thanks 2.5%, "when you can" 2.4%.
- There are 1,292 distinct 3-word heads in 6,000 prompts.
- Grammars run through `persona.SeedBank`, which keeps 66.7% of every non-root bank with at least 4 alternatives, per seed (persona/bank.go:28-62).

**Assistant voice:**
- Responses are ≤210 characters, 79 at the median.
- 0% contain emoji in v15. The 💛 pool in assistantvoice is not reached.
- 16.6% end with `(thread: <coined label>)`.
- Served responses repeat heavily: 53.9% of records share an identical response with more than 2 other records (21–32 copies of the same response per seed). The dataset caps each response at 2 copies by appending codas such as "I can follow where this fits." (gen/artifact.go:224). That is why 34% of dataset responses differ from what was served.

**Worst-case lengths (served, 60 seeds):**

| class | median | p99 | max |
|---|---|---|---|
| tool prompt | 92 chars / 16 words | 223 chars | 252 chars / 42 words |
| question | 122 chars | 272 chars | 336 chars / 59 words |
| short record | 147 chars | 16,679 chars | 17,080 chars |
| story record | 2,525 chars / 455 words | 18,102 chars | 18,276 chars / 2,311 words |

There are 702–736 records per seed.

## 3. Wordbanks and coined words

**Names** (`internal/humandata`):
- 10,000 given names: 4 of every 5 draws are frequency-weighted from the top 1,000, and every 5th comes from ranks 1,001–10,000.
- 10,000 surnames: weighted from the top 2,000, with every 7th draw from the long tail.
- 1,124 nickname mappings, 7 short forms, and 32 social nicknames (Ace, Bear, Scout, Wren…).

**Public data** (`internal/publicdata`):
- 31,799 cities (every 5th draw from beyond the top 2,000)
- 721 occupations, 1,946 fonts, 952 colours (xkcd + CSS), 181 purposes
- **805 real brand or organisation stems** (Sanofi, Petrobras, Reebok, Temasek, Germanwings, Brembo…), combined with 32 suffixes such as "Supply", "Digital", "Energy" and "& Co."
- 30 of the 805 stems are plain English words: Credit, Square, Total, Next, Video, Under, Focus, Watch, Image, Medium, Nothing…

**Other banks:**
- v13 org stems: 24 × 8 suffixes
- company families (`universe/world.go:149-150`): 18 starts × 12 ends, e.g. "Ashbrook", "Fairmont"
- v13 status-alias terms used as schema labels, all real words: amber, slate, ember, cobalt, harbour, quartz…
- workstream and thread labels built from syllable banks: 24 starts × 16 mids × 20 ends, e.g. `vorailnode`, `quillawire`

**Coined words:**
- `catalog.CoinedStem` (catalog/v13.go:641): 2–3 consonant-vowel syllables from bdfgklmnprstvz × aeiou, with an optional final l/n/r/s/t.
- Uses: the brands of 3–5 decoy tools per seed (23 shapes, e.g. `gagoso_weather`, `vofu_notebook_add`, `luma_pricing_quote`), coined workflow, job and routine names, and a capitalised brand in prompts ("Pull Gagoso conditions…").
- `persona.CoinShaped` codes: one shape per seed out of `GAVOTU-8841`, `VK-7GH2K9QRTZ`, `gavotu_8841` and `84-GAVO-TUKE`.

The 60 seeds produced 235 distinct decoy stems. At least 6 are ordinary English words (side, motel, ruse, fuse, votes, mare: 2.6%, checked by hand). At least 29 (12%) are one edit from a common word: nosa→nose, tira→tire, figur→figure, titel→title, velume→volume, mave→move. That 12% is a lower bound, measured against a 2.2k-word proxy dictionary. The 240 thread labels are not near any proxy-dictionary word.

**Catalog** (`catalog/v15.go`):
- 233–235 tools per seed: 30 product tools, 3–5 decoys, and 200 connectors from a pool of 136 apps / 277 actions.
- Every product tool has 6 description variants chosen per seed.
- Connectors have 2 description variants.
- Positions are seeded: `search_web` sits anywhere from index 17 to 43, `gmail_send` from 162 to 195.

## 4. Surface salt

**What it varies** (30 seeds × salts 1–3, 90 comparisons with salt 0):
- **Typo-v2 draws.** These cover which 70% of items are hit (Jaccard 0.53 between the salt-0 and salt-k hit sets), which tokens, which edits, and the keyboard layout.

  | text | share still identical to salt 0 |
  |---|---|
  | tool prompts | 10.1% (range 4–15%) |
  | questions | 14.8% |
  | record prompts | 16.8% |
  | responses | 100% |

- **The world-canary nonce.** It is the only expected answer that changes (exactly 1 per dataset, 90/90). The salt-0 nonce is appended as a distractor in 90/90 cases (v13_surface.go:333-365).
- **Stage-1 marker composition.** No effect in v15: none of the five markers occur in the raw text.
- A new top-level `surface_salt` key appears.

**What it never varies:**
- catalog names, descriptions and order (90/90 identical)
- case ids and order, expected tools and arguments, fixtures, `generated_at`
- assistant responses
- story-internal typos (the story pass hard-codes salt 0)

Implications:
- A rule mined from the typos in salt-0 dataset files fits about 10% of the salt-k text, and fits **none** of the live served text, which has no typo-v2 at all.
- For live v15 the salt is moot in this code. The run path builds and hash-checks the salt-0 artifact (main.go:1605, 1631-1636), and private-dataset mode accepts bench 13 only (`private_dataset.go:49`). Even a salted artifact would only be hashed, never served.

## 5. Serve-time behaviour

**Text is not re-noised.** `runner.runOneWithTelemetry` sends `c.Prompt` unchanged (`internal/runner/runner.go:450-454`).

**What does change per run.** A fresh `crypto/rand` blinding key (main.go:1649-1654; `gen/projection.go:147-458`) does the following:
- replaces `case_id`, `user_id`, `pair_id`, `session_id` and subject ids with UUIDs;
- rewrites any occurrence of those ids inside text (none occur in v15 text);
- permutes the tool-case order (then `V13ArrangeToolOrder`), the memory-case order within a wave, the session blocks of records, subjects and links.

The same seed therefore always gives the same text, with different ids and order on each run. The `c<16hex>` references inside text ("Use only case file …", "For planning context …") are not run ids and are never rewritten. They will not match any wire `pair_id`.

**Matching traces to datasets:**
- Use `/tmp/atlas_surf/servedgen -seed N -out F` (about 0.5 s per seed) for exact matching.
- Against dataset files you need fuzzy matching. About 66% of prompts and questions differ from the served text by 1–4 tokens, and 34% of responses differ by an appended coda.
- Match records by text, not `pair_id`.

## 6. Character-level oddities (served)

**Character set:**
- **ASCII letters only.** No accented letters (names and cities are ASCII), no NBSP or narrow NBSP (U+202F), no emoji.

**Non-ASCII punctuation:**

| class | em dash | other |
|---|---|---|
| tool prompts | 27% | — |
| questions | 22% | — |
| records | 12% | curly double quotes 8.7%, curly ’ 7.8% |
| stories | 50% | — |
| responses | 33% | curly ’ 47.8% |

- Apostrophes are mixed: 46.3% of responses and 28.8% of records use a straight `'`.
- € and £ appear in 0.8% of records.

**Numbers, dates and money:**
- `$10729.08` has no thousands separator. Dollar amounts appear in 7.2% of records.
- Minor-unit or ISO currency codes appear in 4% of questions.
- Dates: ISO `2025-06-05` in 1.6% of records, "March 3" in 3.8% of records and 5.2% of questions, weekdays in 7% of tool prompts, `hh:mm` times in 8.4% of stories.

**IDs and codes:**
- `c` + 16 hex: 43% of records, 21% of questions, 8% of tool prompts.
- Join keys `CASE-1234-abcdef`, `TKT-12345`, `REF AB-abcdef`, `PO-…`, `BK12345AB`, `JOB-AB12345`, `CLM-…`, `Q-…`, `F/12345/AB`: in 40% of stories.
- Coined codes: about 2% of records.
- Email addresses: 19.7% of records.
- ALL-CAPS tokens: 15% of records, 70% of stories.
- Pipe tables: 10.9% of records. JSON fragments: 2.6%.

**Casing and punctuation:**
- 5.2% of records start lowercase.
- 13.9% of records lack terminal punctuation.
- Prompts and questions always start uppercase.

## 7. Fragility checklist for regex and keyword rules

| # | rule pattern | breaks when | how often (measured) |
|---|---|---|---|
| 1 | trigger words copied from dataset files | the typos are not served live; rules tuned on them overfit | 66–69% of dataset prompts/questions differ from served text |
| 2 | exact keyword match on dataset/practice text | the keyword is distorted | remind 45%, calendar 35%, workflow 29%, search 23%, check 15% (salt 0) |
| 3 | exact match on a font/colour/theme value | the value is misspelled on purpose (1–3 edits) | 8.2% of tool prompts, 100% of those categories |
| 4 | fact keywords in stories (served) | up to 6 typo'd tokens per story; layout varies by seed | ≥72% of stories (lower bound) |
| 5 | isolation questions and secondary-user records | v1 typo or grammar swap (dont, its, alot) | 25% of those items |
| 6 | prefix anchors (`^What`, `^Remind`) | a scaffold prefix comes first | 20.8% of questions "Use only case file…", 8.2% of tool prompts "For planning context…", 16% of questions other openers |
| 7 | `'` vs `’`, `-` vs `—` | mixed typography | curly ’ in 48% of responses vs straight in 46%; em dash in 22–50% by class |
| 8 | treating `c[0-9a-f]{16}` as a wire id | text ids are not pair or case ids; wire ids are UUIDs | 43% of records contain one; 0 match a wire id |
| 9 | brand allow/deny lists | coined decoy brands change every seed; 2.6% are real words, ≥12% one edit from one | 3–5 decoys per seed, 235 stems across 60 seeds |
| 10 | real org names as "non-entity" stopwords | 805 real brand stems; 30 are English words (Square, Total, Focus) | every seed |
| 11 | tool position or description regex on the catalog | 6 description variants per product tool; seeded positions | 30/30 product tools vary; `search_web` at index 17–43 |
| 12 | dedup of identical responses | served responses repeat up to 32× | 54% of served records |
| 13 | sentence-split on `\n\n` / length caps | stories up to 18.3k chars and 2.3k words; 10.9% of records contain pipe tables | ~87 long records per seed |
| 14 | money/date parsers | `$10729.08` (no comma), `£/€`, minor units, ISO vs "March 3" vs weekday | 0.8–7% per format |
| 15 | salt-specific typo tables | other salts re-draw the hit set and edits | 10–17% of items identical across salts; Jaccard 0.53 |
| 16 | lists of words that are never noised | the protected set depends on each run's graded values (619–666 words) | `open`/`dentist` protected in 7/3 of 30 seeds |

Safe anchors, per the code: the 177 meaning-critical words, tokens shorter than 4 letters, tokens containing digits or `@/$_`, ALL-CAPS tokens, quoted spans and mid-sentence capitalised names. None of these is ever typo'd by v2. The first and last letters of an edited word are also always preserved.
