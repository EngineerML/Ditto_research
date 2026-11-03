#!/bin/bash
# Prints the L1 review's progress every 20 steps, then its verdict lines; exits when the review ends.
LOG=/home/bittensor/ditto/practice/gates/l1_drp23v15_base.log
last=0
start=$(date +%s)
while true; do
  step=$(grep -oE 'review step [0-9]+' "$LOG" 2>/dev/null | tail -1 | grep -oE '[0-9]+$')
  step=${step:-0}
  if [ "$step" -ge $((last + 20)) ]; then
    last=$((step / 20 * 20))
    echo "step $step/200 after $(( ($(date +%s) - start) / 60 )) min"
  fi
  if grep -qE 'full observation in|Traceback|Error' "$LOG" 2>/dev/null; then
    echo "review ended at step $step:"
    grep -E '"risk_level"|"clearance_certified"|"categories"|notes:|Traceback|Error' "$LOG" | head -8
    exit 0
  fi
  if ! pgrep -f 'l1_review_local.py practice/submission_drp23v15' >/dev/null; then
    echo "review process gone at step $step; last log lines:"; tail -5 "$LOG" | cut -c1-300
    exit 0
  fi
  sleep 15
done
