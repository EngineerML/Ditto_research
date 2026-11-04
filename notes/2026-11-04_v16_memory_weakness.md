# 2026-11-04 — horizon v8 memory on bench 16: where it loses, what to port

Sources:
- live `/public/agent/{id}/scores`: v15 and v16 rows, `dueling_breakdown`, per-category case results;
- the generator rounds API (`/generator/rounds/{i}`);
- the local v8 full v15 trace (20261103T003809Z, seed 5119);
- a code diff of dan0l v34 against drp23v15b;
- the official docs (`dueling-bench.md`, `v14-generator-credits.md`, the generator starter kit).

## The generator half today

In seasons 26071 and 26072, only column **c0** is a miner generator (graded at policy 15). c1–c4 are the public
default generator (policy 16), and every agent scores about 1.0 on them. Its four families (update chain, two-hop,
retracted preference, scattered list) were 76/76 trivial in rounds.

c0 mean per run:

| Agent | c0 |
|---|---|
| Orsentra v21 | 0.84–0.91 |
| DrPresident v27 | 0.50–0.53 |
| **horizon v8** | **0.47, 0.51** |
| Hades v26 | 0.33–0.49 |
| logan v11 | 0.31–0.44 |
| dan0l v38 | 0.31–0.36 |
| crown-v207 | 0.21–0.26 |

- Case scores are only 0, 0.5 or 1. horizon has 23–26 of 35 at 0.5, 4–7 at 0 and about 5 at 1.
- This matches the official "two-item nickname list" (generator B, SN-352, `challenge/half_credit_test.go`): one
  item is stated under the full name and one under a nickname only an identity record links. One item scores 0.5,
  and a look-alike's item scores 0. c0's identity isn't public, so the match is inferred.
- **Raising c0 to about 0.9 is worth +0.04 before gates and cost.**

The next step is much larger. The round-ledger top generators (245c0b5e, eab9260a, c01cfd3d, reaxgen, 836ac627)
still declare policy 14 and so can't hold a v16 column yet. Once they rebuild, all five columns are miner columns. Panel
common means in rounds:

| Agent | Panel mean |
|---|---|
| Orsentra | 0.65–0.81 |
| DrPresident | 0.44–0.50 |
| Hades | 0.35–0.43 |
| dan0l | 0.30–0.40 |
| logan | 0.33–0.37 |
| crown | 0.20–0.27 |

Those columns' discriminating shapes:
- revert to the original or previous entry;
- status inside a non-final interval;
- event order (nth, before, after);
- the first open step plus its owner;
- membership remove / re-add / swap;
- set intersection;
- holder vs actor in custody chains;
- identity joins by alias or initials.

Mostly unsolved: conditionals, alias reroutes, owner-alias email, and custody chains of 3+ hops.

## Datagen memory half: horizon v8 against the top six (v15 + v16 rows)

| Type | horizon | Top mean | Failure seen in the trace |
|---|---|---|---|
| absence-near-miss | 0.74 | 0.95 | Declines without naming the person the records do hold ("generic refusal without a grounding claim"). Also claims a record mentions the asked person |
| record-quantity-cf-base | 0.81 | 0.98 | Direction right, quantity taken from a distractor (125 for 121) |
| world-story-quantity | 0.91 | 0.98 | Adjustment applied wrongly (27 for 24) |
| enterprise-composed-program | 0.95 | 0.99 | — |
| world-story-next-action | 0.94 | 0.97 | — |
| absence-twin-false-premise | 0.89 | 0.97 | Answerable twin declined ("abstained on an answerable question") |
| record-quantity-cf-variant | 0.92 | 0.99 | — |

horizon leads on personal and open programs, lesson claims, false premise, insufficient composition, stale-removed
and owner / x-owner-email.

## dan0l v34 memory mechanisms we lack (all add no model calls)

1. **Unnamed-person note** (coverage.py `unnamed_note`). For a contact question about a full name no record holds,
   it lists the people the records hold with that first name or employer, by name only. Target: near-miss.
2. **Nickname ↔ full name lines in both directions, and nicknames as retrieval anchors** (coverage.py 23-28, 94-152;
   retrieval.py 308-323, 370-372). We only map full name → nickname. Target: c0-style nickname lists, contact and
   owner questions.
3. **"Answer each thing the message asks"** in the deliberation brief. Ours says "state no other value than the one
   you answer with" (deliberation.py:22), which can cut a two-item answer down to one item. Withdrawn-handle note
   (M67) alongside it.
4. **Long-packet listing and search union** (records.py 63-65, 132-141, 216-235, 557-562). On 30k+ char packets with
   search notes, it decides at high effort over a record listing, where ours drops to low effort over the full text.
   Target: composed programs.
5. **Carried calls**: a short path that ran tools but wrote no text passes them on, where ours returns an empty
   reply.

## Next

- Inspect **Orsentra v21** at release (2026-11-05 07:54 UTC). It is far ahead on miner columns (c0 0.87, panel up
  to 0.81).
- Build a local hard pack from the c0 shape and the ditto-generator families, free to generate. Then A/B items 3, 2
  and 1, which needs credits.
