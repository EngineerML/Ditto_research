#!/bin/bash
# drp23v15b (v8 + capitalised product names, dan0l's live handling, empty required argument unfilled) under the real
# bench-15 scorer with the mock model (free), on the three seeds the drp23v15 mocks used, for a lane and hint diff.
cd /home/bittensor/ditto || exit 1
source /etc/profile.d/zz-proxy.sh
SRC=drp23v15b TAG=drp23v15b BENCH=15 SCORER="$PWD/.cache/dittobench-api-v15" \
  SEEDS="4140899197327149732 5451784605348316629 8047062976504477843" bash practice/gates/run_drp22_mock.sh
