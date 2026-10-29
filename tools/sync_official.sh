#!/bin/bash
# Keep the official clones under repos/ current: fetch each through the proxy and fast-forward it.
# Run by cron every 3 hours; safe to run by hand.
#
#   bash tools/sync_official.sh
#
# Never forces, resets or discards anything: a repo that cannot fast-forward is only fetched and
# reported. While a practice run or a local screening review is running, it fetches but defers the
# merge, so code under a running job does not move. Each run appends to .cache/repo_sync/sync.log and
# rewrites .cache/repo_sync/latest.md (the new commits by area, and whether the scorer must be rebuilt).
source /etc/profile.d/zz-proxy.sh
ROOT=/home/bittensor/ditto
OUT=$ROOT/.cache/repo_sync
mkdir -p "$OUT"
exec 9>"$OUT/lock"
flock -n 9 || { echo "$(date -u +%FT%TZ) another sync is running" >> "$OUT/sync.log"; exit 0; }

G="git -c safe.directory=*"
NOW=$(date -u +%FT%TZ)
BUSY=$(pgrep -fa "dittobench-api|practice_docker.py|l1_review_local.py|l2l3_review_local.py" | grep -v pgrep | head -1)
REPORT=$OUT/latest.md
{
  echo "# Official repo sync $NOW"
  [ -n "$BUSY" ] && echo "A practice run or review is running, merges deferred: ${BUSY:0:120}"
} > "$REPORT"

# path areas worth a look in ditto-subnet, in report order
AREAS=(
  "scorer and generator|services/dittobench-api research/dittobench-datagen"
  "screener and screening protocol|workers/screener packages/ditto-screening-protocol"
  "operator precedents and review rules|.agents/skills/backroom-review"
  "miner kit and CLI|miners packages/ditto-cli"
  "platform scoring and crown|apps/platform/ditto/api_server/koth.py apps/platform/ditto/api_server/scoring_gate.py apps/platform/ditto/db/queries/scores.py"
)

for dir in "$ROOT"/repos/*/; do
  repo=$(basename "$dir")
  [ -d "$dir/.git" ] || continue
  branch=$($G -C "$dir" rev-parse --abbrev-ref HEAD)
  if ! timeout 600 $G -C "$dir" fetch -q --prune origin 2>>"$OUT/sync.log"; then
    echo "$NOW $repo fetch failed" >> "$OUT/sync.log"
    echo -e "\n## $repo\nfetch failed (see sync.log)" >> "$REPORT"
    continue
  fi
  old=$($G -C "$dir" rev-parse HEAD)
  new=$($G -C "$dir" rev-parse "origin/$branch")
  if [ "$old" = "$new" ]; then
    echo "$NOW $repo up to date at ${old:0:8}" >> "$OUT/sync.log"
    continue
  fi
  count=$($G -C "$dir" rev-list --count "$old..$new")
  {
    echo -e "\n## $repo: $count new commit(s) ${old:0:8}..${new:0:8}"
    $G -C "$dir" log --format="- %h %ci %s" "$old..$new" | grep -v "chore(release)"
    if [ "$repo" = ditto-subnet ]; then
      for area in "${AREAS[@]}"; do
        name=${area%%|*}
        paths=${area#*|}
        # shellcheck disable=SC2086
        files=$($G -C "$dir" diff --name-only "$old" "$new" -- $paths | grep -vE "_test\.go$|/tests?/|testdata/" )
        [ -n "$files" ] && { echo -e "\n### $name"; echo "$files" | sed 's/^/- /' | head -40; }
      done
      # shellcheck disable=SC2086
      if $G -C "$dir" diff --name-only "$old" "$new" -- services/dittobench-api research/dittobench-datagen | grep -vE "_test\.go$|testdata/|version/version\.go$|\.md$" | grep -q .; then
        echo -e "\n**Scorer or generator code changed: rebuild .cache/dittobench-api (and the subset scorer) before the next practice run.**"
      fi
    fi
  } >> "$REPORT"
  if [ -n "$BUSY" ]; then
    echo "$NOW $repo $count new, merge deferred (busy)" >> "$OUT/sync.log"
  elif timeout 900 $G -C "$dir" merge -q --ff-only "origin/$branch" >>"$OUT/sync.log" 2>&1; then
    echo "$NOW $repo fast-forwarded ${old:0:8} -> ${new:0:8} ($count)" >> "$OUT/sync.log"
    echo "fast-forwarded" >> "$REPORT"
  else
    echo "$NOW $repo $count new, fast-forward FAILED (local changes or divergence; nothing was discarded)" >> "$OUT/sync.log"
    echo "**fast-forward failed; nothing was discarded, needs a look**" >> "$REPORT"
  fi
done
grep -q "^## " "$REPORT" || echo -e "\nNo new commits." >> "$REPORT"
cp "$REPORT" "$OUT/report_$(date -u +%Y%m%dT%H%M).md"
