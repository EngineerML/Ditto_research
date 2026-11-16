"""Static (free): cases where the asked-name filter of tied_names_view drops a tie, and whether the view turns off.

    python3 practice/c228_askedrun_static.py SEEDSET_OR_PACK.json [...]
Uses each case's user store over all waves (an approximation of the store at question time).
"""
import json, sys, collections
sys.path.insert(0, "/home/bittensor/ditto/c228")
from app.protocol import MemoryPair  # noqa: E402
from app.memory.retrieval import UserIndex  # noqa: E402
from app import evidence  # noqa: E402

tot = collections.Counter()
for path in sys.argv[1:]:
    d = json.load(open(path))
    by_user, owner = {}, {}
    for w in d["memory_waves"]:
        for p in w.get("pairs") or []:
            by_user.setdefault(w.get("user_id", "pack"), []).append(p)
            owner[p["pair_id"]] = w.get("user_id", "pack")
    idx = {}
    changed = []
    n = 0
    for c in d.get("memory_cases") or d.get("cases") or []:
        n += 1
        q = c["question"]
        ev = c.get("v10_evidence_pair_ids") or c.get("evidence_pair_ids") or []
        users = sorted({owner[e] for e in ev if e in owner} or set(by_user))
        if len(q) > evidence.SEVERAL_MAX_CHARS or not evidence.SEVERAL_OF_RE.search(q) or evidence.NOT_A_LIST_ASK_RE.search(q):
            continue
        fulls = [name for name in dict.fromkeys(evidence.FULL_NAME_RE.findall(q)) if name.split()[0].lower() not in evidence.ORDINARY_OPENERS]
        if len(fulls) != 1:
            continue
        for u in users:
            if u not in idx:
                idx[u] = UserIndex([MemoryPair(**{k: p[k] for k in ("pair_id", "prompt", "response", "timestamp") if k in p}) for p in by_user[u]])
            raw = evidence.person_ties(idx[u], q, fulls[0])
            run = {word for r in evidence.CAPITAL_RUN_RE.findall(q) if fulls[0] in r for word in r.split()}
            dropped = [a for a in raw if a in run]
            if dropped:
                changed.append((c.get("id"), dropped, len(raw) - len(dropped), q[:110]))
    name = path.rsplit("/", 2)[-2] + "/" + path.rsplit("/", 1)[-1]
    print(f"{name:40} cases {n:4} ties dropped in {len(changed)}")
    for row in changed[:4]:
        print("     ", row)
    tot["cases"] += n
    tot["changed"] += len(changed)
print(dict(tot))
