"""For cases where person_places keeps a trap or misses an item: the records that write that place (free).

    python3 practice/qv_trap_texts.py PACK.json
"""
import json, sys
sys.path.insert(0, "/home/bittensor/ditto/c228")
from app.protocol import MemoryPair  # noqa: E402
from app.memory.retrieval import UserIndex  # noqa: E402
from app.packet import person_forms, person_places  # noqa: E402
from app.guide_records import current_list_notes  # noqa: E402

FIELDS = ("pair_id", "prompt", "response", "timestamp", "session_id")
d = json.load(open(sys.argv[1]))
pairs = [p for w in d["memory_waves"] for p in w.get("pairs") or []]
index = UserIndex([MemoryPair(**{k: p[k] for k in FIELDS if k in p}) for p in pairs])
for c in d["cases"]:
    found = current_list_notes(c["question"]) and person_forms(index, c["question"])
    if not found:
        continue
    holds = {p["place"] for p in person_places(index, found) if not p["left"] and not p["plan"]}
    for tag, places in (("TRAP KEPT", holds & set(c["distractor_answers"])), ("ITEM LOST", set(c["answer_items"]) - holds)):
        for place in places:
            print(f"{c['id']} {tag} {place}  (gender={found['gender']})")
            for p in sorted(pairs, key=lambda p: p["timestamp"]):
                if place in p["prompt"]:
                    print(f"     [{p['timestamp'][:10]}] {p['prompt'][:170]}")
