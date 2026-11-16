#!/bin/bash
# Download the released querverweis v2 source (01e36814, predecessor of the always-pinned v3) and build packs 1-3 in the no-network sandbox.
cd /home/bittensor/ditto || exit 1
read SID HK < <(python3 - <<'P'
import json, glob
for f in sorted(glob.glob("live/2026-11-1*/generator_board.json")) + sorted(glob.glob("live/2026-11-1*/public_dueling_seasons.json")):
    j = json.load(open(f))
    rows = j.get("entries") or [c for s in j.get("seasons", []) for c in (s.get("pins") or {}).get("columns") or []]
    for g in rows:
        if g["submission_id"].startswith("01e36814"):
            print(g["submission_id"], g["miner_hotkey"]); raise SystemExit
P
)
echo "sid ${SID:0:8} hotkey ${HK:0:8}"
[ -n "$SID" ] || { echo "id not found"; exit 1; }
DL=.cache/miner_gens/dl/querverweis-v2_01e36814
[ -e $DL/archive.bin ] || bash live/gen_fetch.sh $SID querverweis-v2_01e36814 | tail -6
echo "archive $(sha256sum $DL/archive.bin | cut -c1-16)  meta $(grep -o '"source_sha256":"[0-9a-f]\{16\}' $DL/meta.json)"
ls $DL/src $DL/src/gen 2>/dev/null | head -40
GRADING_BENCH=18 GRADING_BENCHES= MINER_HOTKEY=$HK bash tools/gen_pack_sandbox.sh \
  $DL/src .cache/miner_gens/packs/qv2 35 1 2 3 2>&1 | tail -6
