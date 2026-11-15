#!/bin/bash
# staged-records-v4 (tetgol predecessor) pack 1, 35 cases: our v6 (traced c228fx2t) vs released dan0l v59 (traced).
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
PY=.venv/bin/python
mkdir -p .cache/miner_gens/packs/sr4-p1
[ -e .cache/miner_gens/packs/sr4-p1/pack-1.json ] || cp .cache/miner_gens/packs/sr4/pack-1.json .cache/miner_gens/packs/sr4-p1/
if ! docker image inspect ditto-harness:d59t > /dev/null 2>&1; then
  rm -rf /tmp/d59t /tmp/replay_build/d59t; mkdir -p /tmp/d59t
  cp -r released/dan0l-v59_a06c97e5/src/. /tmp/d59t/
  python3 tools/add_trace_dan0l.py /tmp/d59t /tmp/replay_build/d59t > /dev/null && bash tools/build_harness.sh ditto-harness:d59t /tmp/replay_build/d59t | tail -1
fi
echo "start $(date -u +%H:%M) $($PY tools/key_usage.py)"
$PY tools/key_usage.py --need 3 > /dev/null || { echo "balance under \$3, not starting"; exit 1; }
timeout 3600 $PY tools/generator_panel.py --packs .cache/miner_gens/packs/sr4-p1 --agent v6=c228fx2t --agent d59=d59t --concurrency 4 2>&1 | grep -v "^20" | tail -25
echo "done $(date -u +%H:%M) $($PY tools/key_usage.py)"
ls -td practice/generator/2026*Z | head -1
