#!/bin/bash
# DrPresident v22 routing under the real local scorer with its mock model (HARNESS_MOCK_MODEL=1: every model call
# returns "Mock reply. ANSWER: mock") and embeddings off, so no model or embedding call is paid for. The harness
# log and trace give each case's lane, reason and path; scores are meaningless.
#
#   BENCH=14|15 SEEDS="s1 s2" bash practice/gates/run_drp22_mock.sh
#   SRC=drp22v15 TAG=drp22v15 BENCH=15 SEEDS="..." bash practice/gates/run_drp22_mock.sh    (the lab copy)
cd /home/bittensor/ditto || exit 1
SRC=${SRC:-released/DrPresident-v22_eeb26552/src}
TAG=${TAG:-drp22}
if [ -n "$REBUILD" ] || ! docker image inspect "ditto-harness:$TAG" > /dev/null 2>&1; then
  rm -rf "/tmp/ab_build/$TAG"
  python3 tools/add_trace_dan0l.py "$SRC" "/tmp/ab_build/$TAG" > /dev/null || exit 1
  bash tools/build_harness.sh "ditto-harness:$TAG" "/tmp/ab_build/$TAG" | tail -1
fi
for S in ${SEEDS:?seed list}; do
  echo "===== $TAG mock bench ${BENCH:?bench} seed $S $(date -u +%H:%M)"
  timeout 3600 python3 tools/practice_docker.py --image "ditto-harness:$TAG" --run-size full --seed "$S" --bench-version "$BENCH" \
    --concurrency 8 --trace --timeout 3500 --env HARNESS_MOCK_MODEL=1 --env HARNESS_EMBEDDINGS=0 ${SCORER:+--scorer-bin "$SCORER"} 2>&1 \
    | grep -E "saved|stopped early|Error|bench v|Traceback" | tail -3
done
echo "===== all done $(date -u +%H:%M)"
