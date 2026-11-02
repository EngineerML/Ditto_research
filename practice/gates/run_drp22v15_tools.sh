#!/bin/bash
# The lab copy drp22v15 (DrPresident v22 with unlinked tools left out) on the tool questions only of one seed, at
# bench 15, with the real model (paid). The case list is the seed's tool cases from the free mock run of the same
# image and seed; every memory wave is still seeded where it falls, so tool cases meet the same store.
#
#   SEED=4140899197327149732 MOCK_RUN=practice/20261102T094752Z_ditto-harness-drp22v15_full bash practice/gates/run_drp22v15_tools.sh
cd /home/bittensor/ditto || exit 1
source /etc/profile.d/zz-proxy.sh
SUBSET=.cache/dittobench-api-subset-v15
if [ ! -x "$SUBSET" ]; then
  python3 tools/build_subset_scorer.py aeeccbb6 "$SUBSET" || exit 1
fi
CASES=practice/gates/drp22v15/tool_cases_${SEED:?seed}.txt
mkdir -p practice/gates/drp22v15
python3 -c "import json,sys; r=json.load(open(sys.argv[1]+'/report.json')); print('\n'.join(p['case_id'] for p in r['partial'] if p['kind']=='tool'))" "${MOCK_RUN:?mock run}" > "$CASES"
echo "tool cases: $(wc -l < "$CASES")"
.venv/bin/python tools/key_usage.py
timeout 5400 python3 tools/practice_docker.py --image ditto-harness:drp22v15 --run-size full --seed "$SEED" --bench-version 15 \
  --concurrency 8 --trace --timeout 5000 --only-cases "$CASES" --scorer-bin "$PWD/$SUBSET" 2>&1 \
  | grep -E "saved|stopped early|Error|bench v|Traceback|score|composite" | tail -12
.venv/bin/python tools/key_usage.py
