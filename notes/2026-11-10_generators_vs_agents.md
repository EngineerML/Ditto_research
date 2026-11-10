# 2026-11-10: what the miner generators aim at, and where our agent stands

## How a generator is scored (`research/dittobench-datagen/challenge/score.go`)
- An agent solves a case at score >= 0.5. A case solved by fewer than 2 owners is *unsolved*: no credit, and the
  pack score is multiplied by (1 - unsolved share)^2. Solved by every agent: *trivial*. Otherwise *discriminating*,
  with credit (1 - mean score), x1.5 when the champion fails it.
- So the best case is one every agent half-solves and few fully solve: a two-item list where one item is easy
  (0.5 = solved, never unsolved) and the second is hidden. Too-hard cases are avoided because they zero the pack.
- The generator owner's own agents are left out of the panel, and in dueling seasons a column from the scored
  agent's own owner is masked for that agent (beast-d41 and kinfolk share a coldkey).

## Released generators (sources read, not run on the host; packs built only in the no-network sandbox)
| Generator | Rotation shipped | Shape | Trap / weakness targeted |
|---|---|---|---|
| kinfolk v2 (5E2J8u7B; live is v4, 5FCRu5Wx) | TwoFavs only, `hop2` on | "Which two cheeses does Alexander love?" item 1 under the first name, item 2 under a nickname bound full name -> surname -> nickname over two records | the item-2 record shares no word with the question; look-alikes are real diminutives (Ted for Theodore) bound to nobody; 1,000 chatter pairs |
| m118-gen v4 (5DWjUMSx, pinned 26090-26097) | AliasPairList x5 | "Which two bakeries does Jane Okafor love?" item 2 under a nickname bound in one alias record | one-suffix look-alikes (Midgeo) bound to others; a same-surname relative's item in a sentence naming the target |
| reaxgen-b1 (5DaLyZfV, pinned to 26094) | ls2b level 3, hd2/hd3, crowd 3 | identity record "Kenya Swartz ... everyone there calls them Teo"; item 2 "Oh and Teo also loves B" in wave 2, buried mid-message | three look-alike people (Teoy, Teos, Teoie) with lines worded like item 2; a decoy's "right now" item |
| 5ELk1RHE v3 (v5 is the round-26100 challenger) | ls2b level 3, late1 + sal8 | same binding; stale item C written 5 times under the nickname in the question's own words, then "Update on Teo: B replaced C" x3, then the "also B" line last | most-repeated / most question-like value wins; the last record before the question is missed |
| starter kit v17 (public default) | UpdateChain, TwoHop, RetractedPreference, ScatteredList | single values and a 3-item list | latest value, one hop, retraction without a keyword, aggregation |

The four miner generators converge on one design: a two-item list whose second item hides behind a name binding,
with look-alikes, decoys or stale values that score 0 if named. Authors' notes: panel answers are almost always 0.5
(item 1 only) or 0 (reaxgen `internal/families/hrd.go:14-17`); a hedge such as "A, and no record of a second"
is graded as an abstention and scores 0 (`internal/mix/mix.go:66`).

## Live columns per agent (seasons 26098-26099, pins revealed)
| Generator | DrPresident | beast-d41 | dan0l v48 | logan | overhorizoner v1 |
|---|---|---|---|---|---|
| kinfolk v4 | 0.51 | 0.48 (masked) | 0.84 | 0.44 | 0.43 (v2 live: 0.86-0.91) |
| 5G9WMtou v2 | 0.93 | 0.93 | 0.91 | 0.93 | 0.93 |
| 5GxpdbRS v4 | 0.94 | 0.99 | 0.98 | 0.90 | 0.94 |
| 5CXEMm6u v7 | 0.95 | 0.96 | 0.99 | 0.93 | 0.92 |
| 5D4XN6uG v5 | 0.94 | 0.97 | 0.93 | 0.93 | 0.96 |
| sn118gen v3 | 0.91 | 0.91 | - | - | 0.86 |

## v12 by family on the stand-ins (official grader, bench 16; practice/generator/20261110T023440Z)
| Pack | Family | Mean | Misses |
|---|---|---|---|
| kinfolk v2 | two-favs | 0.89 | 4 half, 1 abstention |
| m118-gen v4 | alias-pair | 1.00 | - |
| reaxgen-b1 | ls2b hopm hd2 / hd3 | 0.69 / 0.85 | 5 abstentions, 6 half |
| 5ELk1RHE v3 | ls2b hopm late1 sal8 / sal8 | 0.80 / 0.93 | 5 stale value asserted |
| starter kit | four families | 1.00 | - |

## What would lift us (in order)
1. No hedge on a partial list: 6 of our zeros are "abstained on an answerable question" (a found item plus "no
   record of a second"). dan0l v46's `MEMORY_LANE_SYSTEM` passage (released) says to give the items found, say
   nothing of the rest and keep the answer line to those: each such zero becomes 0.5.
2. Name chain for full names too: reaxgen-style identity records ("Kenya Swartz ... calls them Teo") tie a
   two-word name to a nickname; pin the nickname's records ("Teo also loves B") the way v12 does for first names.
3. Pin the nickname's newest and distinct records first: with the stale C copied five times, the 6-record cap fills
   with copies and can drop the update and the last "also" line.
