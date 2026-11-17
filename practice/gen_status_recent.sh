#!/bin/bash
# Case status per family for the N most recent generator panel runs (default 6).
#   bash practice/gen_status_recent.sh [N]
cd /home/bittensor/ditto || exit 1
for r in $(ls -td practice/generator/2026*Z | head -${1:-6}); do
    echo "== $r"
    python3 practice/gen_case_status.py "$r" 2>&1 | tail -14
done
