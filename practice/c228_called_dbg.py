import json, sys, re
tree = sys.argv[1]
sys.path.insert(0, tree)
from app.protocol import MemoryPair
from app.memory.retrieval import UserIndex
from app.memory import coverage
d = json.load(open("/home/bittensor/ditto/.cache/v18sets/1810004.json"))
c = next(c for c in d["memory_cases"] if c["id"] == "c96c0dfd28f4a6124")
owner = {p["pair_id"]: w["user_id"] for w in d["memory_waves"] for p in w.get("pairs") or []}
u = owner[c["v10_evidence_pair_ids"][0]]
pairs = [MemoryPair(**{k: p[k] for k in ("pair_id", "prompt", "response", "timestamp")}) for w in d["memory_waves"] if w["user_id"] == u for p in w.get("pairs") or []]
idx = UserIndex(pairs)
for p in pairs:
    if "Sunny" in p.prompt:
        print(len(p.prompt), repr(p.prompt[:200]), "short" if coverage.short_prompt(idx, p.pair_id) else "LONG")
print("asked", coverage.asked_names(c["question"]))
print("called", coverage.called_names(idx, c["question"]))
print("Breanna holders", len(coverage.name_holders(idx, "Breanna")), "short", len({p for p in coverage.name_holders(idx, "Breanna") if coverage.short_prompt(idx, p)}))
