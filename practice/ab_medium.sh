#!/bin/bash
# Same medium dataset (seed 4242) through traced Hades v6 and traced dev, one after the other.
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto
PY=.venv/bin/python
echo "before: $($PY tools/key_usage.py)"
for image in ditto-harness:hades-v6-trace ditto-harness:dev-trace; do
  echo "===== $image"
  timeout 7000 python3 tools/practice_docker.py --image "$image" --run-size medium --seed 4242 --trace 2>&1 | tail -25
  echo "after $image: $($PY tools/key_usage.py)"
done
echo "===== all done"
