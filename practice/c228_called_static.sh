#!/bin/bash
# Free: called-name results of crown-v228 vs the c228 tree on v18 datagen seeds and every local generator pack.
cd /home/bittensor/ditto || exit 1
S=".cache/v18sets/1810003.json .cache/v18sets/1810004.json .cache/v18sets/1810005.json .cache/v18sets/1810006.json $(ls .cache/miner_gens/packs/*/*.json | grep -v -E '/(fix1|fq-v2-p1)/')"
.venv/bin/python practice/c228_called_static.py released/crown-v228-v1_673386d0/src /tmp/c228_called_old.json $S 2>&1 | grep -v "wave without" || exit 1
.venv/bin/python practice/c228_called_static.py c228 /tmp/c228_called_new.json $S 2>&1 | grep -v "wave without" || exit 1
python3 - <<'P'
import json, collections
a = json.load(open("/tmp/c228_called_old.json")); b = json.load(open("/tmp/c228_called_new.json"))
diff = [k for k in b if a.get(k) != b[k]]
print("changed questions", len(diff), "of", len(b))
print(collections.Counter(k.split(":")[0].split("/")[0] for k in diff))
for k in diff[:12]:
    print(k, "old", a.get(k), "new", b[k])
P
