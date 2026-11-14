#!/bin/bash
# Watch a local practice run in the background: every time another block of N cases is graded, append the
# progress table (accuracy and token cost per block) to OUT. Stops when the scorer is gone (run finished).
#
#   bash tools/watch_progress.sh RUN_DIR [OUT] [N]
cd /home/bittensor/ditto || exit 1
RUN=${1:?run dir}
OUT=${2:-$RUN/progress.txt}
N=${3:-10}
last=-1
while true; do
  table=$(.venv/bin/python tools/run_progress.py "$RUN" --block "$N" 2>/dev/null)
  if [ $? -ne 0 ]; then
    echo "$(date -u +%H:%M) run finished (scorer gone)" >> "$OUT"
    break
  fi
  done_n=$(echo "$table" | sed -n 's/^graded \([0-9]*\).*/\1/p')
  block=$(( ${done_n:-0} / N ))
  if [ "$block" -gt "$last" ]; then
    { echo "=== $(date -u +%H:%M) graded ${done_n}"; echo "$table" | tail -n +3; } >> "$OUT"
    last=$block
  fi
  sleep 30
done
