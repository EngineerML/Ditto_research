"""Static check (free): which datagen memory questions get a different called-name result from a harness tree.

    python3 practice/c228_called_static.py TREE_DIR OUT.json SEEDSET.json [...]

Imports TREE_DIR/app (the harness package) and runs memory.coverage.called_names for every memory case
against the store of the case's user (all waves). Writes {case_id: [[full, alias, n_where, n_holders], ...]}.
"""
import json, sys
tree, out = sys.argv[1], sys.argv[2]
sys.path.insert(0, tree)
from app.protocol import MemoryPair  # noqa: E402
from app.memory.retrieval import UserIndex  # noqa: E402
from app.memory import coverage  # noqa: E402

res = {}
for path in sys.argv[3:]:
    d = json.load(open(path))
    by_user, owner = {}, {}
    for w in d["memory_waves"]:
        if "pairs" not in w:
            print(path, "wave without pairs, keys", sorted(w)[:10])
            continue
        for p in w["pairs"]:
            by_user.setdefault(w.get("user_id", "pack"), []).append(p)
            owner[p["pair_id"]] = w.get("user_id", "pack")
    if not res:
        print("pair keys", sorted(d["memory_waves"][0]["pairs"][0]))
    idx = {}
    d.setdefault("seed", path.rsplit("/", 2)[-2] + "/" + path.rsplit("/", 1)[-1])
    for c in d.get("memory_cases") or d.get("cases") or []:
        ev = c.get("v10_evidence_pair_ids") or c.get("evidence_pair_ids") or []
        users = sorted({owner[e] for e in ev if e in owner} or set(by_user))
        rows = []
        for u in users:
            if u not in idx:
                pairs = [MemoryPair(**{k: p[k] for k in ("pair_id", "prompt", "response", "timestamp") if k in p}) for p in by_user[u]]
                idx[u] = UserIndex(pairs)
            got = coverage.called_names(idx[u], c["question"])
            rows += [[u, f, a, len(w), len(h)] for f, a, w, h in got]
        res[f"{d['seed']}:{c['id']}"] = rows
json.dump(res, open(out, "w"), indent=0)
print(tree, "cases", len(res), "with a called name", sum(1 for v in res.values() if v))
