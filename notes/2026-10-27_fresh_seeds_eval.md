# Current build on five brand-new seeds, inspected by trajectory (2026-10-27)

Build e1900b1 (image combined-v5g: fixes 1, 2, 3, 4b/4c, 6 on top of v4d), all 100 tool questions per
seed, platform providers, traces kept (practice/<stamp>_ditto-harness-combined-v5g_full_rerun).
Every miss with its trajectory: practice/fresh5/misses.md, made by tools/misses_by_trace.py.

| Seed | Tool |
|---|---|
| 6731859204417765093 | 0.901 |
| 2390481765520983117 | 0.960 |
| 8156240937718452209 | 0.957 |
| 4917382650194027763 | 0.957 |
| 1078534962281746651 | 0.951 |
| mean | 0.945 |

(Seed 7019583318866023713, partly seen while tuning: 0.987, with horizon v1 0.948 and v4b 0.928 on the
same questions.)

## Where the ~27 points per 500 questions go

| | Mechanism | Misses | Points | Kind |
|---|---|---|---|---|
| A | world_business_workflow: "do I already have a workflow ... if not create it": answered from a memory note without listing (1); refused after listing because another project's routing note says "do not create or run a reusable workflow" (1); create_workflow with the wrong or garbled review contact (2) | 4 | 4.0 | design |
| B | world_memory_delete with "email" in the message: deleted the person's email record or another record, the receipt in the packet every time | 4 | 4.0 | design (wrongly skipped earlier from older-seed tallies) |
| C | delegated work: "have a worker ... in the background" -> artifacts or "send the PDF"; "please actually generate unit tests" -> asks for the code; run_code before execute_agent_job | 4 | 3.3 | design |
| D | live questions routed to the records lane: capability ("what can I lean on you for"), route_web_not_memory ("this minute ... the newest"), stale_context_web ("what's current") -> "no record" or general knowledge | 3 | 3.0 | design |
| E | feedback: "let the team know ..." asks for an email; "report to the devs" uses an add-on tracker; no note | 2 | 2.0 | design |
| F | restraint effort: clarification without the setting name ("Which do you want: quick answers or deep dives?"), 2 of 5 seeds | 2 | 2.0 | fragile, recurring |
| G | routing: gave up after list_workflows | 2 | 2.0 | design (deferred) |
| H | one extra call: second web search, web search before run_code, search_tools before set_chat_tool_preferences, run_code twice | 4 | 1.3 | fragile |
| I | singles: scoped "planning context" notes overrode the project's own recipient (email); a wrong-id update overwrote another project's scratchpad (and broke its follow-up read); registry figure; image create-then-edit order; add-on confirmation code not reported | 6 | ~5.4 | mixed |

Two lessons: families that pass on the seeds we had looked at can still fail at 1 in 4 on new seeds (B,
C), so a skip needs fresh-seed evidence; and notes from other questions sharing one memory store (scoped
"planning context" notes, other projects' routing notes) cause misses in several families (A, I).
