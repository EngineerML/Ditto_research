#!/bin/bash
# Re-run only the v13 open/personal program memory cases of one v18 seed (subset scorer, every wave seeded), traced.
#
#   bash practice/c228_program.sh IMG [SEED]
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
PY=.venv/bin/python
IMG=${1:?image tag}
SEED=${2:-1810005}
ids=practice/c228_program_$SEED.txt
python3 - "$SEED" "$ids" <<'P'
import json, sys
d = json.load(open(f"/home/bittensor/ditto/.cache/v18sets/{sys.argv[1]}.json"))
ids = [c["id"] for c in d["memory_cases"] if c["question_type"] in ("v13-open-program", "v13-personal-program")]
open(sys.argv[2], "w").write("\n".join(ids) + "\n")
print(len(ids), "cases")
P
echo "start $(date -u +%H:%M) $($PY tools/key_usage.py)"
$PY tools/key_usage.py --need 3 > /dev/null || { echo "balance under \$3, not starting"; exit 1; }
timeout 3600 python3 tools/practice_docker.py --image ditto-harness:$IMG --run-size full --bench-version 18 --seed $SEED --trace \
  --only-cases $ids --scorer-bin $PWD/.cache/dittobench-api-subset-v18 --concurrency 4 2>&1 | tail -2
echo "done $(date -u +%H:%M) $($PY tools/key_usage.py)"
