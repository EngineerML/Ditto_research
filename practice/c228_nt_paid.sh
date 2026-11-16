#!/bin/bash
# number_threads port: traced image of the c228 working tree (c228ntt), staged-records-v4 pack 1, 35 cases.
# Compare with v6 (0.01) and dan0l v59 (0.74) in practice/generator/20261115T232734Z.
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
PY=.venv/bin/python
rm -rf /tmp/c228ntt /tmp/replay_build/c228ntt; mkdir -p /tmp/c228ntt
cp -r c228/. /tmp/c228ntt/
python3 tools/add_trace_dan0l.py /tmp/c228ntt /tmp/replay_build/c228ntt > /dev/null && bash tools/build_harness.sh ditto-harness:c228ntt /tmp/replay_build/c228ntt | tail -1
echo "start $(date -u +%H:%M) $($PY tools/key_usage.py)"
$PY tools/key_usage.py --need 3 > /dev/null || { echo "balance under \$3, not starting"; exit 1; }
timeout 3600 $PY tools/generator_panel.py --packs .cache/miner_gens/packs/sr4-p1 --agent nt=c228ntt --concurrency 4 2>&1 | grep -v "^20" | tail -5
echo "done $(date -u +%H:%M) $($PY tools/key_usage.py)"
ls -td practice/generator/2026*Z | head -1
