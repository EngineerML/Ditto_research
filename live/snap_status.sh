#!/bin/bash
# Fetch a live snapshot and print board, releases and our agent's activity.
cd /home/bittensor/ditto || exit 1
d=$(bash live/fetch_now.sh | tail -1)
echo "snapshot $d"
python3 live/board_now.py "$d" 2>&1 | head -22
echo "==== releases"
python3 live/release_now.py "$d" 2>&1 | head -40
echo "==== ours"
source /etc/profile.d/zz-proxy.sh
python3 live/ours_now.py 2>&1 | head -150
