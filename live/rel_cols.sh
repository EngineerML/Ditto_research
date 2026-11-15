#!/bin/bash
# Released beast v16-v19 / dan0l v59 / crown-v228 column scores vs ours and leaders, per season.
cd /home/bittensor/ditto || exit 1
source /etc/profile.d/zz-proxy.sh
d=$(bash live/fetch_now.sh | tail -1)
echo "snapshot $d"
A="ours6=aa7f166c ours5=52d15b97 b16=9c2f44cc b17=dfc295d0 b18=d6d5c157 b19=871a93d4 d59=a06c97e5 cr228=673386d0"
python3 live/fetch_scores.py $d $A | tail -12
L=$(python3 - "$d" <<'P'
import json, sys
d = sys.argv[1] + "/"
print(" ".join(f"{r['agent_name'][:10]}{r['agent_version']}={r['agent_id']}" for r in json.load(open(d + "public_leaderboard.json"))["entries"][:5]))
P
)
python3 live/rel_cols.py $d $A $L
