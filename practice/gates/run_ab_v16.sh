#!/bin/bash
# A/B (paid, real model) of the dan0l v34 memory ports in drp23v16 against v8 (ditto-harness:drp23v15), on the memory
# types horizon trails the top agents on (near-miss and its twin, record-quantity cf-base/cf-variant, story quantity
# and next action, false-premise and its twin, isolation contact): 61 cases a seed on seeds 5119 and 2190 (bench 15).
# Every memory wave is still seeded where it falls. Image ditto-harness:drp23v16 must be built (traced) first.
cd /home/bittensor/ditto || exit 1
source /etc/profile.d/zz-proxy.sh
.venv/bin/python tools/key_usage.py
for SEED in 5119792693744740612 2190058953981709433; do
  for IMAGE in drp23v15 drp23v16; do
    echo "===== $IMAGE seed $SEED ($(wc -l < practice/gates/ab_v16/cases_$SEED.txt) cases) $(date -u +%H:%M)"
    timeout 3600 python3 tools/practice_docker.py --image ditto-harness:$IMAGE --run-size full --seed "$SEED" --bench-version 15 \
      --concurrency 8 --trace --timeout 3400 --only-cases "practice/gates/ab_v16/cases_$SEED.txt" --scorer-bin "$PWD/.cache/dittobench-api-subset-v15" 2>&1 \
      | grep -E "saved|stopped early|Error|Traceback|memory_mean|composite" | tail -6
    .venv/bin/python tools/key_usage.py
  done
done
echo "===== A/B done $(date -u +%H:%M)"
