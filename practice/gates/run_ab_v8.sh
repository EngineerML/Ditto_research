#!/bin/bash
# A/B on horizon v8's tool misses (paid, real model): the decoy, discovery, memory-delete, follow-up-read,
# parallel-image and code-compute tool cases of v8's three live seeds (regenerated locally at surface salt 0), run
# on v8 (ditto-harness:drp23v15) and on plain DrPresident v23 (ditto-harness:drp23), bench 15, traces kept.
# Case lists: practice/gates/ab_v8/cases_<seed>.txt. Every memory wave is still seeded where it falls.
cd /home/bittensor/ditto || exit 1
source /etc/profile.d/zz-proxy.sh
SUBSET=.cache/dittobench-api-subset-v15
.venv/bin/python tools/key_usage.py
for SEED in 2190058953981709433 6007065558233246269 2497187654609273566; do
  for IMAGE in drp23v15 drp23; do
    echo "===== $IMAGE seed $SEED ($(wc -l < practice/gates/ab_v8/cases_$SEED.txt) cases) $(date -u +%H:%M)"
    timeout 3600 python3 tools/practice_docker.py --image ditto-harness:$IMAGE --run-size full --seed "$SEED" --bench-version 15 \
      --concurrency 8 --trace --timeout 3400 --only-cases "practice/gates/ab_v8/cases_$SEED.txt" --scorer-bin "$PWD/$SUBSET" 2>&1 \
      | grep -E "saved|stopped early|Error|Traceback|tool_mean|composite" | tail -6
    .venv/bin/python tools/key_usage.py
  done
done
echo "===== A/B done $(date -u +%H:%M)"
