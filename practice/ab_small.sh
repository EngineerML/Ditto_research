#!/bin/bash
# Same small dataset (seed 4242) through unchanged Hades v6 and our dev image, one after the other.
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto
PY=.venv/bin/python
echo "before: $($PY tools/key_usage.py)"
for image in ditto-harness:hades-v6 ditto-harness:dev; do
  echo "===== $image"
  timeout 3000 python3 tools/practice_docker.py --image "$image" --run-size small --seed 4242 2>&1 | tail -25
  echo "after $image: $($PY tools/key_usage.py)"
done
