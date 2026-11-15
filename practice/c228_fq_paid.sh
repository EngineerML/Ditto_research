#!/bin/bash
# 5FqQq9 v2 (pollen-probe 0.9) pack 1, 35 cases: vanilla crown-v228 vs v5 as uploaded, traced, real model.
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
PY=.venv/bin/python
echo "start $(date -u +%H:%M) $($PY tools/key_usage.py)"
$PY tools/key_usage.py --need 3 > /dev/null || { echo "balance under \$3, not starting"; exit 1; }
P=.cache/miner_gens/packs/fq-v2-p1; rm -rf $P; mkdir -p $P
cp .cache/miner_gens/packs/fq-v2/pack-1.json $P/fq-v2.json
timeout 3600 $PY tools/generator_panel.py --packs $P --agent crown=crown228t --agent v5=c228v5t --concurrency 4 2>&1 | grep -v "^20" | head -30
echo "done $(date -u +%H:%M) $($PY tools/key_usage.py)"
