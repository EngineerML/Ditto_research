#!/bin/bash
# Watch a local practice run in the background: every time another block of N cases is graded, append the
# progress table (accuracy and token cost per block) to OUT. Stops once the run has written report.json, or after
# the scorer has not answered for 20 checks in a row (about 10 minutes).
#
#   bash tools/watch_progress.sh RUN_DIR [OUT] [N]
cd /home/bittensor/ditto || exit 1
RUN=${1:?run dir}
OUT=${2:-$RUN/progress.txt}
N=${3:-10}
last=-1
misses=0
while [ ! -f "$RUN/report.json" ]; do
  table=$(.venv/bin/python tools/run_progress.py "$RUN" --block "$N" 2>/dev/null)
  if [ $? -ne 0 ]; then
    misses=$((misses + 1))
    [ "$misses" -ge 20 ] && { echo "$(date -u +%H:%M) scorer silent for 20 checks, watcher stops" >> "$OUT"; break; }
    sleep 30
    continue
  fi
  misses=0
  done_n=$(echo "$table" | sed -n 's/^graded \([0-9]*\).*/\1/p')
  block=$(( ${done_n:-0} / N ))
  if [ "$block" -gt "$last" ]; then
    { echo "=== $(date -u +%H:%M) graded ${done_n}"; echo "$table" | tail -n +3; } >> "$OUT"
    last=$block
  fi
  sleep 30
done
echo "$(date -u +%H:%M) run finished" >> "$OUT"
