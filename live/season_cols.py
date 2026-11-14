"""Per season: pinned generator per column and each agent's column means (from scores_*.json in a snapshot)."""
import json, sys, glob, os
from collections import defaultdict
d = sys.argv[1].rstrip("/") + "/"
se = {s["season_index"]: s for s in json.load(open(d + "public_dueling_seasons.json"))["seasons"]}
gb = {g["submission_id"]: g for g in json.load(open(d + "generator_board.json"))["entries"]}
rows = defaultdict(dict)
for f in sorted(glob.glob(d + "scores_*.json")):
    name = os.path.basename(f)[7:-5]
    for r in json.load(open(f)).get("scores", []):
        bd = r.get("dueling_breakdown") or {}
        si = bd.get("season_index")
        if not si:
            continue
        rows[si].setdefault(name, []).append({c["column_id"]: c["mean"] for c in bd.get("columns", [])} | {"dg": bd.get("datagen_raw") or 0, "comp": r["composite"]})
for si in sorted(rows, reverse=True)[:8]:
    s = se.get(si, {})
    pins = {c["column_id"]: f"{c['miner_hotkey'][:6]}/{c['submission_id'][:8]}/b{c['grading_bench_version']}" + (f"({gb[c['submission_id']]['name']} v{gb[c['submission_id']]['version']})" if c['submission_id'] in gb and gb[c['submission_id']].get('name') else "") for c in (s.get("pins") or {}).get("columns") or []}
    print(f"\nseason {si} revealed {(s.get('revealed_at') or '-')[:16]}")
    for c in ("c0", "c1", "c2", "c3", "c4"):
        print(f"   {c}: {pins.get(c, '?')}")
    for name, rs in sorted(rows[si].items(), key=lambda kv: -sum(x['comp'] for x in kv[1]) / len(kv[1])):
        m = lambda k: sum(x.get(k, 0) for x in rs) / len(rs)
        print(f"   {name:12} n{len(rs)} comp {m('comp'):.3f} dg {m('dg'):.3f} | " + " ".join(f"{c}={m(c):.2f}" for c in ("c0", "c1", "c2", "c3", "c4")))
