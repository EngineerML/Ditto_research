#!/bin/bash
# Rerun the Hades full run (seed 4242) once ab_full.sh has finished; the first attempt was cut at 107/350.
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto
until grep -q 'all done' practice/ab_full.log; do sleep 30; done
PY=.venv/bin/python
echo "before: $($PY tools/key_usage.py)"
echo "===== ditto-harness:hades-v6-trace (rerun)"
timeout 12000 python3 tools/practice_docker.py --image ditto-harness:hades-v6-trace --run-size full --seed 4242 --trace 2>&1 | tail -25
echo "after: $($PY tools/key_usage.py)"
echo "===== all done"
