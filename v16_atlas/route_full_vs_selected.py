"""Hades-lineage routing on the full catalog against the selector's catalog, over served bench-16 text (no model).

Run inside the harness image, with the served dumps mounted at /served:
    docker run --rm -v $PWD/.cache/served16:/served:ro -v $PWD/v16_atlas:/atlas:ro IMAGE python /atlas/route_full_vs_selected.py 20
Compares, per request, the lane classify() gives and the request kinds request_kinds() gives, and checks that the
tool lists the model is shown are the selector's choice in the same order either way.
"""
import collections
import glob
import json
import sys

sys.path.insert(0, "/srv")
from app.lane import classify, main_clause  # noqa: E402
from app.protocol import ToolDefinition  # noqa: E402
from app.request_kinds import request_kinds  # noqa: E402
from app.surface import Surface  # noqa: E402
from app.toolselect import OFFER, Offer, select  # noqa: E402

limit = int(sys.argv[1]) if len(sys.argv) > 1 else 20
files = sorted(glob.glob("/served/v16_s*.json"))[:limit]
moved = collections.Counter()
kinds_moved = collections.Counter()
order_diff = 0
total = 0
examples = []
for path in files:
    d = json.load(open(path))
    catalog = [ToolDefinition(name=t["name"], description=t.get("description", ""), parameters=t.get("parameters")) for t in d["catalog"]]
    texts = [("tool:" + c["category"], c["prompt"]) for c in d["tool_cases"]] + [("mem:" + c["question_type"], c["question"]) for c in d["memory_cases"]]
    for kind, text in texts:
        total += 1
        chosen, _ = select([{"name": t.name, "description": t.description} for t in catalog], text)
        picked = [t for t in catalog if t.name in set(chosen)]
        lane_full, lane_sel = classify(main_clause(text), catalog), classify(main_clause(text), picked)
        if (lane_full.name, lane_full.reason) != (lane_sel.name, lane_sel.reason):
            moved[(kind, f"{lane_sel.name}:{lane_sel.reason}", f"{lane_full.name}:{lane_full.reason}")] += 1
            if len(examples) < 8:
                examples.append((kind, text[:110]))
        k_full, k_sel = request_kinds(text, [t.name for t in catalog]), request_kinds(text, chosen)
        if k_full != k_sel:
            kinds_moved[(kind, str(k_sel), str(k_full))] += 1
        token = OFFER.set(Offer([t.name for t in catalog], chosen))
        shown_now = [x["function"]["name"] for x in Surface(catalog, text).visible()]
        OFFER.reset(token)
        shown_t1 = [x["function"]["name"] for x in Surface(picked, text).visible()]
        order_diff += shown_now != shown_t1
print(f"{len(files)} seeds, {total} requests")
print(f"shown tool list differs from T1's (names or order): {order_diff}")
print(f"lane differs, selected -> full catalog: {sum(moved.values())}")
for key, n in moved.most_common(20):
    print(f"  {n:>4} {key}")
print(f"request kinds differ: {sum(kinds_moved.values())}")
for key, n in kinds_moved.most_common(20):
    print(f"  {n:>4} {key}")
for e in examples:
    print("   e.g.", e)
