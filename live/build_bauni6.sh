#!/bin/bash
# Download the released bauni v6 source (season 26126 c2, 41a497e8) and build packs 1-3 in the no-network sandbox.
cd /home/bittensor/ditto || exit 1
SID=41a497e8-0124-48f4-b73b-56466801459c
DL=.cache/miner_gens/dl/bauni-v6_41a497e8
[ -e $DL/archive.bin ] || bash live/gen_fetch.sh $SID bauni-v6_41a497e8 | tail -12
HK=$(python3 - <<'P'
import json
se = json.load(open("live/2026-11-15T2256/public_dueling_seasons.json"))["seasons"]
for s in se:
    for c in (s.get("pins") or {}).get("columns") or []:
        if c["submission_id"].startswith("41a497e8"):
            print(c["miner_hotkey"]); raise SystemExit
P
)
echo "hotkey ${HK:0:8}"
python3 -c "import json; m=json.load(open('$DL/meta.json')); print({k: m[k] for k in m if k not in ('archive_url',)})" 2>&1 | cut -c1-600
GRADING_BENCH=18 GRADING_BENCHES= MINER_HOTKEY=$HK bash tools/gen_pack_sandbox.sh \
  $DL/src .cache/miner_gens/packs/bauni6 35 1 2 3 2>&1 | tail -15
ls -la .cache/miner_gens/packs/bauni6
