#!/bin/bash
# Source release state of the generators pinned in seasons 26123-26129, plus any querverweis / lh2gen ids seen in snapshots.
cd /home/bittensor/ditto || exit 1
source /etc/profile.d/zz-proxy.sh
B=https://platform-api.heyditto.ai/api/v1/public/dueling/generator-sources/
ids=$(python3 - <<'P'
import json, glob
seen = {}
for f in sorted(glob.glob("live/2026-11-1*/public_dueling_seasons.json")):
    for s in json.load(open(f))["seasons"]:
        for c in (s.get("pins") or {}).get("columns") or []:
            seen[c["submission_id"]] = 1
for f in sorted(glob.glob("live/2026-11-1*/generator_board.json")):
    for g in json.load(open(f))["entries"]:
        if g.get("name") in ("querverweis", "lh2gen", "gan-v1", "bauni", "tetgol", "kinlist", "bounty", "tessera") or g["submission_id"] in seen:
            seen[g["submission_id"]] = f"{g.get('name')} v{g.get('version')}"
print(" ".join(f"{k}={v if v != 1 else '?'}".replace(" ", "_") for k, v in seen.items()))
P
)
for x in $ids; do
  sid=${x%%=*}; name=${x#*=}
  r=$(curl -s --max-time 20 "$B$sid")
  python3 -c "import json,sys; j=json.loads(sys.argv[1] or '{}'); print(sys.argv[2][:8], sys.argv[3].ljust(22), 'available', j.get('available'), 'release_at', str(j.get('release_at'))[:16])" "$r" "$sid" "$name" 2>/dev/null || echo "$sid $name no answer"
done | sort -k5
