import json, sys, glob, os
d = sys.argv[1].rstrip("/") + "/"
for f in sorted(glob.glob(d + "scores_*.json")):
    s = json.load(open(f))
    print("\n##", os.path.basename(f)[7:-5], "median", s.get("median_composite"))
    for r in s.get("scores", [])[:6]:
        bd = r.get("dueling_breakdown") or {}
        cols = bd.get("columns") or []
        cs = {}
        for c in cols if isinstance(cols, list) else []:
            cs[c.get("column_id")] = round(c.get("score") if c.get("score") is not None else c.get("column_score", -1), 3)
        cost = (r.get("cost") or {})
        print(f"  s{bd.get('season_index')} comp {r['composite']:.3f} tool {r['tool_mean']:.3f} mem {r['memory_mean']:.3f} dg {bd.get('datagen_raw')} gsum {round(bd.get('generator_sum') or 0,3)} cols {cs}")
    if f.endswith("dan0l_53.json"):
        print(json.dumps(s["scores"][0]["dueling_breakdown"])[600:2600])
