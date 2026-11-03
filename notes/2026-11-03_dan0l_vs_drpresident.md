# 2026-11-03 — dan0l v30 vs DrPresident v23: what differs and what to combine

Both are released. They share an ancestor: 32 files each; calc, store, surface, main, memory/embedding, people,
worksheet and closest are byte-identical. Biggest divergence: short.py 578 lines, action.py 339, lane.py 293,
records.py 274. DrPresident-only: thint.py, typofold.py, qtype.py. dan0l-only: request_kinds.py, guide_tools.py,
guide_records.py. Two read-only code reviews (tool path, memory path) plus live score data; nothing edited.

## Scores by series (live provisional runs)

| series | bench | runs | tool points lost / run | tool efficiency | tokens / run |
|---|---|---|---|---|---|
| dan0l v29–v35 | 14 | 21 | 1.23 | 0.997 | 14.7M |
| dan0l v35–v36, whole 235-tool catalog | 15 | 6 | 1.14 | 0.998 | 17.6M |
| DrPresident v22–v28 | 14 | 12 | 1.58 | 0.999 | 15.1M |
| DrPresident v23 | 15 | 3 | 5.22 | 0.998 | 21.8M |
| DrPresident v29 | 15 | 3 | 1.33 | 1.000 | 22.1M |
| horizon v8 (v23 + connector step) | 15 | 3 | 2.97 | 0.994 | 14.7M |

## Tool path

| | dan0l v30 | DrPresident v23 |
|---|---|---|
| lane vocabulary | from every tool name (connectors leak in) | same code |
| brand hint | Capitalised word equal to a tool-name head, exact; every match listed | any word, any case, one edit off; exactly one match; checked first, shadows every other kind |
| request kinds | multi-label, literal regexes (typos miss) | one label, typo folding with real/decoy word lists |
| hint placement | system prompt and again after the request (doubled) | once, after the request |
| after a tool result | verdict + result read; skips the verdict and drops to low effort after a live lookup | verdict + result read always, medium effort |
| reply with no call | two temperature-0.8 drafts with the full menu, then a reply check | reply check only |
| empty required argument | treated as missing, the model resends | sent |
| tool output | cut at 6,000 characters | passed whole |

v8 already removes the 200 connectors before routing, so the vocabulary leak and the connector brand collisions
(monday/Monday, teams/team, lever/level, sentry/entry) do not reach it.

## Memory path (main points)

- DrPresident is richer on programs (state reading, filing order with times, revert/list/step rules) and on question
  kinds (qtype hints after the message, reaching records, topic and the short path).
- dan0l has nickname coverage in the records lane (nickname → full name lines, ranking anchors), a routed no-record
  clause in the lane system and the draft check, and carries short-path tool results into the records lane where
  DrPresident ends with an empty reply.
- Checked on our seed-5119 run: 0 empty replies among 250 memory cases; the earlier-reply note was used on 18 program
  cases, all scored 1 (twin rewordings kept the same value).

## Candidates, tool side first

1. product_tool: capitalised words only (exact or one slip), keep exactly-one, stop it shadowing the tool kinds.
   40-seed check: false fires 37 → 1, true matches kept 400 of 400.
2. Live lookups: dan0l's verdict skip and low effort after a live result. Targets the repeat-search loop
   (link_chain 4 searches, parallel_web_image extra searches) and token cost.
3. Empty required argument treated as missing (dan0l). Small.
4. Not to port: dan0l's no-call drafts and doubled hints (about 32k extra tokens on a no-call case, and the drafts
   can turn a restraint case into a call).

Memory side, later and A/B only on the cases each reaches: dan0l's nickname coverage, the draft-check additions
("a withdrawn value is not held", "answer each thing asked"), and the no-record clause reconciled with qtype's
ANSWER-line convention.
