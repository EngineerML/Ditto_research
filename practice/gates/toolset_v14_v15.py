"""Tool list per request, v14 vs v15 with the connectors removed (DrPresident v22 mock runs on the s45 seeds)."""
import json
from collections import Counter
P = "/home/bittensor/ditto/practice/"
runs = {"4140": ("20261102T034736Z", "20261102T043226Z"), "5451": ("20261102T034915Z", "20261102T043539Z"), "8047": ("20261102T035047Z", "20261102T043724Z")}
def load(stamp):
    return [json.loads(l) for l in open(f"{P}{stamp}_ditto-harness-drp22_full/trace.jsonl")]
for seed, (a, b) in runs.items():
    A, B = load(a), load(b)
    v14 = set(n for t in A for n in t.get("tools") or [])
    by_text = {}
    for t in A:
        by_text.setdefault(t["user_input"], t)
    extra = Counter(); same_order = diff_order = 0; paired = 0; v14_sizes = Counter(); v15_sizes = Counter()
    for t in B:
        tools = t.get("tools") or []
        kept = [n for n in tools if n in v14]
        extra[len(tools) - len(kept)] += 1
        v15_sizes[len(kept)] += 1
        u = by_text.get(t["user_input"])
        if u is not None:
            paired += 1
            if kept == (u.get("tools") or []):
                same_order += 1
            else:
                diff_order += 1
    for t in A:
        v14_sizes[len(t.get("tools") or [])] += 1
    print(f"seed {seed}: v14 distinct tools {len(v14)}; v15 tools not in v14 per request {dict(extra)}")
    print(f"  per-request sizes v14 {dict(v14_sizes)} | v15 after removing non-v14 names {dict(v15_sizes)}")
    print(f"  exactly paired requests {paired}: filtered v15 list == v14 list (names and order) {same_order}, differs {diff_order}")
