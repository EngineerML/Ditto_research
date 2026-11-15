#!/bin/bash
cd /home/bittensor/ditto/live || exit 1
S=2026-11-15T0705
G=${1:-f5659f80}
for f in ours5 ours4 crown240 beast16; do
  echo "== $f"
  python3 slice_col.py "$S/scores_$f.json" "$G" "$S"
done
