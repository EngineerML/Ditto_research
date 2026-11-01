"""Accuracy by question form (scope token, opener and closer stripped crudely) for shapes with presupposing forms."""
import json, re, sys
from collections import defaultdict
OUT = "/mnt/c/Users/Administrator/AppData/Local/Temp/claude/--wsl-localhost-ubuntu-24-04-home-bittensor-minos/3adafca1-9457-4695-b456-d48686e6121d/scratchpad"
rows = json.load(open(f"{OUT}/program_cases.json"))
want = sys.argv[1]
acc = defaultdict(lambda: [0, 0, set()])
for r in rows:
    if not r["shape"].startswith(want) or "counterfactual" in r["relation"]:
        continue
    q = r["question"] or ""
    m = re.search(r"((?:After|Which|What|Who|Whose|For|On|In)[^?]*\?)", q)
    body = m.group(1) if m else q
    body = re.sub(r"\b(my|our) (\w+)", r"\1 X", body)
    body = re.sub(r"(for|on) the [\w' -]+?(\?| week| trip| day)", r"\1 the Y\2", body)
    a = acc[body[:110]]
    a[0] += r["score"] >= 1
    a[1] += 1
    a[2].add(r["seed"])
for k, (ok, n, seeds) in sorted(acc.items(), key=lambda x: x[1][0] / x[1][1]):
    print(f"{ok:4}/{n:<4} seeds={len(seeds)} {k}")
