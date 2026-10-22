# Medium A/B, the anti-copy check, and four fixes (2026-10-22)

## Anti-copy check (how the platform compares code)

`apps/platform/ditto/api_server/fingerprint.py` and `docs/anti-copy-reference.md`:
- every file is normalized (intra-line whitespace removed, blank lines dropped) and cut into
  overlapping 4-line windows; a second sketch keeps every line of 30+ characters (comments dropped,
  `a.b.c(` read as `c(`), so splitting or reordering files does not hide a copy;
- starter-kit content is removed first, whole untouched kit files and lockfiles before shingling;
- a candidate is compared only with earlier submissions of other owners; a copy signal is Jaccard
  >= 0.75 or containment >= 0.95 on either sketch;
- a signal is withdrawn when the matching artifact is already published (released kings), unless an
  unpublished artifact matches more closely; embargoed code still holds the submission.

`tools/anticopy_check.py` runs that code unchanged. Our harness vs Hades v6: windows 0.922 / 0.972,
lines 0.930 / 1.000 (a fork, withdrawn because Hades v6 is published). blinkrazor vs Hades: 0.

## Medium A/B (seed 4242, 48 tool + 95 memory)

| run | composite (stderr) | tool | memory | cost |
|---|---|---|---|---|
| Hades v6, traced | 0.862 (0.029) | 0.860 | 0.875 | $0.436 |
| ours e78bab4, traced | 0.838 (0.031) | 0.839 | 0.847 | $0.475 |

Within one standard error. We lost 10 cases Hades won and won 7 Hades lost. Traced causes of our
losses; none involve our routing or widening (same lane, same packet or prompt size):

- 4 x `v13-personal-program`: the order pass read the four notes as M4,M3,M1,M2 instead of
  M1,M4,M2,M3, so "postponed" instead of "tentative". The reading is shared across rewordings, so
  one bad reading lost all four.
- `injection-data-inside-envelope`: right value written `ZAPELI‑6364` with U+2011; the v13 fold
  (`grade/v13_text.go`) does not map it, so no match.
- `absence-twin-stale-removed`: same packet; the timeline pass wrote 12,413 tokens and the reply
  then declined an answerable question.
- `schedules_result_usage`: decision step chose `list_workflows` over `list_schedules` (identical prompt).
- `v13_restraint_negation_web`: decision step said `search_memories`, then the reply was the bare word NONE.
- `capability_discovery`: decision step said NONE and the reply came from general knowledge.

## Fixes (commit after this note)

1. Order vote: three shared order readings (one as before, two at 0.7 with fixed seeds), combined by
   head-to-head majority, then Borda points.
2. Plain hyphens: U+2010 / U+2011 become "-" in `final_text` and `answer`; answer-value tokens are
   letters and digits only (`answer_io_capture.go` `valueTokenSet`), so this never changes them.
3. A bare NONE reply in the action lane gets one nudge to answer the user.
4. Timeline pass capped at 8,000 output tokens (a cut pass leaves no note, as before).
