"""Fetch /scores for the leaderboard agents plus extra NAME=agent_id pairs into a snapshot as scores_NAME.json.

    python3 live/fetch_scores.py SNAPSHOT [name=agent_id ...]
"""
import json, sys, subprocess
B = "https://platform-api.heyditto.ai/api/v1/public/agent/"
d = sys.argv[1].rstrip("/") + "/"
ids = {}
for r in json.load(open(d + "public_leaderboard.json"))["entries"]:
    ids[f"{r['agent_name'][:10]}{r['agent_version']}"] = r["agent_id"]
for x in sys.argv[2:]:
    name, aid = x.split("=")
    ids[name] = aid
act = json.load(open(d + "public_activity_limit_200.json"))["entries"]
full = {e["agent_id"][:8]: e["agent_id"] for e in act}
for name, aid in ids.items():
    aid = full.get(aid[:8], aid)
    subprocess.run(["curl", "-s", "--max-time", "30", B + aid + "/scores", "-o", d + f"scores_{name}.json"])
    try:
        n = len(json.load(open(d + f"scores_{name}.json")).get("scores", []))
    except Exception as e:
        n = f"error {e}"
    print(name, aid[:8], n)
