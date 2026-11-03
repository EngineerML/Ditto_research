#!/bin/bash
# A/B (paid, real model): v8 (ditto-harness:drp23v15) against drp23v15b on the requests its changes reach: product-hint
# changes, live lookups, restraint and parallel web-image cases, on v8's three live seeds plus seed 5119 (where the
# coined brand Rigut collides with "right"), regenerated at surface salt 0. Case lists: practice/gates/ab_v15b/.
cd /home/bittensor/ditto || exit 1
source /etc/profile.d/zz-proxy.sh
SUBSET=.cache/dittobench-api-subset-v15
.venv/bin/python tools/key_usage.py
for SEED in 5119792693744740612 2190058953981709433 6007065558233246269 2497187654609273566; do
  for IMAGE in drp23v15 drp23v15b; do
    echo "===== $IMAGE seed $SEED ($(wc -l < practice/gates/ab_v15b/cases_$SEED.txt) cases) $(date -u +%H:%M)"
    timeout 3600 python3 tools/practice_docker.py --image ditto-harness:$IMAGE --run-size full --seed "$SEED" --bench-version 15 \
      --concurrency 8 --trace --timeout 3400 --only-cases "practice/gates/ab_v15b/cases_$SEED.txt" --scorer-bin "$PWD/$SUBSET" 2>&1 \
      | grep -E "saved|stopped early|Error|Traceback|tool_mean|memory_mean|composite" | tail -6
    .venv/bin/python tools/key_usage.py
  done
done
echo "===== A/B done $(date -u +%H:%M)"
