import json, subprocess
from datetime import datetime
B = "https://platform-api.heyditto.ai/api/v1/public/"
def get(p):
    return json.loads(subprocess.run(["curl", "-s", "--max-time", "30", B + p], capture_output=True, text=True).stdout)
def t(s): return datetime.fromisoformat(s.replace("Z", "+00:00"))
act = get("activity?limit=200")["entries"]
for e in act:
    if e["name"] == "overhorizoner" and e["version"] == 3:
        print("OURS", e["status"], "rank", e["validator_queue_rank"], "count", e["score_count"], "wait", e["scoring_wait"], "retry", e["retry_state"])
recent = sorted([e for e in act if e["status"] == "scored" and e.get("submitted_at")], key=lambda e: e["submitted_at"], reverse=True)[:10]
for e in recent:
    sc = get(f"agent/{e['agent_id']}/scores")
    times = sorted(t(s[k]) for s in sc.get("scores", []) for k in ("created_at", "scored_at", "submitted_at") if s.get(k))
    sub = t(e["submitted_at"])
    first = f"{(times[0]-sub).total_seconds()/60:.0f} min" if times else "?"
    last = f"{(times[-1]-sub).total_seconds()/60:.0f} min" if times else "?"
    print(f"{e['name']} v{e['version']} submitted {e['submitted_at'][:16]} first score +{first} quorum +{last} n={len(sc.get('scores', []))}")
