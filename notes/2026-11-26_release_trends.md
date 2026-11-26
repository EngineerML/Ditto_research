# 2026-11-26: every unread SN118 release downloaded, and the trend across generators and agents

## What was fetched
- Snapshot `live/2026-11-26T1515/` (activity, leaderboard, generator board/rounds, dueling seasons, bench, terms, CLA).
- `live/release_inventory.py` checked 657 agent ids and 207 generator ids seen in all snapshots against the public
  artifact / generator-source endpoints. Missing and released: **68 generator sources + 2 agents**, all downloaded with
  `live/fetch_missing_releases.py` (SHA-256 checked, safe extraction; nothing run). Generators in
  `.cache/miner_gens/dl/`, agents in `released/` (kaelith v2 = an old bench-13 king, horizon v5 = ours).
- Generator sources were read (not built) by four reviewers; their full reports with file:line citations are in
  `notes/2026-11-26_gen_review/G1-G4.md`. Strongest claims re-checked by hand (marked ✔ below).

## Agents: no new code since 11-13, scores flat
- **Release stall:** the newest released bench-18 agent is still dan0l v59 (finalized 11-13). All 208 later crowned
  agents answer 425 "source is awaiting confirmed winner emissions from a completed tempo"; no crown since 11-24 has
  `emission_confirmed_at`, so their 48 h embargo has not even started. Agent code trends can only be read from scores.
- **Ceiling:** bench 18 best composite 0.80–0.84 since 11-12 (0.92 one day), top-10 mean ~0.75, cost ~$0.48/run.
  Leader 11-26: Tessellate v3 0.843 ($0.43), crown-v284 0.796, ditto1 v5 0.783, Hades v54 0.777, tern-mem v10 0.761.
- **Crown churn:** 8–17 crowns a day since 11-12 (1–9 before). New lines: wren-mem, lh2mem, WorldLike, dinn,
  tern-mem, outline-mem, gth5. dan0l stops at v79 (11-19); bujhmml starts 11-20, its leaderboard family includes
  dan0l v70 and its generator hotkey 5DveEYvi published "dan0l v1" → bujhmml is dan0l renamed.
- **Vertical integration:** owners run an agent and a generator: wren, tern, lh2, gth5, bujhmml/dan0l, crown, Dr.
- Ditto itself merged five released-champion techniques into its product (tool-result ledger, TF-IDF tool pruning
  with top-3 safe harbor, hub-damped entity links + 1-edit typo repair, near-duplicate collapse + arc ordering,
  completeness nudges); next: alias linking and negative-instruction enforcement.

## Generators: one template, tuned to the 0.5 line, aimed at agents' code
Board 11-26: bujhmml v9 0.396, querverweis v12 0.346, m118 "bravo" v12 0.327, gen118 v3 0.318, m118 "delta" v11
0.268, gth5-gen v9 0.266, crown-scatter v13 0.256. Leaders change every snapshot; single rounds swing 0.1–0.5.

1. **Convergence on one case shape.** Nearly every lineage now ships a list question with one easy item (worth exactly
   0.5 = solved but not trivial), the other item(s) behind one indirection, and declared decoys (stale/cancelled/
   look-alike/other-case gold) that zero a filled slot. Packs narrowed to 1–2 tuned families each (no mixes).
2. **The indirection moved** from names (nicknames, titles, look-alikes; 11-08..11-15) to corrections and digit-swap
   twins (11-13..11-19), to joins whose deciding record shares no word with the question (landmarks, spouse
   reports, routines, physical marks, pronoun-only dates; 11-19..11-26), and to state over time and groups
   (bookings cancelled/reinstated, group-wide updates applied to members, conditional plans, timestamps with UTC
   offsets, computed keys).
3. **Count-word games.** ✔ crown-scatter asks "which two" while the gold holds every place (cases.go:124-133,
   text.go:184); ✔ sn118-recall asks "which two" (pools.go:40-47; G2 reports a 4-item gold); querverweis/bujhmml drop
   the count word; kinlist asks for four. A correct answer to the question as asked can be capped at 0.5.
4. **Fitting to the live panel and to agents' code.** ✔ wrengen2 v48b sets dials from logistic fits on live
   per-agent labels naming Tessellate, bujhmml, Hades, WorldLike, crown, DrPres (main.go:34-76). reaxgen keeps cells
   aimed at released harness limits (400-char windows, fan-out caps); lh2gen buries the deciding revision just past
   crown-v228's 2,500-char link cutoff and adds a fixed "There is no …" line so memory dumps read as abstentions;
   sn118gen V6 targets specific harness rules ("went back to" as revert).
5. **Multi-hotkey operation and copy-hold evasion.** ✔ m118-gen runs on three hotkeys/coldkeys with salts
   "brav…"/"char…"/"gd48…" and a comment that sibling copies never repeat fingerprints (main.go:30-32); two of
   them hold top-5 slots. ✔ bauni v4 shipped memgen v7's coref.go byte-identical 12 h before memgen v7 was
   released (same operator). ✔ Dr's world-bank code on 5GsKtwcq hard-codes Dr's hotkey (main_test.go:15).
   reaxgen 1.1 sits on four trees differing only by salt. kinfolk/kinlist span three hotkeys. gth5-gen runs an
   overlap check against 40 released archives; querverweis strips comments from v4 on.
6. **Frontier-oracle bets.** Dr's gen-v8 is built to be unsolved by the panel and credited by the frontier oracle
   (68/70 unsolved in 26151, 60/67 credited in 26145); with the oracle broken it scores 0 (Discord complaints).
7. **Data-heavy does not win.** Offline LLM-written banks (Dr only, `tools/shard_prompt.md`) and reaxgen's tables
   burned out; logic-only gan-v1 is the best released tree; tetgol's 500-line computed-key rewrite fell 0.35 → 0.13
   because one template tips the whole pack at once.
8. **Speed.** Ideas spread in 1–3 days (digit swap: staged-records → tessera → tern → querverweis → dittogen;
   hand-off chains tern → wrengen2; groups crown → gth5); a shape decays within days, so fast re-releases and extra
   hotkeys beat durable design.

## What this means for us
- **Our generator (v9.3, not uploaded):** our MultiList design is exactly the converged template, so it will not
  stand out; the live edge now is (a) state over time / group updates and (b) joins with no shared words, tuned on
  current agents. Fitting dials to live per-agent labels is the norm among leaders.
- **Agents / horizon-core:** the cheap wins the generators punish: give partial lists without hedging; never fill a
  slot with a stale, cancelled or "still at" value; link landmark/description/spouse references and adjacent turns;
  apply group-wide updates to members; order by timestamp with offsets; don't treat a memory dump as an answer.
  horizon-core already has nickname/role/description links; missing: state over time, group membership updates,
  typo repair, duplicate collapse.
- The release-watch routine's state was last written 11-23; it should be checked.
