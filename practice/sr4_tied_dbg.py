"""Which tie made crown's tied-names view take chosen staged-records cases (free, offline)."""
import json, sys
sys.path.insert(0, "/home/bittensor/ditto/c228")
from app.protocol import MemoryPair  # noqa: E402
from app.memory.retrieval import UserIndex  # noqa: E402
from app import evidence  # noqa: E402

pack = json.load(open(sys.argv[1]))
want = set(sys.argv[2:])
by_user = {}
for w in pack["memory_waves"]:
    by_user.setdefault(w["user_id"], []).extend((w["wave"], p) for p in w["pairs"])
idx = {}
hit = 0
for c in pack["cases"]:
    u = c["user_id"]
    pairs = [MemoryPair(**{k: p[k] for k in ("pair_id", "prompt", "response", "timestamp")}) for wv, p in by_user[u] if wv <= c["run_after_wave"]]
    key = (u, c["run_after_wave"])
    if key not in idx:
        idx[key] = UserIndex(pairs)
    view = evidence.tied_names_view(c["question"], idx[key])
    if view:
        hit += 1
    if c["id"] in want:
        fulls = evidence.FULL_NAME_RE.findall(c["question"])
        print("==", c["id"], "fulls", fulls, "view", bool(view))
        if fulls:
            ties = evidence.person_ties(idx[key], c["question"], fulls[0])
            for alias, pids in ties.items():
                print("  tie", alias, [idx[key].nodes[p].pair.prompt[:160] for p in pids][:2])
print("cases taking the tied-names view:", hit, "of", len(pack["cases"]))
