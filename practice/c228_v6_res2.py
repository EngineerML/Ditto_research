"""Full run report: score fields, gates, cost and the cases under 1."""
import json, sys
R = sys.argv[1] if len(sys.argv) > 1 else "/home/bittensor/ditto/practice/20261115T080014Z_ditto-harness-c228fx2t_full"
d = json.load(open(R + "/report.json"))
def walk(x, path=""):
    if isinstance(x, dict):
        for k, v in x.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                if any(s in k.lower() for s in ("score", "composite", "gate", "factor", "mean", "cost", "accuracy", "metamorphic", "tool", "memory", "usd")):
                    print(f"  {path}{k} = {v}")
            elif isinstance(v, dict):
                walk(v, path + k + ".")
walk(d)
res = None
for k in ("case_results", "results", "cases"):
    for src in (d, d.get("result") or {}, d.get("report") or {}):
        if isinstance(src, dict) and isinstance(src.get(k), list):
            res = src[k]
            break
    if res:
        break
print("top keys", sorted(d)[:30])
if res:
    low = [r for r in res if (r.get("score") if r.get("score") is not None else 1) < 1]
    print("cases", len(res), "below 1:", len(low))
    for r in low:
        print("   ", r.get("kind"), r.get("category"), r.get("score"), str(r.get("notes") or r.get("reason") or "")[:140])
