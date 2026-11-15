#!/bin/bash
# Build packs from released staged-records-v4 (tetgol's predecessor, 5FnYAk) in the no-network sandbox.
cd /home/bittensor/ditto || exit 1
HK=$(python3 - <<'P'
import json
se = json.load(open("live/2026-11-15T2256/public_dueling_seasons.json"))["seasons"]
for s in se:
    for c in (s.get("pins") or {}).get("columns") or []:
        if c["submission_id"].startswith("e4cfece4"):
            print(c["miner_hotkey"]); raise SystemExit
P
)
echo "hotkey ${HK:0:8}"
GRADING_BENCH=18 GRADING_BENCHES= MINER_HOTKEY=$HK bash tools/gen_pack_sandbox.sh \
  .cache/miner_gens/dl/5FnYAk_e4cfece4/src .cache/miner_gens/packs/sr4 35 1 2 3 2>&1 | tail -15
ls -la .cache/miner_gens/packs/sr4
