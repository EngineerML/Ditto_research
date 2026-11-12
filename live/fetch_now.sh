#!/bin/bash
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto
d=live/$(date -u +%Y-%m-%dT%H%M)
mkdir -p $d
B=https://platform-api.heyditto.ai/api/v1
for p in public/leaderboard "public/activity?limit=200" public/bench/rollout generator/board public/dueling/seasons; do
  f=$(echo "$p" | tr '/?=' '___')
  curl -s --max-time 30 "$B/$p" -o $d/$f.json
  echo "$p $(wc -c < $d/$f.json)"
done
echo $d
