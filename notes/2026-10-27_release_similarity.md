# How alike the released harnesses are, across submitters (2026-10-27)

The platform's own lexical fingerprint (tools/anticopy_check.py, which runs
apps/platform/ditto/api_server/fingerprint.py unchanged) between every pair of the 13 releases
saved in released/. Bars: Jaccard 0.75 or containment 0.95 on either the 4-line window channel or
the line channel. The fingerprint's own calibration: independent harnesses peak at line Jaccard
0.24.

Pairs above a bar:

| pair | line Jaccard / containment | same submitter? |
|---|---|---|
| blinkrazor v2 / v3 | 0.98 / 1.00 | yes |
| lets_637 / 638 / 640 | 0.94-0.98 / 1.00 | names suggest one operator |
| dan0l v19 / v21 / v24 / v25 | 0.75-0.94 / 0.88-1.00 (v24-v25 0.90 / 0.97) | yes |
| hades v6 / hardes v1 | 0.93 / 0.98 | names suggest one operator |
| hades v6 vs dan0l v19, v21 | 0.82 / 0.93, 0.78 / 0.88 | **no** |
| hardes v1 vs dan0l v19, v21 | 0.88 / 0.93, 0.84 / 0.93 | **no** |
| our combined vs dan0l v24, v25 | 0.85 / 1.00, 0.75 / 0.92 | no |

Hades v6 and hardes v1 are built on dan0l's released v19/v21 (line overlap three to four times
the independent ceiling), and Hades sits at #4 on the leaderboard (0.856).

That is allowed. scoring_gate.py: "the subnet owner has confirmed that building on a released
agent is permitted"; a copy signal that a published artifact accounts for is *withdrawn*
("recorded, not held"). What the gate still holds for human review is content taken from an
artifact still inside its embargo window, or a match a still-embargoed artifact explains better
than any published one. The withdrawal compares in both directions (_withdraw_ranked), so our
tree must not resemble dan0l's embargoed v26 more closely than the published v25 does; it was
built only from v24/v25 releases and our own code.

Correction to the 2026-10-27 session: tools/anticopy_check.py's docstring said a release match
"is withdrawn", which was read as the upload being withdrawn. It is the copy signal that is
withdrawn; the docstring now says so.
