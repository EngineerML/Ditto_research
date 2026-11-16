"""Static (free) check of packet.person_forms on querverweis packs: where each item record and each trap record lands
(full / first / title / other / not found), and gender reads. Also counts reach on any other file given.

    python3 practice/qv_forms_static.py FILE.json [...]
"""
import json, sys, collections
sys.path.insert(0, "/home/bittensor/ditto/c228")
from app.protocol import MemoryPair  # noqa: E402
from app.memory.retrieval import UserIndex  # noqa: E402
from app.packet import person_forms  # noqa: E402
from app.guide_records import current_list_notes  # noqa: E402

FIELDS = ("pair_id", "prompt", "response", "timestamp", "session_id")
for path in sys.argv[1:]:
    d = json.load(open(path))
    pairs = [p for w in d["memory_waves"] for p in w.get("pairs") or []]
    index = UserIndex([MemoryPair(**{k: p[k] for k in FIELDS if k in p}) for p in pairs])
    text = {p["pair_id"]: p["prompt"] for p in pairs}
    where = collections.Counter()
    reached = 0
    for c in d.get("memory_cases") or d.get("cases") or []:
        if not current_list_notes(c["question"]):
            continue
        found = person_forms(index, c["question"])
        if not found:
            where["no forms (role question or none)"] += 1
            continue
        reached += 1
        kind_of = {pid: k for k in ("full", "first", "title", "other") for pid in found[k]}
        for tag, items in (("item", c["answer_items"]), ("trap", c.get("distractor_answers") or [])):
            for it in items:
                for pid, t in text.items():
                    if it in t:
                        where[(tag, kind_of.get(pid, "-"))] += 1
    name = path.rsplit("/", 2)[-2] + "/" + path.rsplit("/", 1)[-1]
    print(name, "reached", reached, dict(sorted(where.items(), key=str)))
