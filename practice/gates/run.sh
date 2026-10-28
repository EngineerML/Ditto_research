#!/bin/bash
# Gate questions (the 39 program twin rewordings and the 9 conversational-sanity questions) on four v14
# seeds, current build (combined-v7a = HEAD for these questions), each run twice to separate noise from
# design. Every trajectory is kept in its practice/ run folder.
cd /home/bittensor/ditto || exit 1
SEEDS="138287359920490853 6233584598314311777 7437279559784817346 553456649953547434"
for S in $SEEDS; do
  python3 -c "assert $S < 2**63" || exit 1
  DITTO_BENCH=14 .venv/bin/python - <<EOF || exit 1
import json, sys
sys.path.insert(0, ".")
from lab import data
d = json.load(open(data.dataset_path($S, 0, "full")))
conv = {"conversational-chitchat", "conversational-declarative", "declarative-behavior"}
ids = [c["id"] for c in d["memory_cases"] if c.get("twin_group") or c["question_type"] in conv]
open("practice/gates/cases_$S.txt", "w").write("\n".join(ids) + "\n")
print("seed $S questions", len(ids))
EOF
done
for S in $SEEDS; do
  BENCH=14 SEED=$S PREFS=platform REPEATS=2 bash practice/ab_subset.sh practice/gates/cases_$S.txt practice/rerun/none.writes.jsonl v7a=combined-v7a
done
echo "===== all done"
