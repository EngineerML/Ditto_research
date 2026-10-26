#!/bin/bash
# Re-run the questions of the dan0l-vs-combined full runs that a provider problem may have spoiled
# (failed or cut model calls, time budget eaten by slow calls, no answer), then merge each re-run
# back into its full run. Same seed, provider list and case concurrency as practice/dan0l_vs_combined.sh;
# every seed wave is loaded as before, and the agent's own tool-phase memory writes are put back.
#
#   bash practice/rerun_flagged.sh DAN0L_FULL_RUN COMBINED_FULL_RUN [min balance $]
#
# Images are the trace images plus the replay hook (tools/add_trace_dan0l.py), built here.
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
DAN0L_RUN=${1:?dan0l full run dir}
COMBINED_RUN=${2:?combined full run dir}
NEED=${3:-1}
SEED=3590624429364033488
PREFS='{"order":["deepinfra","parasail","akashml"],"allow_fallbacks":false,"data_collection":"deny"}'
PY=.venv/bin/python
WORK=practice/rerun
mkdir -p "$WORK"

[ -x .cache/dittobench-api-subset ] && [ -x .cache/ditto-rescore ] || python3 tools/build_subset_scorer.py || exit 1
build() {  # build TAG SRC
  python3 tools/add_trace_dan0l.py "$2" "/tmp/replay_build/$1" > /dev/null || exit 1
  bash tools/build_harness.sh "ditto-harness:$1" "/tmp/replay_build/$1" | tail -2
}
build dan0l-v24-replay released/dan0l-v24_ecf5a1a2/src
build combined-replay combined

for spec in "dan0l=dan0l-v24-replay=$DAN0L_RUN" "combined=combined-replay=$COMBINED_RUN"; do
  name=${spec%%=*}; rest=${spec#*=}; image=ditto-harness:${rest%%=*}; full=${rest#*=}; full=${full%/}
  $PY tools/flag_failed_calls.py "$full" --ids "$WORK/$name.flagged.txt" | tail -1
  $PY tools/replay_writes.py "$full" "$WORK/$name.writes.jsonl" --skip "$WORK/$name.flagged.txt" || exit 1
  [ -s "$WORK/$name.flagged.txt" ] || { echo "$name: nothing to re-run"; continue; }
  $PY tools/key_usage.py --need "$NEED" || { echo "balance under \$$NEED, not starting $name"; exit 1; }
  echo "===== $name re-run of $(wc -l < "$WORK/$name.flagged.txt") questions $(date -u +%H:%M) $($PY tools/key_usage.py)"
  timeout 7200 python3 tools/practice_docker.py --image "$image" --run-size full --seed "$SEED" --trace \
    --env "HARNESS_PROVIDER_PREFS=$PREFS" --only-cases "$WORK/$name.flagged.txt" --replay-writes "$WORK/$name.writes.jsonl" 2>&1 | tail -6
  rerun=$(ls -td practice/*_ditto-harness-${rest%%=*}_full_rerun | head -1)
  grep -E "replayed" "$rerun/harness.log" | sed -E 's/^[0-9-]+ [0-9:,]+ //'
  $PY tools/merge_rerun.py "$full" "$rerun" "practice/${full##*/}_merged" || exit 1
  echo "after $name: $($PY tools/key_usage.py)"
done
echo "===== done $(date -u +%H:%M)"
