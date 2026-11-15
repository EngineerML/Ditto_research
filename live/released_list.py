"""From a snapshot: count artifact release statuses, list downloadable (released) agents, and show seasons."""
import json, sys
from collections import Counter
d = sys.argv[1].rstrip("/") + "/"
act = json.load(open(d + "public_activity_limit_200.json"))["entries"]
c = Counter((e.get("artifact_release") or {}).get("status") for e in act)
print("release statuses", dict(c))
for e in act:
    r = e.get("artifact_release") or {}
    if r.get("download_available") or r.get("status") in ("released", "available", "public"):
        print(f"  DOWNLOADABLE {e['name']} v{e['version']} {e['agent_id'][:8]} status {r.get('status')} avail {r.get('available_at')} bench {r.get('bench_version')} prov {e.get('provisional_composite')}")
print("\nscored bench-18 agents by provisional composite (activity window):")
rows = [e for e in act if e.get("provisional_composite") is not None and (e.get("artifact_release") or {}).get("bench_version") == 18]
for e in sorted(rows, key=lambda e: -e["provisional_composite"])[:20]:
    print(f"  {e['provisional_composite']:.4f} {e['name']} v{e['version']} {e['agent_id'][:8]} scored {str(e.get('last_scored_at'))[:16]} status {e['status']}")
s = json.load(open(d + "public_dueling_seasons.json"))
items = s.get("entries") or s.get("seasons") or s
if isinstance(items, dict):
    print("seasons keys", list(items)[:10])
else:
    for x in items[:4]:
        print("season", {k: x.get(k) for k in list(x)[:12]})
