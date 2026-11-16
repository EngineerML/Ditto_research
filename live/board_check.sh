#!/bin/bash
# Fresh live snapshot, then the board top 15, our rank, pending activity and the current season with its pins.
cd /home/bittensor/ditto || exit 1
d=$(bash live/fetch_now.sh | tail -1)
python3 live/board_now.py $d 2>&1 | head -60
echo "=== ours"
python3 live/rank_ours.py $d
