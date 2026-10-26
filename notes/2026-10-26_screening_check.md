# Screening check of the current design (combined at 969a351, 2026-10-26)

Local, using the upstream screener's own code (repos/ditto-subnet/workers/screener at 7748a7b5).
Tree screened: combined/ as it would be uploaded (caches left out), 38 files, 918 KB.
Reference: dan0l v24's released source, which cleared screening.

## Static checks ($0, tools/screen_local.py)

| check | combined | dan0l v24 |
|---|---|---|
| decisive malicious source (pre-build quarantine) | 0 | 0 |
| C13 benchmark-emulation fingerprints | 4 x typo-tolerant-token-compare (medium), app/ours/lane.py 464-474 | 0 |
| L1 static review leads | 6 x numeric-candidate-shotgun | 3 x the same |
| v14 generator-template n-grams (draft, report-only) | 1: app/ours/lane.py 333, 506-507 | 0 |

- typo-tolerant-token-compare: the routing typo mender (edit_distance / slip_of next to
  "word"/"phrase"). Its slip rule (same first and last letter, at most len/3 edits, capped at 3)
  has the shape of the generator's own typo model, which an I5 reviewer may call generator-fitted.
  v13 W4 allows typo handling and routing; the mender only picks a lane.
- numeric-candidate-shotgun: the arithmetic-word constants that app/ours/lane.py copies from dan0l's
  app/lane.py (3 of the 6 are in dan0l's own file); inherited, cleared with dan0l.
- n-grams: example phrases in comments and a docstring of app/ours/lane.py; no behaviour.

## L1 source review (tools/l1_review_local.py, $0.51)

One review by the screener's reviewer with its production defaults (openai/gpt-6-luna, high
effort, 200-step budget; it used about 95): risk low, category none, clearance certified, 48 notes.
On the mender (notes 22, 33, confidence 0.9-0.91): it repairs request wording for lane routing,
constructs no scored answer, and the request reaches the model unchanged. The meaning router
(app/ours/meaning.py) only picks the product lane and keeps the catalog. The topic path changes
(app/short.py) were cleared: drafts and recent-passage notes are preliminary, the deciding model
receives the notes and writes the answer. Full observation: practice/l1_combined.json.

## Limits

- One L1 run of a sampled model; another run can read the same code differently.
- L2/L3 (gpt-6-sol), the adjudicator and the build/health gate were not run here; the build and
  health path is the one every practice run exercises.
- Production review settings (policy version, static preflight mode) may differ from the defaults.
