#!/bin/bash
# Snapshot of the public endpoints needed to find every released agent and generator (data only).
#   bash live/snapshot_releases.sh   -> live/<UTC date>T<HHMM>/
set -u
source /etc/profile.d/zz-proxy.sh 2>/dev/null || true
API=https://platform-api.heyditto.ai/api/v1
OUT=/home/bittensor/ditto/live/$(date -u +%Y-%m-%dT%H%M)
mkdir -p "$OUT"
get() {  # get ENDPOINT FILE
  for i in 1 2 3; do curl -sS -f --max-time 90 "$API/$1" -o "$OUT/$2" && break; sleep 4; done
  printf "%-44s %s bytes\n" "$1" "$(stat -c %s "$OUT/$2" 2>/dev/null || echo FAILED)"
}
get "public/activity?limit=200" public_activity_limit_200.json
get public/leaderboard public_leaderboard.json
get generator/board generator_board.json
get generator/rounds generator_rounds.json
get public/dueling/seasons public_dueling_seasons.json
get public/bench/rollout public_bench_rollout.json
get public/bench/config public_bench_config.json
get public/bench/timeline public_bench_timeline.json
get public/submission-terms public_submission_terms.json
get public/cla public_cla.json
get generator/upload-terms generator_upload_terms.json
echo "$OUT"
