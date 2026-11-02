#!/bin/bash
# Every 20 review steps of the local L1 on v8.1 (and its end): step, time, and credit spent so far.
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
LOG=practice/gates/l1_v8.1pack.log
START=12.6964
last=""
while true; do
  step=$(grep -oE "review step [0-9]+" "$LOG" | tail -1 | grep -oE "[0-9]+$")
  if [ -n "$step" ] && [ $((step % 20)) -eq 0 ] && [ "$step" != "$last" ]; then
    last=$step
    used=$(.venv/bin/python tools/key_usage.py 2>/dev/null | grep -oE 'usage \$[0-9.]+' | grep -oE '[0-9.]+')
    echo "$(date -u +%H:%M) review step $step/200 | spent so far \$$(python3 -c "print(f'{${used:-$START} - $START:.2f}')")"
  fi
  if grep -qE "full observation in|Traceback|rejected|Error" "$LOG"; then
    echo "L1 finished: $(grep -vE 'review step' "$LOG" | tail -10 | tr '\n' ' ' | cut -c1-500)"
    exit 0
  fi
  if ! pgrep -f "l1_review_local.py practice/submission_v8.1.tgz" > /dev/null; then
    echo "L1 process is gone without a result: $(tail -3 "$LOG" | tr '\n' ' ')"
    exit 1
  fi
  sleep 30
done
