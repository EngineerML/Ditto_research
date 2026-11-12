import json, subprocess
B = "https://platform-api.heyditto.ai/api/v1/public/"
def get(p): return json.loads(subprocess.run(["curl", "-s", "--max-time", "30", B + p], capture_output=True, text=True).stdout)
for aid, nm in (("d2429eb9", "dan0l v50"), ("f6463c12", "Tessellate v11")):
    act = get("activity?limit=200")["entries"]
    full = next(e["agent_id"] for e in act if e["agent_id"].startswith(aid))
    sc = get(f"agent/{full}/scores")
    print(nm, full, "release", json.dumps(next(e for e in act if e["agent_id"] == full)["artifact_release"]))
    for s in sc.get("scores", [])[:6]:
        bd = s.get("dueling_breakdown") or {}
        pc = (s.get("gate_evidence") or {}).get("priced_cost") or {}
        cols = " ".join(f"{c['column_id']}={c['mean']:.2f}(b{c['grading_bench_version']})" for c in bd.get("columns", []))
        print(f"  b{s.get('bench_version')} s{bd.get('season_index')} comp {s['composite']:.3f} tool {s['tool_mean']:.3f} mem {s['memory_mean']:.3f} dg {bd.get('datagen_raw')} gate {bd.get('datagen_gate')} cost {pc.get('cost_usd')} | {cols}")
