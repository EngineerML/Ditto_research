"""Static reach (free) of referring_turns: cases where it would add or move a record, and on bauni v6 packs whether the
seated turn is the case's evidence relay and never a distractor.

    python3 practice/c228_referring_reach.py SEEDSET_OR_PACK.json [...]

Upper bound: every stored record of the case's user that writes an asked full name is treated as a packet record
(the real packet holds a subset).
"""
import json, sys, collections
sys.path.insert(0, "/home/bittensor/ditto/c228")
from app.protocol import MemoryPair  # noqa: E402
from app.memory.retrieval import Candidate, UserIndex  # noqa: E402
from app.packet import Packet, asked_full_names, referring_turns  # noqa: E402

FIELDS = ("pair_id", "prompt", "response", "timestamp", "session_id")
tot = collections.Counter()
for path in sys.argv[1:]:
    d = json.load(open(path))
    by_user, owner = {}, {}
    for w in d["memory_waves"]:
        for p in w.get("pairs") or []:
            by_user.setdefault(w.get("user_id", "pack"), []).append(p)
            owner[p["pair_id"]] = w.get("user_id", "pack")
    idx = {}
    cases = reached = right = wrong = 0
    shown = []
    for c in d.get("memory_cases") or d.get("cases") or []:
        cases += 1
        ev = c.get("v10_evidence_pair_ids") or c.get("evidence_pair_ids") or []
        users = sorted({owner[e] for e in ev if e in owner} or set(by_user))
        names = asked_full_names(c["question"])
        if not names:
            continue
        seated = []
        for u in users:
            if u not in idx:
                idx[u] = UserIndex([MemoryPair(**{k: p[k] for k in FIELDS if k in p}) for p in by_user[u]])
            index = idx[u]
            anchors = [Candidate(pair=n.pair) for n in sorted(index.nodes.values(), key=lambda n: n.pair.timestamp) if any(x in n.pair.prompt for x in names)]
            if not anchors:
                continue
            packet = Packet(records=anchors)
            added, moved = referring_turns(packet, c["question"], index, False)
            seated += [cand.pair for cand in packet.records if cand.continues]
        if not seated:
            continue
        reached += 1
        dist = c.get("distractor_answers") or []
        for pair in seated:
            if pair.pair_id in ev:
                right += 1
            elif any(x and x in pair.prompt for x in dist):
                wrong += 1
        if len(shown) < 3:
            shown.append((c.get("id") or c.get("question_id"), c["question"][:90], [p.prompt[:90] for p in seated]))
    name = path.rsplit("/", 2)[-2] + "/" + path.rsplit("/", 1)[-1]
    print(f"{name:40} cases {cases:4} reached {reached:4} evidence seated {right:4} distractor seated {wrong:3}")
    if "-v" in sys.argv[0:0] or "bauni" not in path:
        for s in shown:
            print("    ", s)
    tot["cases"] += cases
    tot["reached"] += reached
    tot["wrong"] += wrong
print(dict(tot))
