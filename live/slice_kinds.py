"""Kind/fields of the slice cases per column for one agent's runs (to tell tool from memory generators)."""
import json, sys
from collections import Counter
sc = json.load(open(sys.argv[1]))["scores"]
for r in sc:
    bd = r.get("dueling_breakdown") or {}
    sl = [c for c in r.get("case_results") or [] if c.get("category") == "dueling_slice"]
    print("season", bd.get("season_index"), "slice n", len(sl), "fields", sorted(sl[0]) if sl else None)
    for i in range(5):
        part = sl[i * 35:(i + 1) * 35]
        print(f"  c{i}", Counter(c.get("kind") for c in part), "mean", round(sum(c["score"] for c in part) / max(1, len(part)), 2),
              {k: str(part[0].get(k))[:80] for k in part[0] if k not in ("score", "kind", "category")} if part else "")
    print("  breakdown keys", sorted(bd)[:40])
    break
