"""Static (free): the places packet.person_places says still hold, against each querverweis case's items and traps.

    python3 practice/qv_places_static.py PACK.json [...] [-v]
"""
import json, sys, collections
sys.path.insert(0, "/home/bittensor/ditto/c228")
from app.protocol import MemoryPair  # noqa: E402
from app.memory.retrieval import UserIndex  # noqa: E402
from app.packet import person_forms, person_places  # noqa: E402
from app.guide_records import current_list_notes  # noqa: E402

verbose = "-v" in sys.argv
FIELDS = ("pair_id", "prompt", "response", "timestamp", "session_id")
for path in [a for a in sys.argv[1:] if a != "-v"]:
    d = json.load(open(path))
    pairs = [p for w in d["memory_waves"] for p in w.get("pairs") or []]
    index = UserIndex([MemoryPair(**{k: p[k] for k in FIELDS if k in p}) for p in pairs])
    tally, score = collections.Counter(), 0.0
    for c in d["cases"]:
        found = current_list_notes(c["question"]) and person_forms(index, c["question"])
        if not found:
            tally["no forms"] += 1
            continue
        places = person_places(index, found)
        holds = {p["place"] for p in places if not p["left"] and not p["plan"]}
        items, traps = set(c["answer_items"]), set(c["distractor_answers"])
        got, bad, extra = holds & items, holds & traps, holds - items - traps
        tally["exact"] += holds == items
        tally["trap held"] += bool(bad)
        tally["item missed"] += len(items - holds)
        tally["extra"] += len(extra)
        score += 0 if bad else len(got) / len(items)
        if verbose and holds != items:
            print(c["id"], c["question"][:60], "| missed", sorted(items - holds), "| traps", sorted(bad), "| extra", sorted(extra))
    n = sum(1 for c in d["cases"]) - tally["no forms"]
    print(path.rsplit("/", 2)[-2] + "/" + path.rsplit("/", 1)[-1], dict(tally), f"code-only mean over {n}: {score / max(n, 1):.2f}")
