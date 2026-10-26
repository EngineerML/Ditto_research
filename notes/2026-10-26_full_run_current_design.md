# Full run of the current combined design (seed 3590624429364033488, 2026-10-26)

Design: combined at 086a6e5 (dan0l v24 loops, our routing and selection, the topic-path fix and
the person cards). Providers: the platform relay's own preferences (throughput sort, CoreWeave
ignored, fallbacks on): Amazon Bedrock served 1993 of 2005 calls, Groq 9, Parasail 3. 77 minutes,
$1.10. Folder practice/20261026T135427Z_ditto-harness-combined-current_full (trajectories in
trace.jsonl); merged with the re-run in ..._merged.

Three questions lost to proxy 429s or a runaway call were re-run on the same image and providers
(writes replayed, every wave seeded): the calendar restraint question passed (0 -> 1); the link
chain and automation list questions failed again, so those are real. Re-run $0.03.

| | composite | tool | memory | tool eff. | consistency | over-call | conversation |
|---|---|---|---|---|---|---|---|
| this run, merged | 0.8679 | 0.8515 | 0.8980 | 0.9922 | 1 (13 groups, 0 split) | 1 | 1 |
| this run, raw | 0.8634 | 0.8425 | 0.8980 | 0.9922 | 1 | 1 | 1 |
| combined before the fixes (pinned cheap providers, merged) | 0.8598 | 0.8692 | 0.8600 | 0.9963 | 1 | 0.9981 | 1 |
| dan0l v24 (pinned cheap providers, merged) | 0.8649 | 0.8592 | 0.8807 | 0.9963 | 1 | 0.9979 | 1 |
| projection from the A/B tests | 0.8817 | 0.8692 | 0.9040 | | | | |

- Memory 0.860 -> 0.898 as projected (0.904): the topic-path fix and person cards hold up in a
  full run on another provider.
- Tool 0.869 -> 0.851 although no tool code changed: five tool questions that flip between runs
  (two timer decoys, a font set, an image edit, a sandbox result) went the other way, five others
  came back; the two re-run failures (link chain, automation list) also passed before. Tool
  questions are as sampling-sensitive as memory ones; one run moves the tool mean by +-0.02.
- Tool efficiency 0.9922: nine questions with an extra call (three link chains search twice,
  two state-dependent calendars, memory save, sandbox, web recovery, memory delete).
- 20 of 2016 calls ran into their own max_tokens (4000/6000/16000) reasoning; Bedrock has no
  lower cap (117964), the model ran away. Almost all of those questions still scored 1.
- Providers differ from dan0l's run, so the 0.003 lead over dan0l's 0.8649 is not a clean
  comparison; a dan0l run on the same providers would make it one.
