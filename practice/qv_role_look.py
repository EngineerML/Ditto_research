"""Role questions: the records naming the role (newest first) and the holder role_holder picks (free).

    python3 practice/qv_role_look.py PACK.json CASE_ID [...]
"""
import json, re, sys
sys.path.insert(0, "/home/bittensor/ditto/c228")
from app.protocol import MemoryPair  # noqa: E402
from app.memory.retrieval import UserIndex  # noqa: E402
from app.packet import ROLE_ASK_RE, role_holder  # noqa: E402

FIELDS = ("pair_id", "prompt", "response", "timestamp", "session_id")
d = json.load(open(sys.argv[1]))
pairs = [p for w in d["memory_waves"] for p in w.get("pairs") or []]
index = UserIndex([MemoryPair(**{k: p[k] for k in FIELDS if k in p}) for p in pairs])
for c in d["cases"]:
    if c["id"] not in sys.argv[2:]:
        continue
    m = ROLE_ASK_RE.search(c["question"])
    print("Q:", c["question"], "| role", m and m.group(1), "| picked", role_holder(index, c["question"]))
    role = m.group(1)
    for p in sorted(pairs, key=lambda p: p["timestamp"], reverse=True):
        if re.search(r"\b" + re.escape(role) + r"\b", p["prompt"], re.I):
            print(f"   [{p['timestamp'][:16]}] {p['prompt'][:160]}")
