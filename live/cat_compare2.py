"""Per datagen category mean score over each agent's latest bench-18 runs: ours vs leaders (+ extra ids).

    python live/cat_compare2.py SNAPSHOT [agent_id ...]
"""
import json, sys, subprocess, os
from collections import defaultdict
B = "https://platform-api.heyditto.ai/api/v1/public/agent/"
d = sys.argv[1].rstrip("/") + "/"
lb = json.load(open(d + "public_leaderboard.json"))["entries"]
ids = {"ours3": "c88411ed-5943-4c81-93e9-f6295349e2d1"}
for r in lb[:7]:
    ids[f"{r['agent_name'][:8]}{r['agent_version']}"] = r["agent_id"]
for x in sys.argv[2:]:
    name, aid = x.split("=")
    ids[name] = aid
tab = defaultdict(dict)
summ = {}
for name, aid in ids.items():
    f = d + f"scores_{name}.json"
    if not os.path.exists(f):
        subprocess.run(["curl", "-s", "--max-time", "40", B + aid + "/scores", "-o", f])
    try:
        runs = [s for s in json.load(open(f))["scores"] if s.get("bench_version", 18) == 18][:6]
    except Exception as e:
        print(name, "no scores", e); continue
    acc = defaultdict(list)
    dg = []
    for s in runs:
        bd = s.get("dueling_breakdown") or {}
        dg.append((bd.get("datagen_raw"), bd.get("datagen_gate"), round(s.get("composite") or 0, 3), bd.get("season_index"),
                   round((s.get("priced_cost_microusd") or s.get("run_cost_microusd") or 0) / 1e6, 3), s.get("metamorphic_consistency")))
        for c in s.get("case_results") or []:
            if c.get("kind") in ("memory", "tool", "datagen", None) or True:
                acc[(c["kind"], c["category"])].append(c["score"])
    summ[name] = dg
    for k, v in acc.items():
        tab[k][name] = (sum(v) / len(v), len(v))
for n, dg in summ.items():
    print(n, dg[:4])
names = [n for n in ids if n in summ]
print(f"{'kind/category':52}" + "".join(f"{n[:10]:>11}" for n in names))
def gap(v):
    others = [v[n][0] for n in v if n != "ours3"]
    return (v.get("ours3", (1, 0))[0] - (sorted(others)[len(others) // 2] if others else 1))
for k, v in sorted(tab.items(), key=lambda kv: gap(kv[1])):
    if all(x[0] > 0.97 for x in v.values()):
        continue
    print(f"{(k[0] or '')[:6]+' '+k[1]:52}" + "".join(f"{v[n][0]:>7.2f}/{v[n][1]:<3}" if n in v else f"{'-':>11}" for n in names))
