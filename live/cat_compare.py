"""Per-category mean score across all validator runs: ours vs leaders."""
import json, sys, subprocess
from collections import defaultdict
B = "https://platform-api.heyditto.ai/api/v1/public/agent/"
d = sys.argv[1].rstrip("/") + "/"
agents = {"ours": d + "scores_overhorizoner_3.json"}
lb = json.load(open(d + "public_leaderboard.json"))
for r in lb["entries"][:4]:
    f = d + f"scores_{r['agent_name']}_{r['agent_version']}.json"
    subprocess.run(["curl", "-s", "--max-time", "30", B + r["agent_id"] + "/scores", "-o", f])
    agents[f"{r['agent_name']}{r['agent_version']}"] = f
tab = defaultdict(dict)
for name, f in agents.items():
    runs = json.load(open(f))["scores"]
    acc = defaultdict(list)
    for s in runs:
        if (s.get("dueling_breakdown") or {}).get("season_index") != 26111:
            continue
        for c in s["case_results"]:
            acc[(c["kind"], c["category"])].append(c["score"])
    for k, v in acc.items():
        tab[k][name] = (sum(v) / len(v), len(v))
names = list(agents)
print(f"{'kind/category':55}" + "".join(f"{n[:12]:>14}" for n in names))
rows = sorted(tab.items(), key=lambda kv: (kv[1].get("ours", (1, 0))[0] - max(v[0] for n, v in kv[1].items() if n != "ours") if len(kv[1]) > 1 else 0))
for k, v in rows:
    print(f"{k[0][:6]+' '+k[1]:55}" + "".join(f"{v[n][0]:>9.2f}({v[n][1]:>3})" if n in v else f"{'-':>14}" for n in names))
