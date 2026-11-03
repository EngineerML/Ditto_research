#!/bin/bash
# Mock bench (free): the harness image under the real bench-15 scorer with the mock model and embeddings off, on N
# corpus seeds, so every case's lane, reason, path and hint events are recorded. Runs stay in practice/ (traces kept).
#
#   TAG=drp23v15b N=40 bash v15_atlas/run_mock_bench.sh
cd /home/bittensor/ditto || exit 1
source /etc/profile.d/zz-proxy.sh
TAG=${TAG:-drp23v15b}
N=${N:-40}
OUT=v15_atlas/mock_runs_$TAG.txt
: > "$OUT"
for S in $(sed -n "4,$((N + 3))p" v15_atlas/corpus_seeds.txt); do
  echo "===== $TAG mock seed $S $(date -u +%H:%M)"
  line=$(timeout 3000 python3 tools/practice_docker.py --image "ditto-harness:$TAG" --run-size full --seed "$S" --bench-version 15 \
    --concurrency 8 --trace --timeout 2900 --env HARNESS_MOCK_MODEL=1 --env HARNESS_EMBEDDINGS=0 --scorer-bin "$PWD/.cache/dittobench-api-v15" 2>&1 | grep -E "^saved" | tail -1)
  echo "$S ${line#saved }" | tee -a "$OUT"
done
echo "===== mock bench done $(date -u +%H:%M)"
