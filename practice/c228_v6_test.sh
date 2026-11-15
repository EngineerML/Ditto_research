#!/bin/bash
# Pre-package test of fix 1 + fix 2 (image c228fx2t, tree 142b5c2), asked for by the user 2026-11-15.
#   A: generator columns, 35 cases each: 5FqQq9 v2 pack 2 (fresh seed), memgen v6 normal + hidden-second-item.
#   B: one full local v18 datagen run (175 cases) on new seed 1810007, with the per-10-case progress table.
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
PY=.venv/bin/python
echo "start $(date -u +%H:%M) $($PY tools/key_usage.py)"
$PY tools/key_usage.py --need 3 > /dev/null || { echo "balance under \$3, not starting"; exit 1; }
P=.cache/miner_gens/packs/v6test; rm -rf $P; mkdir -p $P
cp .cache/miner_gens/packs/fq-v2/pack-2.json $P/fq-v2-2.json
cp .cache/miner_gens/packs/fix1/memgen-v6.json .cache/miner_gens/packs/fix1/memgen-v6-hidden.json $P/
echo "== A: generator packs"
timeout 3600 $PY tools/generator_panel.py --packs $P --agent v6=c228fx2t --concurrency 4 2>&1 | grep -v "^20" | head -14
echo "after A $(date -u +%H:%M) $($PY tools/key_usage.py)"
echo "== B: full datagen seed 1810007"
bash practice/c228_full_watch.sh c228fx2t 1810007
echo "done $(date -u +%H:%M) $($PY tools/key_usage.py)"
