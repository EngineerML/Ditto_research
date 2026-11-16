"""Reach (free) of guide_records.current_list_notes over packs / v18 seed sets: cases that get the note.

    python3 practice/qv_note_reach.py FILE.json [...]
"""
import json, sys, collections
sys.path.insert(0, "/home/bittensor/ditto/c228")
from app.guide_records import current_list_notes  # noqa: E402
tot = collections.Counter()
for path in sys.argv[1:]:
    d = json.load(open(path))
    cases = d.get("memory_cases") or d.get("cases") or []
    hit = [c["question"] for c in cases if current_list_notes(c["question"])]
    tot["cases"] += len(cases); tot["hit"] += len(hit)
    if hit:
        miss = [c["question"] for c in cases if not current_list_notes(c["question"])][:2]
        print(f"{path.rsplit('/', 2)[-2] + '/' + path.rsplit('/', 1)[-1]:42} cases {len(cases):4} note {len(hit):3}  not: {miss}")
print(dict(tot))
