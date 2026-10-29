#!/bin/bash
# Full traced practice run of the current combined design on dan0l v24's scored seed, with the
# platform relay's own provider preferences (fastest by throughput, as validators score).
#
#   SEED=... BENCH=14 [SRC=v5] [CONCURRENCY=8] bash practice/full_current.sh [TAG] [min balance $]
#   (default seed: dan0l v24's scored seed, bench 13; SRC defaults to combined, CONCURRENCY to 2;
#   validators run case concurrency 8)
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
TAG=${1:-combined-current}
NEED=${2:-2}
SEED=${SEED:-3590624429364033488}
SRC=${SRC:-combined}
PREFS='{"sort":"throughput","ignore":["coreweave"],"allow_fallbacks":true,"data_collection":"deny","zdr":true}'
PY=.venv/bin/python
echo "===== build ditto-harness:$TAG from $SRC at $(git rev-parse --short HEAD)"
python3 tools/add_trace_dan0l.py "$SRC" "/tmp/full_build/$TAG" > /dev/null || exit 1
bash tools/build_harness.sh "ditto-harness:$TAG" "/tmp/full_build/$TAG" | tail -1
$PY tools/key_usage.py --need "$NEED" || { echo "balance under \$$NEED, not starting"; exit 1; }
echo "===== ditto-harness:$TAG full seed $SEED bench ${BENCH:-13} providers platform concurrency ${CONCURRENCY:-2} $(date -u +%H:%M) $($PY tools/key_usage.py)"
timeout 15000 python3 tools/practice_docker.py --image "ditto-harness:$TAG" --run-size full --seed "$SEED" --bench-version "${BENCH:-13}" --concurrency "${CONCURRENCY:-2}" --trace --timeout 14400 \
  --env "HARNESS_PROVIDER_PREFS=$PREFS" 2>&1 | tail -20
run=$(ls -td practice/*_ditto-harness-${TAG}_full | head -1)
echo "$PREFS" > "$run/provider_prefs.json"
echo "served by: $(grep -oE 'llm provider=[A-Za-z0-9 ._-]+ model' "$run/harness.log" | sed 's/llm provider=//; s/ model//' | sort | uniq -c | sort -rn | tr '\n' ' ')"
echo "after: $($PY tools/key_usage.py)"
echo "===== done $(date -u +%H:%M)"
