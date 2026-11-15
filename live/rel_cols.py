"""Per-season column means for released agents vs ours, with the pinned generator per column when revealed.

    python3 live/rel_cols.py SNAPSHOT name=agent_id ...
Reads scores_NAME.json (fetched by fetch_scores.py). For each season: column means per agent and,
when revealed, the generator submission id + board name pinned in that column.
"""
import json, sys, collections
d = sys.argv[1].rstrip("/") + "/"
names = [x.split("=")[0] for x in sys.argv[2:]]
seasons = {s["season_index"]: s for s in json.load(open(d + "public_dueling_seasons.json"))["seasons"]}
gb = {g["submission_id"]: g for g in json.load(open(d + "generator_board.json"))["entries"]}
rows = collections.defaultdict(dict)
for name in names:
    try:
        sc = json.load(open(d + f"scores_{name}.json")).get("scores", [])
    except Exception:
        continue
    for r in sc:
        bd = r.get("dueling_breakdown") or {}
        si = bd.get("season_index")
        sl = [c["score"] for c in r.get("case_results") or [] if c.get("category") == "dueling_slice"]
        if si and len(sl) == 175:
            rows[si].setdefault(name, []).append(sl)
for si in sorted(rows, reverse=True)[:8]:
    s = seasons.get(si) or {}
    pins = (s.get("pins") or {}).get("columns") or []
    print(f"\n== season {si} revealed {str(s.get('revealed_at'))[:16]}")
    for col in range(5):
        pin = ""
        if col < len(pins):
            sid = pins[col]["submission_id"]
            g = gb.get(sid, {})
            pin = f"{sid[:8]} hk {pins[col]['miner_hotkey'][:6]} {g.get('name')} v{g.get('version')}"
        cells = []
        for name in names:
            runs = rows[si].get(name)
            if runs:
                v = [x for run in runs for x in run[col * 35:(col + 1) * 35]]
                z = sum(1 for x in v if x == 0)
                cells.append(f"{name} {sum(v)/len(v):.2f}/z{z}")
        print(f"  c{col} {pin}\n      " + "  ".join(cells))
