"""Show the per-case slice results of one column for an agent's runs: score distribution and any text fields.

    python3 live/col_cases.py scores_FILE.json COLUMN_INDEX
"""
import json, sys
from collections import Counter
sc = json.load(open(sys.argv[1]))["scores"]
col = int(sys.argv[2])
for r in sc:
    bd = r.get("dueling_breakdown") or {}
    cr = bd.get("case_results") or r.get("case_results") or []
    if not cr:
        print("no case_results; breakdown keys", sorted(bd)); continue
    part = cr[col * 35:(col + 1) * 35]
    print("season", bd.get("season_index"), "column", col, "n", len(part), "keys", sorted(part[0]) if part else None)
    print("  score counts", Counter(round(c.get("score", 0), 2) for c in part))
    for c in part[:3]:
        print("  ", {k: (str(v)[:160]) for k, v in c.items()})
