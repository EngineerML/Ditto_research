#!/bin/bash
# Medium dataset (seed 4242) through traced dev only; compare with the Hades medium run of the same seed.
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto
PY=.venv/bin/python
echo "before: $($PY tools/key_usage.py)"
echo "===== ditto-harness:dev-trace"
timeout 7000 python3 tools/practice_docker.py --image ditto-harness:dev-trace --run-size medium --seed 4242 --trace 2>&1 | tail -25
echo "after: $($PY tools/key_usage.py)"
echo "===== all done"
