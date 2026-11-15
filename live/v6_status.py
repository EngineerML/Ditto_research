"""Status of our overhorizoner entries in a snapshot's activity feed, plus per-run scores."""
import json, sys
d = sys.argv[1].rstrip("/") + "/"
for e in json.load(open(d + "public_activity_limit_200.json"))["entries"]:
    if e["name"] == "overhorizoner" and e["version"] >= 5:
        print({k: e.get(k) for k in ("version", "agent_id", "status", "last_scored_at", "score_count", "provisional_composite", "review_reason", "screening_reason")})
for r in json.load(open(d + "scores_ours6.json")).get("scores", []):
    bd = r.get("dueling_breakdown") or {}
    print("season", bd.get("season_index"), "comp", r.get("composite"), "created", str(r.get("created_at"))[:16])
