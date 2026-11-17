"""Look inside one fetched generator round: top-level keys, panel standings, and any per-case data.
    python3 live/round_look.py live/rounds/r26131.json
"""
import json, sys
d = json.load(open(sys.argv[1]))
print("keys", list(d))
for s in d.get("standings", []):
    print(f"  panel {s['agent_name']} v{s['agent_version']} id={s['agent_id'][:8]} common_mean={s['common_mean']:.3f} ref={s['reference']} wins={s['wins']}")
for k, v in d.items():
    if k in ("summary", "standings"):
        continue
    if isinstance(v, list) and v:
        print(k, len(v), "first keys", list(v[0]) if isinstance(v[0], dict) else type(v[0]))
    elif isinstance(v, dict):
        print(k, list(v)[:30])
c = d["columns"][0]
print("column keys", list(c))
