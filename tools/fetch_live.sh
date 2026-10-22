#!/bin/bash
# Save a dated snapshot of the public Ditto platform API into live/YYYY-MM-DD/.
set -u
[ -f /etc/profile.d/zz-proxy.sh ] && source /etc/profile.d/zz-proxy.sh
API=https://platform-api.heyditto.ai
HERE=$(cd "$(dirname "$0")/.." && pwd)
OUT=$HERE/live/$(date -u +%Y-%m-%d)
mkdir -p "$OUT"
for ep in public/leaderboard public/bench/config public/submissions upload/eval-pricing public/ledger-epochs; do
  f="$OUT/$(echo "$ep" | tr '/' '_').json"
  for i in 1 2 3; do curl -sS -f --max-time 60 "$API/api/v1/$ep" -o "$f" && break; sleep 4; done
  printf "%-26s %s bytes\n" "$ep" "$(stat -c %s "$f" 2>/dev/null || echo FAILED)"
done
echo "saved to $OUT"
