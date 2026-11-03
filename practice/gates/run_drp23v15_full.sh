#!/bin/bash
# The lab copy drp23v15 (DrPresident v23 + unlinked tools left out) on a whole seed at bench 15, real model
# (paid), with the official composite from the v15 scorer. Same run as run_drp22v15_full.sh on the v23 image.
#
#   SEED=... bash practice/gates/run_drp23v15_full.sh
cd /home/bittensor/ditto || exit 1
source /etc/profile.d/zz-proxy.sh
.venv/bin/python tools/key_usage.py
timeout 9000 python3 tools/practice_docker.py --image ditto-harness:drp23v15 --run-size full --seed "${SEED:?seed}" --bench-version 15 \
  --concurrency 8 --trace --timeout 8600 --scorer-bin "$PWD/.cache/dittobench-api-v15" 2>&1 \
  | grep -vE "^\s*$" | tail -40
.venv/bin/python tools/key_usage.py
