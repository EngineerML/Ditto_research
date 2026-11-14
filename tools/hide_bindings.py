"""Make a "hidden second item" copy of a two-item list pack: drop each case's evidence notes that name no gold item.

In memgen-style packs a case's evidence is: the note giving item 1 under the full name, the note(s) tying a nickname
to the person, and the note giving item 2 under the nickname. Dropping the notes that hold no gold item removes the
tie, so item 2 stays in the store (the pack stays grounded) but nothing links it to the person: the shape the
current generators' 0.5-for-everyone columns show. An ideal reply then names item 1 and nothing else (0.5);
"no record of a second ..." scores 0.

    python3 tools/hide_bindings.py IN_PACK.json OUT_PACK.json
"""
import json
import sys

src, out = sys.argv[1], sys.argv[2]
pack = json.load(open(src))
drop = set()
for case in pack["cases"]:
    items = case.get("answer_items") or []
    pairs = {p["pair_id"]: p for w in pack["memory_waves"] for p in w["pairs"]}
    for pid in case.get("evidence_pair_ids") or []:
        text = pairs.get(pid, {}).get("prompt", "") + " " + pairs.get(pid, {}).get("response", "")
        if not any(item in text for item in items):
            drop.add(pid)
for w in pack["memory_waves"]:
    w["pairs"] = [p for p in w["pairs"] if p["pair_id"] not in drop]
for case in pack["cases"]:
    case["evidence_pair_ids"] = [pid for pid in case.get("evidence_pair_ids") or [] if pid not in drop]
json.dump(pack, open(out, "w"))
print(f"dropped {len(drop)} tie notes from {len(pack['cases'])} cases -> {out}")
