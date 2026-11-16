"""Render the person-forms block (free) for given cases of a pack, with a packet of every record naming the surname.

    python3 practice/qv_block_show.py PACK.json CASE_ID [...]
"""
import json, sys
sys.path.insert(0, "/home/bittensor/ditto/c228")
from app.protocol import MemoryPair  # noqa: E402
from app.memory.retrieval import Candidate, UserIndex  # noqa: E402
from app.packet import Packet, person_forms, person_forms_block  # noqa: E402

FIELDS = ("pair_id", "prompt", "response", "timestamp", "session_id")
d = json.load(open(sys.argv[1]))
pairs = [p for w in d["memory_waves"] for p in w.get("pairs") or []]
index = UserIndex([MemoryPair(**{k: p[k] for k in FIELDS if k in p}) for p in pairs])
for c in d["cases"]:
    if c["id"] not in sys.argv[2:]:
        continue
    found = person_forms(index, c["question"])
    last = c["question"].split(" does ")[1].split()[1] if found else ""
    packet = Packet(records=[Candidate(pair=n.pair) for n in sorted(index.nodes.values(), key=lambda n: n.pair.timestamp) if last and last in n.pair.prompt])
    print("Q:", c["question"], "| items", c["answer_items"])
    print(person_forms_block(packet, found, index), "\n")
