#!/bin/bash
# Build the official scorer (dittobench-api, unpatched) from one upstream commit into its own binary, so a new bench
# version can be practised without replacing .cache/dittobench-api. The upstream clone is only read (git archive).
#
#   bash tools/build_scorer_rev.sh REV OUT        e.g. bash tools/build_scorer_rev.sh HEAD .cache/dittobench-api-v15
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
REV=${1:?upstream revision}; OUT=${2:?output binary}
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
sha=$(git -C repos/ditto-subnet rev-parse "$REV") || exit 1
git -C repos/ditto-subnet archive "$sha" services/dittobench-api research/dittobench-datagen | tar -x -C "$WORK" || exit 1
(cd "$WORK/services/dittobench-api" && go build -o "/home/bittensor/ditto/$OUT" ./cmd/dittobench-api) || exit 1
echo "built $OUT from ${sha:0:12}"
