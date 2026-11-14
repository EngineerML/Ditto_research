"""Per-generator score profiles from public run data.

Each official run lists its 175 generator-column cases in column order, 35 per column (checked 2026-11-14: the 35-case
blocks equal the published column means in every run). With the revealed season pins, that gives for every pinned
generator the distribution of per-case scores (0 / partial / 1) for every agent that met it. The shape of that
distribution says what kind of case the generator writes: everyone at 0.5 is a two-item list with a hidden second
item; many 0s are traps (a wrong item or a decline is graded 0); 0.33/0.67 are three-item lists.

    python3 live/gen_profiles.py [SNAPSHOT_GLOB ...]      (default: every live/2026-11-1* snapshot)
"""
import collections
import glob
import json
import os
import sys

pattern = sys.argv[1:] or ["/home/bittensor/ditto/live/2026-11-1*/"]
dirs = sorted({d for p in pattern for d in glob.glob(p)})
seasons, boards, runs = {}, {}, {}
for d in dirs:
    try:
        for s in json.load(open(os.path.join(d, "public_dueling_seasons.json")))["seasons"]:
            if s.get("revealed_at"):
                seasons[s["season_index"]] = s
        for g in json.load(open(os.path.join(d, "generator_board.json")))["entries"]:
            boards[g["submission_id"]] = g
    except Exception:
        pass
    for f in glob.glob(os.path.join(d, "s*_*.json")):
        try:
            data = json.load(open(f))
        except Exception:
            continue
        aid = data.get("agent_id") or ""
        for r in data.get("scores") or []:
            bd = r.get("dueling_breakdown") or {}
            key = r.get("run_id") or (aid, bd.get("season_index"), r.get("composite"))
            runs[key] = (aid, os.path.basename(f), r)

names = {}
for d in dirs:
    try:
        for e in json.load(open(os.path.join(d, "public_activity_limit_200.json")))["entries"]:
            names[e["agent_id"]] = f"{e['name']} v{e['version']}"
    except Exception:
        pass

prof = collections.defaultdict(lambda: collections.defaultdict(list))
for aid, fname, r in runs.values():
    bd = r.get("dueling_breakdown") or {}
    s = seasons.get(bd.get("season_index"))
    sl = [c["score"] for c in r.get("case_results") or [] if c.get("category") == "dueling_slice"]
    if not s or len(sl) != 175:
        continue
    pins = (s.get("pins") or {}).get("columns") or []
    agent = names.get(aid) or fname
    for i, c in enumerate(pins[:5]):
        prof[c["submission_id"]][agent].extend(sl[i * 35:(i + 1) * 35])


def gname(sid):
    g = boards.get(sid) or {}
    return f"{g.get('name') or '?'} v{g.get('version') or '?'}"


rows = []
for sid, agents in prof.items():
    allv = [x for v in agents.values() for x in v]
    rows.append((sum(allv) / len(allv), sid, agents, allv))
for mean, sid, agents, allv in sorted(rows):
    c = collections.Counter(round(x, 2) for x in allv)
    zero = c.get(0.0, 0) / len(allv)
    full = sum(v for k, v in c.items() if k >= 1) / len(allv)
    print(f"\n{sid[:8]} {gname(sid):22} runs-cases {len(allv):5}  mean {mean:.2f}  zero {zero:.0%}  full {full:.0%}  values {sorted(c.items())[:6]}")
    for agent, v in sorted(agents.items(), key=lambda kv: -sum(kv[1]) / len(kv[1]))[:9]:
        cc = collections.Counter(round(x, 2) for x in v)
        print(f"     {agent[:20]:20} n{len(v):4} mean {sum(v)/len(v):.2f}  0:{cc.get(0.0, 0):3}  part:{sum(n for k, n in cc.items() if 0 < k < 1):3}  1:{sum(n for k, n in cc.items() if k >= 1):3}")
