#!/bin/bash
# s44: a harness's program path (DIR, default v7) on the 40 program questions of seven seeds:
# v6's live run 3 seed, the three holdout seeds and the three king seeds, which all have v6 traces to compare.
# Two rounds, concurrency 8, platform providers. Compare with practice/gates/v14_shapes.py.
cd /home/bittensor/ditto || exit 1
LABEL=${LABEL:-v7p}; TAG=${TAG:-v7-prog}; ROUNDS=${ROUNDS:-2}
rev=$(git -c safe.directory='*' rev-parse --short HEAD)
rm -rf /tmp/variants/$TAG && mkdir -p /tmp/variants/$TAG
git -c safe.directory='*' archive "$rev" ${DIR:-v7} | tar -x -C /tmp/variants/$TAG --strip-components=1 || exit 1
SRC=/tmp/variants/$TAG
echo "===== s44 $LABEL start $(date -u +%Y%m%dT%H%M%SZ), $TAG from $rev, $ROUNDS rounds"
first=1
for round in $(seq 1 "$ROUNDS"); do
  while read -r S; do
    if [ $first = 1 ]; then V="$LABEL=$TAG=$SRC"; first=0; else V="$LABEL=$TAG"; fi
    BENCH=14 SEED=$S PREFS=platform REPEATS=1 CONCURRENCY=8 bash practice/ab_subset.sh practice/gates/s44/cases_$S.txt practice/rerun/none.writes.jsonl "$V"
  done < practice/gates/s44/seeds.txt
done
echo "===== all done $(date -u +%H:%M)"
