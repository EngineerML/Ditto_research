#!/bin/bash
# The lab copy drp22v15 on a whole seed (tool and memory questions) at bench 15, real model (paid), with the
# official composite from the v15 scorer. Tool questions run too: some of them write to memory before memory
# questions are asked, so a memory-only subset would meet a different store.
#
#   SEED=4140899197327149732 bash practice/gates/run_drp22v15_full.sh
cd /home/bittensor/ditto || exit 1
source /etc/profile.d/zz-proxy.sh
.venv/bin/python tools/key_usage.py
timeout 9000 python3 tools/practice_docker.py --image ditto-harness:drp22v15 --run-size full --seed "${SEED:?seed}" --bench-version 15 \
  --concurrency 8 --trace --timeout 8600 --scorer-bin "$PWD/.cache/dittobench-api-v15" 2>&1 \
  | grep -vE "^\s*$" | tail -40
.venv/bin/python tools/key_usage.py
