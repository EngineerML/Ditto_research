"""Generator board from a snapshot: score, rounds, and release fields of the top entries.
    python3 live/gen_board_release.py SNAPSHOT_DIR [N]
"""
import json, sys
d = json.load(open(sys.argv[1].rstrip("/") + "/generator_board.json"))
n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
print("fields:", sorted(d["entries"][0]))
for g in d["entries"][:n]:
    extra = {k: g[k] for k in g if any(w in k for w in ("releas", "avail", "created", "submitted", "artifact"))}
    print(f"{g['score']:.3f} {g.get('name')} v{g.get('version')}", json.dumps(extra)[:300])
