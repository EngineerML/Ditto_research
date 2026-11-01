"""Do the three rewordings of a twin group see identical notes? Compare the first user turn (notes part) of each call kind."""
import json, difflib, re
from collections import defaultdict, Counter
OUT = "/mnt/c/Users/Administrator/AppData/Local/Temp/claude/--wsl-localhost-ubuntu-24-04-home-bittensor-minos/3adafca1-9457-4695-b456-d48686e6121d/scratchpad"
rows = json.load(open(f"{OUT}/program_cases.json"))
calls = json.load(open(f"{OUT}/program_calls.json"))

def body(cl):
    for m in cl["messages"]:
        if m["role"] == "user":
            t = m["content"]
            cut = t.find("\nMessage:")
            return t[:cut] if cut >= 0 else t
    return ""

def sysmsg(cl):
    for m in cl["messages"]:
        if m["role"] == "system":
            return m["content"]
    return ""

fams = ["v30-released", "v6-f123", "v6-hold", "v7-prog2", "v7-1", "v5-", "combined", "dan0l"]
res = defaultdict(Counter)
examples = {}
groups = defaultdict(list)
for r in rows:
    if "counterfactual" in (r["relation"] or ""):
        continue
    groups[(r["run"], r["domain"], r["group"])].append(r)
for (run, dom, g), mem in groups.items():
    lab = mem[0]["label"]
    f = next((x for x in fams if lab.startswith(x)), lab)
    cls = [calls.get(f"{run}|{m['case_id']}") for m in mem]
    if any(c is None for c in cls):
        continue
    # deciding call = last call; compare its notes body and system
    last = [c[-1] if c else None for c in cls]
    if any(l is None for l in last):
        res[f]["nocalls"] += 1
        continue
    bodies = [body(l) for l in last]
    systems = [sysmsg(l) for l in last]
    same_b = len(set(bodies)) == 1
    same_s = len(set(systems)) == 1
    res[f][("body_same" if same_b else "body_diff")] += 1
    res[f][("sys_same" if same_s else "sys_diff")] += 1
    if not same_b and f not in examples:
        a, b = bodies[0], next(x for x in bodies if x != bodies[0])
        d = [l for l in difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=0)][:20]
        examples[f] = (run, dom, g, d)
    if not same_s and (f + "_sys") not in examples:
        a, b = systems[0], next(x for x in systems if x != systems[0])
        sm = difflib.SequenceMatcher(None, a, b)
        d = [(op, a[i1:i2][:300], b[j1:j2][:300]) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal"][:6]
        examples[f + "_sys"] = (run, dom, g, d)
for f, c in res.items():
    print(f, dict(c))
for k, v in examples.items():
    print("=====", k, v[0], v[1], v[2])
    for l in v[3]:
        print("   ", str(l)[:400])
