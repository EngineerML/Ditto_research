"""List artifact releases in a snapshot: released ones and upcoming ETAs, with bench and composite."""
import json, sys
from datetime import datetime, timedelta, timezone
d = sys.argv[1].rstrip("/") + "/"
act = json.load(open(d + "public_activity_limit_200.json"))["entries"]
lb = {r["agent_id"]: r for r in json.load(open(d + "public_leaderboard.json"))["entries"]}
now = datetime.now(timezone.utc)
print("now", now.strftime("%m-%d %H:%M"), "keys", sorted(act[0]["artifact_release"].keys()))
seen = set()
for e in act:
    r = e.get("artifact_release") or {}
    if not r or r.get("status") in (None, "none", "not_eligible") or e["agent_id"] in seen:
        continue
    seen.add(e["agent_id"])
    fin = r.get("finalized_at") or r.get("crowned_at")
    eta = r.get("available_at") or (fin and (datetime.fromisoformat(fin.replace("Z", "+00:00")) + timedelta(hours=r.get("embargo_hours") or 48)).isoformat())
    l = lb.get(e["agent_id"], {})
    print(f"{e['name']:<14} v{e['version']:<4} {e['agent_id'][:8]} {r.get('status'):<10} crowned {(r.get('crowned_at') or '')[:16]} avail {(eta or '')[:16]} bench {l.get('bench_version')} comp {l.get('composite')} mem {l.get('memory_mean')}")
