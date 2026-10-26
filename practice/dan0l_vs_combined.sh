#!/bin/bash
# dan0l v24 (released code) and combined (our routing and selection + dan0l's loops), traced, on one competition seed,
# both pinned to one OpenRouter provider. Usage: bash practice/dan0l_vs_combined.sh small|medium|full [min balance $]
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
SIZE=${1:-small}
NEED=${2:-0.5}
SEED=3590624429364033488   # dan0l v24's own scored competition seed
# One fixed, ordered set of cheap hosts for both images; a host that rate-limits passes the call to the next.
PREFS='{"order":["deepinfra","parasail","akashml"],"allow_fallbacks":false,"data_collection":"deny"}'
PY=.venv/bin/python
for image in ditto-harness:dan0l-v24-trace ditto-harness:combined-trace; do
  $PY tools/key_usage.py --need "$NEED" || { echo "balance under \$$NEED, not starting $image"; exit 1; }
  echo "===== $image $SIZE seed $SEED $(date -u +%H:%M) $($PY tools/key_usage.py)"
  timeout 14000 python3 tools/practice_docker.py --image "$image" --run-size "$SIZE" --seed "$SEED" --trace --env "HARNESS_PROVIDER_PREFS=$PREFS" 2>&1 | tail -20
  echo "after $image: $($PY tools/key_usage.py)"
done
echo "===== done $(date -u +%H:%M)"
