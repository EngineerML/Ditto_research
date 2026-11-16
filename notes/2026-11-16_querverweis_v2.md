# 2026-11-16 querverweis v2: current places of one person

## Why querverweis
- querverweis v3 (`c955422c`) was pinned in all 7 revealed seasons 26123–26129.
  - Our v6 scored 0.38 on it in 26126; leaders scored 0.80–0.92.
  - The v3 source has no release date.
- v2 (`01e36814`, hotkey 5DcBmn, released 2026-11-16 00:44 UTC, sha `a8be61ba…` matches) is its predecessor.
  - Its internal version is "querverweis 5".
  - Downloaded to `.cache/miner_gens/dl/querverweis-v2_01e36814`; packs 1–3 in `.cache/miner_gens/packs/qv2` (`live/build_qv2.sh`).
- **Caveat:** v3 may add knobs the README lists that v2 packs don't exercise (nickname, feature binding, relation to another person).

## Case shape (README + packs)
- "Which <things> does <Full Name> ... these days?", or "... does my <role> ... now?" / "my <role> <First> ...?".
- 2–4 items and no count word.
- Items are told under:
  - the full name;
  - the first name alone;
  - "Mr./Ms. Surname";
  - swapped/switched/replaced records.
- Traps:
  - the same person's places given up, in many wordings;
  - a relative with the same surname (another first name, or the other title);
  - a twin first name (role questions);
  - the previous role holder's places.

## Baseline (57853f5)
- 0.39 on pack 1, matching the official 0.38.
- 12 of 35 replies named a trap.
- 32 of 39 missed-item records were in the packet, so it was a reading problem.

## Steps (pack 1 unless noted; grader-normalised tally `practice/list_tally.py`)

| Version | Score |
|---|---|
| note only (`CURRENT_LIST_NOTE`) | 0.51 |
| + code index of the person's records by name form (first fix of a key bug) | 0.66 |
| + code-read place list with leaving records | 0.77 |
| + "read that way" summary line, 3 packs | 0.81 / 0.84 / 0.79 |
| + role holder resolution, 3 packs (final) | **0.89 / 0.89 / 0.94 = 0.91** |

## Static checks (free)
- `practice/qv_note_reach.sh`: the note reaches 105/105 querverweis cases and 0 of the v18 datagen seeds or other packs (3,160 cases).
- `practice/qv_places_static.py`: from code alone, the right place set scores 0.93–0.96 per pack, no trap kept, no extras.
- Its misses are "unsettled title" cases (both Mr. and Ms. in the records, no pronoun), which the block lists separately for the model.

## Runs and cost
- Runs: `practice/generator/20261116T101130Z` (base), `…101907Z`, `…102547Z` (broken block), `…103112Z`, `…103828Z`, `…104338Z` (3 packs), `…105823Z` (final, 3 packs).
- About $0.35 in all; balance $12.83.
