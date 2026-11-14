#!/bin/bash
# One full local v18 datagen run (175 cases) of the patched c228 base, traced. Approved by the user 2026-11-14.
#
#   bash practice/c228_full1.sh [IMG] [SEED]
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
PY=.venv/bin/python
IMG=${1:-c228ft}
SEED=${2:-1810005}
echo "start $(date -u +%H:%M) $($PY tools/key_usage.py)"
$PY tools/key_usage.py --need 3 > /dev/null || { echo "balance under \$3, not starting"; exit 1; }
timeout 7000 python3 tools/practice_docker.py --image ditto-harness:$IMG --run-size full --bench-version 18 --seed $SEED --trace \
  --scorer-bin $PWD/.cache/dittobench-api-v18 --concurrency 4 --timeout 6900 2>&1 | tail -6
echo "done $(date -u +%H:%M) $($PY tools/key_usage.py)"
