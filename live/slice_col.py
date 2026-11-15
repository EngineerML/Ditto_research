"""Slice cases of one pinned generator for an agent: score, latency and notes per case, per run.

    python3 live/slice_col.py SCORES_FILE GENERATOR_SUBMISSION_PREFIX SNAPSHOT_DIR
"""
import json, sys, statistics
from collections import Counter
sc = json.load(open(sys.argv[1]))["scores"]
gen = sys.argv[2]
seasons = {s["season_index"]: s for s in json.load(open(sys.argv[3].rstrip("/") + "/public_dueling_seasons.json"))["seasons"]}
for r in sc:
    bd = r.get("dueling_breakdown") or {}
    s = seasons.get(bd.get("season_index")) or {}
    pins = (s.get("pins") or {}).get("columns") or []
    sl = [c for c in r.get("case_results") or [] if c.get("category") == "dueling_slice"]
    for i, p in enumerate(pins[:5]):
        if not p["submission_id"].startswith(gen):
            continue
        part = sl[i * 35:(i + 1) * 35]
        lat = [c.get("latency_ms") or 0 for c in part]
        lat0 = [c.get("latency_ms") or 0 for c in part if c.get("score") == 0]
        lat1 = [c.get("latency_ms") or 0 for c in part if c.get("score") == 1]
        print(f"season {bd.get('season_index')} col c{i} mean {sum(c['score'] for c in part)/35:.2f}"
              f" lat med {statistics.median(lat):.0f} ms  zero-cases med {statistics.median(lat0) if lat0 else 0:.0f}  one-cases med {statistics.median(lat1) if lat1 else 0:.0f}"
              f" notes {Counter(str(c.get('notes'))[:60] for c in part).most_common(3)} cost {r.get('run_cost_microusd') or r.get('average_run_cost_microusd')}")
        print("   seq", "".join("1" if c["score"] == 1 else "0" for c in part))
