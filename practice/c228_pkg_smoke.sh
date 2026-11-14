#!/bin/bash
# Build the upload tarball exactly as shipped (no trace hooks) and answer a free mock pack run with it.
cd /home/bittensor/ditto || exit 1
OUT=${1:-practice/submission_c228_v1.tgz}
B=$(mktemp -d); tar -xzf "$OUT" -C "$B"
docker build -q -t ditto-harness:c228pkg "$B" | tail -1
rm -rf "$B"
timeout 900 .venv/bin/python tools/generator_panel.py --mock --packs .cache/miner_gens/packs/s26111-seed1 --agent pkg=c228pkg --concurrency 6 > /tmp/c228_pkg_mock.log 2>&1
echo "panel exit $?"
d=$(ls -td practice/generator/*-mock | head -1)
echo "$d"
ls "$d"
grep -h "case=" "$d"/*.log "$d"/*/*.log 2>/dev/null | grep -c "lane=" || true
grep -h -i "traceback\|exception" "$d"/*.log "$d"/*/*.log /tmp/c228_pkg_mock.log 2>/dev/null | head -5
python3 - "$d" <<'P'
import json, glob, sys
for f in sorted(glob.glob(sys.argv[1] + "/run-*.json")):
    r = json.load(open(f))
    seeds = (r.get("score") or {}).get("seeds") or []
    cases = seeds[0]["cases"] if seeds else []
    print(f.split("/")[-1], "cases graded", len(cases), "status", (r.get("score") or {}).get("status"))
P
