# 2026-11-03 — horizon v8 tool A/B against plain DrPresident v23, and the top miners' tool/memory trend

## Paid A/B (`practice/gates/run_ab_v8.sh`, $0.32, 09:31–09:51 UTC)

Cases: v8's live miss categories (every decoy_*_result_usage, discovery_accent_set, capability_discovery,
world_memory_delete, v13_mutation_follow_up_read, parallel_web_image, code_compute_not_agent_job) on v8's three
live seeds, regenerated at surface salt 0: 62 cases per build (`practice/gates/ab_v8/cases_<seed>.txt`). Runs
`practice/20261103T09*_ditto-harness-drp23{v15,}_full_rerun`, traces kept.

| category | v8 | plain v23 |
|---|---|---|
| decoy result usage | 28.10 / 29 | 28.63 / 30 |
| parallel_web_image | 3.00 / 3 | 2.53 / 3 (4 and 8 extra searches) |
| discovery_accent_set | 8 / 8 | 8 / 9 |
| code_compute_not_agent_job | 2 / 2 | 2.67 / 3 |
| capability_discovery, world_memory_delete, v13_mutation_follow_up_read | equal | equal |
| **mean** | **0.968** | **0.933** |

- 3 v8 cases on seed 6007 dropped: local transport timeouts, then the inherited llm client rebuild closed in-flight
  requests (`anyio.ClosedResourceError`). Live telemetry had 0 infrastructure failures.
- Plain v23 also hit one provider 400, "'tools': maximum number of items", from the 235-tool menu.
- Run cost: v8 $0.04–0.05 a seed, v23 $0.09–0.10 (the 235-tool menu).
- The decoy misses are one mechanism in both builds: the decoy's served reply holds a figure ("Amgen alloy was last
  measured at 65,340 basis points"), not the asked issue number or session id. A reply that names the figure scores
  1.0; "No issue number was provided." scores 0.1. Which way the model goes is chance, per case.

## Trend, last versions of the top miners (`live/2026-11-03/trend/`)

| miner | bench-14 tool, oldest → newest | bench-14 memory, oldest → newest | bench-15 tool (v15-era version) |
|---|---|---|---|
| Hades v18–v25 | 0.973 → 0.989 | 0.909 → 0.957 | 0.987 (v25) |
| dan0l v29–v36 | 0.988 → 0.996 | 0.894 → 0.953 | 0.989 (v36) |
| Orsentra v16–v23 | 0.992 → 0.987 | 0.912 → 0.958 | 0.978 (v23) |
| DrPresident v22–v29 | 0.986 → 0.976 | 0.935 → 0.954 | 0.987 (v29) |
| crown v194–v202 | 0.971 → 0.980 | 0.921 → 0.928 | 0.983 (v202) |
| nanodevs v3–v10 | 0.957 → 0.993 | 0.901 → 0.936 | 0.977 (v10) |

- Tool was already 0.98–0.99 on bench 14 for every top miner; the gains of the last week are on memory.
- Bench-14 builds rescored on bench 15 with the whole catalog mostly kept their tool score (dan0l v35 0.989,
  Orsentra v21 0.985, crown-v198 0.983). DrPresident v23 is the exception (0.948), and v29 fixed it (0.987).
- v8 live tool 0.970 over three runs; the A/B puts its misses on those categories at chance, so its expected tool
  score is nearer 0.98.
