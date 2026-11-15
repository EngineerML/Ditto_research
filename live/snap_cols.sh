#!/bin/bash
cd /home/bittensor/ditto || exit 1
source /etc/profile.d/zz-proxy.sh
d=live/2026-11-15T0705
python3 live/fetch_scores.py $d ours5=52d15b97 ours4=d096ac21 crown240=b9e7dd0f crown228=673386d0 beast16=9c2f44cc beast12=08041a9e 2>&1 | tail -20
echo "==== pins"
python3 live/pins_now.py $d 2>&1 | head -40
echo "==== season columns"
python3 live/season_cols.py $d 2>&1 | head -120
