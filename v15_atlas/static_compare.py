#!/usr/bin/env python3
"""Compare two static benches (served text) by family: unexpected first-stage lanes and product notes.

    python3 v15_atlas/static_compare.py .cache/atlas/static_A.jsonl .cache/atlas/static_B.jsonl
"""
import json
import sys
from collections import Counter, defaultdict

MEMORY_TOOLS = {"search_memories", "fetch_memories", "search_subjects", "search_memories_in_subjects"}


def load(path):
    return {(r["seed"], r["id"]): r for r in map(json.loads, open(path))}


a, b = load(sys.argv[1]), load(sys.argv[2])
seeds = len({k[0] for k in a})
stat = defaultdict(lambda: Counter())
changed = Counter()
for key, x in a.items():
    y = b[key]
    fam = (x["kind"], x["family"])
    s = stat[fam]
    s["n"] += 1
    for tag, r in (("a", x), ("b", y)):
        if x["kind"] == "tool" and r["lane"].startswith("records") and not set(r["expected"]) <= MEMORY_TOOLS:
            s[tag + "_unexpected"] += 1
        if x["kind"] == "memory" and r["lane"].startswith("action"):
            s[tag + "_unexpected"] += 1
        if r["product"] and r["product"] not in r["expected"]:
            s[tag + "_product_wrong"] += 1
    if (x["lane"], x["request_kind"], x["product"]) != (y["lane"], y["request_kind"], y["product"]):
        changed[fam] += 1
print(f"{seeds} seeds, {len(a)} requests (served text)")
print("connector step, B: left out", dict(Counter(r["left_out"] for r in b.values())), "kept as linked", dict(Counter(r["stayed"] for r in b.values())))
print("product notes on the wrong tool: A", sum(s["a_product_wrong"] for s in stat.values()), "B", sum(s["b_product_wrong"] for s in stat.values()),
      "| right: A", sum(1 for r in a.values() if r["product"] and r["product"] in r["expected"]), "B", sum(1 for r in b.values() if r["product"] and r["product"] in r["expected"]))
print("requests whose lane/kind/product differ A vs B:", sum(changed.values()), dict(changed.most_common(8)))
print("\nfamilies whose first-stage lane is unexpected in >= 5% (tool -> records lane, memory -> action lane), per run:")
print(f"{'family':<48} {'n/run':>6} {'A %':>6} {'B %':>6}")
for (kind, fam), s in sorted(stat.items(), key=lambda kv: -kv[1]["b_unexpected"] / kv[1]["n"]):
    if s["b_unexpected"] / s["n"] >= 0.05 or s["a_unexpected"] / s["n"] >= 0.05:
        print(f"{kind[:3]} {fam[:44]:<44} {s['n'] / seeds:>6.1f} {100 * s['a_unexpected'] / s['n']:>6.1f} {100 * s['b_unexpected'] / s['n']:>6.1f}")
