#!/bin/bash
# Small paid check of the c228 base (2026-11-14): one seed of memgen v6 + 5DWjUM v5 packs, then the
# 14 encounter / mutation-read / unlinked-probe tool cases of two v18 seeds. Traces kept.
#
#   bash practice/c228_small.sh            (IMG=c228bt by default)
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
PY=.venv/bin/python
IMG=${IMG:-c228bt}
echo "start $(date -u +%H:%M) $($PY tools/key_usage.py)"
$PY tools/key_usage.py --need 3 > /dev/null || { echo "balance under \$3, not starting"; exit 1; }
if [ -z "$SKIP_PACKS" ]; then
P=.cache/miner_gens/packs/s26111-small; mkdir -p $P
cp .cache/miner_gens/packs/s26111-memgen-v6/pack-1.json $P/memgen-v6-1.json
cp .cache/miner_gens/packs/s26111-5DWjUM-v5/pack-1.json $P/5DWjUM-v5-1.json
timeout 3600 $PY tools/generator_panel.py --packs $P --agent crown=$IMG --concurrency 4 2>&1 | grep -v "^20" | tail -25
echo "after packs $($PY tools/key_usage.py)"
fi
for seed in 1810003 1810004; do
  ids=practice/c228_tool_$seed.txt
  python3 - "$seed" "$ids" <<'P'
import json, sys
d = json.load(open(f"/home/bittensor/ditto/.cache/v18sets/{sys.argv[1]}.json"))
open(sys.argv[2], "w").write("\n".join(c["id"] for c in d["tool_cases"] if c["category"].startswith(("encounter", "v13_mutation", "connector_unlinked"))) + "\n")
P
  timeout 3600 python3 tools/practice_docker.py --image ditto-harness:$IMG --run-size full --bench-version 18 --seed $seed --trace \
    --only-cases $ids --scorer-bin $PWD/.cache/dittobench-api-subset-v18 --concurrency 4 2>&1 | tail -4
  echo "after seed $seed $($PY tools/key_usage.py)"
done
echo "done $(date -u +%H:%M)"
