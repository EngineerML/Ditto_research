#!/bin/bash
# Static bench of v8 (drp23v15) and drp23v15b over the 200 corpus seeds' served text, then the per-family summaries.
cd /home/bittensor/ditto || exit 1
sed -i 's/\r$//' v15_atlas/static_bench.py v15_atlas/static_summary.py
for tree in drp23v15 drp23v15b; do
  .venv/bin/python v15_atlas/static_bench.py $tree .cache/atlas/static_$tree.jsonl &
done
wait
find drp23v15 drp23v15b -name __pycache__ -prune -exec rm -rf {} +
for tree in drp23v15 drp23v15b; do
  wc -l .cache/atlas/static_$tree.jsonl
  python3 v15_atlas/static_summary.py .cache/atlas/static_$tree.jsonl v15_atlas/static_$tree | tail -2
done
