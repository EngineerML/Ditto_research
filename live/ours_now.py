import json, subprocess, sys
B = "https://platform-api.heyditto.ai/api/v1/public/"
def get(p):
    r = subprocess.run(["curl", "-s", "--max-time", "30", B + p], capture_output=True, text=True)
    return json.loads(r.stdout)
act = get("activity?limit=200")
for e in act["entries"]:
    if e["name"] == "overhorizoner" and e["version"] >= 3:
        print(json.dumps(e, indent=1)[:6000])
print("status_counts", act["status_counts"])
waiting = [e for e in act["entries"] if e["status"] in ("evaluating", "not_queued", "queued", "scoring", "awaiting_validators") or e.get("scoring_wait")]
for e in waiting[:15]:
    print(e["name"], e["version"], e["status"], e.get("submitted_at"), "rank", e.get("validator_queue_rank"), "gate", e.get("validator_queue_gate"), "wait", json.dumps(e.get("scoring_wait"))[:200], "count", e.get("score_count"))
