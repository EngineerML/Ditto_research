#!/bin/bash
# Rebuild our images from the committed harness, then full runs of traced Hades v6 and traced dev on two seeds.
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto
PY=.venv/bin/python
echo "commit: $(git rev-parse --short HEAD)"
$PY tools/key_usage.py --need 6 || { echo "account balance too low for four full runs"; exit 1; }
bash tools/build_harness.sh ditto-harness:dev harness || exit 1
TRACED=$(mktemp -d)
python3 tools/add_trace.py harness "$TRACED/src" && bash tools/build_harness.sh ditto-harness:dev-trace "$TRACED/src" || exit 1
rm -rf "$TRACED"
echo "before: $($PY tools/key_usage.py)"
for seed in 4242 777; do
  for image in ditto-harness:hades-v6-trace ditto-harness:dev-trace; do
    echo "===== $image seed $seed $(date -u +%H:%M)"
    timeout 12000 python3 tools/practice_docker.py --image "$image" --run-size full --seed "$seed" --trace 2>&1 | tail -25
    echo "after $image seed $seed: $($PY tools/key_usage.py)"
  done
done
echo "===== all done $(date -u +%H:%M)"
