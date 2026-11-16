"""Static reach (free) of the number_threads port: questions where it could add or move records.

    python3 practice/c228_numthread_reach.py SEEDSET_OR_PACK.json [...]

Upper bound: treats every stored record of the case's user that names an asked full name and holds a 5+ digit
number as a packet anchor (the real packet holds a subset), and counts the records the thread would reach.
"""
import json, sys, collections
sys.path.insert(0, "/home/bittensor/ditto/c228")
from app.protocol import MemoryPair  # noqa: E402
from app.memory.retrieval import Candidate, UserIndex  # noqa: E402
from app.packet import NUMBER_RE, Packet, asked_full_names, number_threads  # noqa: E402

tot = collections.Counter()
for path in sys.argv[1:]:
    d = json.load(open(path))
    by_user, owner = {}, {}
    for w in d["memory_waves"]:
        for p in w.get("pairs") or []:
            by_user.setdefault(w.get("user_id", "pack"), []).append(p)
            owner[p["pair_id"]] = w.get("user_id", "pack")
    idx = {}
    reached, cases, sizes = 0, 0, []
    for c in d.get("memory_cases") or d.get("cases") or []:
        cases += 1
        ev = c.get("v10_evidence_pair_ids") or c.get("evidence_pair_ids") or []
        users = sorted({owner[e] for e in ev if e in owner} or set(by_user))
        hit = 0
        for u in users:
            if u not in idx:
                idx[u] = UserIndex([MemoryPair(**{k: p[k] for k in ("pair_id", "prompt", "response", "timestamp") if k in p}) for p in by_user[u]])
            index = idx[u]
            names = asked_full_names(c["question"])
            if not names:
                continue
            anchors = [Candidate(pair=n.pair) for n in index.nodes.values() if any(x in n.pair.prompt for x in names) and NUMBER_RE.search(n.pair.prompt)]
            if not anchors:
                continue
            _, added, moved = number_threads(Packet(records=anchors), c["question"], index, False)
            hit += added
        if hit:
            reached += 1
            sizes.append(hit)
    name = path.rsplit("/", 2)[-2] + "/" + path.rsplit("/", 1)[-1]
    print(f"{name:40} cases {cases:4} reached {reached:4} records added {sizes[:12]}")
    tot["cases"] += cases
    tot["reached"] += reached
print(dict(tot))
