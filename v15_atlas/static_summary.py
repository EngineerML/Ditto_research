#!/usr/bin/env python3
"""Summarise a static bench (static_bench.py output) by family, as markdown plus JSON.

    python3 v15_atlas/static_summary.py .cache/atlas/static_<tag>.jsonl v15_atlas/static_<tag>
"""
import json
import sys
from collections import Counter, defaultdict

rows = [json.loads(line) for line in open(sys.argv[1])]
base = [r for r in rows if r["salt"] == 0]
MEMORY_TOOLS = {"search_memories", "fetch_memories", "search_subjects", "search_memories_in_subjects"}


def share(n, d):
    return f"{100 * n / d:.1f}%" if d else "-"


fam = defaultdict(list)
for r in base:
    fam[(r["kind"], r["family"])].append(r)

summary = {"datasets": len({(r["seed"], r["salt"]) for r in rows}), "seeds_salt0": len({r["seed"] for r in base}), "requests": len(rows), "families": {}}
lines = [f"# Static bench: {sys.argv[1].split('/')[-1]}", "",
         f"{summary['seeds_salt0']} seeds at salt 0 ({len(base)} requests); {summary['datasets']} datasets with salts 1-3 in all.", ""]

left = Counter(r["left_out"] for r in rows)
stayed = Counter(r["stayed"] for r in rows)
lines += ["## Connector step", "", f"- tools left out per request: {dict(left)}", f"- connectors kept as linked by the request: {dict(stayed)}", ""]

lines += ["## Tool families", "", "| family | n | first-stage lane | records-lane share | product note (wrong / right) | live | top request kinds |", "|---|---|---|---|---|---|---|"]
for (kind, name), rs in sorted(fam.items()):
    if kind != "tool":
        continue
    n = len(rs)
    lanes = Counter(r["lane"].split(":")[0] for r in rs)
    reasons = Counter(r["lane"] for r in rs).most_common(2)
    to_records = sum(1 for r in rs if r["lane"].startswith("records") and not set(r["expected"]) <= MEMORY_TOOLS)
    wrong = sum(1 for r in rs if r["product"] and r["product"] not in r["expected"])
    right = sum(1 for r in rs if r["product"] and r["product"] in r["expected"])
    live = sum(r["live"] for r in rs)
    kinds = Counter(r["request_kind"] or "-" for r in rs).most_common(3)
    summary["families"][name] = {"kind": kind, "n": n, "lanes": dict(lanes), "records_unexpected": to_records, "product_wrong": wrong, "product_right": right, "live": live, "kinds": dict(Counter(r["request_kind"] or "-" for r in rs))}
    lines.append(f"| {name} | {n} | {', '.join(f'{k} {v}' for k, v in reasons)} | {share(to_records, n)} | {wrong} / {right} | {live} | {', '.join(f'{k} {v}' for k, v in kinds)} |")

lines += ["", "## Memory families", "", "| family | n | action-lane share (first stage) | product note (wrong) | qtype (top) | qtype empty | top reasons |", "|---|---|---|---|---|---|---|"]
for (kind, name), rs in sorted(fam.items()):
    if kind != "memory":
        continue
    n = len(rs)
    action = sum(1 for r in rs if r["lane"].startswith("action"))
    wrong = sum(1 for r in rs if r["product"])
    qt = Counter(r["qtype"] or "-" for r in rs)
    reasons = Counter(r["lane"] for r in rs).most_common(2)
    summary["families"][name] = {"kind": kind, "n": n, "action_first_stage": action, "product_wrong": wrong, "qtype": dict(qt), "reasons": dict(Counter(r["lane"] for r in rs))}
    lines.append(f"| {name} | {n} | {share(action, n)} | {wrong} | {', '.join(f'{k} {v}' for k, v in qt.most_common(2))} | {share(qt.get('-', 0), n)} | {', '.join(f'{k} {v}' for k, v in reasons)} |")

# salt sensitivity: same seed, salts 0-3, per family distribution of (lane, request_kind, qtype)
salted_seeds = {r["seed"] for r in rows if r["salt"] > 0}
dist = defaultdict(lambda: defaultdict(Counter))
for r in rows:
    if r["seed"] in salted_seeds:
        dist[(r["kind"], r["family"])][r["salt"]][(r["lane"].split(":")[0], r["request_kind"], r["qtype"])] += 1
lines += ["", "## Salt sensitivity", "", f"{len(salted_seeds)} seeds at salts 0-3. Total-variation distance of the (lane, request kind, qtype) mix against salt 0; families above 10%:", "", "| family | salt 1 | salt 2 | salt 3 |", "|---|---|---|---|"]
for key, by_salt in sorted(dist.items()):
    ref = by_salt.get(0)
    if not ref:
        continue
    tv = []
    for salt in (1, 2, 3):
        other = by_salt.get(salt, Counter())
        na, nb = sum(ref.values()), sum(other.values())
        keys = set(ref) | set(other)
        tv.append(0.5 * sum(abs(ref[k] / na - (other[k] / nb if nb else 0)) for k in keys))
    summary["families"].setdefault(key[1], {})["salt_tv"] = [round(x, 3) for x in tv]
    if max(tv) > 0.10:
        lines.append(f"| {key[0]} {key[1]} | {tv[0]:.0%} | {tv[1]:.0%} | {tv[2]:.0%} |")

open(sys.argv[2] + ".md", "w").write("\n".join(lines) + "\n")
json.dump(summary, open(sys.argv[2] + ".json", "w"), indent=1)
print("\n".join(lines[:12]))
print(f"... written {sys.argv[2]}.md and .json")
