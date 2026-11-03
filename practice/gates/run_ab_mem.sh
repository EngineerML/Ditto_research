#!/bin/bash
# A/B (paid, real model) of the grounded-decline and account-figure changes: v8 (ditto-harness:drp23v15) against
# drp23v15b at ba93daf, on every absence question, the record-quantity cf-base/cf-variant questions and the answerable
# near-miss and cross-user twins of seeds 5119 and 2190 (bench 15). Every memory wave is still seeded where it falls.
cd /home/bittensor/ditto || exit 1
source /etc/profile.d/zz-proxy.sh
TAG=drp23v15b
rm -rf /tmp/ab_build/$TAG
python3 tools/add_trace_dan0l.py drp23v15b /tmp/ab_build/$TAG > /dev/null || exit 1
bash tools/build_harness.sh ditto-harness:$TAG /tmp/ab_build/$TAG | tail -1
mkdir -p practice/gates/ab_mem
python3 - <<'EOF'
import json
WANT_PREFIX = ("absence-pure-absence", "absence-near-miss", "absence-stale-removed", "absence-false-premise", "absence-cross-user", "absence-insufficient-composition")
WANT = {"record-quantity-cf-base", "record-quantity-cf-variant", "absence-twin-near-miss", "absence-twin-cross-user"}
for seed in (5119792693744740612, 2190058953981709433):
    d = json.load(open(f"/home/bittensor/ditto/.cache/datasets/v15_s{seed}_salt0_full.json"))
    ids = [c["id"] for c in d["memory_cases"] if c["question_type"] in WANT or c["question_type"] in WANT_PREFIX]
    open(f"/home/bittensor/ditto/practice/gates/ab_mem/cases_{seed}.txt", "w").write("\n".join(ids) + "\n")
    print(seed, len(ids), "cases")
EOF
.venv/bin/python tools/key_usage.py
for SEED in 5119792693744740612 2190058953981709433; do
  for IMAGE in drp23v15 $TAG; do
    echo "===== $IMAGE seed $SEED ($(wc -l < practice/gates/ab_mem/cases_$SEED.txt) cases) $(date -u +%H:%M)"
    timeout 3600 python3 tools/practice_docker.py --image ditto-harness:$IMAGE --run-size full --seed "$SEED" --bench-version 15 \
      --concurrency 8 --trace --timeout 3400 --only-cases "practice/gates/ab_mem/cases_$SEED.txt" --scorer-bin "$PWD/.cache/dittobench-api-subset-v15" 2>&1 \
      | grep -E "saved|stopped early|Error|Traceback|memory_mean|composite" | tail -6
    .venv/bin/python tools/key_usage.py
  done
done
echo "===== A/B done $(date -u +%H:%M)"
