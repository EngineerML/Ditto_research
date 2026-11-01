"""How often does the deciding call depart from the shared artifact (draft / earlier reply), and is the departure a fix or harm?"""
import json, re, unicodedata
from collections import defaultdict, Counter
OUT = "/mnt/c/Users/Administrator/AppData/Local/Temp/claude/--wsl-localhost-ubuntu-24-04-home-bittensor-minos/3adafca1-9457-4695-b456-d48686e6121d/scratchpad"
st = json.load(open(f"{OUT}/stages.json"))


def norm(s):
    s = unicodedata.normalize("NFKC", s or "").lower().replace(" ", " ")
    return re.sub(r"[\s\.\,;:!\"“”'`*_]+", " ", s).strip()


tab = defaultdict(Counter)
for r in st:
    f = r["fam"]
    tw = "counterfactual" not in r["rel"]
    ok = r["score"] >= 1
    for what, val, j in (("draft", r["draft"], r["draft_j"]), ("earlier", r["earlier"], r["earlier_j"])):
        if val is None:
            continue
        same = norm(val) == norm(r["answer"])
        if same:
            tab[f][f"{what}: kept ({'ok' if ok else 'X'})"] += 1
        else:
            tab[f][f"{what}: departed {j}->{'ok' if ok else 'X'}"] += 1
for f, c in sorted(tab.items()):
    tot = sum(c.values())
    print(f, tot)
    for k, v in sorted(c.items()):
        print(f"    {k:36} {v}")
