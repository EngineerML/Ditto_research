#!/bin/bash
# s46: v8.1 (routing fix) on the one group that v8 split on seed 5451784605348316629 at s45, the news
# subscription question (3 rewordings and the counterfactual). One round, platform providers, concurrency 8.
cd /home/bittensor/ditto || exit 1
rev=$(git -c safe.directory='*' rev-parse --short HEAD)
rm -rf /tmp/variants/v8.1 && mkdir -p /tmp/variants/v8.1
git -c safe.directory='*' archive "$rev" v8 | tar -x -C /tmp/variants/v8.1 --strip-components=1 || exit 1
echo "===== s46 start $(date -u +%Y%m%dT%H%M%SZ), v8.1 from $rev"
BENCH=14 SEED=5451784605348316629 PREFS=platform REPEATS=1 CONCURRENCY=8 bash practice/ab_subset.sh practice/gates/s46/cases_5451784605348316629.txt practice/rerun/none.writes.jsonl "v81=v8.1=/tmp/variants/v8.1"
echo "===== all done $(date -u +%H:%M)"
