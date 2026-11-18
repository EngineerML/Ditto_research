"""Release status of every generator seen in the snapshots' boards and dueling pins: fetches the public source
metadata (no archives) and prints name, version, status, available time, and whether it is downloaded already.
    python3 -I live/gen_release_status.py
"""
import glob, json, os, subprocess
seen = {}
for f in sorted(glob.glob("/home/bittensor/ditto/live/2026-11-1*/generator_board.json")) + \
        sorted(glob.glob("/home/bittensor/ditto/live/2026-11-1*/public_dueling_seasons.json")):
    j = json.load(open(f))
    rows = j.get("entries") or [c for s in j.get("seasons", []) for c in (s.get("pins") or {}).get("columns") or []]
    for g in rows:
        seen[g["submission_id"]] = (g.get("name") or g.get("generator_name"), g.get("version") or g.get("generator_version"))
have = {d.rsplit("_", 1)[-1] for d in os.listdir("/home/bittensor/ditto/.cache/miner_gens/dl")}
B = "https://platform-api.heyditto.ai/api/v1/public/dueling/generator-sources/"
rows = []
for sid, (name, ver) in seen.items():
    out = subprocess.run(["curl", "-s", "--max-time", "20", B + sid], capture_output=True, text=True).stdout
    try:
        m = json.loads(out)
    except Exception:
        m = {"status": "?"}
    keys = {k: m.get(k) for k in m if any(w in k for w in ("status", "avail", "releas", "embargo"))}
    rows.append((str(keys.get("available_at") or keys.get("release_at") or ""), name, ver, sid[:8], keys, sid[:8] in have))
for r in sorted(rows, key=lambda r: r[0]):
    print(f"{str(r[1]):16s} v{r[2]!s:4s} {r[3]} {'HAVE' if r[5] else '    '} {json.dumps(r[4])[:200]}")
