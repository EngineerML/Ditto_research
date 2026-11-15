"""Our and gth5's rank on a snapshot's leaderboard."""
import json, sys
lb = json.load(open(sys.argv[1].rstrip("/") + "/public_leaderboard.json"))["entries"]
print("entries", len(lb))
for i, r in enumerate(lb):
    if r["agent_name"] in ("overhorizoner", "gth5", "Tessellate", "marlowe"):
        print(i + 1, r["agent_name"], r["agent_version"], r["agent_id"][:8], r.get("composite"))
