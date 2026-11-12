import json, subprocess, os, time
B = "https://platform-api.heyditto.ai/api/v1/public/"
def get(p):
    return json.loads(subprocess.run(["curl", "-s", "--max-time", "30", B + p], capture_output=True, text=True).stdout)
d = "/home/bittensor/ditto/live/" + time.strftime("%Y-%m-%dT%H%M", time.gmtime())
os.makedirs(d, exist_ok=True)
sc = get("agent/c88411ed-5943-4c81-93e9-f6295349e2d1/scores")
json.dump(sc, open(d + "/scores_overhorizoner_3.json", "w"))
lb = get("leaderboard"); json.dump(lb, open(d + "/public_leaderboard.json", "w"))
print(d, "status", sc.get("status"), "median", sc.get("median_composite"), "n", sc.get("score_count"))
for s in sc.get("scores", []):
    bd = s.get("dueling_breakdown") or {}
    cols = " ".join(f"{c['column_id']}={c['mean']:.2f}" for c in bd.get("columns", []))
    tu = s.get("token_usage") or {}
    print(f" comp {s['composite']:.3f} tool {s['tool_mean']:.3f} mem {s['memory_mean']:.3f} dg {bd.get('datagen_raw')} gate {bd.get('datagen_gate')} gsum {bd.get('generator_sum')} s{bd.get('season_index')} | {cols} | req {tu.get('requests')} tok {tu.get('total_tokens')}")
    print("   keys", [k for k in s if k not in ("token_usage","token_efficiency","composite_breakdown","dueling_breakdown")])
for r in lb["entries"][:10]:
    print(r["rank"], r["agent_name"], r["agent_version"], round(r["official_composite"],4), "tool", r["tool_mean"], "mem", r["memory_mean"], "cost", round((r["average_run_cost_microusd"] or 0)/1e6,3))
