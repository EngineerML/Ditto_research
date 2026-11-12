import json, sys
d = sys.argv[1].rstrip("/") + "/"
for f in ("overhorizoner_3", "dan0l_53", "beast-d41_9", "Tessellate_5", "DrPresident_44"):
    for s in json.load(open(d + f"scores_{f}.json"))["scores"]:
        bd = s["dueling_breakdown"]; pc = s["gate_evidence"].get("priced_cost", {})
        print(f"{f:16} s{bd['season_index']} cost {pc.get('cost_usd')} pf {bd['priced_cost_factor']} other {bd['other_gate_factor']} "
              f"meta {s['metamorphic_consistency']} over {s['memory_over_call']} ptok {pc.get('prompt_tokens')} ctok {pc.get('completion_tokens')} emb {pc.get('embedding_tokens')}")
