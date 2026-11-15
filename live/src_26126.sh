#!/bin/bash
# Source availability of the season 26126 pins, local copies, and the current board top 8.
cd /home/bittensor/ditto || exit 1
source /etc/profile.d/zz-proxy.sh
B=https://platform-api.heyditto.ai/api/v1/public/dueling/generator-sources/
for sid in 33c60a4b-* c955422c-9891-4d09-9f8a-bc2022533934 41a497e8-0124-48f4-b73b-56466801459c 0506250c ba2ee4d1 e4cfece4-6fe2-448c-863d-304da1c242cf; do :; done
d=live/2026-11-15T2256
python3 - $d <<'P'
import json, sys, subprocess
d = sys.argv[1] + "/"
B = "https://platform-api.heyditto.ai/api/v1/public/dueling/generator-sources/"
se = {s["season_index"]: s for s in json.load(open(d + "public_dueling_seasons.json"))["seasons"]}
for c in se[26126]["pins"]["columns"]:
    sid = c["submission_id"]
    r = subprocess.run(["curl", "-s", "--max-time", "20", B + sid], capture_output=True, text=True).stdout
    try: j = json.loads(r)
    except Exception: j = {}
    print(c["column_id"], sid, "available", j.get("available"), "release_at", str(j.get("release_at"))[:16])
for sid in ["e4cfece4-6fe2-448c-863d-304da1c242cf"]:
    r = subprocess.run(["curl", "-s", "--max-time", "20", B + sid], capture_output=True, text=True).stdout
    try: j = json.loads(r)
    except Exception: j = {}
    print("staged-records-v4", sid, "available", j.get("available"), "release_at", str(j.get("release_at"))[:16])
lb = json.load(open(d + "public_leaderboard.json"))["entries"]
for i, r in enumerate(lb[:8]):
    print(i + 1, r["agent_name"], r["agent_version"], r["agent_id"][:8], r.get("composite") or r.get("score"))
P
ls .cache/miner_gens/dl/
