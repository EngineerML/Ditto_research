"""Per-generator round history from fetched round files (live/rounds/r*.json): name, version, submission prefix,
score / discriminating / trivial / unsolved per round.
    python3 live/gen_round_history.py [NAME_SUBSTRING ...]
"""
import collections, glob, json, sys
want = [w.lower() for w in sys.argv[1:]]
hist = collections.defaultdict(list)
for f in sorted(glob.glob("/home/bittensor/ditto/live/rounds/r*.json")):
    try:
        d = json.load(open(f))
    except Exception:
        continue
    r = d.get("summary", {}).get("round_index")
    for c in d.get("columns", []):
        if c.get("score") is None or c.get("discriminating") is None:
            continue
        key = (str(c.get("name")), c.get("version"), c["submission_id"][:8])
        hist[key].append((r, c["score"], c["discriminating"], c["trivial"], c["unsolved"]))
for (n, v, s), rows in sorted(hist.items(), key=lambda kv: -max(x[1] for x in kv[1])):
    if want and not any(w in f"{n} {s}".lower() for w in want):
        continue
    mean = sum(x[1] for x in rows) / len(rows)
    print(f"{n[:14]:14} v{v} {s} rounds={len(rows)} mean={mean:.3f}  " + "  ".join(f"{r}:{sc:.3f}/{d}d{t}t{u}u" for r, sc, d, t, u in rows))
