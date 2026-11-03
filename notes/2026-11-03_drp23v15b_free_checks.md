# 2026-11-03 — drp23v15b (v8 + three tool-side changes): free checks

Branch `lab/drp23-v15b` (local only), tree `drp23v15b/`, commit 3989c70. v8 itself (`drp23v15/`, package a3803d6e)
is unchanged.

## Changes

| change | file | lines |
|---|---|---|
| product names need a capitalised word (exact, or one slip when the word is not a real word) | `app/thint.py` product_tool | 3 changed |
| live lookups (dan0l v30's LIVE_WORLD/NO_LOOKUP, only when no other request kind): after a completed lookup, no result verdict, no link note, low effort | `app/thint.py` live_lookup; `app/action.py` run | 13 + ~6 |
| an empty required argument counts as missing unless its description says optional (dan0l v30's rule, with that guard for "optional reminder filter") | `app/action.py` unfilled, missing_required (records lane uses it too) | ~12 |

Deviation from the proposal: product matching keeps its first place among the kinds. Removing the false matches
was enough: each freed request now gets its own kind's hint (no-web, calendar-named, handoff, planning-send,
agreed), and moving "product" later would have cost decoy requests their hint.

## Checks (no model call)

- Unit checks on the three rules: 17 of 17.
- `practice/gates/hint_compare.py` over 43 generated bench-15 seeds (15,050 requests): 36 hint/kind changes, all
  false product notes removed (14 tool cases, 22 memory questions), 0 of 400 true product matches lost. Live
  handling applies to 89 tool requests: single-search web categories, plus 4 parallel_web_image.
- The "web" request kind was ruled out as the live trigger: it covers two-tool categories (parallel_web_image,
  contact research then email, link chains).
- Mock runs (seeds 4140…, 5451…, 8047…; `practice/20261103T11*_ditto-harness-drp23v15b_full`) against the
  drp23v15 mocks of the same seeds: no lane change, no request-hint change. Remaining event differences are run-order
  noise (which twin shows the earlier reply first, and a person-record count), symmetric in both directions. Mocks
  make no tool calls, so the live and empty-argument changes are not exercised there.
- Package `practice/submission_drp23v15b.tgz`, sha256 97fce15e…, 37 files: `ditto verify` PASS.
- Static screen against released v23: 0 malicious, 0 fingerprints, the 3 numeric-candidate leads inherited (lane.py).
  The generator n-gram lead in thint.py grows from 16 to 18 grams: the two new lines are the ported LIVE_WORLD and
  NO_LOOKUP patterns, phrases that echo the public generator's live-question wording. They are dan0l v30's released
  code, which passed policy 13 with them; the declaration row cites it.
- 78 changed lines against v8.

## Not done (paid)

A/B of the reached categories only (restraint, web, link chain, parallel web, decoy, empty-argument cases).
