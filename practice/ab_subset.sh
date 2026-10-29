#!/bin/bash
# Run harness images on one fixed list of questions, repeated, under the re-run conditions
# (subset scorer, every wave seeded, the full run's tool-phase memory writes replayed, same seed,
# provider list and case concurrency). Each run folder name goes to practice/topic_fix/runs.txt
# as "LABEL RUN_DIR", for tools/ab_compare.py.
#
#   bash practice/ab_subset.sh CASES.txt WRITES.jsonl LABEL=TAG[=SRC] [LABEL=TAG[=SRC] ...]
#
# A SRC folder is patched with the trace hooks and built as ditto-harness:TAG first; without
# SRC the image must already exist. REPEATS (default 1) runs every image that many times.
# PREFS (OpenRouter provider preferences, JSON) defaults to the cheap pinned list; PREFS=platform
# uses the platform relay's own default (fastest provider by throughput), as validators score.
# BENCH (default 13) is the bench version the scorer generates and grades.
# CONCURRENCY (default 2) is the scorer's case concurrency; validators run 4 unless operators set more.
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
CASES=${1:?case list}; WRITES=${2:?replay writes}; shift 2
REPEATS=${REPEATS:-1}
SEED=${SEED:-3590624429364033488}
PINNED='{"order":["deepinfra","parasail","akashml"],"allow_fallbacks":false,"data_collection":"deny"}'
PLATFORM='{"sort":"throughput","ignore":["coreweave"],"allow_fallbacks":true,"data_collection":"deny","zdr":true}'
case "${PREFS:-pinned}" in
  pinned) PREFS=$PINNED; PREFS_NAME=pinned ;;
  platform) PREFS=$PLATFORM; PREFS_NAME=platform ;;
  *) PREFS_NAME=custom ;;
esac
PY=.venv/bin/python
LOG=practice/topic_fix/runs.txt
mkdir -p practice/topic_fix
for spec in "$@"; do
  IFS='=' read -r label tag src <<< "$spec"
  if [ -n "$src" ]; then
    python3 tools/add_trace_dan0l.py "$src" "/tmp/ab_build/$tag" > /dev/null || exit 1
    bash tools/build_harness.sh "ditto-harness:$tag" "/tmp/ab_build/$tag" | tail -1
  fi
done
for round in $(seq 1 "$REPEATS"); do
  for spec in "$@"; do
    IFS='=' read -r label tag src <<< "$spec"
    $PY tools/key_usage.py --need 1 || { echo "balance under \$1, stopping"; exit 1; }
    echo "===== $label ($tag) round $round, $(wc -l < "$CASES") questions, providers $PREFS_NAME, concurrency ${CONCURRENCY:-2} $(date -u +%H:%M) $($PY tools/key_usage.py)"
    timeout 11000 python3 tools/practice_docker.py --image "ditto-harness:$tag" --run-size full --seed "$SEED" --bench-version "${BENCH:-13}" --concurrency "${CONCURRENCY:-2}" --trace --timeout 10800 \
      --env "HARNESS_PROVIDER_PREFS=$PREFS" --only-cases "$CASES" --replay-writes "$WRITES" 2>&1 | grep -E "saved|stopped early|Error" | tail -2
    run=$(ls -td practice/*_ditto-harness-${tag}_full_rerun | head -1)
    echo "$PREFS" > "$run/provider_prefs.json"
    echo "$label $PREFS_NAME $run" >> "$LOG"
    echo "served by: $(grep -oE 'llm provider=[A-Za-z0-9 ._-]+ model' "$run/harness.log" | sed 's/llm provider=//; s/ model//' | sort | uniq -c | sort -rn | tr '\n' ' ')"
    echo "replayed: $(grep -c 'replayed .*: applied' "$run/harness.log") applied"
  done
done
echo "===== done $(date -u +%H:%M) $($PY tools/key_usage.py)"
