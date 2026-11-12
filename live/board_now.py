"""Summarise a live snapshot folder: leaderboard, pending activity, generator board, current season."""
import json
import sys
from collections import defaultdict

d = sys.argv[1].rstrip("/") + "/"
lb = json.load(open(d + "public_leaderboard.json"))
print({k: lb[k] for k in ("generated_at", "count", "active_bench_version", "emission_bench_version")})
rows = lb.get("entries") or lb.get("leaderboard") or lb.get("agents")
for r in rows:
    print(r["rank"], f"{r['agent_name']} v{r['agent_version']}", r["agent_id"][:8], (r["miner_hotkey"] or "")[:6],
          "comp", r["composite"], "off", r["official_composite"], "tool", r["tool_mean"], "mem", r["memory_mean"],
          "cost", round((r["average_run_cost_microusd"] or 0) / 1e6, 3), "n", r["score_count"],
          "elig", r["eligible"], r["emission_eligible"], "bench", r["bench_version"])

print("\n== activity (latest per agent) ==")
act = json.load(open(d + "public_activity_limit_200.json"))
items = act.get("items") or act.get("activity") or act.get("events") or act
if isinstance(items, dict):
    print(list(items)[:20])
else:
    print(sorted(items[0].keys()))
    seen = {}
    for it in items:
        key = (it.get("agent_name"), it.get("agent_version"))
        if key not in seen:
            seen[key] = it
    for key, it in list(seen.items())[:30]:
        print(key, {k: it.get(k) for k in ("kind", "event", "status", "composite", "score", "reason", "created_at", "miner_hotkey") if k in it})

print("\n== generator board ==")
gb = json.load(open(d + "generator_board.json"))
if isinstance(gb, dict):
    print(list(gb)[:20])
    gens = gb.get("entries") or gb.get("generators") or gb.get("board") or []
else:
    gens = gb
if gens:
    print(sorted(gens[0].keys()))
    for g in gens[:15]:
        print({k: g.get(k) for k in ("rank", "name", "generator_name", "version", "score", "board_score", "hotkey", "miner_hotkey", "status", "column", "pinned") if k in g})

print("\n== seasons ==")
se = json.load(open(d + "public_dueling_seasons.json"))
ss = se.get("seasons") if isinstance(se, dict) else se
if isinstance(se, dict):
    print(list(se)[:20])
if ss:
    print(sorted(ss[0].keys()))
    for s in ss[:4]:
        print(json.dumps(s)[:700])
