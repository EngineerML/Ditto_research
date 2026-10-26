#!/bin/bash
# Second re-run round: the questions whose first re-run again hit a provider problem and lost the point.
# Merged on top of the first round's merged runs, same conditions as practice/rerun_flagged.sh.
#
#   bash practice/rerun_round2.sh
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
SEED=3590624429364033488
PREFS='{"order":["deepinfra","parasail","akashml"],"allow_fallbacks":false,"data_collection":"deny"}'
PY=.venv/bin/python
WORK=practice/rerun
printf '%s\n' ccdb65058501f1052 > $WORK/dan0l.round2.txt
printf '%s\n' c4a8233eda611281e c67e9b6e40c203eb8 > $WORK/combined.round2.txt
for spec in "dan0l=dan0l-v24-replay=practice/20261026T021053Z_ditto-harness-dan0l-v24-trace_full_merged" \
            "combined=combined-replay=practice/20261026T040314Z_ditto-harness-combined-trace_full_merged"; do
  name=${spec%%=*}; rest=${spec#*=}; tag=${rest%%=*}; merged=${rest#*=}
  $PY tools/key_usage.py --need 1 || { echo "balance under \$1, not starting $name"; exit 1; }
  echo "===== $name round 2: $(tr '\n' ' ' < $WORK/$name.round2.txt) $(date -u +%H:%M)"
  timeout 11000 python3 tools/practice_docker.py --image "ditto-harness:$tag" --run-size full --seed "$SEED" --trace --timeout 10800 \
    --env "HARNESS_PROVIDER_PREFS=$PREFS" --only-cases "$WORK/$name.round2.txt" --replay-writes "$WORK/$name.writes.jsonl" 2>&1 | tail -2
  rerun=$(ls -td practice/*_ditto-harness-${tag}_full_rerun | head -1)
  grep -c "replayed .*: applied" "$rerun/harness.log"
  $PY tools/merge_rerun.py "$merged" "$rerun" "${merged}2" | sed -n '/| case |/,$p'
done
echo "===== done $(date -u +%H:%M) $($PY tools/key_usage.py)"
