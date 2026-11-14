#!/bin/bash
# Full local v18 datagen run (175 cases) of a c228 image on one seed, with the per-10-case progress watcher.
# The progress table goes to <run>/progress.txt while it runs.
#
#   bash practice/c228_full_watch.sh IMG SEED
cd /home/bittensor/ditto || exit 1
IMG=${1:?image tag}
SEED=${2:?seed}
bash practice/c228_full1.sh "$IMG" "$SEED" > "/tmp/c228_full_$SEED.log" 2>&1 &
runner=$!
run=""
for _ in $(seq 1 60); do
  sleep 5
  run=$(ls -td practice/2026*_ditto-harness-${IMG}_full 2>/dev/null | head -1)
  [ -n "$run" ] && [ -f "$run/scorer.log" ] && break
done
[ -n "$run" ] && bash tools/watch_progress.sh "$run" "$run/progress.txt" 10 &
wait $runner
sleep 40
grep -E "^start|^done" "/tmp/c228_full_$SEED.log"
echo "run $run"
[ -n "$run" ] && tail -22 "$run/progress.txt"
