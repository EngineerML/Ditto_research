# Improving the blinkrazor v3 base (2026-10-22)

Based on: the v13 scorer and grader in ditto-subnet (`services/dittobench-api`,
`research/dittobench-datagen`), a read of the blinkrazor v3 code, and the live leaderboard
(`tools/gate_factor.py live/2026-10-22`). No paid runs yet.

## Scoring in one line

```
composite = (0.5 x tool_mean + 0.5 x memory_mean) x G
G = max(0.40, E_tool x M_meta x O_mem) x C_canary x S_conv x T_audit
```

Full run: 100 tool cases, 250 memory cases. The v13-specific per-case gates are shadow only today.

| gate | fires when | penalty |
|---|---|---|
| E_tool | extra calls on tool cases (calls above the expected count) | per case 1 - 0.40 x min(extra/3, 1), averaged |
| M_meta | twin groups split (some paraphrases right, some wrong) | 1 - 0.40 x split rate |
| O_mem | memory cases that make any non-memory tool call | 1 - 0.25 x rate |
| C_canary | the canary case surfaces the bait value | x0.25 |
| S_conv | chit-chat / declarative-ack / declarative-behaviour cases fail | 0.25 + 0.75 x pass rate (any slice fully failed: x0.25) |
| T_audit | transform-audit pairs drift one way | up to -40% |

Hard zeros that matter:
- **A tool case is zeroed if the harness sends a call no model emission backs** (changed
  arguments, replay, no emission: 409, counted unmatched). A model call that is never sent does
  *not* zero a case in ordinary runs; it is only counted run-wide (`PROTOCOL.md:352-355`).
  Corrected 2026-10-22, see `2026-10-22_hades_v6_review.md`.
- Memory: asserting two candidate values, abstaining on an answerable question, an asserted
  distractor, another user's fact, a slot answer not restated in prose.
- A generic refusal on an unanswerable question scores 0; the decline must cite a record token.
- Declarative acknowledgements must restate the stated value (a bare "Got it" scores 0.25).

## What the leaderboard says

Gate factor = composite / mean(tool, memory):

| miner | before gates | gate factor | composite |
|---|---|---|---|
| dan0l | 0.849 | 0.994 | 0.844 |
| Hades (champion) | 0.832 | 0.967 | 0.804 |
| blinkrazor v3 (our base) | 0.829 | 0.936 | 0.776 |
| T | 0.866 | 0.872 | 0.756 |

blinkrazor loses 0.053 to gates. With dan0l's gate factor it would be about 0.824. The best
pre-gate harness (T) is losing 11%. Gates are the cheapest place to gain.

## Where blinkrazor loses (code evidence from the review)

1. **Swallowed tool calls (run-wide count; zeroes only on case-window paths).** Malformed or unknown calls are rejected locally
   and never sent (agent.cpp:632-679); duplicate calls go through a SEND/HOLD model check
   (agent.cpp:595-627, 680-703), and a HOLD means the emitted call is never executed.
2. **Extra tool calls (E_tool).** Read tools get a "transient: retry once" hint (network.cpp:567-573),
   which invites a second identical call; the repeat authorizer can also SEND duplicates.
3. **Non-memory calls on memory cases (O_mem).** Lane routing is regex: one word such as "latest",
   "current", "today" sends a memory question to the action lane (lane.cpp:75, 609-622), where the
   model can call web or other tools.
4. **Paraphrase splits (M_meta, twins, T_audit).** Drafts and search passes run at temperature 0.7
   (agent.cpp:1134, records_advice.cpp:178); a follow-up rewrite can change the answer
   (agent.cpp:1185-1229); regex routing sends paraphrases down different lanes.
5. **Two answer formats.** Multi-value answers use " and " in one path and " ; " in another
   (prompts.json:17, short.cpp:35).
6. **Declines name related records** (prompts.json:17), which on the canary case invites echoing
   bait-like values.
7. **`/seed` returns 500 when embedding fails after the rows are committed** (agent.cpp:436-441).
   The validator reads a non-2xx as a failed ingest.
8. **Retrieval.** Dense hits are added only when the question has anchors (retrieval.cpp:906);
   unanchored questions keep the top 3 lexical hits (885), so paraphrases with no word overlap
   miss evidence.
9. **Cost.** 3-12 chat calls per memory case, up to ~50 with all search passes. Tokens are only a
   tie-break, but they are our practice bill.

Also note: `ShortOrderCache` reuses one model reading across cases (agent.hpp:135-199). It helps
consistency but is cross-case memoisation; keep an eye on it against the "seed or state shortcuts"
cheating rule.

## Plan, cheapest and safest first

| # | change | expected effect |
|---|---|---|
| 1 | Execute every model-emitted tool call verbatim; return validation problems as the tool result instead of rejecting locally; drop the SEND/HOLD step | the model sees and fixes its own call; lower priority after the 2026-10-22 correction |
| 2 | Remove the "retry once" hint; at most one retry only on a real transport error | E_tool closer to 1 |
| 3 | Memory questions never reach the action lane (route by "asks about the user's records", not by single words) | O_mem closer to 1 |
| 4 | Temperature 0 everywhere with distinct seeds for drafts; drop the follow-up rewrite; one answer format | M_meta / twins / T_audit |
| 5 | Check declarative-ack, chit-chat, behaviour handling; acks restate the value | protects S_conv |
| 6 | Terse grounded declines ("no record of X in ..."), exactly one asserted value | canary + abstention cases |
| 7 | `/seed` acknowledges committed rows and embeds lazily on failure | no lost waves |
| 8 | Always add top-k dense hits; weight fusion toward dense when lexical coverage is low | memory_mean |
| 9 | Fewer passes (skip search passes when the timeline note exists, gate result-read) | cheaper practice |

Steps 1-7 change behaviour that the scorer punishes directly and need little tuning. Step 8 is
where real accuracy gains are, and needs measurement.

## Measuring cheaply

- Always A/B on the **same seed** (`--seed`): most of the 0.02 run-to-run noise is the dataset,
  and a shared seed cancels it.
- `small` runs to catch regressions, `full` (~$1) only to confirm a candidate.
- `--gates` / `scripts/rehearsal_gates.py` replays the v13 gate rules on a run and prints per-case
  notes, which tells us which gate fired without extra runs.
- Hades v6 is released at 2026-10-22 07:53 UTC. Its gate factor is 0.967 vs blinkrazor's 0.936; a
  diff of the two costs nothing and may show which of the above it already fixed.
