"""Pinned generator per column for the most recent seasons of a snapshot (name/version from the generator board and
known ids), plus open/close/reveal times.

    python3 -I live/pins_recent.py SNAPSHOT [N]
"""
import json, sys
d = sys.argv[1].rstrip("/") + "/"
n = int(sys.argv[2]) if len(sys.argv) > 2 else 6
KNOWN = {"33c60a4b": "tetgol v6", "e4cfece4": "staged-records v4", "41a497e8": "bauni v6", "ba2ee4d1": "5Ey8jp ba2ee4d1", "f5659f80": "5FqQq9 v2 pollen-probe"}
gb = {g["submission_id"]: g for g in json.load(open(d + "generator_board.json"))["entries"]}
seasons = sorted(json.load(open(d + "public_dueling_seasons.json"))["seasons"], key=lambda s: -s["season_index"])
for s in seasons[:n]:
    print(f"season {s['season_index']} open {str(s['opened_at'])[5:16]} close {str(s.get('closed_at'))[5:16]} revealed {str(s.get('revealed_at'))[5:16]}")
    for c in (s.get("pins") or {}).get("columns") or []:
        sid = c["submission_id"]
        g = gb.get(sid) or {}
        name = KNOWN.get(sid[:8]) or (f"{g.get('name')} v{g.get('version')}" if g else "?")
        print(f"   {c['column_id']} {sid[:8]} {c.get('miner_hotkey', '')[:6]} {name}")
