#!/bin/bash
# s45: v8 on all 250 memory questions of three fresh v14 seeds (no tool questions; v8 changes only the program
# path, so tool prompts are v6's). The v8 image built by s44 (bcd3312), concurrency 8, platform providers, one round.
cd /home/bittensor/ditto || exit 1
mkdir -p practice/gates/s45
if [ ! -s practice/gates/s45/seeds.txt ]; then
  python3 - > practice/gates/s45/seeds.txt <<'PY'
import glob, random, re
used = {int(re.search(r"_s(\d+)_", p).group(1)) for p in glob.glob(".cache/datasets/*_s*_salt0_full.json")}
rng = random.SystemRandom()
seeds = []
while len(seeds) < 3:
    s = rng.randrange(1, 2**63)
    if s not in used:
        seeds.append(s)
print("\n".join(map(str, seeds)))
PY
fi
while read -r S; do
  DITTO_BENCH=14 .venv/bin/python -c "import sys; sys.path.insert(0, '.'); from lab.data import dataset_path; print(dataset_path($S))" || exit 1
  python3 - "$S" > practice/gates/s45/cases_$S.txt <<'PY'
import json, sys
for c in json.load(open(f".cache/datasets/v14_s{sys.argv[1]}_salt0_full.json"))["memory_cases"]:
    print(c["id"])
PY
  echo "===== s45 seed $S, $(wc -l < practice/gates/s45/cases_$S.txt) memory questions, start $(date -u +%H:%M)"
  BENCH=14 SEED=$S PREFS=platform REPEATS=1 CONCURRENCY=8 bash practice/ab_subset.sh practice/gates/s45/cases_$S.txt practice/rerun/none.writes.jsonl "v8m=v8"
done < practice/gates/s45/seeds.txt
echo "===== all done $(date -u +%H:%M)"
