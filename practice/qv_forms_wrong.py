"""Examples where person_forms puts an item record in 'other' or a trap record in 'title' (free).

    python3 practice/qv_forms_wrong.py PACK.json
"""
import json, sys
sys.path.insert(0, "/home/bittensor/ditto/c228")
from app.protocol import MemoryPair  # noqa: E402
from app.memory.retrieval import UserIndex  # noqa: E402
from app.packet import person_forms  # noqa: E402
from app.guide_records import current_list_notes  # noqa: E402

FIELDS = ("pair_id", "prompt", "response", "timestamp", "session_id")
d = json.load(open(sys.argv[1]))
pairs = [p for w in d["memory_waves"] for p in w.get("pairs") or []]
index = UserIndex([MemoryPair(**{k: p[k] for k in FIELDS if k in p}) for p in pairs])
text = {p["pair_id"]: p["prompt"] for p in pairs}
for c in d["cases"]:
    found = current_list_notes(c["question"]) and person_forms(index, c["question"])
    if not found:
        continue
    for tag, items, bad in (("ITEM in other", c["answer_items"], "other"), ("TRAP in title", c["distractor_answers"], "title")):
        for it in items:
            for pid, t in text.items():
                if it in t and pid in found[bad]:
                    print(f"{c['id']} {c['question'][:70]} gender={found['gender']} | {tag}: {t[:150]}")
