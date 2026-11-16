#!/bin/bash
# On the newest snapshot: our v6 status in the activity feed, then per-season column means for ours vs the board top 6, with pins.
cd /home/bittensor/ditto || exit 1
source /etc/profile.d/zz-proxy.sh
d=$(ls -d live/2026-11-1*T* | tail -1)
echo "snapshot $d"
python3 - "$d" <<'P'
import json, sys
d = sys.argv[1] + "/"
act = json.load(open(d + "public_activity_limit_200.json"))
for e in act["entries"]:
    if e["name"] == "overhorizoner":
        print({k: e.get(k) for k in ("version", "agent_id", "status", "last_scored_at", "score_count", "provisional_composite", "review_reason", "screening_reason")})
P
A="ours6=aa7f166c"
L=$(python3 - "$d" <<'P'
import json, sys
d = sys.argv[1] + "/"
print(" ".join(f"{r['agent_name'][:10]}{r['agent_version']}={r['agent_id']}" for r in json.load(open(d + "public_leaderboard.json"))["entries"][:6]))
P
)
python3 live/fetch_scores.py $d $A $L | tail -8
python3 live/rel_cols.py $d $A $L 2>&1 | tail -45
