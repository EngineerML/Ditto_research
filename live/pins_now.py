import json, sys
d = sys.argv[1].rstrip("/") + "/"
se = json.load(open(d + "public_dueling_seasons.json"))["seasons"]
gb = {g["submission_id"]: g for g in json.load(open(d + "generator_board.json"))["entries"]}
for s in se[:4]:
    print(f"\nseason {s['season_index']} opened {s['opened_at'][:16]} closed {(s['closed_at'] or '')[:16]} revealed {(s['revealed_at'] or '')[:16]}")
    pins = (s.get("pins") or {}).get("columns") or []
    for c in pins:
        sid = c.get("submission_id") or c.get("generator_submission_id")
        g = gb.get(sid, {})
        rest = {k: v for k, v in c.items() if k not in ("column_id",) and not isinstance(v, (dict, list))}
        print("  ", c.get("column_id"), g.get("name"), "v", g.get("version"), (g.get("miner_hotkey") or "")[:6], "board", round(g.get("score") or 0, 3), rest)
