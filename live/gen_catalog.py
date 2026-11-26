"""Catalog of downloaded generator sources grouped by miner hotkey: release time, size, languages, top files.
    python3 -I live/gen_catalog.py [--json OUT]
"""
import collections, json, os, sys

DL = "/home/bittensor/ditto/.cache/miner_gens/dl"
rows = []
for d in sorted(os.listdir(DL)):
    meta = {}
    try:
        meta = json.load(open(f"{DL}/{d}/meta.json"))
    except Exception:
        pass
    src = f"{DL}/{d}/src"
    exts, lines, files = collections.Counter(), 0, []
    for base, _, fs in os.walk(src):
        for f in fs:
            p = os.path.join(base, f)
            rel = os.path.relpath(p, src)
            files.append(rel)
            ext = os.path.splitext(f)[1] or f
            exts[ext] += 1
            if ext in (".go", ".py", ".json", ".yaml", ".md", ".txt", ".rs", ".ts"):
                try:
                    lines += sum(1 for _ in open(p, errors="ignore"))
                except Exception:
                    pass
    rows.append({"dir": d, "hotkey": meta.get("miner_hotkey"), "released_at": meta.get("released_at"),
                 "scorer": meta.get("scorer_version"), "files": len(files), "lines": lines,
                 "exts": dict(exts.most_common(4)), "top": sorted({f.split('/')[0] for f in files})[:8]})
by_hk = collections.defaultdict(list)
for r in rows:
    by_hk[r["hotkey"] or "?"].append(r)
for hk, rs in sorted(by_hk.items(), key=lambda kv: min(str(r["released_at"]) for r in kv[1])):
    print(f"== {hk}")
    for r in sorted(rs, key=lambda r: str(r["released_at"])):
        print(f"   {str(r['released_at'])[:16]} {r['dir']:<36} {r['files']:>4} files {r['lines']:>6} lines {r['exts']} {r['scorer']}")
if "--json" in sys.argv:
    json.dump(rows, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1)
