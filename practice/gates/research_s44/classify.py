"""Assign a root cause to every miss in the key designs and cost it: 0.2 pt per wrong answer, 3.1 pt per split group."""
import json, re, unicodedata
from collections import defaultdict, Counter
OUT = "/mnt/c/Users/Administrator/AppData/Local/Temp/claude/--wsl-localhost-ubuntu-24-04-home-bittensor-minos/3adafca1-9457-4695-b456-d48686e6121d/scratchpad"
rows = json.load(open(f"{OUT}/program_cases.json"))
st = {(r["run"], r["seed"], r["dom"], r["grp"], r["rel"]): r for r in json.load(open(f"{OUT}/stages.json"))}
KEY = ["v30-released", "v6-f123", "v6-hold", "v7-prog", "v7-prog2", "v7-1"]


def norm(s):
    s = unicodedata.normalize("NFKC", s or "").lower().replace(" ", " ")
    return re.sub(r"[\s\.\,;:!\"“”'`*_]+", " ", s).strip()


def cause(r, s):
    a = r["answer"] or ""
    na = norm(a)
    sh = r["shape"]
    acc = [norm(x) for x in (r["accept_any"] or [r["expected"]])]
    if r["label"] == "v7-prog" and na in acc:
        return "E: served text carried the ledger (earlier values/decoys) - echo bug"
    if 0 < r["score"] < 1:
        return "V1: value shortened/reworded (partial credit)"
    if re.search(r"before (then|renewal)|the plan was", a, re.I):
        return "V2: kept timing/qualifier or copied the sentence"
    if sh.startswith("chain:revert-to-middle"):
        return "C1: unnamed revert read as the entry just before it (C, not B)"
    if sh == "membership":
        return "Q1: 'after the X's change' read as one change"
    if sh.startswith("identity:contact"):
        if "joraelfin" in a.lower():
            return "L1: glossary label given instead of its value"
        if ";" in a:
            return "Q2: 'after every reassignment' answered one value per change"
        if re.fullmatch(r"[a-z]+", a.strip()):
            return "L1: glossary label given instead of its value"
        return "L2: stopped at the name; not mapped through the directory to the handle"
    if sh == "client-vs-vendor":
        return "L3: client/vendor role swapped (paying vs billing)"
    if sh.startswith("chain:error") and na in ("none", "not stated", "no status"):
        return "C2: struck entry read as erasing the item (nothing left)"
    if sh.startswith("chain:declined") and "13 january" in na:
        return "C3: proposal taken as a change; the dropped request not linked to the item"
    if sh.startswith("process"):
        return "P1: later pass overruled right answer (missed late reopen)"
    if "renew" in na:
        return "Q3: asked field misread (renewal date given as next action)"
    if sh.startswith("chain:revert") or sh.startswith("chain:change") or sh.startswith("chain:declined") or sh.startswith("chain:error") or sh.startswith("as-of") or sh.startswith("sequence") or sh.startswith("identity:name"):
        return "X: other (" + sh + ")"
    return "X: other (" + sh + ")"


groups = defaultdict(list)
for r in rows:
    if r["label"] not in KEY:
        continue
    groups[(r["label"], r["run"], r["seed"], r["domain"], r["group"])].append(r)
runs = Counter(r["run"] for r in rows if r["label"] in KEY)
nruns = Counter()
for run in runs:
    lab = next(r["label"] for r in rows if r["run"] == run)
    nruns[lab] += 1
cost = defaultdict(lambda: defaultdict(lambda: [0, 0, 0.0]))  # label -> cause -> [wrong, splits, points]
detail = []
for (lab, run, seed, dom, g), mem in groups.items():
    twins = [m for m in mem if "counterfactual" not in m["relation"]]
    split = any(m["score"] >= 1 for m in twins) and any(m["score"] < 1 for m in twins)
    causes = []
    for m in mem:
        if m["score"] >= 1:
            continue
        s = st.get((m["run"], m["seed"], m["domain"], m["group"], m["relation"]), {})
        c = cause(m, s)
        causes.append(c)
        cost[lab][c][0] += 1
        cost[lab][c][2] += 0.2 * (1 - m["score"])
        detail.append(dict(label=lab, run=run, seed=seed, dom=dom, grp=g, shape=m["shape"], rel=m["relation"], score=m["score"], answer=m["answer"], expected=m["expected"], cause=c, split=split))
    if split:
        c = Counter(causes).most_common(1)[0][0]
        cost[lab][c][1] += 1
        cost[lab][c][2] += 3.1
json.dump(detail, open(f"{OUT}/miss_causes.json", "w"), indent=0)


def mechanism(m):
    s = st.get((m["run"], m["seed"], m["dom"], m["grp"], m["rel"]), {})
    if m["cause"].startswith(("V", "E")):
        return "value form / serving"
    if s.get("draft_j") is not None:
        return {"wrong": "shared draft wrong, kept", "right": "draft right, later pass overruled", "?": "draft unclear"}.get(s["draft_j"], "?")
    if s.get("draft") is None and s.get("ledger_j") is None and s.get("earlier") is None:
        return "single reading (no shared artifact)"
    if s.get("earlier") is not None:
        if s.get("earlier_j") == "right":
            return "earlier reply right, later rewording overruled"
        return "earlier reply wrong, kept"
    if s.get("ledger_j") == "right":
        return "ledger right, reply overruled"
    if s.get("ledger_j") == "wrong":
        return "ledger wrong, reply followed"
    return "ledger mixed/unclear"


mech = defaultdict(Counter)
for m in detail:
    mech[m["label"]][mechanism(m)] += 1
print("\nmechanism of each miss")
for lab in KEY:
    print(lab, dict(mech[lab]))
allc = sorted({c for l in cost for c in cost[l]})
print("per design: misses / splits / points per run (0.2 per miss, 3.1 per split)")
for lab in KEY:
    n = nruns[lab]
    print(f"== {lab} ({n} runs)")
    tot = 0
    for c in allc:
        if c in cost[lab]:
            w, s, p = cost[lab][c]
            tot += p
            print(f"    {c:80} miss {w:3}  split {s:2}  pts/run {p / n:5.2f}")
    print(f"    {'TOTAL':80} pts/run {tot / n:5.2f}")
