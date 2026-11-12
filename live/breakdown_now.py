"""Per-agent dueling breakdowns for the leaderboard agents in a snapshot folder; also our agents in activity."""
import json, sys, subprocess
d = sys.argv[1].rstrip("/") + "/"
B = "https://platform-api.heyditto.ai/api/v1/public/agent/"
lb = json.load(open(d + "public_leaderboard.json"))
for r in lb["entries"][:7] + [e for e in lb["entries"] if e["agent_name"] == "uid236"]:
    out = d + f"scores_{r['agent_name']}_{r['agent_version']}.json"
    subprocess.run(["curl", "-s", "--max-time", "30", B + r["agent_id"] + "/scores", "-o", out])
    js = json.load(open(out))
    rows = js.get("scores") or js.get("entries") or js
    print(f"\n## {r['agent_name']} v{r['agent_version']}  off {r['official_composite']:.4f}")
    if isinstance(rows, dict):
        print(list(rows)[:15]); continue
    for s in rows[:6]:
        bd = s.get("dueling_breakdown") or {}
        cols = bd.get("columns") or bd.get("column_scores") or {}
        if isinstance(cols, list):
            cols = {c.get("column_id"): round(c.get("score", c.get("value", 0)) or 0, 3) for c in cols}
        print(" ", s.get("season_index") or bd.get("season_index"), "comp", s.get("composite"),
              "datagen", bd.get("datagen") or bd.get("datagen_score") or bd.get("base"),
              "cols", cols, "| keys", sorted(bd)[:14] if bd and not cols else "")
act = json.load(open(d + "public_activity_limit_200.json"))
print("\nstatus_counts", act["status_counts"])
for e in act["entries"]:
    nm = (e.get("agent_name") or e.get("name") or "")
    if "horizon" in nm.lower() or (e.get("miner_hotkey") or "").startswith("5GHE") :
        print("OURS", json.dumps(e)[:400])
print(sorted(act["entries"][0]))
for e in act["entries"][:12]:
    print({k: e.get(k) for k in ("agent_name", "agent_version", "status", "composite", "reason", "created_at", "updated_at") if k in e})
