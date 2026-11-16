"""bauni v6: minutes between intro and relay per case, over all packs given; and how many sessions hold two relay-like records.

    python3 -I live/bauni6_gaps.py PACK.json [PACK.json...]
"""
import json, sys, collections
from datetime import datetime
t = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
gaps = collections.Counter()
for path in sys.argv[1:]:
    p = json.load(open(path))
    pairs = {x["pair_id"]: x for w in p["memory_waves"] for x in w["pairs"]}
    for c in p["cases"]:
        intro, relay = (pairs[i] for i in c["evidence_pair_ids"][-2:])
        gaps[round((t(relay["timestamp"]) - t(intro["timestamp"])) / 60)] += 1
print("minutes intro->relay:", dict(sorted(gaps.items())))
