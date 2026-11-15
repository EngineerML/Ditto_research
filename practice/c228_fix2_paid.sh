#!/bin/bash
# Fix 2 paid: 5FqQq9 v2 pack 1 (35 cases), working tree image c228fx2t; compare with the crown/v5 run 20261115T071342Z.
source /etc/profile.d/zz-proxy.sh
cd /home/bittensor/ditto || exit 1
PY=.venv/bin/python
echo "start $(date -u +%H:%M) $($PY tools/key_usage.py)"
$PY tools/key_usage.py --need 3 > /dev/null || { echo "balance under \$3, not starting"; exit 1; }
timeout 3600 $PY tools/generator_panel.py --packs .cache/miner_gens/packs/fq-v2-p1 --agent fix2=c228fx2t --concurrency 4 2>&1 | grep -v "^20" | head -12
echo "done $(date -u +%H:%M) $($PY tools/key_usage.py)"
d=$(ls -td practice/generator/2026*Z | head -1)
python3 - "$d" <<'P'
import json, sys, re
d = sys.argv[1]
pack = json.load(open("/home/bittensor/ditto/.cache/miner_gens/packs/fq-v2/pack-1.json"))
byq = {c["question"]: c for c in pack["cases"]}
ok = 0
for i, line in enumerate(open(f"{d}/trace/fq-v2-r0/fix2/trace.jsonl")):
    t = json.loads(line)
    c = byq[t["user_input"]]
    reply = t.get("final_text") or ""
    good = c["expected_answer"].lower() in reply.lower()
    ok += good
    if i == 0:
        m = re.search(r'[^\\]*says they are called[^\\]*', json.dumps(t.get("calls", [])))
        print("example line:", m.group(0)[:300] if m else None)
    if not good:
        print("BAD", c["id"], "gold", c["expected_answer"], "|", reply.replace("\n", " ")[:160])
print("fix2 solved", ok, "of 35")
P
